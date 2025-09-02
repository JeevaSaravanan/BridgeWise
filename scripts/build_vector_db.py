# scripts/build_vector_db.py
"""
Build embeddings from data/enriched_people.json and upsert into Pinecone.
No CLI args. Everything important is baked into the embedding text.
Upserts id + vector (+ sanitized metadata).

ENV (set before running)
  # Pinecone
  PINECONE_API_KEY=...
  PINECONE_INDEX_NAME=bridgewise-profiles     # optional; default used if unset
  PINECONE_REGION=us-east-1                   # serverless region (or use PINECONE_ENV)

  # Prefer Azure OpenAI for embeddings:
  AZURE_OPENAI_API_KEY=...
  AZURE_OPENAI_ENDPOINT=https://<resource>.openai.azure.com/
  AZURE_OPENAI_API_VERSION=2024-02-15-preview
  AZURE_OPENAI_EMBED_DEPLOYMENT=text-embedding-3-small

  # OR vanilla OpenAI:
  OPENAI_API_KEY=...
  OPENAI_EMBED_MODEL=text-embedding-3-small
"""

import os, json
from pathlib import Path
from typing import List, Dict, Any, Tuple

from dotenv import load_dotenv
load_dotenv()

# Pinecone (v3)
from pinecone import Pinecone, ServerlessSpec

# Embeddings via LangChain
from langchain_openai import AzureOpenAIEmbeddings, OpenAIEmbeddings


