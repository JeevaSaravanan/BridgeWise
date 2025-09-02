"""
This script reads the enriched people data from ``data/enriched_people.json``
and loads it into a Neo4j graph database.  Each person is represented as
a ``Person`` node with an ``id``, ``name`` and ``description``.  A
``Skill`` node is created for every distinct skill across all people,
and a ``HAS_SKILL`` relationship connects a person to a skill.  If
per‑role skills are present, a ``Role`` node is created for each
unique combination of title and company, and a ``HAS_SKILL`` link is
also created from the role to the skill; the person is linked to
their roles via a ``HAS_ROLE`` relationship.

To use this script you'll need to set the following environment
variables:

* ``NEO4J_URI`` – the bolt URI for your Neo4j Aura instance (e.g.
  ``neo4j+s://<your-instance>.databases.neo4j.io``).
* ``NEO4J_USER`` – the username (often ``neo4j``).
* ``NEO4J_PASS`` – the password for the Neo4j database.

Before loading the data the script creates uniqueness constraints on
``Person.id``, ``Skill.name`` and ``Role.id`` to prevent duplicate
nodes when running the loader multiple times.
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, List, Tuple

from neo4j import GraphDatabase  # type: ignore

from dotenv import load_dotenv
load_dotenv()

def load_people(path: Path) -> List[Dict[str, Any]]:
    """Load the enriched people records from JSON."""
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("enriched_people.json does not contain a list")
    return data


def connect_driver() -> GraphDatabase.driver:
    uri = os.getenv("NEO4J_URI")
    user = os.getenv("NEO4J_USER")
    password = os.getenv("NEO4J_PASS")
    if not uri or not user or not password:
        raise EnvironmentError(
            "Please set NEO4J_URI, NEO4J_USER and NEO4J_PASS environment variables."
        )
    return GraphDatabase.driver(uri, auth=(user, password))


def ensure_constraints(tx):
    """Create uniqueness constraints for Person, Skill and Role."""
    tx.run("CREATE CONSTRAINT IF NOT EXISTS FOR (p:Person) REQUIRE p.id IS UNIQUE")
    tx.run("CREATE CONSTRAINT IF NOT EXISTS FOR (s:Skill) REQUIRE s.name IS UNIQUE")
    tx.run("CREATE CONSTRAINT IF NOT EXISTS FOR (r:Role) REQUIRE r.id IS UNIQUE")


def load_graph(records: List[Dict[str, Any]]):
    driver = connect_driver()
    with driver.session() as session:
        session.execute_write(ensure_constraints)
        # Create Person nodes and direct skill relations
        for rec in records:
            person_id: str = rec["person_id"]
            name: str = rec.get("full_name") or ""
            description: str = rec.get("description") or ""
            skills: List[str] = rec.get("skills", [])
            role_skills: List[Dict[str, Any]] = rec.get("role_skills", [])
            # Upsert person
            session.execute_write(
                lambda tx, pid, nm, desc: tx.run(
                    "MERGE (p:Person {id:$pid}) "
                    "SET p.name=$nm, p.description=$desc",
                    pid=pid,
                    nm=nm,
                    desc=desc,
                ),
                person_id,
                name,
                description,
            )
            # Upsert skills and relationships
            for skill in skills:
                if not skill:
                    continue
                session.execute_write(
                    lambda tx, pid, sk: tx.run(
                        "MERGE (s:Skill {name:$sk}) "
                        "WITH s MATCH (p:Person {id:$pid}) "
                        "MERGE (p)-[:HAS_SKILL]->(s)",
                        sk=sk,
                        pid=pid,
                    ),
                    person_id,
                    skill,
                )
            # Upsert role skills if present
            for role in role_skills:
                title = role.get("title") or ""
                company = role.get("company") or ""
                # Compose a stable role ID.  Combining person_id, title and company
                # ensures uniqueness even if multiple people share the same title at
                # the same company.
                role_id = f"{person_id}:{title}:{company}"
                rskills: List[str] = role.get("skills") or []
                # Upsert role node and connect person to role
                session.execute_write(
                    lambda tx, rid, ttl, comp, pid: tx.run(
                        "MERGE (r:Role {id:$rid}) "
                        "SET r.title=$ttl, r.company=$comp "
                        "WITH r MATCH (p:Person {id:$pid}) "
                        "MERGE (p)-[:HAS_ROLE]->(r)",
                        rid=rid,
                        ttl=title,
                        comp=company,
                        pid=person_id,
                    ),
                    role_id,
                    title,
                    company,
                    person_id,
                )
                # Connect role to each skill
                for sk in rskills:
                    if not sk:
                        continue
                    session.execute_write(
                        lambda tx, rid, sk: tx.run(
                            "MERGE (s:Skill {name:$sk}) "
                            "WITH s MATCH (r:Role {id:$rid}) "
                            "MERGE (r)-[:HAS_SKILL]->(s)",
                            rid=role_id,
                            sk=sk,
                        ),
                        role_id,
                        sk,
                    )
    driver.close()


def main():
    data_path = Path("data/enriched_people.json")
    if not data_path.exists():
        raise FileNotFoundError(
            f"Could not find {data_path}. Make sure the enriched data file exists."
        )
    records = load_people(data_path)
    load_graph(records)
    print("Finished loading data into Neo4j.")


if __name__ == "__main__":
    main()