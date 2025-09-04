"""Ad-hoc integration smoke tests for Graph Processor API endpoints.

Run: python test_all_api.py (assumes server running via ./start.sh on localhost:4000)

Environment requirements:
  - Neo4j + data loaded
  - Pinecone index populated
  - OPENAI / Azure OpenAI credentials (for embedding)

This does not use pytest; it's a quick sequential check printing concise results.
"""
from __future__ import annotations
import os
import json
import time
import random
from typing import Any, Dict, List

import requests

BASE_URL = os.getenv("GRAPH_API_BASE", "http://127.0.0.1:4000")
ME_ID = os.getenv("ME_ID", "d45ee172")  # fallback to value found in data/me.json

SESSION = requests.Session()

def _print(title: str, payload: Any):
    print(f"\n=== {title} ===")
    if isinstance(payload, (dict, list)):
        print(json.dumps(payload, indent=2)[:1500])
    else:
        print(str(payload)[:1500])


def _req(method: str, path: str, **kwargs) -> requests.Response:
    url = f"{BASE_URL}{path}"
    r = SESSION.request(method, url, timeout=60, **kwargs)
    return r


def test_health():
    r = _req("GET", "/health")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("status") == "ok"
    _print("health", data)


def test_connections():
    r = _req("GET", "/connections")
    assert r.status_code == 200, r.text
    data = r.json()
    assert isinstance(data, list)
    _print("connections", data[:5])


def test_cluster_summary():
    r = _req("GET", "/clusters/summary?top_n=3")
    assert r.status_code == 200, r.text
    data = r.json()
    assert isinstance(data, list)
    _print("cluster_summary", data[:2])


def _maybe_pick_person() -> str | None:
    # Use cluster member list for first cluster to fetch a person ID
    r = _req("GET", "/clusters")
    if r.status_code != 200:
        return None
    clusters = r.json()
    if not clusters:
        return None
    cid = clusters[0]["community"]
    r2 = _req("GET", f"/clusters/{cid}?limit=5")
    if r2.status_code != 200:
        return None
    members = r2.json()
    return members[0]["id"] if members else None


def test_person():
    pid = _maybe_pick_person()
    if not pid:
        print("Skipping /person test (no members found)")
        return
    r = _req("GET", f"/person/{pid}")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("id") == pid
    _print("person", data)


def test_rank_basic():
    r = _req("POST", "/rank", json={"query": "software engineer", "top_k": 5})
    assert r.status_code == 200, r.text
    data = r.json()
    assert "people" in data
    _print("rank_basic", data["people"][:3])


def test_rank_connections_debug():
    payload = {
        "me_id": ME_ID,
        "query": "software engineers with python",
        "top_k": 5,
        "debug": True
    }
    r = _req("POST", "/rank-connections", json=payload)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "results" in data
    assert "debug" in data
    _print("rank_connections_debug", data["debug"])


def test_rank_connections_explain():
    payload = {
        "me_id": ME_ID,
        "query": "data scientists gen ai",
        "sample": 5
    }
    r = _req("POST", "/rank-connections/explain", json=payload)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "candidate_count" in data
    _print("rank_connections_explain", data)


def test_rank_connections_batch():
    payload = {
        "me_id": ME_ID,
        "queries": [
            "software engineers with python",
            "data scientists gen ai",
            "software engineers working at google"
        ],
        "top_k": 5
    }
    r = _req("POST", "/rank-connections/batch", json=payload)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "results" in data and isinstance(data["results"], list)
    _print("rank_connections_batch", data["results"])


def test_intro_path():
    # Try to get two random people and request a path
    r = _req("GET", "/clusters")
    if r.status_code != 200:
        print("Skipping intro-path (no clusters)")
        return
    clusters = r.json()
    ids: List[str] = []
    for c in clusters[:3]:
        cid = c["community"]
        r2 = _req("GET", f"/clusters/{cid}?limit=5")
        if r2.status_code == 200:
            ids.extend([m["id"] for m in r2.json()])
    ids = list({i for i in ids if i})
    if len(ids) < 2:
        print("Skipping intro-path (not enough distinct people)")
        return
    src, dst = random.sample(ids, 2)
    r = _req("GET", f"/intro-path?src={src}&dst={dst}&max_depth=4")
    assert r.status_code == 200, r.text
    data = r.json()
    _print("intro_path", data)




def run_all():
    funcs = [
        test_health,
        #test_connections,
        #test_cluster_summary,
        #test_person,
        #test_rank_basic,
        test_rank_connections_debug,
        #test_rank_connections_explain,
       # test_rank_connections_batch,
       # test_intro_path,
    ]
    start = time.time()
    for f in funcs:
        try:
            f()
        except AssertionError as e:
            print(f"Assertion failed in {f.__name__}: {e}")
        except Exception as e:
            print(f"Error in {f.__name__}: {e}")
    dur = time.time() - start
    print(f"\nCompleted {len(funcs)} tests in {dur:.2f}s")

if __name__ == "__main__":
    run_all()
