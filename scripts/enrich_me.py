"""enrich_me.py

Single-profile enrichment for data/me.json producing data/enriched_me.json
in the same shape as records from enrich_profiles.py:
[
  {
    "person_id": str,
    "full_name": str,
    "description": str,
    "skills": [str,...],
    "role_skills": [ {"title": str, "company": str, "skills": [str,...]} ],
    "linkedinProfileUrl": str | None,
    "raw": { original source object }
  }
]

Differences from enrich_profiles.py:
- No connections.json lookup (we trust linkedinProfileUrl already present).
- Handles a single JSON object (me.json) not a list.

Requires Azure OpenAI env vars (or adjust to your backend):
  AZURE_OPENAI_CHAT_DEPLOYMENT
  AZURE_OPENAI_API_VERSION
  AZURE_OPENAI_API_KEY / endpoint etc configured for langchain_openai
"""
import os, json, uuid, time
from pathlib import Path
from typing import Dict, Any, List
from tenacity import retry, stop_after_attempt, wait_exponential
from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI
from langchain.schema import SystemMessage, HumanMessage

load_dotenv()

INPUT_PATH = Path("data/me.json")
OUTPUT_PATH = Path("data/enriched_me.json")

# ---------- Load single profile ----------
if not INPUT_PATH.exists():
    raise FileNotFoundError(f"Missing {INPUT_PATH}")
with INPUT_PATH.open("r", encoding="utf-8") as f:
    profile: Dict[str, Any] = json.load(f)

# ---------- Helper functions ----------
def make_description(p: Dict[str, Any]) -> str:
    parts: List[str] = []
    if p.get('linkedinHeadline'):          parts.append(p['linkedinHeadline'])
    if p.get('linkedinJobTitle'):          parts.append(p['linkedinJobTitle'])
    if p.get('linkedinPreviousJobTitle'):  parts.append(p['linkedinPreviousJobTitle'])
    if p.get('linkedinSchoolName'):
        deg = p.get('linkedinSchoolDegree') or ""
        parts.append(f"{deg} at {p['linkedinSchoolName']}".strip())
    return ' | '.join(filter(None, parts))

def extract_roles(p: Dict[str, Any]) -> List[Dict[str, str]]:
    roles: List[Dict[str,str]] = []
    cur = p.get('linkedinJobTitle')
    cur_co = p.get('companyName') or p.get('linkedinCompanyName') or p.get('linkedinCompanyUrl') or ''
    if cur:
        roles.append({"title": cur, "company": str(cur_co)[:120]})
    prev = p.get('linkedinPreviousJobTitle')
    prev_co = p.get('previousCompanyName') or p.get('linkedinPreviousCompanyUrl') or ''
    if prev:
        roles.append({"title": prev, "company": str(prev_co)[:120]})
    return roles[:4]

# ---------- Azure OpenAI (LangChain) ----------
AZURE_CHAT_DEPLOYMENT = os.environ["AZURE_OPENAI_CHAT_DEPLOYMENT"]
AZURE_OPENAI_API_VERSION = os.environ["AZURE_OPENAI_API_VERSION"]
llm = AzureChatOpenAI(
    azure_deployment=AZURE_CHAT_DEPLOYMENT,
    api_version=AZURE_OPENAI_API_VERSION,
    temperature=0.0,
    request_timeout=60,
)

SYSTEM = SystemMessage(content=(
    "You are a precise skills extractor. Output STRICT JSON only.\n"
    "Schema:\n"
    "{\n"
    '  "skills_overall": ["skill1", "skill2", ...],\n'
    '  "role_skills": [{"title":"...","company":"...","skills":["...","..."]}]\n'
    "}\n"
    "Guidelines: extract concrete skills/technologies/methodologies/domains; lowercase; "
    "1–3 words each; deduplicate; max 25 overall, max 10 per role."
))

