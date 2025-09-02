"""
cluster_and_bridge.py
======================

This module exposes a set of utilities for analysing a professional network
stored in Neo4j and indexed in Pinecone.  It implements the three core
functions requested by the BridgeWise application:

1. **Generating clusters in Neo4j** – using the Graph Data Science (GDS)
   library's Louvain algorithm, each person node is assigned to a
   community.  The results are written back to Neo4j on a property
   called ``community``.  Additional statistics such as betweenness
   centrality and bridging coefficients are computed to enable
   path‑finding and re‑ranking.

2. **Computing a bridge score per query** – given a natural language
   search term, the script embeds it using a configurable embeddings
   model (Azure OpenAI or OpenAI), retrieves the top‑K most similar
   contacts from Pinecone, fetches their graph‑based metrics
   (community and ``bridgePotential``) from Neo4j, and combines the
   similarity and the graph signal into a single ``bridgeScore``.  The
   bridge score thus reflects both how relevant the person is to the
   query and how effective they are at connecting disparate parts of
   the network.

3. **Exposing clusters and nodes to front‑end** – helper functions
   summarise the communities (size, top skills, top titles) and return
   search results enriched with graph metrics.  These payloads are
   designed to be serialised as JSON and consumed by a web API.

Usage
-----
This file can be used as a module or executed as a script.  When
executed directly it exposes a simple CLI to (a) compute graph
metrics, (b) print a cluster summary, and (c) execute a search with
bridge scores.  Environment variables are used to configure
connectivity to Neo4j, Pinecone and the embeddings provider.  See the
``README.md`` or accompanying documentation for details.

Note
----
This script relies on the Neo4j Python driver and the Graph Data
Science (GDS) library.  GDS must be installed and enabled in your
Neo4j instance.  Pinecone must also be accessible via the API key and
index name defined in the environment.  The embeddings model is
selected dynamically depending on whether Azure OpenAI deployment
variables are present.
"""

from __future__ import annotations

import os
import json
import argparse
from typing import Dict, List, Any, Iterable, Tuple


from dotenv import load_dotenv
load_dotenv()


from neo4j import GraphDatabase
from pinecone import Pinecone, ServerlessSpec
from langchain_openai import AzureOpenAIEmbeddings, OpenAIEmbeddings


# -----------------------------------------------------------------------------
# Configuration helpers
# -----------------------------------------------------------------------------

def _get_neo4j_driver() -> GraphDatabase.driver:
    """Initialise a Neo4j driver using environment variables.

    The following variables are used:
    - ``NEO4J_URI``: bolt or neo4j+s URI, e.g. ``neo4j+s://...``.
    - ``NEO4J_USER``: username (defaults to ``neo4j`` if absent).
    - ``NEO4J_PASS``: password.
    """
    uri = os.getenv("NEO4J_URI")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASS")
    if not uri or not password:
        raise EnvironmentError(
            "NEO4J_URI and NEO4J_PASS must be set in the environment to connect to Neo4j"
        )
    return GraphDatabase.driver(uri, auth=(user, password))


def _get_embedder():
    """Return an embeddings object based on environment configuration.

    If ``AZURE_OPENAI_EMBED_DEPLOYMENT`` is set, use Azure OpenAI
    embeddings; otherwise fall back to the OpenAI API.  The model name
    for OpenAI is taken from ``OPENAI_EMBED_MODEL`` (defaults to
    ``text-embedding-3-small``).  Note: the environment must include
    the appropriate API keys for the chosen provider.
    """
    azure_dep = os.getenv("AZURE_OPENAI_EMBED_DEPLOYMENT")
    if azure_dep:
        return AzureOpenAIEmbeddings(azure_deployment=azure_dep)
    model = os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small")
    return OpenAIEmbeddings(model=model)


