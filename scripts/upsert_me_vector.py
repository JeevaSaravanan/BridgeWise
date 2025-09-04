import os, json
from pathlib import Path
from typing import List, Dict, Any, Tuple
from dotenv import load_dotenv
load_dotenv()

from pinecone import Pinecone
from langchain_openai import AzureOpenAIEmbeddings, OpenAIEmbeddings

ME_PATH = Path("../data/enriched_me.json")
INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "bridgewise-profiles")

def get_embedder():
    dep = os.getenv("AZURE_OPENAI_EMBED_DEPLOYMENT")
    if dep:
        return AzureOpenAIEmbeddings(azure_deployment=dep)
    return OpenAIEmbeddings(model=os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small"))

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
    parts = []
    name = rec.get("full_name") or ""
    pid  = rec.get("person_id") or ""
    desc = rec.get("description") or ""
    url  = rec.get("linkedinProfileUrl") or (rec.get("raw") or {}).get("linkedinProfileUrl") or ""
    if name: parts.append(f"name: {name}")
    if pid:  parts.append(f"id: {pid}")
    if desc: parts.append(f"description: {desc}")
    skills = rec.get("skills") or []
    if skills: parts.append("skills: " + ", ".join(skills))
    for r in (rec.get("role_skills") or []):
        t = (r.get("title") or "").strip()
        c = (r.get("company") or "").strip()
        rs = [s for s in (r.get("skills") or []) if s]
        head = " ".join(x for x in [t, ("at " + c if c else "")] if x)
        parts.append(("role: " + head).strip() + (": " + ", ".join(rs) if rs else ""))
    raw = rec.get("raw") or {}
    sch = [raw.get("linkedinSchoolName"), raw.get("linkedinPreviousSchoolName")]
    deg = [raw.get("linkedinSchoolDegree"), raw.get("linkedinPreviousSchoolDegree")]
    sch = [s for s in sch if s]; deg = [d for d in deg if d]
    if sch: parts.append("education_schools: " + ", ".join(sch))
    if deg: parts.append("education_degrees: " + ", ".join(deg))
    prevc, prevt = (raw.get("previousCompanyName") or ""), (raw.get("linkedinPreviousJobTitle") or "")
    if prevc or prevt: parts.append(f"previous: {prevt} at {prevc}".strip())
    loc = raw.get("location") or (raw.get("originalConnectionData") or {}).get("locationName")
    if loc: parts.append("location: " + loc)
    if url: parts.append("linkedin: " + url)
    return " | ".join(parts)

def main():
    me = json.loads(ME_PATH.read_text(encoding="utf-8"))
    embedder = get_embedder()
    text = build_embedding_text(me)
    vec = embedder.embed_documents([text])[0]

    pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
    index = pc.Index(INDEX_NAME)

    # Build Pinecone-safe metadata matching build_vector_db.make_metadata keys
    raw = me.get("raw") or {}

    def _str_or_none(x):
        return str(x).strip() if x is not None and str(x).strip() else None

    skills = [s.strip() for s in (me.get("skills") or []) if isinstance(s, str) and s.strip()]
    role_skills_lines = _role_lines(me.get("role_skills") or [])

    md = {
        "name": _str_or_none(me.get("full_name")),
        "description": _str_or_none(me.get("description")),
        "skills": skills,
        "role_skills": role_skills_lines,
        "linkedinProfileUrl": _str_or_none(me.get("linkedinProfileUrl") or raw.get("linkedinProfileUrl")),
        "linkedinSchoolName": _str_or_none(raw.get("linkedinSchoolName")),
        "linkedinSchoolDegree": _str_or_none(raw.get("linkedinSchoolDegree")),
        "linkedinPreviousSchoolName": _str_or_none(raw.get("linkedinPreviousSchoolName")),
        "linkedinPreviousSchoolDegree": _str_or_none(raw.get("linkedinPreviousSchoolDegree")),
        "previousCompanyName": _str_or_none(raw.get("previousCompanyName")),
        "linkedinPreviousJobTitle": _str_or_none(raw.get("linkedinPreviousJobTitle")),
        "location": _str_or_none(raw.get("location") or (raw.get("originalConnectionData") or {}).get("locationName")),
    }

    # Clean None / empty lists
    metadata: Dict[str, Any] = {}
    for k, v in md.items():
        if v is None:
            continue
        if isinstance(v, list):
            v = [str(x).strip() for x in v if isinstance(x, str) and str(x).strip()]
            if not v:
                continue
        metadata[k] = v

    index.upsert(vectors=[{"id": me["person_id"], "values": vec, "metadata": metadata}])
    print(f"Upserted self vector for {me['person_id']} into {INDEX_NAME}")

if __name__ == "__main__":
    main()