# Summary system prompt (mirrors enrich_profiles optional summary)
SUMMARY_SYSTEM = SystemMessage(content=(
    "You are a concise professional profile summarizer. Given raw profile text, roles and extracted skills, "
    "produce ONE polished professional summary sentence (max 50 words). Mention current role, prior relevant role/company if notable, primary domains, and 3-6 distinctive skills/technologies. Output plain text only."
))

def make_user_prompt(description: str, roles: List[Dict[str,str]]) -> str:
    return (
        "Career summary:\n"
        f"{description}\n\n"
        "Roles to analyze (JSON array):\n"
        f"{json.dumps(roles, ensure_ascii=False)}\n\n"
        "Return JSON now."
    )

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
def extract_skills_and_roles(description: str, roles: List[Dict[str,str]]) -> Dict[str, Any]:
    if not description and not roles:
        return {"skills_overall": [], "role_skills": []}
    resp = llm.invoke([
        SYSTEM,
        HumanMessage(content=make_user_prompt(description, roles))
    ])
    raw = resp.content
    try:
        data = json.loads(raw)
    except Exception:
        start, end = raw.find("{"), raw.rfind("}")
        data = json.loads(raw[start:end+1]) if start >= 0 and end >= 0 else {"skills_overall": [], "role_skills": []}

    def norm_list(xs):
        out, seen = [], set()
        for x in xs or []:
            if isinstance(x, str):
                s = " ".join(x.lower().replace("/", " ").replace("-", " ").split())
                if s and s not in seen:
                    seen.add(s); out.append(s)
        return out

    skills_overall = norm_list(data.get("skills_overall", []))
    role_skills_norm = []
    for r in data.get("role_skills", []):
        title = (r.get("title") or "").strip()
        comp  = (r.get("company") or "").strip()
        rskills = norm_list(r.get("skills", []))[:15]
        if title or comp or rskills:
            role_skills_norm.append({"title": title, "company": comp, "skills": rskills})
    return {"skills_overall": skills_overall[:25], "role_skills": role_skills_norm}

def generate_summary(raw_description: str, roles: List[Dict[str,str]], skills: List[str]) -> str:
    if not raw_description and not roles and not skills:
        return ""
    try:
        role_snips = []
        for r in roles[:4]:
            t = r.get('title') or ''
            c = r.get('company') or ''
            if t or c:
                role_snips.append(f"{t} at {c}".strip())
        skills_short = ", ".join(skills[:8])
        user_prompt = (
            "Raw description: " + (raw_description or "(none)") + "\n" +
            "Roles: " + "; ".join(role_snips) + "\n" +
            "Skills: " + skills_short + "\n\n" +
            "Write summary now:"
        )
        resp = llm.invoke([SUMMARY_SYSTEM, HumanMessage(content=user_prompt)])
        text = (resp.content or '').strip()
        return " ".join(text.split())[:300]
    except Exception as e:
        print(f"[WARN] Summary generation failed: {e}")
        return raw_description

# ---------- Process single record ----------
person_id = profile.get('id') or str(uuid.uuid4())
full_name = profile.get('fullName') or f"{profile.get('firstName','')} {profile.get('lastName','')}".strip()
original_desc = make_description(profile)
roles = extract_roles(profile)

try:
    result = extract_skills_and_roles(original_desc, roles)
except Exception as e:
    print(f"[WARN] LLM failed: {e}")
    result = {"skills_overall": [], "role_skills": []}

if os.getenv('GENERATE_PROFILE_SUMMARY', '1') != '0':
    refined_desc = generate_summary(original_desc, roles, result.get('skills_overall', []))
else:
    refined_desc = original_desc

record = {
    "person_id": person_id,
    "full_name": full_name,
    "description": refined_desc,
    "skills": result["skills_overall"],
    "role_skills": result["role_skills"],
    "linkedinProfileUrl": profile.get("linkedinProfileUrl"),
    "raw": {**profile, "original_description": original_desc}
}

OUTPUT_PATH.write_text(json.dumps([record], ensure_ascii=False, indent=2), encoding='utf-8')
print(f"Wrote enriched profile → {OUTPUT_PATH}")
