import os, json
from pathlib import Path
from neo4j import GraphDatabase

from dotenv import load_dotenv
load_dotenv()

ME_PATH = Path("../data/enriched_me.json")
PEOPLE_PATH = Path("../data/enriched_people.json")

URI  = os.getenv("NEO4J_URI")
USER = os.getenv("NEO4J_USER", "neo4j")
PASS = os.getenv("NEO4J_PASS")

def main():
    me = json.loads(ME_PATH.read_text(encoding="utf-8"))
    people = json.loads(PEOPLE_PATH.read_text(encoding="utf-8"))

    driver = GraphDatabase.driver(URI, auth=(USER, PASS))
    with driver.session() as ses:
        ses.run("CREATE CONSTRAINT IF NOT EXISTS FOR (p:Person) REQUIRE p.id IS UNIQUE")
        ses.run("CREATE CONSTRAINT IF NOT EXISTS FOR (s:Skill)  REQUIRE s.name IS UNIQUE")

        # Upsert ME
        ses.run(
            "MERGE (me:Person {id:$id}) "
            "SET me.name=$name, me.description=$desc",
            id=me["person_id"], name=me.get("full_name"), desc=me.get("description")
        )
        # Skills
        for sk in (me.get("skills") or []):
            ses.run("MERGE (s:Skill {name:$n})", n=sk)
            ses.run(
                "MATCH (me:Person {id:$id}), (s:Skill {name:$n}) "
                "MERGE (me)-[:HAS_SKILL]->(s)",
                id=me["person_id"], n=sk
            )

        # KNOWS edges from me to each of my connections already in the graph
        # (assumes everyone in enriched_people.json is a 1st-degree connection)
        ses.run(
            """
            MATCH (me:Person {id:$meid})
            WITH me
            UNWIND $ids AS pid
            MATCH (p:Person {id:pid})
            MERGE (me)-[:KNOWS]->(p)
            """,
            meid=me["person_id"], ids=[p["person_id"] for p in people if p.get("person_id")]
        )
    driver.close()
    print(f"Upserted {me['person_id']} and KNOWS edges to {len(people)} nodes.")

if __name__ == "__main__":
    main()
