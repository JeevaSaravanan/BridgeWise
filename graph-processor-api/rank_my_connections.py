# rank_my_connections.py
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Tuple

# Types for clarity
Neo4jDriver = object  # Expecting neo4j.GraphDatabase.driver(...)
PineconeIndex = object  # Expecting a .query(...) method (see _pinecone_query_adapter)


# =========================
# Public API
# =========================

@dataclass
class RankedPerson:
    id: str
    name: str
    title: str
    score: float
    components: Dict[str, float]


def rank_my_connections(
    neo4j_driver: Neo4jDriver,
    pinecone_index: PineconeIndex,
    me_id: str,
    query_text: str,
    top_k: int = 20,
    weights: Tuple[float, float, float, float, float] = (0.40, 0.20, 0.15, 0.15, 0.10),
    embed: Optional[Callable[[str], Sequence[float]]] = None,
    pinecone_top_k: int = 1000,
    prefilter: bool = True,
) -> List[RankedPerson]:
    """
    Rank *your connections* (nodes connected to Me via [:KNOWS]) for a natural-language query
    by combining:
      - Pinecone vector similarity (query → person docs)
      - Skill match (Jaccard over goal skills vs p.skills)
      - Job match   (Jaccard over goal job tokens vs p.jobTitleCanonTokens/jobTitleTokens)
      - struct_global: normalized p.bridgePotentialSkills (already in your graph)
      - struct_ego:    ego-bridging on your [:KNOWS] subgraph (computed at query time)

    Scores are combined as:
        bridgeScore = α*vec_sim + β*skill_match + γ*job_match + δ*struct_global + ε*struct_ego

    Args:
        neo4j_driver: Active Neo4j driver (neo4j.GraphDatabase.driver(...)).
        pinecone_index: Pinecone index object exposing .query(...).
        me_id: Person.id for the "Me" node in Neo4j.
        query_text: Natural language query.
        top_k: How many results to return.
        weights: (α, β, γ, δ, ε).
        embed: Callable(text) -> vector of floats. If None, we try sending text directly to .query(text=...).
        pinecone_top_k: How many top Pinecone hits to pull before intersecting with your connections.
        prefilter: If True, apply a quick Neo4j prefilter to reduce candidate set.

    Returns:
        List[RankedPerson] of length up to top_k, sorted by descending score.
    """
    α, β, γ, δ, ε = weights

    # 0) Fetch skills lexicon once (used for query parsing).
    all_skills = _fetch_all_skills(neo4j_driver)

    # 1) Parse query → (goal_skills, goal_job_tokens)
    goal_skills, goal_job_tokens = _parse_query(query_text, all_skills)

    # 2) Candidate set = your connections (optionally prefiltered by simple skill/job conditions).
    candidate_ids = _fetch_candidate_connections(
        neo4j_driver, me_id, goal_skills if prefilter else None, goal_job_tokens if prefilter else None
    )
    if not candidate_ids:
        return []

    # 3) Vector sim from Pinecone; intersect with your candidates; ensure all candidates have a score.
    vec_sim = _pinecone_similarity(
        pinecone_index=pinecone_index,
        query_text=query_text,
        embed=embed,
        top_k=pinecone_top_k,
        allowed_ids=set(candidate_ids),
    )
    for pid in candidate_ids:
        vec_sim.setdefault(pid, 0.0)

    # 4) Pull features for candidates (skills, job tokens, bridgePotentialSkills, name/title).
    feats = _fetch_candidate_features(neo4j_driver, candidate_ids)
    if not feats:
        return []

    # 5) Ego-bridging on your [:KNOWS] ego network (read-only; per-query; no writes).
    struct_ego_raw = _ego_bridging_on_knows(neo4j_driver, me_id)
    # normalize ego coeff on the candidate pool
    struct_ego = _minmax_on_subset(struct_ego_raw, candidate_ids)

    # 6) Compute per-candidate matches + normalize global structure signal
    skill_match: Dict[str, float] = {}
    job_match: Dict[str, float] = {}
    for pid, f in feats.items():
        skill_match[pid] = _jaccard(set(map(str.lower, goal_skills)), set(f.skills))
        job_match[pid] = _jaccard(set(goal_job_tokens), set(f.job_tokens))

    struct_global = _minmax_on_subset({pid: f.bp_skills for pid, f in feats.items()}, candidate_ids)

    # 7) Final score
    scored: List[RankedPerson] = []
    for pid in candidate_ids:
        f = feats.get(pid)
        if not f:
            # If the person disappeared between steps, skip.
            continue
        score = (
            α * vec_sim.get(pid, 0.0)
            + β * skill_match.get(pid, 0.0)
            + γ * job_match.get(pid, 0.0)
            + δ * struct_global.get(pid, 0.0)
            + ε * struct_ego.get(pid, 0.0)
        )
        scored.append(
            RankedPerson(
                id=pid,
                name=f.name or pid,
                title=f.title or "",
                score=round(float(score), 6),
                components={
                    "vec_sim": vec_sim.get(pid, 0.0),
                    "skill_match": skill_match.get(pid, 0.0),
                    "job_match": job_match.get(pid, 0.0),
                    "struct_global": struct_global.get(pid, 0.0),
                    "struct_ego": struct_ego.get(pid, 0.0),
                },
            )
        )

    scored.sort(key=lambda r: r.score, reverse=True)
    return scored[:top_k]


