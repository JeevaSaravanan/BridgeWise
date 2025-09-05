"""Graph Processor API
======================

FastAPI service for query-time ranking, connection-centric ranking, cluster
inspection and shortest introduction paths on the BridgeWise graph.

Endpoints
---------
GET  /health                        -> { status: "ok" }
GET  /clusters                      -> List clusters with sizes
GET  /clusters/summary?top_n=5      -> Top skills & titles per cluster
GET  /clusters/{cid}?limit=100      -> Members (id,name,title,company,bridgePotential)
GET  /person/{pid}                  -> Basic person info + community + bridgePotential
POST /rank                          -> Vector + bridgePotential ranking over whole graph
POST /recompute                     -> Rebuild SIMILAR edges & metrics (see RecomputePayload)
POST /rank-connections              -> Rank a user's own connections (multi-signal, optional debug)
POST /rank-connections/explain      -> Parse query & show candidate pool stats
POST /rank-connections/batch        -> Batch variant of /rank-connections for multiple queries
GET  /intro-path?src=..&dst=..      -> Shortest KNOWS path (ids + hop count)

Models (request bodies)
-----------------------
RankRequest:
    query: str
    top_k: int = 10
    exclude: List[str] = []

RecomputePayload:
    min_shared_skills: int = 2
    weight_mode: str = 'count'
    boost_company: float = 1.0
    boost_school: float = 0.5
    exclude: List[str] = [] (ids to exclude from metrics graph)
    max_iter: int = 20
    embed_top_k: int = 0 (optional extra embedding-derived edges)
    embed_scale: float = 1.0

RankConnectionsRequest (multi-signal weights order vec,skill,job,struct_global,struct_ego):
    me_id: str
    query: str
    top_k: int = 20
    pinecone_top_k: int = 1000
    prefilter: bool = True (quick Neo4j filter by skills/job tokens before vector step)
    w_vec: float = 0.40
    w_skill: float = 0.20
    w_job: float = 0.15
    w_struct_global: float = 0.15
    w_struct_ego: float = 0.10
    rescale_top: float | None = 0.8 (normalize max score)
    debug: bool = False (include parse + candidate stats)

RankConnectionsExplainRequest:
    me_id: str
    query: str
    pinecone_top_k: int = 200 (currently not used directly; reserved for future)
    prefilter: bool = True
    sample: int = 10 (return first N candidate IDs)

RankConnectionsBatchRequest:
    me_id: str
    queries: List[str]
    top_k: int = 10
    pinecone_top_k: int = 500
    prefilter: bool = True
    same weight & rescale fields as RankConnectionsRequest

Notes
-----
* Vector similarity uses Pinecone; embeddings via Azure OpenAI (if deployment provided)
    else OpenAI model defined by OPENAI_EMBED_MODEL (default 'text-embedding-3-small').
* Connection ranking combines: vec_sim + skill_match + job_match + global structure
    (bridgePotentialSkills/Job + betweenness proxies) + ego bridging coefficient.
* /recompute triggers metrics recalculation across both skill and job similarity graphs.
* /intro-path leverages shortestPath over [:KNOWS] with a bounded depth.
"""
from __future__ import annotations
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any
import os
from neo4j import GraphDatabase
from dotenv import load_dotenv
load_dotenv()
from langchain_openai import AzureOpenAIEmbeddings, OpenAIEmbeddings
from pinecone import Pinecone

app = FastAPI(title="Graph Processor API")

# Add CORS middleware to allow cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

# --- helpers ---

def get_driver():
    uri = os.getenv('NEO4J_URI'); user = os.getenv('NEO4J_USER','neo4j'); pw = os.getenv('NEO4J_PASS')
    if not uri or not pw: raise EnvironmentError('Missing Neo4j env vars')
    return GraphDatabase.driver(uri, auth=(user, pw))