def _init_pinecone() -> Tuple[Pinecone, str]:
    """Initialise the Pinecone client and return it along with the index name.

    This helper reads ``PINECONE_API_KEY``, ``PINECONE_REGION`` (or
    ``PINECONE_ENV``) and ``PINECONE_INDEX_NAME`` from the environment.
    If the index does not exist, the function raises an exception so
    that the caller may decide to create it.
    """
    api_key = os.getenv("PINECONE_API_KEY")
    region = os.getenv("PINECONE_REGION") or os.getenv("PINECONE_ENV")
    index_name = os.getenv("PINECONE_INDEX_NAME")
    if not api_key or not region or not index_name:
        raise EnvironmentError(
            "PINECONE_API_KEY, PINECONE_REGION (or PINECONE_ENV) and "
            "PINECONE_INDEX_NAME must be set to use Pinecone"
        )
    pc = Pinecone(api_key=api_key)
    names = pc.list_indexes().names()
    if index_name not in names:
        raise RuntimeError(
            f"Pinecone index '{index_name}' does not exist.  "
            f"Create it using your upsert scripts before searching."
        )
    return pc, index_name


# -----------------------------------------------------------------------------
# Graph metrics: clustering and bridging
# -----------------------------------------------------------------------------

def compute_graph_metrics(
    neo4j_driver: GraphDatabase.driver,
    gds_graph_name: str = "personGraph",
    max_iter_louvain: int = 20,
) -> None:
    """Compute community detection and bridging metrics.

    This function uses the Graph Data Science library to perform
    Louvain community detection on the projected ``Person`` graph.  It
    also writes betweenness centrality to each node and computes a
    bridging coefficient and potential in Python before writing those
    values back to Neo4j.

    Parameters
    ----------
    neo4j_driver : GraphDatabase.driver
        An authenticated Neo4j driver.
    gds_graph_name : str
        The name of the in‑memory GDS graph to create (defaults to
        ``"personGraph"``).
    max_iter_louvain : int
        Maximum iterations for the Louvain algorithm (defaults to 20).

    Returns
    -------
    None
        The function writes properties to the ``Person`` nodes in
        Neo4j: ``community``, ``betweenness``, ``bridgeCoeff`` and
        ``bridgePotential``.
    """
    with neo4j_driver.session() as session:
        # Drop any existing GDS graph with the same name to avoid
        # conflicts.  This is safe because the graph exists only in
        # memory.
        session.run("CALL gds.graph.drop($name, false) YIELD graphName", name=gds_graph_name)

        # Project the Person graph.  We treat KNOWS edges as
        # undirected because connections are mutual.  If your model
        # differentiates direction (e.g. follower vs following) you may
        # adjust orientation accordingly.
        session.run(
            "CALL gds.graph.project($name, 'Person', {KNOWS:{type:'KNOWS', orientation:'UNDIRECTED'}})",
            name=gds_graph_name,
        )

        # Run Louvain community detection and write to 'community'
        session.run(
            "CALL gds.louvain.write($graph, {writeProperty:'community', maxIterations:$maxIter})",
            graph=gds_graph_name,
            maxIter=max_iter_louvain,
        )

        # Run betweenness centrality and write to 'betweenness'.  We
        # use a sample rate of 1.0 by default for accuracy; adjust to
        # improve performance on very large graphs.
        session.run(
            "CALL gds.betweenness.write($graph, {writeProperty:'betweenness'})",
            graph=gds_graph_name,
        )

        # Fetch degrees and neighbour degrees to compute bridging
        # coefficient in Python.  The bridging coefficient for node i
        # is (1/degree(i)) / sum_j(1/degree(j)) for all neighbours j.
        degree_results = session.run(
            """
            MATCH (p:Person)
            OPTIONAL MATCH (p)--(n:Person)
            RETURN p.id AS id, COUNT { (p)--() } AS degree,
                   collect(COUNT { (n)--() }) AS neighbourDegrees
            """
        )
        bridging_data = {}
        for row in degree_results:
            pid = row["id"]
            deg = row["degree"] or 0
            neigh_degs = row["neighbourDegrees"] or []
            # Compute bridging coefficient: avoid division by zero
            if deg > 0 and neigh_degs:
                inv_deg_sum = sum(1.0 / d for d in neigh_degs if d)
                coeff = (1.0 / deg) * (1.0 / inv_deg_sum) if inv_deg_sum > 0 else 0.0
            else:
                coeff = 0.0
            bridging_data[pid] = coeff

        # Write bridging coefficients and potentials back to Neo4j
        # along with betweenness; compute bridgePotential = betweenness * coeff.
        # Use UNWIND to pass a map of values.
        bridge_records = [
            {
                "id": pid,
                "bridgeCoeff": coeff,
            }
            for pid, coeff in bridging_data.items()
        ]
        session.run(
            """
            UNWIND $records AS rec
            MATCH (p:Person {id: rec.id})
            SET p.bridgeCoeff = rec.bridgeCoeff,
                p.bridgePotential = coalesce(p.betweenness, 0.0) * rec.bridgeCoeff
            """,
            records=bridge_records,
        )

        # Optionally drop the in‑memory graph to free memory
        session.run("CALL gds.graph.drop($name, false) YIELD graphName", name=gds_graph_name)


