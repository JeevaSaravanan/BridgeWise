"""Assign job titles to existing Person nodes in Neo4j with tokenization.

This script reads a JSON array from ``data/enriched_people.json`` and assigns job
titles to ``:Person`` nodes in the Neo4j graph. It extends the original
implementation by additionally deriving tokenized versions of both the raw job
title and its canonical form. These tokens are stored on the person as
``jobTitleTokens`` and ``jobTitleCanonTokens``, respectively. Having tokens
available in the graph makes it possible to compute Jaccard similarity between
job titles and natural language queries, which is used by the ranking logic in
``graph-processor-api/rank_my_connections.py``.

Summary of logic:

1. Determine ``jobTitle`` based on available LinkedIn titles:
   * Prefer the current LinkedIn job title if present.
   * Fallback to the previous LinkedIn job title.
   * If neither exists, classify as ``"student"`` if the person is currently
     studying (detected via ``linkedinSchoolDateRange``), else ``"unemployed"``.
2. Compute a canonical category from the raw title using a simple set of rules
   (see ``canonicalize``). The canonical category is stored as
   ``jobTitleCanon``. Also compute a short version (first two words) and
   snake-case version for grouping.
3. Tokenize both the raw job title and its canonical category. Tokens are
   lowercased and split on spaces and punctuation. These lists are saved on
   ``:Person`` as ``jobTitleTokens`` and ``jobTitleCanonTokens``. Tokens
   support fuzzy matching for ranking purposes.
4. Write back updates to Neo4j in a single query using UNWIND for batch
   efficiency. Only the specified properties are overwritten; other
   properties on the person remain intact.

Environment variables used for Neo4j connection (must be set before running):

* ``NEO4J_URI``: Bolt URI (e.g., ``bolt://localhost:7687``)
* ``NEO4J_USER``: Username (default ``neo4j``)
* ``NEO4J_PASS``: Password

If you adjust or extend the canonicalization logic, you should also consider
whether the tokenization rules still hold and adjust the regular expression
accordingly.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from neo4j import GraphDatabase  # type: ignore
from dotenv import load_dotenv  # type: ignore

load_dotenv()

DATA_PATH = Path("data/enriched_people.json")

DATE_RANGE_PATTERN = re.compile(r"^(?P<start>[^\u2013\u2014\u2012\u2010-]+)\s*[\u2013\u2014\u2012\u2010-]\s*(?P<end>.+)$")
YEAR_ONLY = re.compile(r"^(\d{4})")
YEAR_MONTH = re.compile(r"^(\d{4})-(\d{2})")

# Regular expression for tokenizing job titles. Splits on spaces, tabs,
# slashes, plus signs, ampersands, hyphens and other punctuation. If you
# extend tokenization, update this pattern accordingly.
TOKEN_SPLIT_RE = re.compile(r"[ \t/\+&\-]+")


def tokenize_title(s: str) -> List[str]:
    """Lowercase and split a job title into simple tokens.

    This helper normalizes by lowercasing and splitting on common separators.
    Empty tokens are filtered out. If the input is empty or None, returns
    an empty list.

    Args:
        s: Raw job title or canonical category.

    Returns:
        List of lowercase tokens.
    """
    if not s:
        return []
    # Normalize to lowercase and replace slashes with spaces to avoid
    # slashes splitting different categories incorrectly (e.g., "ml engineer")
    s = s.lower().replace("/", " ")
    tokens = [tok for tok in TOKEN_SPLIT_RE.split(s) if tok]
    return tokens


def parse_date_piece(piece: str) -> Optional[datetime]:
    piece = piece.strip()
    if not piece or piece.lower() in {"present", "current", "now"}:
        return None  # treat as open-ended
    # Try YYYY-MM
    m = YEAR_MONTH.match(piece)
    if m:
        year, month = int(m.group(1)), int(m.group(2))
        return datetime(year, month, 1)
    # Try YYYY
    m = YEAR_ONLY.match(piece)
    if m:
        year = int(m.group(1))
        return datetime(year, 1, 1)
    return None


def school_active(school_range: str, today: datetime) -> bool:
    """Return True if school date range suggests the user is still a student."""
    if not school_range:
        return False
    m = DATE_RANGE_PATTERN.match(school_range)
    if not m:
        return False
    end_raw = m.group("end").strip()
    end_dt = parse_date_piece(end_raw)
    # If end date missing or 'Present', assume still active.
    if end_dt is None:
        return True
    return end_dt >= today.replace(day=1)


CANON_CLEAN_RE = re.compile(r"[^a-z0-9\s]")
WHITESPACE_RE = re.compile(r"\s+")

# ---- Imported / inlined title category mapping (camel-case canon) ----
# Source: generate_job_category.py (trimmed to required structures)
# Each entry: {"contains": original_title_lowercase, "canon": CamelCaseCategory }
# We'll build a dict mapping exact lowercase job title -> canon category.
DEFAULT_TITLE_SYNONYMS_CAMEL: List[Dict[str, str]] = []  # populated below


def _load_title_canon_mapping() -> Dict[str, str]:
    """Dynamically build mapping using categorize logic from generate_job_category.

    This avoids maintaining two large hard-coded lists; it derives categories on
    demand.
    """

    def categorize_raw(t: str) -> str:
        base = t.lower().strip()
        if base in {"student", "unemployed"}:
            return base
        if any(k in base for k in ["co-founder", "cofounder", "founder", "ceo", "chief executive officer"]):
            cat = "founder/ceo"
        elif any(k in base for k in ["chief technology officer", "cto", "chief operating officer", "svp", "vice president"]):
            cat = "executive"
        elif any(k in base for k in ["recruit", "talent acquisition", "technical recruiter", "recruiter", "hrbp", "human resources", "hr ", " hr", "people"]):
            cat = "recruiting/hr"
        elif "product" in base:
            cat = "product"
        elif "design" in base and "product" not in base:
            cat = "design"
        elif any(k in base for k in [
            "ml ", " ml", "machine learning", "ai/", "ai ", " ai", "artificial intelligence", "applied scientist", "research scientist", "data and applied scientist"
        ]):
            if "data scientist" in base:
                if any(k in base for k in ["ml", "machine learning", "ai"]):
                    cat = "ml engineer"
                else:
                    cat = "data scientist"
            elif any(k in base for k in ["intern", "trainee", "co-op", "co op"]):
                cat = "intern"
            else:
                cat = "ml engineer"
        elif "data scientist" in base:
            cat = "data scientist"
        elif any(k in base for k in ["data engineer", "big data engineer", "cloud data engineer"]):
            cat = "data engineer"
        elif "analyst" in base:
            cat = "analyst"
        elif any(k in base for k in ["devops", "site reliability engineer", "sre", "system engineer - devops"]):
            cat = "devops/sre"
        elif any(k in base for k in [
            "software engineer", "sde", "developer", "programmer", "member of technical staff", "mots", "mts",
            ".net developer", "full stack", "frontend", "backend", "react developer", "zoho developer",
            "solutions engineer", "software qa engineer", "software quality engineer", "software project developer",
            "software development engineer", "software engineering manager", "software engineering specialist"
        ]):
            cat = "software engineer"
        elif any(k in base for k in ["cloud engineer", "cloud support engineer", "azure cloud engineer"]):
            cat = "cloud engineer"
        elif "security" in base:
            cat = "security"
        elif any(k in base for k in ["solutions architect", "architect"]):
            cat = "architect"
        elif any(k in base for k in ["quality", "qa "]):
            cat = "qa"
        elif any(k in base for k in ["consultant", "advisor"]):
            cat = "consultant/advisor"
        elif any(k in base for k in ["manager", "program manager", "project manager", "operations manager", "lead ", "lead,", "lead-", "lead/"]):
            cat = "management"
        elif any(k in base for k in ["marketing", "sales", "business development", "account executive", "public relations"]):
            cat = "sales/marketing"
        elif any(k in base for k in ["professor", "lecturer", "teaching assistant", "graduate", "adjunct", "visiting graduate student", "student research", "faculty"]):
            cat = "academic"
        elif "research" in base:
            cat = "research"
        elif "engineer" in base:
            cat = "engineer"
        elif any(k in base for k in ["intern", "trainee", "co-op", "co op"]):
            cat = "intern"
        elif any(k in base for k in ["customer", "support", "assistant"]):
            cat = "support"
        elif "network" in base:
            cat = "network engineer"
        elif "supply chain" in base:
            cat = "supply chain"
        elif any(k in base for k in ["quantitative", "investment banking", "finance", "financial"]):
            cat = "finance/quant"
        elif "human resources" in base or base == "hr":
            cat = "recruiting/hr"
        elif any(k in base for k in ["writer", "content creator", "writing"]):
            cat = "content/writing"
        elif any(k in base for k in ["operations", "admin", "administrator"]):
            cat = "operations"
        else:
            cat = "other"
        # convert to CamelCase path style
        if cat in {"student", "unemployed"}:
            return cat
        parts = cat.split("/")
        return "/".join([p.title().replace(" ", "") for p in parts])

    mapping: Dict[str, str] = {}
    if DATA_PATH.exists():
        try:
            with DATA_PATH.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                for rec in data:
                    raw = rec.get("raw", {}) if isinstance(rec, dict) else {}
                    for candidate in [
                        rec.get("linkedinJobTitle"),
                        raw.get("linkedinJobTitle"),
                        raw.get("linkedinPreviousJobTitle"),
                    ]:
                        if candidate and isinstance(candidate, str):
                            key = candidate.lower().strip()
                            if key and key not in mapping:
                                mapping[key] = categorize_raw(candidate)
        except Exception:
            pass
    return mapping


TITLE_CANON_MAP = _load_title_canon_mapping()


def canonicalize(title: str) -> Tuple[str, str, str]:
    """Return (canonCategoryCamel, short, snake).

    Overridden to use TITLE_CANON_MAP if possible; fallback to previous normalization.
    """
    lower_key = title.lower().strip()
    if lower_key in TITLE_CANON_MAP:
        canon_category = TITLE_CANON_MAP[lower_key]
        base = canon_category.replace("/", " ")
        parts = re.split(r"(?=[A-Z])", base)
        words = [w for w in re.split(r"\s+", re.sub(r"[^A-Za-z0-9]+", " ", base)) if w]
        short = " ".join(words[:2]) if len(words) >= 2 else (words[0] if words else canon_category)
        snake = re.sub(r"[^a-z0-9]+", "_", canon_category.lower()).strip("_")
        return canon_category, short.lower(), snake
    t = lower_key
    t = CANON_CLEAN_RE.sub(" ", t)
    t = WHITESPACE_RE.sub(" ", t).strip() or "unknown"
    parts = t.split(" ")
    short = " ".join(parts[:2]) if len(parts) >= 2 else t
    snake = "_".join(parts)
    camel = "".join([p.capitalize() for p in parts]) or "Unknown"
    return camel, short, snake


def derive_job_title(rec: Dict[str, Any], today: datetime) -> Tuple[str, str, str, str]:
    raw: Dict[str, Any] = rec.get("raw", {})  # type: ignore
    current = rec.get("linkedinJobTitle") or raw.get("linkedinJobTitle") or ""
    previous = raw.get("linkedinPreviousJobTitle") or ""
    school_range = raw.get("linkedinSchoolDateRange") or ""

    if current.strip():
        job_title = current.strip()
    elif previous.strip():
        job_title = previous.strip()
    else:
        if school_active(school_range, today):
            job_title = "student"
        else:
            job_title = "unemployed"

    canon, short, snake = canonicalize(job_title)
    return job_title, canon, short, snake


def load_people() -> List[Dict[str, Any]]:
    with DATA_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("Expected list in enriched_people.json")
    return data


def get_driver():
    uri = os.getenv("NEO4J_URI")
    user = os.getenv("NEO4J_USER", "neo4j")
    pw = os.getenv("NEO4J_PASS")
    if not uri or not pw:
        raise EnvironmentError("NEO4J_URI and NEO4J_PASS must be set")
    return GraphDatabase.driver(uri, auth=(user, pw))


def update_person_titles(driver, updates: List[Dict[str, Any]]):
    """Batch update job title properties.

    Each dict in ``updates`` must contain the following keys:
        id: Person.id
        title: jobTitle
        canon: jobTitleCanon
        short: jobTitleCanonShort
        snake: jobTitleSnake
        jobTokens: List[str] of raw job title tokens
        canonTokens: List[str] of canonical job title tokens

    The query only sets these properties, leaving others untouched. Running this
    in a single transaction via ``UNWIND`` greatly improves performance.
    """
    query = (
        "UNWIND $rows AS row "
        "MATCH (p:Person {id: row.id}) "
        "SET p.jobTitle = row.title, "
        "    p.jobTitleCanon = row.canon, "
        "    p.jobTitleCanonShort = row.short, "
        "    p.jobTitleSnake = row.snake, "
        "    p.jobTitleTokens = row.jobTokens, "
        "    p.jobTitleCanonTokens = row.canonTokens "
        "RETURN count(p) AS updated"
    )
    with driver.session() as session:
        res = session.run(query, rows=updates)
        return res.single()["updated"]


def main():
    people = load_people()
    today = datetime.utcnow()
    updates: List[Dict[str, Any]] = []
    for rec in people:
        pid = rec.get("person_id") or rec.get("id")
        if not pid:
            continue
        job_title, canon, short, snake = derive_job_title(rec, today)
        # Tokenize both the raw job title and the canonical category. Replace slashes
        # with spaces before tokenizing canonical categories so cross-category
        # separators become separate tokens.
        raw_tokens = tokenize_title(job_title)
        canon_tokens = tokenize_title(canon)
        updates.append(
            {
                "id": pid,
                "title": job_title,
                "canon": canon,
                "short": short,
                "snake": snake,
                "jobTokens": raw_tokens,
                "canonTokens": canon_tokens,
            }
        )

    driver = get_driver()
    updated = update_person_titles(driver, updates)
    driver.close()
    print(f"Processed {len(updates)} records. Updated {updated} Person nodes.")
    # Optional: print a few samples
    for sample in updates[:5]:
        print("Sample:", sample)


if __name__ == "__main__":
    main()