def get_embedder():
    dep = os.getenv('AZURE_OPENAI_EMBED_DEPLOYMENT')
    if dep: return AzureOpenAIEmbeddings(azure_deployment=dep)
    return OpenAIEmbeddings(model=os.getenv('OPENAI_EMBED_MODEL','text-embedding-3-small'))

def get_pinecone():
    api_key = os.getenv('PINECONE_API_KEY'); region = os.getenv('PINECONE_REGION') or os.getenv('PINECONE_ENV'); idx = os.getenv('PINECONE_INDEX_NAME')
    if not api_key or not region or not idx: raise EnvironmentError('Missing Pinecone env vars')
    pc = Pinecone(api_key=api_key)
    names = pc.list_indexes().names()
    if idx not in names: raise RuntimeError(f"Index {idx} not found")
    return pc, idx

# --- models ---
class RankRequest(BaseModel):
    query: str
    top_k: int = 10
    exclude: List[str] = []

class RecomputeRequest(BaseModel):
    min_shared_skills: int = 2
    weight_mode: str = 'count'
    boost_company: float = 1.0
    boost_school: float = 0.5
    exclude: List[str] = []
    max_iter: int = 20

# --- endpoints ---
@app.get('/health')
def health(): return {'status':'ok'}

@app.get('/connections')
def connections():
    drv = get_driver()
    with drv.session() as s:
        rows = s.run("MATCH (p:Person) RETURN p.community AS comm, count(*) AS size ORDER BY size DESC")
        return [{"community": r['comm'], "size": r['size']} for r in rows]

@app.get('/clusters')
def clusters():
    """Return job titles and their counts, ordered by count in descending order."""
    drv = get_driver()
    with drv.session() as s:
        rows = s.run(
            """
            MATCH (p:Person)
            RETURN p.jobTitleCanon AS jobTitle, COUNT(*) AS totalCount
            ORDER BY totalCount DESC
            """
        )
        return [{"jobTitle": r['jobTitle'], "totalCount": r['totalCount']} for r in rows]

@app.get('/clusters/summary')
def cluster_summary(top_n: int = 5):
    drv = get_driver()
    with drv.session() as s:
        # Pure Cypher frequency ordering without APOC
        rows = s.run(
            """
            MATCH (p:Person)
            WITH p.community AS comm, collect(p) AS members
            WITH comm, members, size(members) AS size
            UNWIND members AS m
            UNWIND m.skills AS sskill
            WITH comm, size, toLower(sskill) AS skill
            WHERE skill IS NOT NULL AND skill <> ''
            WITH comm, size, skill, count(*) AS sc
            ORDER BY comm, sc DESC, skill
            WITH comm, size, collect(skill)[0..$topN] AS topSkills
            MATCH (m2:Person {community: comm})
            WITH comm, size, topSkills,
                 CASE WHEN m2.title IS NOT NULL AND trim(m2.title)<>'' THEN toLower(m2.title) ELSE toLower(split(m2.description,'|')[0]) END AS rawTitle
            WHERE rawTitle IS NOT NULL AND trim(rawTitle)<>''
            WITH comm, size, topSkills, rawTitle, count(*) AS tc
            ORDER BY comm, tc DESC, rawTitle
            WITH comm, size, topSkills, collect(rawTitle)[0..$topN] AS topTitles
            RETURN comm AS community, size, topSkills, topTitles
            ORDER BY size DESC
            """,
            topN=top_n
        )
        return [dict(r) for r in rows]

@app.get('/clusters/{cid}')
def cluster_members(cid: int, limit: int = 100):
    drv = get_driver()
    with drv.session() as s:
        rows = s.run(
            """
            MATCH (p:Person {community:$c})
            RETURN p.id AS id, p.name AS name, p.title AS title, p.company AS company, p.bridgePotential AS bridgePotential
            ORDER BY bridgePotential DESC LIMIT $limit
            """,
            c=cid, limit=limit
        )
        return [dict(r) for r in rows]