# -----------------------------
# Data loading
# -----------------------------
def load_people(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Missing {path}")
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("Expected a list in enriched_people.json")
    return data


# -----------------------------
# Embedding text assembly
# -----------------------------
def _edu_from_raw(raw: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    schools, degrees = [], []
    if raw.get("linkedinSchoolName"):           schools.append(str(raw["linkedinSchoolName"]).strip())
    if raw.get("linkedinPreviousSchoolName"):   schools.append(str(raw["linkedinPreviousSchoolName"]).strip())
    if raw.get("linkedinSchoolDegree"):         degrees.append(str(raw["linkedinSchoolDegree"]).strip())
    if raw.get("linkedinPreviousSchoolDegree"): degrees.append(str(raw["linkedinPreviousSchoolDegree"]).strip())
    # dedupe preserve order
    schools = list(dict.fromkeys([s for s in schools if s]))
    degrees = list(dict.fromkeys([d for d in degrees if d]))
    return schools, degrees

def _prev_job_from_raw(raw: Dict[str, Any]) -> Tuple[str, str]:
    prev_company = (raw.get("previousCompanyName") or "").strip()
    prev_title   = (raw.get("linkedinPreviousJobTitle") or "").strip()
    return prev_company, prev_title

def _role_lines(role_skills: List[Dict[str, Any]]) -> List[str]:
    lines = []
    for r in (role_skills or []):
        title = (r.get("title") or "").strip()
        comp  = (r.get("company") or "").strip()
        rskills = [s.strip() for s in (r.get("skills") or []) if s and str(s).strip()]
        head = " ".join(x for x in [title, ("at " + comp if comp else "")] if x)
        if head or rskills:
            tail = (": " + ", ".join(rskills)) if rskills else ""
            lines.append(f"{head}{tail}".strip())
    return lines

def build_embedding_text(rec: Dict[str, Any]) -> str:
    """One compact, info-dense string for semantic indexing (no metadata used in embedding text)."""
    parts: List[str] = []

    pid   = rec.get("person_id") or ""
    name  = rec.get("full_name") or ""
    desc  = rec.get("description") or ""
    url   = rec.get("linkedinProfileUrl") or (rec.get("raw") or {}).get("linkedinProfileUrl") or ""

    if name: parts.append(f"name: {name}")
    if pid:  parts.append(f"id: {pid}")
    if desc: parts.append(f"description: {desc}")

    skills = rec.get("skills") or []
    if skills:
        parts.append("skills: " + ", ".join(skills))

    # role-specific skills
    rlines = _role_lines(rec.get("role_skills") or [])
    if rlines:
        parts.append("role_skills: " + " | ".join(rlines))

    # education, previous job/company, location
    raw = rec.get("raw") or {}
    edu_schools, edu_degrees = _edu_from_raw(raw)
    if edu_schools: parts.append("education_schools: " + ", ".join(edu_schools))
    if edu_degrees: parts.append("education_degrees: " + ", ".join(edu_degrees))

    prev_company, prev_title = _prev_job_from_raw(raw)
    if prev_company or prev_title:
        parts.append("previous: " + " ".join(x for x in [prev_title, ("at " + prev_company if prev_company else "")] if x))

    location = raw.get("location") or (raw.get("originalConnectionData") or {}).get("locationName")
    if location:
        parts.append(f"location: {location}")

    if url:
        parts.append(f"linkedin: {url}")

    return " | ".join(parts)


# -----------------------------
# Metadata sanitation (Pinecone-safe)
# -----------------------------
def make_metadata(rec: Dict[str, Any]) -> Dict[str, Any]:
    """
    Pinecone metadata must be primitives or list[str].
    This converts nested structures to strings and filters empties.
    """
    raw = rec.get("raw") or {}

    def _str_or_none(x):
        return str(x).strip() if x is not None and str(x).strip() else None

    # skills expected list[str]
    skills = [s.strip() for s in (rec.get("skills") or []) if isinstance(s, str) and s.strip()]

    # role_skills must be list[str]; reuse _role_lines()
    role_skills_lines = _role_lines(rec.get("role_skills") or [])

    md = {
        "name": _str_or_none(rec.get("full_name")),
        "description": _str_or_none(rec.get("description")),
        "skills": skills,                         # list[str]
        "role_skills": role_skills_lines,         # list[str]
        "linkedinProfileUrl": _str_or_none(rec.get("linkedinProfileUrl") or raw.get("linkedinProfileUrl")),
        "linkedinSchoolName": _str_or_none(raw.get("linkedinSchoolName")),
        "linkedinSchoolDegree": _str_or_none(raw.get("linkedinSchoolDegree")),
        "linkedinPreviousSchoolName": _str_or_none(raw.get("linkedinPreviousSchoolName")),
        "linkedinPreviousSchoolDegree": _str_or_none(raw.get("linkedinPreviousSchoolDegree")),
        "previousCompanyName": _str_or_none(raw.get("previousCompanyName")),
        "linkedinPreviousJobTitle": _str_or_none(raw.get("linkedinPreviousJobTitle")),
        "location": _str_or_none(raw.get("location") or (raw.get("originalConnectionData") or {}).get("locationName")),
    }

    # Drop None/empty; ensure lists are non-empty list[str]
    clean_md: Dict[str, Any] = {}
    for k, v in md.items():
        if v is None:
            continue
        if isinstance(v, list):
            v = [str(x).strip() for x in v if isinstance(x, str) and str(x).strip()]
            if not v:
                continue
        clean_md[k] = v

    return clean_md


# -----------------------------
# Embeddings
# -----------------------------
def get_embedder():
    azure_dep = os.getenv("AZURE_OPENAI_EMBED_DEPLOYMENT")
    if azure_dep:
        return AzureOpenAIEmbeddings(azure_deployment=azure_dep)
    model = os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small")
    return OpenAIEmbeddings(model=model)


# -----------------------------
# Pinecone helpers
# -----------------------------
def get_pinecone() -> Pinecone:
    api_key = os.getenv("PINECONE_API_KEY")
    if not api_key:
        raise EnvironmentError("Set PINECONE_API_KEY")
    return Pinecone(api_key=api_key)

def get_region() -> str:
    return os.getenv("PINECONE_REGION") or os.getenv("PINECONE_ENV") or "us-east-1"

def ensure_index(pc: Pinecone, name: str, dim: int):
    names = pc.list_indexes().names()
    if name not in names:
        pc.create_index(
            name=name,
            dimension=dim,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region=get_region())
        )


# -----------------------------
# Main
# -----------------------------
def main():
    # 1) Load data
    records = load_people(Path("data/enriched_people.json"))

    # 2) Build embedding texts
    texts = [build_embedding_text(r) for r in records]

    # 3) Embed (in batches)
    embedder = get_embedder()
    embeddings: List[List[float]] = []
    batch = 128
    for i in range(0, len(texts), batch):
        embeddings.extend(embedder.embed_documents(texts[i:i+batch]))
    if not embeddings:
        raise RuntimeError("No embeddings generated")

    # 4) Ensure index exists (or just connect if you already recreated it)
    index_name = os.getenv("PINECONE_INDEX_NAME", "bridgewise-profiles")
    pc = get_pinecone()
    dim = len(embeddings[0])
    ensure_index(pc, index_name, dim)
    index = pc.Index(index_name)

    # 5) Upsert id + vector with sanitized metadata
    vectors = []
    for rec, vec in zip(records, embeddings):
        rid = rec.get("person_id")
        if not rid:
            continue

        vectors.append({
            "id": rid,
            "values": vec,
            "metadata": make_metadata(rec)  # Pinecone-safe metadata
        })

    for i in range(0, len(vectors), 100):
        index.upsert(vectors=vectors[i:i+100])

    print(f"Upserted {len(vectors)} vectors to Pinecone index '{index_name}' (dim={dim}).")

if __name__ == "__main__":
    main()