def get_clusters_summary(neo4j_driver: GraphDatabase.driver) -> List[Dict[str, Any]]:
    """Return a summary of each community.

    For each community found by Louvain, this function returns the
    community ID, the number of people in that community, and the top
    skills and titles aggregated from the members' profiles.  Only the
    top three items in each category are returned to keep the output
    compact.  The resulting list is sorted by community size in
    descending order.

    Parameters
    ----------
    neo4j_driver : GraphDatabase.driver
        An authenticated driver for Neo4j.

    Returns
    -------
    List[Dict[str, Any]]
        A list of dictionaries, each containing keys ``community``,
        ``size``, ``topSkills`` and ``topTitles``.
    """
    with neo4j_driver.session() as session:
        result = session.run(
            """
            MATCH (p:Person)
            WITH p.community AS comm, collect(p) AS members, size(collect(p)) AS size
            UNWIND members AS m
            UNWIND m.skills AS skill
            WITH comm, size, skill
            WITH comm, size, toLower(skill) AS skill
            WITH comm, size, skill, count(*) AS skill_count
            ORDER BY comm, skill_count DESC
            WITH comm, size, collect({skill: skill, count: skill_count})[0..3] AS topSkillsRaw
            MATCH (p2:Person)
            WHERE p2.community = comm
            WITH comm, size, topSkillsRaw, p2
            WITH comm, size, topSkillsRaw, toLower(p2.linkedinJobTitle) AS title
            WITH comm, size, topSkillsRaw, title, count(*) AS title_count
            ORDER BY comm, title_count DESC
            WITH comm, size, topSkillsRaw, collect({title: title, count: title_count})[0..3] AS topTitlesRaw
            RETURN comm AS community, size,
                   [x IN topSkillsRaw | x.skill][0..3] AS topSkills,
                   [x IN topTitlesRaw | x.title][0..3] AS topTitles
            ORDER BY size DESC
            """
        )
        return [dict(r) for r in result]


# -----------------------------------------------------------------------------
# Search with bridge scores
# -----------------------------------------------------------------------------

