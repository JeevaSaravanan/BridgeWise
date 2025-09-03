"""Similarity graph builder supporting skill overlap, Jaccard weighting, boosts, and optional embedding kNN edges."""
from __future__ import annotations
from typing import List, Dict
from neo4j import GraphDatabase
import os
try:  # optional dependency
    from pinecone import Pinecone  # type: ignore
except Exception:  # broad to avoid runtime issues if partially installed
    Pinecone = None  # type: ignore

# Core edge construction; embedding kNN augmentation implemented below.

def build_similar_edges(
    driver: GraphDatabase.driver,
    min_shared_skills: int = 2,
    weight_mode: str = "count",  # or 'jaccard'
    boost_company: float = 1.0,
    boost_school: float = 0.5,
    clear_existing: bool = True,
):
    with driver.session() as session:
        if clear_existing:
            session.run("MATCH ()-[r:SIMILAR]-() DELETE r")
        # Shared skills base edges
        if weight_mode == "count":
            base = """
            MATCH (p1:Person)-[:HAS_SKILL]->(s:Skill)<-[:HAS_SKILL]-(p2:Person)
            WHERE p1.id < p2.id
            WITH p1, p2, count(s) AS shared
            WHERE shared >= $min_shared
            MERGE (p1)-[r:SIMILAR]->(p2)
            SET r.weight = toFloat(shared), r.sharedSkills = shared
            """
        else:  # jaccard without APOC
            base = """
            MATCH (p1:Person)-[:HAS_SKILL]->(s:Skill)<-[:HAS_SKILL]-(p2:Person)
            WHERE p1.id < p2.id
            WITH p1, p2, count(s) AS shared
            WHERE shared >= $min_shared
            // Collect distinct skills for each person
            MATCH (p1)-[:HAS_SKILL]->(s1:Skill)
            WITH p1, p2, shared, collect(DISTINCT s1.name) AS s1Skills
            MATCH (p2)-[:HAS_SKILL]->(s2:Skill)
            WITH p1, p2, shared, s1Skills, collect(DISTINCT s2.name) AS s2Skills
            // Compute union size in pure Cypher
            WITH p1, p2, shared, s1Skills, s2Skills,
                 size(s1Skills) AS a,
                 size(s2Skills) AS b,
                 size([x IN s1Skills WHERE x IN s2Skills]) AS inter
            WITH p1, p2, shared, (a + b - inter) AS unionSize
            WITH p1, p2, shared, CASE WHEN unionSize = 0 THEN 0.0 ELSE toFloat(shared)/unionSize END AS jaccard
            MERGE (p1)-[r:SIMILAR]->(p2)
            SET r.weight = jaccard, r.sharedSkills = shared, r.jaccard = jaccard
            """
        session.run(base, min_shared=min_shared_skills)
        if boost_company > 0:
            session.run(
                """
                MATCH (p1:Person)-[:WORKED_AT]->(c:Company)<-[:WORKED_AT]-(p2:Person)
                WHERE p1.id < p2.id
                MERGE (p1)-[r:SIMILAR]->(p2)
                SET r.weight = coalesce(r.weight,0) + $b
                """,
                b=float(boost_company),
            )
        if boost_school > 0:
            session.run(
                """
                MATCH (p1:Person)-[:ATTENDED]->(u:School)<-[:ATTENDED]-(p2:Person)
                WHERE p1.id < p2.id
                MERGE (p1)-[r:SIMILAR]->(p2)
                SET r.weight = coalesce(r.weight,0) + $b
                """,
                b=float(boost_school),
            )

def augment_with_embedding_edges(
    driver: GraphDatabase.driver,
    top_k: int,
    scale: float = 1.0,
    namespace: str | None = None,
):
    """Augment SIMILAR edges with embedding similarity from Pinecone (kNN per node).

    For each Person id an id-based query retrieves top_k neighbours (excluding self)
    and adds weight += scale * similarity. Use small top_k to control cost.
    """
    if top_k <= 0:
        return
    if Pinecone is None:
        raise ImportError("pinecone package not installed. Install or skip embedding augmentation.")
    api_key = os.getenv("PINECONE_API_KEY")
    region = os.getenv("PINECONE_REGION") or os.getenv("PINECONE_ENV")
    index_name = os.getenv("PINECONE_INDEX_NAME")
    if not api_key or not region or not index_name:
        raise EnvironmentError("Pinecone env vars missing for embedding augmentation")
    pc = Pinecone(api_key=api_key)
    if index_name not in pc.list_indexes().names():
        raise RuntimeError(f"Pinecone index '{index_name}' not found")
    index = pc.Index(index_name)
    with driver.session() as session:
        ids = [r["id"] for r in session.run("MATCH (p:Person) RETURN p.id AS id")]
    edges: List[Dict[str, object]] = []
    for pid in ids:
        try:
            resp = index.query(id=pid, top_k=top_k + 1, include_metadata=False, namespace=namespace)
        except Exception:
            continue
        for match in resp.get("matches", []):
            mid = match.get("id")
            if not mid or mid == pid:
                continue
            score = match.get("score") or 0.0
            if score <= 0:
                continue
            a, b = sorted([pid, mid])
            edges.append({"a": a, "b": b, "w": float(score) * scale})
    if not edges:
        return
    with driver.session() as session:
        session.run(
            """
            UNWIND $edges AS e
            MATCH (p1:Person {id:e.a}), (p2:Person {id:e.b})
            MERGE (p1)-[r:SIMILAR]->(p2)
            SET r.weight = coalesce(r.weight,0) + e.w
            """,
            edges=edges,
        )
