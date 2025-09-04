import os
from rank_my_connections import rank_my_connections

# Set up Neo4j driver using your environment variables
from neo4j import GraphDatabase
from pinecone import Pinecone
from langchain_openai import AzureOpenAIEmbeddings, OpenAIEmbeddings

from dotenv import load_dotenv
load_dotenv()

print(os.getenv("NEO4J_URI"))

driver = GraphDatabase.driver(
    os.getenv("NEO4J_URI"),
    auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASS"))
)



pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index(os.getenv("PINECONE_INDEX_NAME"))

"""Provide a query embedding function for Pinecone similarity.
Falls back to Azure OpenAI if AZURE_OPENAI_EMBED_DEPLOYMENT is set, else OpenAI.
Mirrors logic used in scripts/build_vector_db.py & scripts/upsert_me_vector.py.
"""

_embedder = None

def _get_embedder():
    global _embedder
    if _embedder is not None:
        return _embedder
    dep = os.getenv("AZURE_OPENAI_EMBED_DEPLOYMENT")
    if dep:
        _embedder = AzureOpenAIEmbeddings(azure_deployment=dep)
    else:
        model = os.getenv("AZURE_OPENAI_EMBED_DEPLOYMENT", "text-embedding-3-small")
        _embedder = OpenAIEmbeddings(model=model)
    return _embedder

def embed_fn(text: str):
    """Return embedding vector (list[float]) for a single query string."""
    emb = _get_embedder().embed_query(text)
    # Ensure plain list[float]
    return [float(x) for x in emb]

# Your own Person.id in the graph (the “Me” node)
ME_ID = "d45ee172"

# Run the ranking
results = rank_my_connections(
    neo4j_driver=driver,
    pinecone_index=index,
    me_id=ME_ID,
    query_text="I want to know who in my connections are software engineers and have skills in Python",
    top_k=10,
    embed=embed_fn
)

for i, r in enumerate(results, 1):
    comps = r.components
    print(f"{i}. {r.name} — {r.title} [score={r.score:.3f}]")
    print(f"   vec={comps['vec_sim']:.2f}, skill={comps['skill_match']:.2f}, "
          f"job={comps['job_match']:.2f}, struct={comps['struct_global']:.2f}, "
          f"ego={comps['struct_ego']:.2f}")


results = rank_my_connections(
    neo4j_driver=driver,
    pinecone_index=index,
    me_id=ME_ID,
    query_text="I want to know who in my connections are Data Scientists and have skills in gen ai",
    top_k=10,
    embed=embed_fn
)

for i, r in enumerate(results, 1):
    comps = r.components
    print(f"{i}. {r.name} — {r.title} [score={r.score:.3f}]")
    print(f"   vec={comps['vec_sim']:.2f}, skill={comps['skill_match']:.2f}, "
          f"job={comps['job_match']:.2f}, struct={comps['struct_global']:.2f}, "
          f"ego={comps['struct_ego']:.2f}")
    
results = rank_my_connections(
    neo4j_driver=driver,
    pinecone_index=index,
    me_id=ME_ID,
    query_text="I want to know who in my connections are software engineers and work in company Google",
    top_k=10,
    embed=embed_fn
)

for i, r in enumerate(results, 1):
    comps = r.components
    print(f"{i}. {r.name} — {r.title} [score={r.score:.3f}]")
    print(f"   vec={comps['vec_sim']:.2f}, skill={comps['skill_match']:.2f}, "
          f"job={comps['job_match']:.2f}, struct={comps['struct_global']:.2f}, "
          f"ego={comps['struct_ego']:.2f}")  