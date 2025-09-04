from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Tuple, Set
import functools

# Types for clarity
Neo4jDriver = object  # Expecting neo4j.GraphDatabase.driver(...)
PineconeIndex = object  # Expecting a .query(...) method (see _pinecone_query_adapter)

# -------------------------
# Role roots constant
#
# These represent the singular forms of job-related tokens used both when
# parsing queries and when expanding candidate job tokens. Plural forms
# are derived automatically in ``_parse_query``.
_ROLE_ROOTS = {
    "engineer", "developer", "manager", "analyst", "designer", "scientist",
    "architect", "software", "backend", "front", "frontend", "fullstack",
    "full-stack", "data", "ml", "ai", "qa", "sre", "devops",
    "security", "mobile", "ios", "android"
}


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


_CACHE_SKILLS: List[str] | None = None
_CACHE_COMPANIES: List[str] | None = None
_SCHEMA_HAS_COMPANY: Optional[bool] = None  # cache detection of Company label / WORKED_AT


def rank_my_connections(
    neo4j_driver: Neo4jDriver,
    pinecone_index: PineconeIndex,
    me_id: str,
    query_text: str,
    top_k: int = 20,
    # We now optionally accept a 6th weight for company_match; default keep previous distribution
    # If 5 weights passed we derive company weight as 0 (ignored)
    weights: Tuple[float, ...] = (0.40, 0.18, 0.14, 0.14, 0.09, 0.05),
    embed: Optional[Callable[[str], Sequence[float]]] = None,
    pinecone_top_k: int = 1000,
    prefilter: bool = True,
    rescale_top: Optional[float] = 0.8,
) -> List[RankedPerson]:
    """
    Rank *your connections* (nodes connected to Me via [:KNOWS]) for a natural-language query
    by combining:
      - Pinecone vector similarity (query → person docs)
      - Skill match (Jaccard over goal skills vs p.skills)
      - Job match   (Jaccard over goal job tokens vs p.jobTitleCanonTokens/jobTitleTokens)
      - struct_global: normalized sum of p.bridgePotentialSkills and p.bridgePotentialJob (already in your graph)
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
    # Unpack weights with backward compatibility
    if len(weights) == 5:
        α, β, γ, δ, ε = weights
        ζ = 0.0  # company_match disabled
    elif len(weights) == 6:
        α, β, γ, δ, ε, ζ = weights
    else:
        raise ValueError("weights must have length 5 or 6")

    # 0) Fetch skills & companies lexicon once (cached for process lifetime).
    global _CACHE_SKILLS, _CACHE_COMPANIES
    global _SCHEMA_HAS_COMPANY
    if _CACHE_SKILLS is None:
        _CACHE_SKILLS = _fetch_all_skills(neo4j_driver)
    if _SCHEMA_HAS_COMPANY is None:
        _SCHEMA_HAS_COMPANY = _detect_company_schema(neo4j_driver)
    if _CACHE_COMPANIES is None:
        _CACHE_COMPANIES = _fetch_all_companies(neo4j_driver, schema_has_company=_SCHEMA_HAS_COMPANY)
    all_skills = _CACHE_SKILLS
    all_companies = _CACHE_COMPANIES

    # 1) Parse query → (goal_skills, goal_job_tokens, goal_companies)
    goal_skills, goal_job_tokens = _parse_query(query_text, all_skills)
    raw_goal_companies = _parse_company_queries(query_text, all_companies)
    # Fuzzy expand goal companies against universe for better recall
    goal_companies = sorted(_fuzzy_normalize_companies(raw_goal_companies, all_companies))

    # 2) Candidate set = your connections (optionally prefiltered by simple skill/job conditions).
    candidate_ids = _fetch_candidate_connections(
        neo4j_driver,
        me_id,
        goal_skills if prefilter else None,
        goal_job_tokens if prefilter else None,
        goal_companies if prefilter else None,
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

    # 4) Pull features for candidates (skills, job tokens, bridgePotentialSkills, bridgePotentialJob, name/title).
    feats = _fetch_candidate_features(neo4j_driver, candidate_ids)
    if not feats:
        return []

    # 5) Ego-bridging on your [:KNOWS] ego network (read-only; per-query; no writes).
    struct_ego_raw = _ego_bridging_on_knows(neo4j_driver, me_id)
    # normalize ego coeff on the candidate pool
    struct_ego = _minmax_on_subset(struct_ego_raw, candidate_ids)

    # 6) Compute per-candidate matches
    skill_match: Dict[str, float] = {}
    job_match: Dict[str, float] = {}
    company_match: Dict[str, float] = {}
    # Prepare goal job set for comparisons
    goal_job_set = set(goal_job_tokens)
    goal_company_set = set(goal_companies)
    # Fetch candidate companies (lower) for company matching
    cand_companies = _fetch_candidate_companies(neo4j_driver, candidate_ids)
    for pid, f in feats.items():
        skill_match[pid] = _jaccard(set(map(str.lower, goal_skills)), set(f.skills))
        expanded_tokens = _expand_job_tokens(f.job_tokens)
        job_match[pid] = _jaccard(goal_job_set, set(expanded_tokens))
        if goal_company_set:
            cset = cand_companies.get(pid, set())
            # Jaccard over goal companies vs candidate companies (after fuzzy normalization)
            company_match[pid] = _jaccard(goal_company_set, cset)
        else:
            company_match[pid] = 0.0

    # Normalize global structure signal using sum of bp_skills and bp_job
    combined_bp = {pid: (f.bp_skills + f.bp_job) for pid, f in feats.items()}
    struct_global = _minmax_on_subset(combined_bp, candidate_ids)

    # 7) Final score (raw weighted sum first)
    scored: List[RankedPerson] = []
    for pid in candidate_ids:
        f = feats.get(pid)
        if not f:
            continue
        score = (
            α * vec_sim.get(pid, 0.0)
            + β * skill_match.get(pid, 0.0)
            + γ * job_match.get(pid, 0.0)
            + δ * struct_global.get(pid, 0.0)
            + ε * struct_ego.get(pid, 0.0)
            + ζ * company_match.get(pid, 0.0)
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
                    "company_match": company_match.get(pid, 0.0),
                },
            )
        )
    # Optional: rescale so the maximum score is ~rescale_top (default 0.8) while preserving ordering
    if rescale_top and scored:
        max_score_val = max(r.score for r in scored) or 1.0
        if max_score_val > 0:
            for r in scored:
                r.score = round((r.score / max_score_val) * float(rescale_top), 6)

    scored.sort(key=lambda r: r.score, reverse=True)
    return scored[:top_k]


# =========================
# Internals
# =========================

def _tokenize(text: str) -> List[str]:
    import re
    if not text:
        return []
    t = text.lower()
    t = re.sub(r"[^a-z0-9\s/+&-]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    if not t:
        return []
    parts = re.split(r"[ \t/+\-&]+", t)
    return [p for p in parts if p]


def _parse_query(goal_text: str, all_skills: Iterable[str]) -> Tuple[List[str], List[str]]:
    """Parse a natural language query into goal skills and job tokens.

    This helper lowercases and tokenizes the query, extracts any tokens that
    correspond to known skills, and attempts to extract job-related tokens.
    To improve matching with job titles stored in the graph, plural job
    descriptors (e.g. "engineers") are singularized when the singular form is
    recognised as a job role. Only tokens matching the role terms set or
    ending in "engineer" are kept for job matching.

    Args:
        goal_text: Natural language query.
        all_skills: Iterable of skills strings from the graph to identify
            goal skills.

    Returns:
        A tuple (goal_skills, goal_job_tokens) where goal_skills are
        lowercased skill tokens and goal_job_tokens are lowercased job tokens.
    """
    tokens = _tokenize(goal_text)
    skills_set = {s.lower().strip() for s in all_skills if s and str(s).strip()}
    # Extract goal skills
    goal_skills = sorted({t for t in tokens if t in skills_set})

    # Use the globally defined _ROLE_ROOTS to create the set of role terms (singular + plural)
    role_roots = _ROLE_ROOTS
    role_terms = role_roots | {r + "s" for r in role_roots if not r.endswith("s")}

    def singularize(t: str) -> str:
        """Return the singular form of a token if it is a plural role term.

        Example: "engineers" -> "engineer", otherwise returns the original token.
        """
        if t.endswith("s") and t[:-1] in role_roots:
            return t[:-1]
        return t

    goal_job_tokens = sorted({
        singularize(t)
        for t in tokens
        if t in role_terms or t.endswith("engineer")
    })
    return goal_skills, goal_job_tokens


# ---------------- Company Parsing Helpers ----------------
def _detect_company_schema(driver: Neo4jDriver) -> bool:
    """Detect whether :Company label or WORKED_AT rel exists to skip invalid OPTIONAL MATCH.

    Returns True if either label or relationship exists; False otherwise.
    """
    try:
        with driver.session() as s:
            # Check counts cheaply; if both zero treat as absent
            rec = s.run(
                """
                CALL {{ MATCH (c:Company) RETURN 1 LIMIT 1 }}
                RETURN 1 AS has
                """
            ).single()
            if rec:
                return True
    except Exception:
        pass
    return False


def _fetch_all_companies(driver: Neo4jDriver, schema_has_company: bool) -> List[str]:
    """Return lowercase list of all Company names in graph.

    We keep raw casing in the graph but parse in lowercase for matching.
    """
    with driver.session() as s:
        comps: Set[str] = set()
        if schema_has_company:
            try:
                rec = s.run(
                    """
                    MATCH (c:Company)
                    WHERE c.name IS NOT NULL AND trim(c.name) <> ''
                    RETURN collect(DISTINCT toLower(c.name)) AS comps
                    """
                ).single()
                if rec and rec.get("comps"):
                    comps.update(rec["comps"])
            except Exception:
                pass
        # Person.company fallback (common in current graph)
        rec2 = s.run(
            """
            MATCH (p:Person)
            WITH collect(DISTINCT toLower(p.company)) AS c1
            RETURN [x IN c1 WHERE x IS NOT NULL AND x <> ''] AS allc
            """
        ).single()
        if rec2 and rec2.get("allc"):
            comps.update(rec2["allc"])
        return sorted(c for c in comps if c)


def _parse_company_queries(text: str, all_companies: Iterable[str]) -> List[str]:
    """Extract referenced company names from natural language query.

    Strategy:
      1. Lowercase query.
      2. For each known company name (lowercased) do a substring containment check on
         word boundaries (simple heuristic). We also look for patterns like
         'at <company>' or 'company <company>' but the substring check usually suffices.
      3. Return unique matched company tokens (lowercase).

    NOTE: For multi-word companies (e.g. 'google cloud'), they will also match if
    the exact phrase appears. More advanced fuzzy matching could be added later.
    """
    if not text:
        return []
    lowered = text.lower()
    comps = set()
    # Quick normalization of punctuation
    import re
    norm = re.sub(r"[^a-z0-9\s]", " ", lowered)
    norm = re.sub(r"\s+", " ", norm).strip()
    tokens = norm.split()
    token_text = " " + " ".join(tokens) + " "
    for c in all_companies:
        if not c:
            continue
        c_low = c.lower().strip()
        if not c_low:
            continue
        # Word boundary-ish match
        pattern = f" {c_low} "
        if pattern in token_text:
            comps.add(c_low)
            continue
        # 'at <company>' or 'company <company>' patterns
        if f" at {c_low} " in token_text or f" company {c_low} " in token_text:
            comps.add(c_low)
    return sorted(comps)


# ---------- Fuzzy company helpers ----------
def _levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            ins = prev[j] + 1
            dele = cur[j - 1] + 1
            sub = prev[j - 1] + (0 if ca == cb else 1)
            cur.append(min(ins, dele, sub))
        prev = cur
    return prev[-1]


def _fuzzy_normalize_companies(targets: List[str], universe: List[str]) -> Set[str]:
    """Return a normalized set of company names matched fuzzily.

    For each target term (already lowered) we attempt:
      1. Exact match
      2. Startswith match in universe
      3. Levenshtein distance <= 2 (short names) or <= 3 (long names)
    Returns the set of universe names that matched.
    """
    u_set = {u.lower() for u in universe}
    out: Set[str] = set()
    for t in targets:
        t = t.lower().strip()
        if not t:
            continue
        if t in u_set:
            out.add(t)
            continue
        sw = [u for u in u_set if u.startswith(t) or t.startswith(u)]
        if sw:
            out.update(sw)
            continue
        # Levenshtein scan (bounded)
        for u in u_set:
            # quick length filter
            if abs(len(u) - len(t)) > 3:
                continue
            dist = _levenshtein(t, u)
            thresh = 2 if max(len(t), len(u)) <= 8 else 3
            if dist <= thresh:
                out.add(u)
    return out


def _fetch_candidate_companies(driver: Neo4jDriver, cand_ids: List[str]) -> Dict[str, Set[str]]:
    if not cand_ids:
        return {}
    global _SCHEMA_HAS_COMPANY
    has_company = bool(_SCHEMA_HAS_COMPANY)
    if has_company:
        q = """
        MATCH (p:Person) WHERE p.id IN $cand
        OPTIONAL MATCH (p)-[:WORKED_AT]->(c:Company)
        WITH p, collect(DISTINCT toLower(c.name)) AS relCompanies, toLower(p.company) AS propCompany
        WITH p,
             CASE WHEN (propCompany IS NOT NULL AND propCompany <> '') THEN relCompanies + [propCompany] ELSE relCompanies END AS companies
        RETURN p.id AS id, [x IN companies WHERE x IS NOT NULL AND x <> ''] AS companies
        """
    else:
        q = """
        MATCH (p:Person) WHERE p.id IN $cand
        WITH p, [toLower(p.company)] AS companies
        RETURN p.id AS id, [x IN companies WHERE x IS NOT NULL AND x <> ''] AS companies
        """
    with driver.session() as s:
        rows = list(s.run(q, cand=cand_ids))
    out: Dict[str, Set[str]] = {}
    for r in rows:
        comps = {str(x).lower() for x in (r.get("companies") or []) if x}
        out[str(r["id"])] = comps
    return out


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return (inter / union) if union else 0.0


# ---------- Helper for expanding job tokens ----------
def _expand_job_tokens(tokens: Iterable[str]) -> List[str]:
    """Expand a set of job tokens by splitting concatenated role words.

    Some job title tokens stored in the graph may be concatenated (e.g.,
    ``softwareengineer`` or ``datascientist``) because of the way canonical
    categories are constructed. To improve matching, this helper looks
    for occurrences of known role roots within each token and adds those
    substrings as separate tokens. For example, ``softwareengineer`` yields
    ``software`` and ``engineer``. Duplicate tokens are removed in the
    result.

    Args:
        tokens: Iterable of lowercase tokens from a candidate's job title.

    Returns:
        A list of expanded tokens, including the originals and any
        extracted substrings, without duplicates.
    """
    expanded: set[str] = set(tokens)
    for tok in tokens:
        if len(tok) < 6:
            continue
        for root in _ROLE_ROOTS:
            if root in tok and root != tok:
                expanded.add(root)
    return list(expanded)


def _minmax_on_subset(values: Dict[str, float], subset: Iterable[str]) -> Dict[str, float]:
    sub = [values.get(k, 0.0) for k in subset]
    if not sub:
        return {k: 0.0 for k in subset}
    mn, mx = min(sub), max(sub)
    if mx <= mn:
        return {k: 0.0 for k in subset}
    return {k: (values.get(k, 0.0) - mn) / (mx - mn) for k in subset}


# ---------- Neo4j fetchers ----------

def _fetch_all_skills(driver: Neo4jDriver) -> List[str]:
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
    goal_companies: Optional[List[str]],
) -> List[str]:
    """Return connection candidate IDs with optional prefiltering.

    Prefilter is a simple OR across provided dimensions (skills, jobs, companies)
    to avoid missing potential matches at vector stage.
    """
    has_skill = bool(goal_skills)
    has_job = bool(goal_job_tokens)
    has_company = bool(goal_companies)
    if not (has_skill or has_job or has_company):
        q = """
        MATCH (me:Person {id:$meId})-[:KNOWS]-(p:Person)
        RETURN DISTINCT p.id AS id
        """
        with driver.session() as s:
            return [r["id"] for r in s.run(q, meId=me_id)]

    # Dynamic WHERE clause: if both job & company specified (and no skills), require AND to narrow.
    global _SCHEMA_HAS_COMPANY
    schema_has_company = bool(_SCHEMA_HAS_COMPANY)
    if has_job and has_company and not has_skill:
        where_clause = """
        ($useJobs AND size([t IN coalesce(p.jobTitleCanonTokens,[]) WHERE t IN $jobTokens]) > 0)
        AND
        ($useCompanies AND any(x IN companies WHERE x IN $companyList))
        """
    else:
        where_clause = """
        ($useSkills AND any(s IN coalesce(p.skills,[]) WHERE toLower(s) IN $skillList))
        OR
        ($useJobs AND size([t IN coalesce(p.jobTitleCanonTokens,[]) WHERE t IN $jobTokens]) > 0)
        OR
        ($useCompanies AND any(x IN companies WHERE x IN $companyList))
        """

    if schema_has_company:
        q = f"""
        MATCH (me:Person {{id:$meId}})-[:KNOWS]-(p:Person)
        OPTIONAL MATCH (p)-[:WORKED_AT]->(c:Company)
        WITH p, collect(DISTINCT toLower(c.name)) AS relCompanies, toLower(p.company) AS propCompany
        WITH DISTINCT p,
             CASE WHEN (propCompany IS NOT NULL AND propCompany <> '') THEN relCompanies + [propCompany] ELSE relCompanies END AS companies
        WHERE {where_clause}
        RETURN p.id AS id
        """
    else:
        q = f"""
        MATCH (me:Person {{id:$meId}})-[:KNOWS]-(p:Person)
        WITH p, [toLower(p.company)] AS companies
        WHERE {where_clause}
        RETURN p.id AS id
        """
    params = {
        "meId": me_id,
        "useSkills": has_skill,
        "skillList": [x.lower() for x in (goal_skills or [])],
        "useJobs": has_job,
        "jobTokens": goal_job_tokens or [],
        "useCompanies": has_company,
        "companyList": [x.lower() for x in (goal_companies or [])],
    }
    with driver.session() as s:
        return [r["id"] for r in s.run(q, **params)]


@dataclass
class _PersonFeatures:
    skills: List[str]
    job_tokens: List[str]
    bp_skills: float
    bp_job: float
    name: str
    title: str


def _fetch_candidate_features(driver: Neo4jDriver, cand_ids: List[str]) -> Dict[str, _PersonFeatures]:
    if not cand_ids:
        return {}
    q = """
    MATCH (p:Person) WHERE p.id IN $cand
    RETURN p.id AS id,
           [x IN coalesce(p.skills, []) WHERE x IS NOT NULL] AS skills,
           [x IN coalesce(p.jobTitleCanonTokens, []) + coalesce(p.jobTitleTokens, []) WHERE x IS NOT NULL] AS jobTokens,
           coalesce(p.bridgePotentialSkills, 0.0) AS bpSkills,
           coalesce(p.bridgePotentialJob, 0.0) AS bpJob,
           coalesce(p.name, p.id) AS name,
           coalesce(p.jobTitleCanon, p.jobTitle, "") AS title
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
            bp_job=float(r.get("bpJob", 0.0) or 0.0),
            name=str(r["name"] or pid),
            title=str(r["title"] or ""),
        )
    return out


