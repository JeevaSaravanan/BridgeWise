"""FastAPI service for query-time ranking and cluster inspection using SIMILAR graph."""
from __future__ import annotations
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
import os
from neo4j import GraphDatabase
from dotenv import load_dotenv
load_dotenv()
from langchain_openai import AzureOpenAIEmbeddings, OpenAIEmbeddings
from pinecone import Pinecone

app = FastAPI(title="Graph Processor API")

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

@app.get('/clusters')
def clusters():
    drv = get_driver()
    with drv.session() as s:
        rows = s.run("MATCH (p:Person) RETURN p.community AS comm, count(*) AS size ORDER BY size DESC")
        return [{"community": r['comm'], "size": r['size']} for r in rows]

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
from precompute_graph import build_company_and_school, build_similar_edges, run_metrics
from similarity_builder import augment_with_embedding_edges

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
    run_metrics(drv, exclude_ids=p.exclude, max_iter=p.max_iter)
    return {'status': 'ok'}

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
