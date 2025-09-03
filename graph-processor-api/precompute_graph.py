#!/usr/bin/env python3
"""
BridgeWise graph precompute (skills + job canon + metrics + ranker)

What this does
--------------
1) Upsert job titles from JSON (optional) -> p.jobTitle / Norm / Tokens.
2) **NEW:** Backfill p.jobTitle from existing p.title (if present) so legacy graphs work.
3) Build :Title nodes, compute base + canonical role (t.base, t.canon).
4) Write canon onto each :Person:
     p.jobTitleCanon, p.jobTitleCanonTokens, p.jobRoleGroup (same as canon)
5) Build :SIMILAR_JOB edges by p.jobTitleCanon, run Louvain/BC/bridging on BOTH layers:
     - skills layer (:SIMILAR) -> *Skills props
     - job layer    (:SIMILAR_JOB) -> *Job props
6) Goal-based connector ranker (skills + job + structure) (optional).

Env
----
NEO4J_URI (required)
NEO4J_PASS (required)
NEO4J_USER (default "neo4j")

CLI
---
See --help
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import time
from datetime import date
from typing import Any, Dict, Iterable, List, Tuple

from dotenv import load_dotenv
from neo4j import GraphDatabase

# Your skills-layer builder
from similarity_builder import build_similar_edges, augment_with_embedding_edges
# from job_title_canon import (
#     upsert_job_titles_from_json,
#     backfill_job_title_from_person_title,
#     group_titles_in_neo4j,
#     _tokenize_title,
# )

load_dotenv()


# ----------------------------
# Neo4j driver + schema
# ----------------------------
def get_driver():
    uri = os.getenv("NEO4J_URI")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASS")
    if not uri or not password:
        raise EnvironmentError("NEO4J_URI and NEO4J_PASS must be set")
    return GraphDatabase.driver(uri, auth=(user, password))


def ensure_schema(driver: Any):
    with driver.session() as session:
        session.run("CREATE INDEX person_id IF NOT EXISTS FOR (p:Person) ON (p.id)")
        session.run("CREATE INDEX title_name IF NOT EXISTS FOR (t:Title)  ON (t.name)")
        session.run("CREATE INDEX title_canon IF NOT EXISTS FOR (t:Title) ON (t.canon)")
        session.run("CREATE INDEX person_jobTitleCanon IF NOT EXISTS FOR (p:Person) ON (p.jobTitleCanon)")


# ----------------------------
# Helpers
# ----------------------------
def _parse_mm_range(s: str) -> Tuple[date | None, date | None]:
    """Parses 'YYYY-MM – YYYY-MM' (also 'YYYY')."""
    if not s:
        return (None, None)
    ss = s.strip().lower().replace("—", "-").replace("–", "-")
    parts = [p.strip() for p in ss.split("-") if p.strip()]
    if not parts:
        return (None, None)

    def _to_date(p: str) -> date | None:
        if p in {"present", "current", "now"}:
            return None
        m = re.match(r"^(\d{4})[./-](\d{2})$", p)
        if m:
            y, mm = int(m.group(1)), int(m.group(2))
            return date(y, mm, 1)
        m2 = re.match(r"^(\d{4})$", p)
        if m2:
            return date(int(m2.group(1)), 12, 31)
        return None

    start = _to_date(parts[0])
    end = _to_date(parts[1]) if len(parts) > 1 else None
    return (start, end)


def _normalize_title(s: str) -> str:
    """Lowercase, trim, collapse whitespace, remove most punctuation (keeps /+&-)."""
    if not s:
        return ""
    s = s.lower().strip()
    s = re.sub(r"[^\w\s/+&-]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _tokenize_title(s: str) -> List[str]:
    if not s:
        return []
    return [t for t in re.split(r"[ /+&-]", s.lower()) if t]


# ----------------------------
# Bootstrap company/school (unchanged)
# ----------------------------
def build_company_and_school(driver):
    cypher_company = """
    MATCH (p:Person)
    WITH p, p.raw.previousCompanyName AS prev
    WHERE prev IS NOT NULL AND prev <> ''
    MERGE (c:Company {name: prev})
    MERGE (p)-[:WORKED_AT]->(c)
    """
    cypher_school = """
    MATCH (p:Person)
    WITH p, p.raw.linkedinSchoolName AS cur, p.raw.linkedinPreviousSchoolName AS prev
    WITH p, [x IN [cur, prev] WHERE x IS NOT NULL AND x <> ''] AS schools
    UNWIND schools AS s
    MERGE (u:School {name: s})
    MERGE (p)-[:ATTENDED]->(u)
    """


# ----------------------------
# 3) Build :SIMILAR_JOB using grouped canon
# ----------------------------
def build_similar_job_edges_grouped(driver: Any, weight: float = 1.0):
    with driver.session() as session:
        session.run("MATCH ()-[r:SIMILAR_JOB]-() DELETE r")
        session.run("""
        MATCH (p1:Person),(p2:Person)
        WHERE p1.jobTitleCanon IS NOT NULL AND trim(p1.jobTitleCanon) <> ''
          AND p2.jobTitleCanon = p1.jobTitleCanon
          AND p1.id < p2.id
        MERGE (p1)-[r:SIMILAR_JOB]-(p2)
        SET r.weight = $w
        """, w=float(weight))
    print("[ok] Rebuilt :SIMILAR_JOB edges (by p.jobTitleCanon)")


# ----------------------------
# 4) Metrics (Louvain + betweenness + bridging)
# ----------------------------
def run_metrics_generic(
    driver: Any,
    relationship_type: str,
    weight_property: str,
    community_prop: str,
    betweenness_prop: str,
    degree_prop: str,
    bridge_coeff_prop: str,
    bridge_potential_prop: str,
    exclude_ids: Iterable[str],
    max_iter: int,
    project_name: str,
):
    exclude_ids = list(set(exclude_ids or []))
    rel_query = (
        f"MATCH (p1:Person)-[r:{relationship_type}]-(p2:Person) "
        f"WHERE p1.id < p2.id "
        f"RETURN id(p1) AS source, id(p2) AS target, r.{weight_property} AS weight"
    )

    with driver.session() as session:
        session.run("CALL gds.graph.drop($name, false) YIELD graphName", name=project_name)

        session.run("""
        CALL gds.graph.project.cypher(
          $name,
          'MATCH (p:Person) WHERE NOT p.id IN $excludeIds RETURN id(p) AS id',
          $relQuery,
          { parameters: { excludeIds: $excludeIds } }
        )
        """, name=project_name, excludeIds=exclude_ids, relQuery=rel_query)

        session.run("""
        CALL gds.louvain.write($gname, {
          writeProperty: $communityProp,
          maxIterations: $maxIter,
          relationshipWeightProperty: $weightProp
        })
        """, gname=project_name, communityProp=community_prop, maxIter=max_iter, weightProp=weight_property)

        session.run("CALL gds.betweenness.write($gname, { writeProperty: $betProp })",
                    gname=project_name, betProp=betweenness_prop)

        rows = session.run(f"""
        MATCH (p:Person)
        OPTIONAL MATCH (p)-[:{relationship_type}]-(n)
        WITH p, collect(DISTINCT n) AS neigh
        WITH p, neigh, size([x IN neigh WHERE x IS NOT NULL]) AS degree
        UNWIND neigh AS neighbor
        OPTIONAL MATCH (neighbor)-[:{relationship_type}]-(m)
        WITH p, degree, neighbor, count(DISTINCT m) AS ndegr
        WITH p, degree, collect(ndegr) AS neighbourDegrees
        RETURN p.id AS id, degree, neighbourDegrees
        """)

        bridging: Dict[str, float] = {}
        degree_map: Dict[str, int] = {}
        for r in rows:
            deg = int(r["degree"] or 0)
            degree_map[r["id"]] = deg
            neigh = r["neighbourDegrees"] or []
            if deg > 0 and neigh:
                inv_sum = sum(1.0 / d for d in neigh if d)
                coeff = (1.0 / deg) * (1.0 / inv_sum) if inv_sum > 0 else 0.0
            else:
                coeff = 0.0
            bridging[r["id"]] = coeff

        recs = [{"id": k, "bridgeCoeff": v} for k, v in bridging.items()]
        session.run(f"""
        UNWIND $rows AS rec
        MATCH (p:Person {{id: rec.id}})
        SET p.{bridge_coeff_prop} = rec.bridgeCoeff,
            p.{bridge_potential_prop} = coalesce(p.{betweenness_prop}, 0.0) * rec.bridgeCoeff,
            p.{degree_prop} = coalesce($deg[rec.id], 0)
        """, rows=recs, deg=degree_map)

        session.run("CALL gds.graph.drop($name, false)", name=project_name)

    print(f"[ok] Metrics for {relationship_type} → {community_prop}, {betweenness_prop}, {bridge_coeff_prop}, {bridge_potential_prop}, {degree_prop}")


def run_metrics_both_graphs(driver: Any, exclude_ids: Iterable[str], max_iter: int):
    # Skills
    run_metrics_generic(
        driver=driver,
        relationship_type="SIMILAR",
        weight_property="weight",
        community_prop="communitySkills",
        betweenness_prop="betweennessSkills",
        degree_prop="similarDegreeSkills",
        bridge_coeff_prop="bridgeCoeffSkills",
        bridge_potential_prop="bridgePotentialSkills",
        exclude_ids=exclude_ids,
        max_iter=max_iter,
        project_name="skillsGraph",
    )
    # Jobs
    run_metrics_generic(
        driver=driver,
        relationship_type="SIMILAR_JOB",
        weight_property="weight",
        community_prop="communityJob",
        betweenness_prop="betweennessJob",
        degree_prop="similarDegreeJob",
        bridge_coeff_prop="bridgeCoeffJob",
        bridge_potential_prop="bridgePotentialJob",
        exclude_ids=exclude_ids,
        max_iter=max_iter,
        project_name="jobGraph",
    )


# ----------------------------
# 5) Goal-based connector ranker
# ----------------------------
def _fetch_all_skills(driver: Any) -> set[str]:
    with driver.session() as session:
        res = session.run("""
            MATCH (p:Person) UNWIND coalesce(p.skills, []) AS s
            WITH toLower(trim(s)) AS s
            WHERE s IS NOT NULL AND s <> ''
            RETURN collect(DISTINCT s) AS allSkills
        """).single()
    return set(res["allSkills"] if res else [])


def _fetch_people_for_ranking(driver: Any) -> List[Dict[str, Any]]:
    with driver.session() as session:
        result = session.run("""
            MATCH (p:Person)
            RETURN
              p.id AS id,
              coalesce(p.full_name, p.raw.fullName, '') AS name,
              coalesce([x IN p.skills WHERE x IS NOT NULL], []) AS skills,
              coalesce(p.jobTitleCanon, '') AS jobTitleCanon,
              coalesce(p.jobTitleCanonTokens, []) AS jobTitleCanonTokens,
              coalesce(p.jobTitleTokens, []) AS jobTitleTokens,
              coalesce(p.betweennessSkills, 0.0) AS bS,
              coalesce(p.betweennessJob, 0.0) AS bJ,
              coalesce(p.bridgePotentialSkills, 0.0) AS bpS,
              coalesce(p.bridgePotentialJob, 0.0) AS bpJ,
              coalesce(p.bridgeCoeffSkills, 0.0) AS bcS,
              coalesce(p.bridgeCoeffJob, 0.0) AS bcJ
        """)
        return [dict(r) for r in result]


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 0.0
    inter = len(a & b)
    uni = len(a | b)
    return float(inter) / float(uni) if uni else 0.0


def _minmax_norm(values: List[float]) -> List[float]:
    if not values:
        return []
    mn, mx = min(values), max(values)
    if mx <= mn:
        return [0.0 for _ in values]
    return [(v - mn) / (mx - mn) for v in values]


def rank_connectors(
    driver: Any,
    goal_text: str | None,
    goal_skills: List[str] | None,
    goal_title: str | None,
    alpha_skills: float,
    beta_job: float,
    gamma_struct: float,
    top_k: int,
    write_rank: bool,
):
    """
    Score = alpha * skill_match + beta * job_match + gamma * structure
    structure = avg(minmax):
      betweennessSkills, betweennessJob, bridgePotentialSkills, bridgePotentialJob,
      bridgeCoeffSkills, bridgeCoeffJob
    """
    # 1) Build goal signals
    all_skills = _fetch_all_skills(driver)
    goal_skills = [s.lower().strip() for s in (goal_skills or []) if s and s.strip()]
    if (not goal_skills) and goal_text:
        tokens = set(_tokenize_title(goal_text))
        goal_skills = sorted(tokens & all_skills)
    skill_set = set(goal_skills)

    if goal_title:
        job_tokens = set(_tokenize_title(goal_title))
    elif goal_text:
        job_tokens = set(_tokenize_title(goal_text))
    else:
        job_tokens = set()

    # 2) Fetch people & compute components
    people = _fetch_people_for_ranking(driver)
    bS, bJ = [p["bS"] for p in people], [p["bJ"] for p in people]
    bpS, bpJ = [p["bpS"] for p in people], [p["bpJ"] for p in people]
    bcS, bcJ = [p["bcS"] for p in people], [p["bcJ"] for p in people]

    nbS, nbJ = _minmax_norm(bS), _minmax_norm(bJ)
    nbpS, nbpJ = _minmax_norm(bpS), _minmax_norm(bpJ)
    nbcS, nbcJ = _minmax_norm(bcS), _minmax_norm(bcJ)

    for i, p in enumerate(people):
        p_skills = set([s.lower().strip() for s in (p.get("skills") or []) if s])

        # Prefer canon tokens; fallback to raw title tokens
        role_tokens = set(p.get("jobTitleCanonTokens") or []) or set(p.get("jobTitleTokens") or [])
        skill_sim = _jaccard(skill_set, p_skills)
        job_sim = _jaccard(job_tokens, role_tokens)
        struct = (nbS[i] + nbJ[i] + nbpS[i] + nbpJ[i] + nbcS[i] + nbcJ[i]) / 6.0

        p["skill_sim"] = skill_sim
        p["job_sim"] = job_sim
        p["struct"] = struct
        p["score"] = float(alpha_skills * skill_sim + beta_job * job_sim + gamma_struct * struct)

    people.sort(key=lambda x: x["score"], reverse=True)
    top = people[: top_k]

    if write_rank:
        now_ts = int(time.time())
        rows = [{
            "id": p["id"],
            "rankScore": p["score"],
            "rankGoal": (goal_title or goal_text or "unspecified")[:200],
            "rankSkillSim": p["skill_sim"],
            "rankJobSim": p["job_sim"],
            "rankStruct": p["struct"],
            "rankAt": now_ts,
        } for p in people]
        with driver.session() as session:
            session.run("""
            UNWIND $rows AS r
            MATCH (p:Person {id: r.id})
            SET p.rankScore   = r.rankScore,
                p.rankGoal    = r.rankGoal,
                p.rankSkillSim= r.rankSkillSim,
                p.rankJobSim  = r.rankJobSim,
                p.rankStruct  = r.rankStruct,
                p.rankAt      = r.rankAt
            """, rows=rows)
        print(f"[ok] Wrote rankScore for {len(rows)} people (goal='{(goal_title or goal_text or 'unspecified')}')")

    print("\n=== Top connectors ===")
    for p in top:
        print(f"- {p['name'] or p['id']}: score={p['score']:.3f} "
              f"(skills={p['skill_sim']:.2f}, job={p['job_sim']:.2f}, struct={p['struct']:.2f})")
    return top


# ----------------------------
# Main
# ----------------------------
def main():
    ap = argparse.ArgumentParser()
    # Skills layer knobs
    ap.add_argument("--min-shared-skills", type=int, default=4)
    ap.add_argument("--weight-mode", choices=["count", "jaccard"], default="count")
    ap.add_argument("--boost-company", type=float, default=1.0)
    ap.add_argument("--boost-school", type=float, default=0.5)
    ap.add_argument("--exclude", nargs="*", default=[])
    ap.add_argument("--max-iter", type=int, default=20)
    ap.add_argument("--output", default="data/graph_metrics_snapshot.json")
    ap.add_argument("--embed-top-k", type=int, default=0)
    ap.add_argument("--embed-scale", type=float, default=1.0)

    # Job layer inputs
    ap.add_argument("--jobs-json", default=os.getenv("JOBS_JSON_PATH", "/Users/jeeva/Documents/BridgeWise/data/enriched_people.json"),
                    help="Path to JSON array with raw.linkedin* fields")
    ap.add_argument("--title-synonyms-json", default=os.getenv("TITLE_SYNONYMS_JSON", ""),
                    help="Optional JSON file of [{'contains': str, 'canon': str}, ...]")
    ap.add_argument("--job-edge-weight", type=float, default=1.0,
                    help="Weight for :SIMILAR_JOB edges when grouped by jobTitleCanon")

    # Ranker knobs
    ap.add_argument("--rank-goal-text", type=str, default=None)
    ap.add_argument("--rank-goal-skills", nargs="*", default=None)
    ap.add_argument("--rank-goal-title", type=str, default=None)
    ap.add_argument("--rank-alpha-skills", type=float, default=0.4)
    ap.add_argument("--rank-beta-job", type=float, default=0.3)
    ap.add_argument("--rank-gamma-struct", type=float, default=0.3)
    ap.add_argument("--rank-top-k", type=int, default=20)
    ap.add_argument("--rank-write", action="store_true")

    args = ap.parse_args()

    # Env overrides
    if args.min_shared_skills == 4 and os.getenv("SIMILAR_MIN_SHARED_SKILLS"):
        args.min_shared_skills = int(os.getenv("SIMILAR_MIN_SHARED_SKILLS"))
    if args.weight_mode == "count" and os.getenv("SIMILAR_WEIGHT_MODE"):
        args.weight_mode = os.getenv("SIMILAR_WEIGHT_MODE")
    if args.boost_company == 1.0 and os.getenv("SIMILAR_BOOST_COMPANY"):
        args.boost_company = float(os.getenv("SIMILAR_BOOST_COMPANY"))
    if args.boost_school == 0.5 and os.getenv("SIMILAR_BOOST_SCHOOL"):
        args.boost_school = float(os.getenv("SIMILAR_BOOST_SCHOOL"))
    if args.max_iter == 20 and os.getenv("LOUVAIN_MAX_ITER"):
        args.max_iter = int(os.getenv("LOUVAIN_MAX_ITER"))
    if not args.exclude and os.getenv("SIMILAR_EXCLUDE_IDS"):
        args.exclude = [x.strip() for x in os.getenv("SIMILAR_EXCLUDE_IDS", "").split(",") if x.strip()]
    if args.embed_top_k == 0 and os.getenv("SIMILAR_EMBED_TOP_K"):
        args.embed_top_k = int(os.getenv("SIMILAR_EMBED_TOP_K"))
    if args.embed_scale == 1.0 and os.getenv("SIMILAR_EMBED_SCALE"):
        args.embed_scale = float(os.getenv("SIMILAR_EMBED_SCALE"))

    driver = get_driver()
    ensure_schema(driver)

    # Company/school
    build_company_and_school(driver)

    # --- SKILLS layer
    build_similar_edges(
        driver,
        min_shared_skills=args.min_shared_skills,
        weight_mode=args.weight_mode,
        boost_company=args.boost_company,
        boost_school=args.boost_school,
    )
    if args.embed_top_k > 0:
        augment_with_embedding_edges(driver, top_k=args.embed_top_k, scale=args.embed_scale)

    # --- JOB layer
    # upsert_job_titles_from_json(driver, args.jobs_json)  # no-op if file missing
    # backfill_job_title_from_person_title(driver)         # <- crucial fallback
    # group_titles_in_neo4j(driver, args.title_synonyms_json)
    build_similar_job_edges_grouped(driver, weight=args.job_edge_weight)

    # --- Metrics on BOTH layers
    run_metrics_both_graphs(driver, exclude_ids=args.exclude, max_iter=args.max_iter)

    # --- Snapshot
    snapshot = {
        "timestamp": int(time.time()),
        "parameters": vars(args),
        "notes": "Job communities computed from grouped canon (p.jobTitleCanon) using Title base+canon mapping with fallback from p.title.",
    }
    out_path = pathlib.Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(snapshot, indent=2))
    print(f"[ok] Snapshot written to {out_path}")

    # --- Ranker (optional)
    if any([args.rank_goal_text, args.rank_goal_skills, args.rank_goal_title]):
        rank_connectors(
            driver=driver,
            goal_text=args.rank_goal_text,
            goal_skills=args.rank_goal_skills,
            goal_title=args.rank_goal_title,
            alpha_skills=args.rank_alpha_skills,
            beta_job=args.rank_beta_job,
            gamma_struct=args.rank_gamma_struct,
            top_k=args.rank_top_k,
            write_rank=bool(args.rank_write),
        )
    else:
        print("[info] Ranker: no goal provided (use --rank-goal-text/--rank-goal-skills/--rank-goal-title)")


if __name__ == "__main__":
    main()