def search_with_bridge_scores(
    query: str,
    top_k: int = 10,
    exclude_ids: Iterable[str] | None = None,
    include_metadata: bool = True,
) -> Dict[str, Any]:
    """Search Pinecone and compute bridge scores.

    Given a natural language ``query``, this helper embeds it, searches
    the Pinecone index for the top ``top_k`` most similar vectors,
    fetches graph metrics from Neo4j, and computes a ``bridgeScore``
    for each candidate as:

    ``bridgeScore = similarity * bridgePotential``.

    Candidates with IDs in ``exclude_ids`` are skipped (useful to
    exclude the user themselves).  The function returns a dictionary
    containing a list of people with their scores and a grouped view
    sorted by community.

    Parameters
    ----------
    query : str
        The user's search query.
    top_k : int
        Number of top results to retrieve from Pinecone (default 10).
    exclude_ids : Iterable[str] or None
        A list or set of IDs to exclude from results (default None).
    include_metadata : bool
        Whether to include the Pinecone metadata in the returned
        records (default True).

    Returns
    -------
    Dict[str, Any]
        A dictionary with two keys:
        ``people`` – a list of result objects with similarity,
        bridgePotential, bridgeScore and community; and
        ``communities`` – a mapping from community to a sorted list of
        its member results.
    """
    # Initialise clients
    embedder = _get_embedder()
    pc, index_name = _init_pinecone()
    index = pc.Index(index_name)
    neo4j_driver = _get_neo4j_driver()

    # Embed the query once
    query_vec = embedder.embed_documents([query])[0]

    # Query Pinecone for top_k matches.  We request metadata if
    # available to display names, companies, etc.  The response
    # includes similarity scores in the ``score`` field.
    response = index.query(vector=query_vec, top_k=top_k, include_metadata=include_metadata)

    # Flatten response to a list of dicts.  Each match contains id,
    # score and optional metadata.
    matches = response.get("matches", [])
    results = []
    excluded = set(exclude_ids or [])
    for m in matches:
        pid = m.get("id")
        if pid in excluded:
            continue
        score = m.get("score")  # similarity as returned by Pinecone
        meta = m.get("metadata", {}) if include_metadata else {}
        results.append({
            "person_id": pid,
            "similarity": score,
            "metadata": meta,
        })

    # Fetch graph properties for these IDs from Neo4j
    ids = [r["person_id"] for r in results]
    if not ids:
        return {"people": [], "communities": {}}
    with neo4j_driver.session() as session:
        graph_data = session.run(
            """
            UNWIND $ids AS pid
            MATCH (p:Person {id: pid})
            RETURN p.id AS id, p.community AS community,
                   coalesce(p.bridgePotential, 0.0) AS bridgePotential
            """,
            ids=ids,
        )
        props_by_id = {r["id"]: {"community": r["community"], "bridgePotential": r["bridgePotential"]} for r in graph_data}

    # Combine similarity with bridgePotential to compute bridgeScore
    for r in results:
        pid = r["person_id"]
        graph_props = props_by_id.get(pid, {"community": None, "bridgePotential": 0.0})
        bridge_potential = graph_props["bridgePotential"] or 0.0
        r["community"] = graph_props["community"]
        r["bridgePotential"] = bridge_potential
        r["bridgeScore"] = (r["similarity"] or 0.0) * bridge_potential

    # Sort results by bridgeScore descending
    results.sort(key=lambda x: x["bridgeScore"], reverse=True)

    # Group by community for convenience
    by_comm: Dict[int, List[Dict[str, Any]]] = {}
    for r in results:
        comm = r.get("community")
        by_comm.setdefault(comm, []).append(r)

    return {"people": results, "communities": by_comm}


# -----------------------------------------------------------------------------
# Command line interface
# -----------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Compute clusters and bridge scores for BridgeWise.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Subcommand to compute graph metrics
    compute_parser = subparsers.add_parser("compute", help="Run community detection and bridge metrics")
    compute_parser.add_argument("--iterations", type=int, default=20, help="Max iterations for Louvain clustering")

    # Subcommand to print cluster summary
    subparsers.add_parser("summary", help="Print cluster summary")

    # Subcommand to search with bridge scores
    search_parser = subparsers.add_parser("search", help="Search the network with a query")
    search_parser.add_argument("query", type=str, help="Query string for vector search")
    search_parser.add_argument("--top_k", type=int, default=10, help="Number of top matches to return")
    search_parser.add_argument("--exclude", type=str, nargs="*", default=[], help="IDs to exclude from results (e.g. your own id)")

    args = parser.parse_args()

    if args.command == "compute":
        drv = _get_neo4j_driver()
        compute_graph_metrics(drv, max_iter_louvain=args.iterations)
        print("Graph metrics computed and written to Neo4j.")
    elif args.command == "summary":
        drv = _get_neo4j_driver()
        summary = get_clusters_summary(drv)
        print(json.dumps(summary, indent=2))
    elif args.command == "search":
        result = search_with_bridge_scores(args.query, top_k=args.top_k, exclude_ids=args.exclude)
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()