# =========================
# Internals
# =========================

def _tokenize(text: str) -> List[str]:
    # Simple, robust tokenizer; mirrors your title tokenization spirit.
    import re
    if not text:
        return []
    t = text.lower()
    t = re.sub(r"[^a-z0-9\s/+&-]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    if not t:
        return []
    # Split on whitespace and a few separators
    parts = re.split(r"[ \t/+\-&]+", t)
    return [p for p in parts if p]


def _parse_query(goal_text: str, all_skills: Iterable[str]) -> Tuple[List[str], List[str]]:
    """Extract goal skills and job tokens from the query."""
    tokens = _tokenize(goal_text)
    skills_set = {s.lower().strip() for s in all_skills if s and str(s).strip()}
    goal_skills = sorted({t for t in tokens if t in skills_set})

    # heuristic job terms (can extend / externalize)
    role_terms = {
        "engineer", "engineers", "developer", "developers", "manager", "managers",
        "analyst", "analysts", "designer", "designers", "scientist", "scientists",
        "architect", "architects",
        "software", "backend", "front", "frontend", "fullstack", "full-stack", "data",
        "ml", "ai", "qa", "sre", "devops", "security", "mobile", "ios", "android"
    }
    goal_job_tokens = sorted({t for t in tokens if t in role_terms or t.endswith("engineer")})
    return goal_skills, goal_job_tokens


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return (inter / union) if union else 0.0


def _minmax_on_subset(values: Dict[str, float], subset: Iterable[str]) -> Dict[str, float]:
    """Min-max normalize a dict but only over the given subset of keys."""
    sub = [values.get(k, 0.0) for k in subset]
    if not sub:
        return {k: 0.0 for k in subset}
    mn, mx = min(sub), max(sub)
    if mx <= mn:
        return {k: 0.0 for k in subset}
    return {k: (values.get(k, 0.0) - mn) / (mx - mn) for k in subset}


# ---------- Neo4j fetchers ----------

def _fetch_all_skills(driver: Neo4jDriver) -> List[str]:
    """Return the distinct skills vocabulary across all persons."""
    q = """
    MATCH (p:Person) UNWIND coalesce(p.skills, []) AS s
    WITH toLower(trim(s)) AS s
    WHERE s IS NOT NULL AND s <> ''
    RETURN collect(DISTINCT s) AS allSkills
    """
    with driver.session() as s:
        rec = s.run(q).single()
        return list(rec["allSkills"] if rec and rec["allSkills"] else [])


def _fetch_candidate_connections(
    driver: Neo4jDriver,
    me_id: str,
    goal_skills: Optional[List[str]],
    goal_job_tokens: Optional[List[str]],
) -> List[str]:
    """Return IDs of people connected to Me via [:KNOWS], optionally prefiltered."""
    # If no prefilter, return all connections.
    if not goal_skills and not goal_job_tokens:
        q = """
        MATCH (me:Person {id:$meId})-[:KNOWS]-(p:Person)
        RETURN DISTINCT p.id AS id
        """
        with driver.session() as s:
            return [r["id"] for r in s.run(q, meId=me_id)]

    q = """
    MATCH (me:Person {id:$meId})-[:KNOWS]-(p:Person)
    WITH DISTINCT p
    WHERE
      ($useSkills AND any(s IN coalesce(p.skills,[]) WHERE toLower(s) IN $skillList))
      OR
      ($useJobs AND size([t IN coalesce(p.jobTitleCanonTokens,[]) WHERE t IN $jobTokens]) > 0)
    RETURN p.id AS id
    """
    params = {
        "meId": me_id,
        "useSkills": bool(goal_skills),
        "skillList": [x.lower() for x in (goal_skills or [])],
        "useJobs": bool(goal_job_tokens),
        "jobTokens": goal_job_tokens or [],
    }
    with driver.session() as s:
        return [r["id"] for r in s.run(q, **params)]


@dataclass
class _PersonFeatures:
    skills: List[str]
    job_tokens: List[str]
    bp_skills: float
    name: str
    title: str


def _fetch_candidate_features(driver: Neo4jDriver, cand_ids: List[str]) -> Dict[str, _PersonFeatures]:
    if not cand_ids:
        return {}
    q = """
    MATCH (p:Person) WHERE p.id IN $cand
    RETURN p.id AS id,
           [x IN coalesce(p.skills, []) WHERE x IS NOT NULL] AS skills,
           CASE
               WHEN size(coalesce(p.jobTitleCanonTokens,[])) > 0
                 THEN [x IN p.jobTitleCanonTokens WHERE x IS NOT NULL]
               ELSE [x IN coalesce(p.jobTitleTokens,[]) WHERE x IS NOT NULL]
           END AS jobTokens,
           coalesce(p.bridgePotentialSkills, 0.0) AS bpSkills,
           coalesce(p.full_name, p.raw.fullName, p.id) AS name,
           coalesce(p.jobTitleCanon, p.raw.title, "") AS title
    """
    with driver.session() as s:
        rows = list(s.run(q, cand=cand_ids))
    out: Dict[str, _PersonFeatures] = {}
    for r in rows:
        pid = r["id"]
        skills = [str(x).lower() for x in r["skills"] or []]
        jobt = [str(x).lower() for x in r["jobTokens"] or []]
        out[pid] = _PersonFeatures(
            skills=skills,
            job_tokens=jobt,
            bp_skills=float(r["bpSkills"] or 0.0),
            name=str(r["name"] or pid),
            title=str(r["title"] or ""),
        )
    return out


def _ego_bridging_on_knows(driver: Neo4jDriver, me_id: str) -> Dict[str, float]:
    """
    Compute a bridge-coefficient-like value IN YOUR EGO NETWORK only ([:KNOWS]).
    Returns dict person_id -> egoBridgeCoeff (not normalized).
    """
    q = """
    MATCH (me:Person {id:$meId})-[:KNOWS]-(x:Person)
    WITH collect(DISTINCT x) AS ego
    UNWIND ego AS p
    OPTIONAL MATCH (p)-[:KNOWS]-(n) WHERE n IN ego
    WITH p, collect(DISTINCT n) AS neigh
    WITH p, neigh, size([x IN neigh WHERE x IS NOT NULL]) AS deg
    UNWIND neigh AS neighbor
    OPTIONAL MATCH (neighbor)-[:KNOWS]-(m) WHERE m IN ego
    WITH p, deg, neighbor, count(DISTINCT m) AS ndegr
    WITH p, deg, collect(ndegr) AS neighDegs
    WITH p.id AS id, deg,
         reduce(s=0.0, d IN neighDegs | s + CASE WHEN d>0 THEN 1.0/d ELSE 0.0 END) AS invSum
    RETURN id,
           CASE WHEN deg>0 AND invSum>0 THEN (1.0/deg) * (1.0/invSum) ELSE 0.0 END AS egoBridgeCoeff
    """
    with driver.session() as s:
        return {r["id"]: float(r["egoBridgeCoeff"] or 0.0) for r in s.run(q, meId=me_id)}


# ---------- Pinecone adapter ----------

def _pinecone_similarity(
    pinecone_index: PineconeIndex,
    query_text: str,
    embed: Optional[Callable[[str], Sequence[float]]],
    top_k: int,
    allowed_ids: Optional[Iterable[str]] = None,
) -> Dict[str, float]:
    """
    Query Pinecone for vector similarity and return {id: score} in [0,1].
    Works with:
      - vector query: index.query(vector=[...], top_k=..., include_metadata=False)
      - text query (if supported by your client): index.query(text="...", top_k=...)

    Filters to allowed_ids if provided.
    """
    allowed = set(allowed_ids) if allowed_ids is not None else None

    # Try vector first if embed is provided; else try text query.
    matches: List[Dict[str, float]] = []

    try:
        if embed is not None:
            vec = embed(query_text)
            res = pinecone_index.query(vector=_ensure_list_floats(vec), top_k=top_k, include_metadata=False)
        else:
            # Some Pinecone SDKs support text queries directly; if not, users should pass embed=...
            res = pinecone_index.query(text=query_text, top_k=top_k, include_metadata=False)
        matches = _extract_matches(res)
    except Exception as e:
        # As a fallback: if embed wasn't provided and text query failed, raise a clear error.
        if embed is None:
            raise RuntimeError(
                "Pinecone query failed and no 'embed' function was provided. "
                "Pass embed=... to supply a query embedding function."
            ) from e
        raise

    out: Dict[str, float] = {}
    for m in matches:
        pid = str(m.get("id"))
        sc = float(m.get("score", 0.0))
        if allowed is None or pid in allowed:
            out[pid] = sc
    return out


def _extract_matches(res_obj) -> List[Dict[str, float]]:
    """
    Normalize different Pinecone client response shapes to a list of {id, score}.
    Known variants:
      - {"matches": [{"id": "...", "score": 0.87}, ...]}
      - .get("results")[0].get("matches") ...
    """
    if res_obj is None:
        return []
    # Direct dict style
    if isinstance(res_obj, dict) and "matches" in res_obj:
        return [{"id": m.get("id"), "score": m.get("score", 0.0)} for m in (res_obj.get("matches") or [])]

    # Some SDKs return pydantic-like objects
    maybe = getattr(res_obj, "matches", None)
    if maybe is not None:
        return [{"id": getattr(m, "id", None), "score": getattr(m, "score", 0.0)} for m in (maybe or [])]

    # Results wrapper
    results = None
    if isinstance(res_obj, dict):
        results = res_obj.get("results")
    else:
        results = getattr(res_obj, "results", None)
    if results:
        # take first result's matches
        m = results[0].get("matches") if isinstance(results[0], dict) else getattr(results[0], "matches", None)
        if m:
            return [{"id": getattr(x, "id", x.get("id")), "score": getattr(x, "score", x.get("score", 0.0))} for x in m]

    return []


def _ensure_list_floats(vec: Sequence[float]) -> List[float]:
    # Defensive conversion
    out: List[float] = []
    for v in vec:
        try:
            out.append(float(v))
        except Exception:
            out.append(0.0)
    return out


# =========================
# Optional CLI for quick manual tests
# =========================
if __name__ == "__main__":
    """
    Minimal CLI usage example (requires env + real embed() wired by you).

    Example:
        export NEO4J_URI="bolt://localhost:7687"
        export NEO4J_USER="neo4j"
        export NEO4J_PASS="password"
        export PINECONE_API_KEY="..."
        export PINECONE_INDEX="people-index"
        export ME_ID="user_123"
        python -m rank_my_connections "who in my connections are software engineers with python"
    """
    import os
    import sys
    from neo4j import GraphDatabase

    try:
        from pinecone import Pinecone  # pip install pinecone-client
    except Exception:
        Pinecone = None  # type: ignore

    def _die(msg: str, code: int = 2):
        print(msg, file=sys.stderr)
        sys.exit(code)

    if len(sys.argv) < 2:
        _die("Provide a query string, e.g.: python -m rank_my_connections 'software engineers with python'")

    query_text = " ".join(sys.argv[1:])
    me_id = os.environ.get("ME_ID") or _die("Set ME_ID env var (your Person.id in Neo4j)")

    # Neo4j
    uri = os.environ.get("NEO4J_URI") or _die("Set NEO4J_URI env var")
    user = os.environ.get("NEO4J_USER", "neo4j")
    pwd = os.environ.get("NEO4J_PASS") or _die("Set NEO4J_PASS env var")
    driver = GraphDatabase.driver(uri, auth=(user, pwd))

    # Pinecone
    if Pinecone is None:
        _die("Install pinecone-client and set PINECONE_API_KEY/PINECONE_INDEX to use the CLI runner.")

    api_key = os.environ.get("PINECONE_API_KEY") or _die("Set PINECONE_API_KEY env var")
    index_name = os.environ.get("PINECONE_INDEX") or _die("Set PINECONE_INDEX env var")
    pc = Pinecone(api_key=api_key)
    index = pc.Index(index_name)

    # You MUST plug in your real embedding here (OpenAI, local model, etc.)
    def embed_fn(text: str) -> List[float]:
        raise NotImplementedError(
            "Replace embed_fn with your real embedding function, e.g., OpenAI text-embedding-3-large."
        )

    results = rank_my_connections(
        neo4j_driver=driver,
        pinecone_index=index,
        me_id=me_id,
        query_text=query_text,
        top_k=10,
        weights=(0.40, 0.20, 0.15, 0.15, 0.10),
        embed=embed_fn,  # or None if your Pinecone client supports text=... queries directly
        pinecone_top_k=1000,
    )

    for i, r in enumerate(results, 1):
        c = r.components
        print(f"{i:>2}. {r.name} — {r.title}  [score={r.score:.3f}]")
        print(f"    vec={c['vec_sim']:.2f}  skill={c['skill_match']:.2f}  job={c['job_match']:.2f}  "
              f"g-struct={c['struct_global']:.2f}  ego-struct={c['struct_ego']:.2f}")