def _ego_bridging_on_knows(driver: Neo4jDriver, me_id: str) -> Dict[str, float]:
    q = """
    MATCH (me:Person {id:$meId})-[:KNOWS]-(x:Person)
    WITH collect(DISTINCT x) AS ego
    UNWIND ego AS p
    OPTIONAL MATCH (p)-[:KNOWS]-(n) WHERE n IN ego
    WITH ego, p, collect(DISTINCT n) AS neigh
    WITH ego, p, neigh, size([x IN neigh WHERE x IS NOT NULL]) AS deg
    UNWIND neigh AS neighbor
    OPTIONAL MATCH (neighbor)-[:KNOWS]-(m) WHERE m IN ego
    WITH ego, p, deg, neighbor, count(DISTINCT m) AS ndegr
    WITH ego, p, deg, collect(ndegr) AS neighDegs
    WITH p.id AS id, deg,
         reduce(s=0.0, d IN neighDegs | s + (CASE WHEN d>0 THEN 1.0/d ELSE 0.0 END)) AS invSum
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
    allowed = set(allowed_ids) if allowed_ids is not None else None
    matches: List[Dict[str, float]] = []
    try:
        if embed is not None:
            vec = embed(query_text)
            res = pinecone_index.query(vector=_ensure_list_floats(vec), top_k=top_k, include_metadata=False)
        else:
            res = pinecone_index.query(text=query_text, top_k=top_k, include_metadata=False)
        matches = _extract_matches(res)
    except Exception as e:
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
    if res_obj is None:
        return []
    if isinstance(res_obj, dict) and "matches" in res_obj:
        return [{"id": m.get("id"), "score": m.get("score", 0.0)} for m in (res_obj.get("matches") or [])]
    maybe = getattr(res_obj, "matches", None)
    if maybe is not None:
        return [{"id": getattr(m, "id", None), "score": getattr(m, "score", 0.0)} for m in (maybe or [])]
    results = None
    if isinstance(res_obj, dict):
        results = res_obj.get("results")
    else:
        results = getattr(res_obj, "results", None)
    if results:
        m = results[0].get("matches") if isinstance(results[0], dict) else getattr(results[0], "matches", None)
        if m:
            return [
                {"id": getattr(x, "id", x.get("id")), "score": getattr(x, "score", x.get("score", 0.0))}
                for x in m
            ]
    return []


def _ensure_list_floats(vec: Sequence[float]) -> List[float]:
    out: List[float] = []
    for v in vec:
        try:
            out.append(float(v))
        except Exception:
            out.append(0.0)
    return out