@app.get('/person/{pid}')
def person(pid: str):
    drv = get_driver()
    with drv.session() as s:
        row = s.run("MATCH (p:Person {id:$id}) RETURN p.id AS id, p.name AS name, p.community AS community, p.bridgePotential AS bridgePotential", id=pid).single()
        if not row: raise HTTPException(404, 'Not found')
        return dict(row)

@app.post('/rank')
def rank(req: RankRequest):
    embedder = get_embedder(); pc, idx = get_pinecone(); index = pc.Index(idx)
    vec = embedder.embed_documents([req.query])[0]
    resp = index.query(vector=vec, top_k=req.top_k, include_metadata=True)
    matches = []
    excluded = set(req.exclude)
    for m in resp.get('matches', []):
        pid = m.get('id');
        if pid in excluded: continue
        matches.append({'person_id': pid, 'similarity': m.get('score'), 'metadata': m.get('metadata', {})})
    if not matches: return {'people': [], 'communities': {}}
    drv = get_driver()
    ids = [m['person_id'] for m in matches]
    with drv.session() as s:
        rows = s.run(
            """
            UNWIND $ids AS pid
            MATCH (p:Person {id: pid})
            RETURN p.id AS id, p.community AS community, coalesce(p.bridgePotential,0.0) AS bridgePotential
            """,
            ids=ids
        )
        props = {r['id']: {'community': r['community'], 'bridgePotential': r['bridgePotential']} for r in rows}
    for m in matches:
        prop = props.get(m['person_id'], {'community': None, 'bridgePotential': 0.0})
        m['community'] = prop['community']
        m['bridgePotential'] = prop['bridgePotential']
        m['bridgeScore'] = (m['similarity'] or 0.0) * prop['bridgePotential']
    matches.sort(key=lambda x: x['bridgeScore'], reverse=True)
    grouped: Dict[Any, List[Dict[str, Any]]] = {}
    for m in matches:
        grouped.setdefault(m['community'], []).append(m)
    return {'people': matches, 'communities': grouped}

# Recompute endpoint defers to precompute script logic (import for reuse if desired)
from precompute_graph import build_company_and_school, build_similar_edges, run_metrics_both_graphs
from similarity_builder import augment_with_embedding_edges
from rank_my_connections import rank_my_connections
from rank_my_connections import _parse_query as _rmc_parse_query, _fetch_all_skills as _rmc_fetch_all_skills, _fetch_candidate_connections as _rmc_fetch_candidate_connections

class RecomputePayload(BaseModel):
    min_shared_skills: int = 2
    weight_mode: str = 'count'
    boost_company: float = 1.0
    boost_school: float = 0.5
    exclude: List[str] = []
    max_iter: int = 20
    embed_top_k: int = 0
    embed_scale: float = 1.0

@app.post('/recompute')
def recompute(p: RecomputePayload):
    drv = get_driver()
    build_company_and_school(drv)
    build_similar_edges(drv, min_shared_skills=p.min_shared_skills, weight_mode=p.weight_mode, boost_company=p.boost_company, boost_school=p.boost_school)
    if p.embed_top_k > 0:
        augment_with_embedding_edges(drv, top_k=p.embed_top_k, scale=p.embed_scale)
    run_metrics_both_graphs(drv, exclude_ids=p.exclude, max_iter=p.max_iter)
    return {'status': 'ok'}

class RankConnectionsRequest(BaseModel):
    me_id: str
    query: str
    top_k: int = 20
    pinecone_top_k: int = 1000
    prefilter: bool = True
    # weight order matches rank_my_connections weights tuple (vec, skill, job, struct_global, struct_ego)
    w_vec: float = 0.40
    w_skill: float = 0.20
    w_job: float = 0.15
    w_struct_global: float = 0.15
    w_struct_ego: float = 0.10
    rescale_top: float | None = 0.8
    debug: bool = False

class RankConnectionsBatchRequest(BaseModel):
    me_id: str
    queries: List[str]
    top_k: int = 10
    pinecone_top_k: int = 500
    prefilter: bool = True
    w_vec: float = 0.40
    w_skill: float = 0.20
    w_job: float = 0.15
    w_struct_global: float = 0.15
    w_struct_ego: float = 0.10
    rescale_top: float | None = 0.8

