"""LLM provider with graceful fallback — Module 2.2 + 2.4.
Order: OpenAI (if OPENAI_API_KEY) -> Ollama (if running) -> rule demo (no setup).
Rule demo lives here so CLI, UI, eval share it. Chain imports from here.
"""
import json, os
from pathlib import Path

CATALOG_PATH = Path(__file__).parent / "catalog.json"
def _catalog_text() -> str:
    return CATALOG_PATH.read_text(encoding="utf-8")[:4000]

def _prompt(version: str = "v2") -> str:
    name = version if version in ("v1", "v2", "v3", "v4", "v5", "v6") else "v2"
    p = Path(__file__).parent / "prompts" / f"{name}_sql.txt"
    if not p.exists():
        p = Path(__file__).parent / "prompts" / "v1_sql.txt"
    return p.read_text(encoding="utf-8").replace("{catalog}", _catalog_text())

def rule_sql(question: str) -> str:
    # Same coverage as chain.py fallback (kept in sync for eval without keys)
    q = question.lower()
    states = ["punjab", "maharashtra", "west bengal", "tamil nadu", "uttar pradesh", "madhya pradesh"]
    crops = ["rice", "wheat", "sugarcane", "cotton", "soybean"]
    fix = {"punjab": "Punjab", "maharashtra": "Maharashtra", "west bengal": "West Bengal",
           "tamil nadu": "Tamil Nadu", "uttar pradesh": "Uttar Pradesh", "madhya pradesh": "Madhya Pradesh"}
    found_state = next((fix[s] for s in states if s in q), None)
    cmap = {"rice": "Rice", "wheat": "Wheat", "sugarcane": "Sugarcane", "cotton": "Cotton", "soybean": "Soybean"}
    found_crop = next((cmap[c] for c in crops if c in q), None)
    year = "2022" if "2022" in q else ("2021" if "2021" in q else "2022")
    if any(k in q for k in ["prime minister", "cricket", "delete", "maize", "capital of india"]):
        return "UNANSWERABLE"
    if "how many states" in q:
        return "SELECT COUNT(*) AS total FROM states LIMIT 100"
    if "how many production rows" in q:
        return f"SELECT COUNT(*) AS total FROM production WHERE year={year} LIMIT 100"
    if "which kharif" in q or (q.strip().startswith("which") and "kharif" in q):
        return "SELECT DISTINCT crop_name FROM crops WHERE season='Kharif' LIMIT 100"
    if "rabi" in q and "which" in q:
        return "SELECT DISTINCT crop_name FROM crops WHERE season='Rabi' LIMIT 100"
    if "annual" in q:
        return "SELECT DISTINCT crop_name FROM crops WHERE season='Annual' LIMIT 100"
    if "which region" in q and found_state:
        return f"SELECT region FROM states WHERE state_name='{found_state}' LIMIT 100"
    if "which states grew soybean" in q:
        return ("SELECT DISTINCT s.state_name FROM production p JOIN states s ON p.state_id=s.state_id "
                f"JOIN crops c ON p.crop_id=c.crop_id WHERE c.crop_name='Soybean' AND p.year={year} LIMIT 100")
    if "north region" in q:
        return ("SELECT SUM(p.production_tonnes) AS total FROM production p JOIN states s ON p.state_id=s.state_id "
                f"WHERE s.region='North' AND p.year={year} LIMIT 100")
    if "all states" in q and "wheat" in q:
        return (f"SELECT SUM(production_tonnes) AS total FROM production p JOIN crops c ON p.crop_id=c.crop_id "
                f"WHERE c.crop_name='Wheat' AND year={year} LIMIT 100")
    if "total rice" in q:
        return (f"SELECT SUM(production_tonnes) AS total FROM production p JOIN crops c ON p.crop_id=c.crop_id "
                f"WHERE c.crop_name='Rice' AND year={year} LIMIT 100")
    if "total soybean" in q:
        return (f"SELECT SUM(production_tonnes) AS total FROM production p JOIN crops c ON p.crop_id=c.crop_id "
                f"WHERE c.crop_name='Soybean' AND year={year} LIMIT 100")
    if "average wheat" in q:
        return (f"SELECT AVG(production_tonnes) AS total FROM production p JOIN crops c ON p.crop_id=c.crop_id "
                f"WHERE c.crop_name='Wheat' AND year={year} LIMIT 100")
    if "top" in q:
        n = "3" if "top 3" in q else "2"
        crop_f = f" AND c.crop_name='{found_crop}'" if found_crop else ""
        return ("SELECT s.state_name, SUM(p.production_tonnes) AS total FROM production p "
                "JOIN states s ON p.state_id=s.state_id JOIN crops c ON p.crop_id=c.crop_id "
                f"WHERE p.year={year}{crop_f} GROUP BY s.state_name ORDER BY total DESC LIMIT {n}")
    if "total cotton" in q:
        return ("SELECT s.state_name, SUM(p.production_tonnes) AS total FROM production p JOIN states s ON p.state_id=s.state_id "
                f"JOIN crops c ON p.crop_id=c.crop_id WHERE c.crop_name='Cotton' AND p.year={year} GROUP BY s.state_name LIMIT 100")
    if "kharif" in q and "maharashtra" in q:
        return ("SELECT SUM(p.production_tonnes) AS total FROM production p JOIN states s ON p.state_id=s.state_id "
                f"JOIN crops c ON p.crop_id=c.crop_id WHERE s.state_name='Maharashtra' AND c.season='Kharif' AND p.year={year} LIMIT 100")
    if "above 30000000" in q or "above 30" in q:
        return ("SELECT s.state_name, c.crop_name, p.year, p.production_tonnes FROM production p "
                "JOIN states s ON p.state_id=s.state_id JOIN crops c ON p.crop_id=c.crop_id "
                "WHERE p.production_tonnes > 30000000 LIMIT 100")
    if "2021 vs 2022" in q or "compare rice" in q:
        return ("SELECT p.year, p.production_tonnes FROM production p JOIN states s ON p.state_id=s.state_id "
                "JOIN crops c ON p.crop_id=c.crop_id WHERE s.state_name='Punjab' AND c.crop_name='Rice' ORDER BY p.year LIMIT 100")
    if found_state and found_crop:
        return ("SELECT p.production_tonnes FROM production p JOIN states s ON p.state_id=s.state_id "
                f"JOIN crops c ON p.crop_id=c.crop_id WHERE s.state_name='{found_state}' AND c.crop_name='{found_crop}' AND p.year={year} LIMIT 100")
    return "UNANSWERABLE"

