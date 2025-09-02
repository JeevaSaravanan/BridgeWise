# scripts/enrich_profiles.py
import os, time, json, uuid
from pathlib import Path
from typing import List, Dict, Any
from tenacity import retry, stop_after_attempt, wait_exponential

from langchain_openai import AzureChatOpenAI
from langchain.schema import SystemMessage, HumanMessage

from dotenv import load_dotenv
load_dotenv()

# ---------- Load input ----------
with open('data/batch_profiles.json', 'r', encoding='utf-8') as f:
    profiles = json.load(f)

with open('data/connections.json', 'r', encoding='utf-8') as f:
    connections = json.load(f)

# ---------- Attach profile URLs from your connections file ----------
conn_lookup: Dict[tuple, str] = {}
for conn in connections:
    first = (conn.get('firstName') or '').strip().lower()
    last  = (conn.get('lastName')  or '').strip().lower()
    if first and last:
        conn_lookup[(first, last)] = conn.get('profileUrl')

for p in profiles:
    first = (p.get('firstName') or '').strip().lower()
    last  = (p.get('lastName')  or '').strip().lower()
    profile_url = conn_lookup.get((first, last))
    if profile_url:
        p['linkedinProfileUrl'] = profile_url

# ---------- Helpers ----------
def make_description(p: Dict[str, Any]) -> str:
    parts = []
    if p.get('linkedinHeadline'):          parts.append(p['linkedinHeadline'])
    if p.get('linkedinJobTitle'):          parts.append(p['linkedinJobTitle'])
    if p.get('linkedinPreviousJobTitle'):  parts.append(p['linkedinPreviousJobTitle'])
    if p.get('linkedinSchoolName'):
        deg = p.get('linkedinSchoolDegree') or ""
        parts.append(f"{deg} at {p['linkedinSchoolName']}".strip())
    return ' | '.join(filter(None, parts))

def extract_roles(p: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    Build a small list of roles we know about (current + previous).
    If you later have a full positions array, replace this with that structure.
    """
    roles = []
    cur = p.get('linkedinJobTitle')
    cur_co = p.get('companyName') or p.get('linkedinCompanyName') or p.get('linkedinCompanyUrl') or ''
    if cur:
        roles.append({"title": cur, "company": str(cur_co)[:120]})
    prev = p.get('linkedinPreviousJobTitle')
    prev_co = p.get('previousCompanyName') or p.get('linkedinPreviousCompanyUrl') or ''
    if prev:
        roles.append({"title": prev, "company": str(prev_co)[:120]})
    return roles[:4]  # keep prompt small/cost-effective

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
        # crude repair if the model wrapped text around JSON
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
    role_skills = []
    for r in data.get("role_skills", []):
        title = (r.get("title") or "").strip()
        comp  = (r.get("company") or "").strip()
        rskills = norm_list(r.get("skills", []))[:15]
        if title or comp or rskills:
            role_skills.append({"title": title, "company": comp, "skills": rskills})
    return {"skills_overall": skills_overall[:25], "role_skills": role_skills}

# ---------- Build records + call LLM ----------
records = []
total_profiles = len(profiles)
for idx, p in enumerate(profiles):
    person_id = p.get('id') or str(uuid.uuid4())
    full_name = p.get('fullName') or f"{p.get('firstName','')} {p.get('lastName','')}".strip()
    desc = make_description(p)
    roles = extract_roles(p)

    try:
        result = extract_skills_and_roles(desc, roles)
    except Exception as e:
        print(f"[WARN] LLM failed for {person_id}: {e}")
        result = {"skills_overall": [], "role_skills": []}

    remaining = total_profiles - (idx + 1)
    print(f"[INFO]  Remaining: {remaining}, Processed {person_id} ({full_name}): {len(result['skills_overall'])} overall skills, {len(result['role_skills'])} roles, {result['role_skills']}.")
    records.append({
        "person_id": person_id,
        "full_name": full_name,
        "description": desc,
        "skills": result["skills_overall"],     # overall list
        "role_skills": result["role_skills"],   # per-role lists
        "linkedinProfileUrl": p.get("linkedinProfileUrl"),
        "raw": p
    })

    time.sleep(0.15)  # gentle pacing for mini/nano deployments


# ---------- Write output ----------
output_path = Path('data/enriched_people.json')
output_path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding='utf-8')
print(f"Wrote {len(records)} rows → {output_path}")