class RankConnectionsExplainRequest(BaseModel):
    me_id: str
    query: str
    pinecone_top_k: int = 200
    prefilter: bool = True
    sample: int = 10


@app.post('/rank-connections')
def rank_connections(req: RankConnectionsRequest):
    """Rank a user's existing network connections for a natural language query.

    Returns list of RankedPerson dicts (id, name, title, score, components) sorted by score.
    """
    # Pinecone index reuse from /rank logic
    embedder = get_embedder()
    pc, idx = get_pinecone(); index = pc.Index(idx)

    def _embed_once(text: str):
        # embed_documents returns List[List[float]]; embed_query returns List[float] in some versions
        try:
            return embedder.embed_query(text)
        except Exception:
            return embedder.embed_documents([text])[0]

    drv = get_driver()
    people = rank_my_connections(
        neo4j_driver=drv,
        pinecone_index=index,
        me_id=req.me_id,
        query_text=req.query,
        top_k=req.top_k,
        embed=_embed_once,
        pinecone_top_k=req.pinecone_top_k,
    )
    out = {'results': [p.__dict__ for p in people]}
    print("out:", out)
    if req.debug:
        # replicate some internal steps for transparency
        all_skills = _rmc_fetch_all_skills(drv)
        goal_skills, goal_job_tokens = _rmc_parse_query(req.query, all_skills)
        cands = _rmc_fetch_candidate_connections(drv, req.me_id, goal_skills if req.prefilter else None, goal_job_tokens if req.prefilter else None)
        out['debug'] = {
            'goal_skills': goal_skills,
            'goal_job_tokens': goal_job_tokens,
            'candidate_count': len(cands),
        }
    return out

@app.post('/rank-connections/explain')
def rank_connections_explain(req: RankConnectionsExplainRequest):
    drv = get_driver()
    all_skills = _rmc_fetch_all_skills(drv)
    goal_skills, goal_job_tokens = _rmc_parse_query(req.query, all_skills)
    cands = _rmc_fetch_candidate_connections(drv, req.me_id, goal_skills if req.prefilter else None, goal_job_tokens if req.prefilter else None)
    sample_ids = cands[: req.sample]
    return {
        'query': req.query,
        'goal_skills': goal_skills,
        'goal_job_tokens': goal_job_tokens,
        'candidate_count': len(cands),
        'candidate_sample': sample_ids,
    }

@app.post('/rank-connections/batch')
def rank_connections_batch(req: RankConnectionsBatchRequest):
    if not req.queries:
        return {'results': []}
    embedder = get_embedder()
    pc, idx = get_pinecone(); index = pc.Index(idx)

    def _embed_once(text: str):
        try:
            return embedder.embed_query(text)
        except Exception:
            return embedder.embed_documents([text])[0]

    drv = get_driver()
    weights = (req.w_vec, req.w_skill, req.w_job, req.w_struct_global, req.w_struct_ego)
    out = []
    for q in req.queries:
        people = rank_my_connections(
            neo4j_driver=drv,
            pinecone_index=index,
            me_id=req.me_id,
            query_text=q,
            top_k=req.top_k,
            weights=weights,
            embed=_embed_once,
            pinecone_top_k=req.pinecone_top_k,
            prefilter=req.prefilter,
            rescale_top=req.rescale_top,
        )
        out.append({'query': q, 'results': [p.__dict__ for p in people]})
    return {'results': out}