def get_sql(question: str, prompt_version: str = "v2") -> tuple[str, str]:
    """Returns (sql, source). source in openai/ollama/rule."""
    template = _prompt(prompt_version)
    # 1) OpenAI
    if os.getenv("OPENAI_API_KEY"):
        try:
            from langchain_openai import ChatOpenAI
            llm = ChatOpenAI(model="gpt-4o-mini", temperature=0).with_structured_output(dict)
            out = llm.invoke(template + f"\nQ: {question}\n")
            sql = out.get("sql", "UNANSWERABLE")
            return sql, "openai"
        except Exception as e:
            print(f"[openai failed, trying ollama: {e}]")
    # 2) Ollama local — needs `ollama serve` running + a pulled model.
    # No extra pip packages needed: talks to http://localhost:11434 directly.
    # Model pick: $LLM_MODEL if present, else llama3.1:8b if present, else first available.
    try:
        import re
        import requests
        tags = requests.get("http://localhost:11434/api/tags", timeout=5).json()
        names = [m.get("name", "") for m in tags.get("models", []) if m.get("name")]
        if not names:
            raise RuntimeError("ollama has no models (try: ollama pull llama3.1:8b)")
        want = os.getenv("LLM_MODEL", "")
        model = want if want in names else ("llama3.1:8b" if "llama3.1:8b" in names else names[0])
        r = requests.post("http://localhost:11434/api/generate", json={
            "model": model, "stream": False, "format": "json",
            "options": {"temperature": 0},
            "prompt": template + f"\nQ: {question}\nReturn ONLY JSON: {{\"sql\": \"SELECT ...\"}} "
                      + "or {\"sql\": \"UNANSWERABLE\"}."}, timeout=300)
        r.raise_for_status()
        txt = (r.json().get("response") or "").strip()
        sql = "UNANSWERABLE"
        try:
            got = json.loads(txt).get("sql", "UNANSWERABLE") if txt.startswith("{") else ""
            if isinstance(got, str) and got:
                sql = got
        except Exception:
            m = re.search(r"\{[^{}]*\"sql\"[^{}]*\}", txt, re.I | re.S)
            if m:
                try:
                    sql = json.loads(m.group(0)).get("sql", "UNANSWERABLE")
                except Exception:
                    sql = "UNANSWERABLE"
        if not isinstance(sql, str) or (sql != "UNANSWERABLE" and not sql.strip().lower().startswith("select")):
            sql = "UNANSWERABLE"
        print(f"[ollama model: {model}]")
        return sql, "ollama"
    except Exception as e:
        print(f"[ollama unavailable, rule fallback: {e}]")
    return rule_sql(question), "rule"