@app.post('/rank-connections/graph')
def rank_connections_graph(req: RankConnectionsRequest):
    """Return graph (nodes + links) for the ranked connections subgraph.

    On error returns {error: str}. Nodes: me + top_k ranked people. Links: existing KNOWS edges.
    """
    try:
        embedder = get_embedder(); pc, idx = get_pinecone(); index = pc.Index(idx)

        def _embed_once(text: str):
            try:
                return embedder.embed_query(text)
            except Exception:
                return embedder.embed_documents([text])[0]

        drv = get_driver()
        try:
            ranked = rank_my_connections(
                neo4j_driver=drv,
                pinecone_index=index,
                me_id=req.me_id,
                query_text=req.query,
                top_k=req.top_k,
                pinecone_top_k=req.pinecone_top_k,
                embed=_embed_once,
            )
        except Exception as embed_err:
            # Fallback: return simple first-degree ego network (limited) with error note
            with drv.session() as s:
                ego_rows = s.run(
                    """
                    MATCH (me:Person {id:$me})-[:KNOWS]-(p:Person)
                    RETURN me.id AS me_id, collect(p.id)[0..50] AS nbrs
                    """,
                    me=req.me_id
                ).single()
                nbr_ids = ego_rows['nbrs'] if ego_rows else []
                keep_ids = {req.me_id} | set(nbr_ids)
                nodes = []
                info_rows = s.run(
                    """
                    UNWIND $ids AS pid
                    MATCH (p:Person {id:pid})
                    RETURN p.id AS id, p.name AS name, p.title AS title, p.skills AS skills,p.company AS company, coalesce(p.bridgePotential,0) AS bridgePotential
                    """,
                    ids=list(keep_ids)
                )
                for r in info_rows:
                    d = dict(r); d['isMe'] = (d['id']==req.me_id); d['score'] = 1.0 if d['isMe'] else 0.0; nodes.append(d)
                link_rows = s.run(
                    """
                    UNWIND $ids AS a
                    UNWIND $ids AS b
                    WITH a,b WHERE a < b
                    MATCH (p1:Person {id:a})-[:KNOWS]-(p2:Person {id:b})
                    RETURN p1.id AS source, p2.id AS target
                    """,
                    ids=list(keep_ids)
                )
                links = [dict(x) for x in link_rows]
            return {'nodes': nodes, 'links': links, 'fallback': True, 'error': f"embed_fail: {embed_err}"}
        keep_ids = {req.me_id} | {p.id for p in ranked}
        nodes = []
        with drv.session() as s:
            rows = s.run(
                """
                UNWIND $ids AS pid
                MATCH (p:Person {id: pid})
                RETURN p.id AS id, p.name AS name, p.title AS title, p.company AS company, p.skills AS skills, coalesce(p.bridgePotential,0) AS bridgePotential
                """,
                ids=list(keep_ids)
            )
            for r in rows:
                nodes.append(dict(r))
            edge_rows = s.run(
                """
                UNWIND $ids AS a
                UNWIND $ids AS b
                WITH a,b WHERE a < b
                MATCH (p1:Person {id:a})-[:KNOWS]-(p2:Person {id:b})
                RETURN p1.id AS source, p2.id AS target
                """,
                ids=list(keep_ids)
            )
            links = [dict(er) for er in edge_rows]
        score_map = {p.id: p.score for p in ranked}
        for n in nodes:
            n['score'] = score_map.get(n['id'], 1.0 if n['id']==req.me_id else 0.0)
            n['isMe'] = (n['id'] == req.me_id)
        return { 'nodes': nodes, 'links': links }
    except Exception as e:
        return JSONResponse(status_code=500, content={'error': str(e)})

@app.get('/intro-path')
def intro_path(src: str, dst: str, max_depth: int = 4):
    """Return a simple shortest KNOWS path (up to max_depth) between two people for warm intro."""
    drv = get_driver()
    with drv.session() as s:
        rec = s.run(
            """
            MATCH (a:Person {id:$src}), (b:Person {id:$dst})
            MATCH p = shortestPath((a)-[:KNOWS*..$d]-(b))
            RETURN [n IN nodes(p) | n.id] AS nodeIds, length(p) AS hops
            """,
            src=src, dst=dst, d=max_depth
        ).single()
        if not rec:
            return {"path": [], "hops": None}
        return {"path": rec["nodeIds"], "hops": rec["hops"]}
