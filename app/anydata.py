"""Ask questions of ANY uploaded CSV — pure logic, no Streamlit.
UI lives in upload_app.py. Safety gate reused from safety.py.
"""
import io, json, os, re, sqlite3, time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).parent.parent
UPLOAD_DB = ROOT / "db" / "uploads.db"
UPLOAD_DB.parent.mkdir(parents=True, exist_ok=True)

try:
    from safety import validate_sql
except ImportError:
    from app.safety import validate_sql


def clean(name: str) -> str:
    c = re.sub(r"\W+", "_", str(name).strip().lower()).strip("_")
    return c or "col"


def load_upload(file_bytes: bytes, filename: str, max_rows: int = 50000) -> dict:
    """Save uploaded CSV into uploads.db. Returns table info + catalog."""
    try:
        df = pd.read_csv(io.BytesIO(file_bytes), encoding="utf-8-sig")
    except Exception:
        df = pd.read_csv(io.BytesIO(file_bytes), encoding="latin1")
    cols, seen = [], set()
    for c in df.columns:
        cc, i = clean(c), 1
        base = cc
        while cc in seen:
            i += 1
            cc = f"{base}_{i}"
        seen.add(cc)
        cols.append(cc)
    df.columns = cols
    if len(df) > max_rows:
        df = df.head(max_rows)
    table = "up_" + clean(Path(filename).stem)[:30]
    con = sqlite3.connect(UPLOAD_DB)
    try:
        df.to_sql(table, con, if_exists="replace", index=False)
    finally:
        con.close()
    catalog = describe_table(table)
    return {"table": table, "rows": len(df), "cols": cols, "catalog": catalog,
            "preview": df.head(5).to_dict(orient="records")}


def describe_table(table: str) -> dict:
    con = sqlite3.connect(f"file:{UPLOAD_DB}?mode=ro", uri=True)
    try:
        df = pd.read_sql(f"SELECT * FROM {table} LIMIT 200", con)
    finally:
        con.close()
    columns = []
    for col in df.columns:
        kind = "TEXT"
        if pd.api.types.is_integer_dtype(df[col]):
            kind = "INTEGER"
        elif pd.api.types.is_float_dtype(df[col]):
            kind = "REAL"
        samples = [str(v) for v in df[col].dropna().unique()[:3]]
        columns.append({"name": col, "type": kind,
                        "meaning": f"Sample values: {', '.join(samples)}" if samples else "No sample values"})
    return {"name": table,
            "description": f"User-uploaded table '{table}'. One row per record in the file.",
            "columns": columns}


def generic_prompt(catalog: dict) -> str:
    col_lines = "\n".join(f"- {c['name']} ({c['type']}): {c['meaning']}" for c in catalog["columns"])
    return f"""You are a SQLite writer. Output ONLY JSON: {{"sql": "SELECT ..."}}.
Table: {catalog['name']} ({catalog['description']})
Columns:
{col_lines}
Rules:
- Only SELECT on this ONE table. Single statement, no semicolon stacking. Always LIMIT <= 100.
- Totals: SUM(col) AS total with GROUP BY. Averages: AVG(col). Counts: COUNT(*).
- Top-N: GROUP BY label ORDER BY total DESC LIMIT N.
- Year comparisons: col IN (...) ORDER BY col. Never self-join (there is only one table).
- Single value: plain SELECT with all filters, NO GROUP BY.
- GROUP TOTAL ("total ...", "by ...", "per ..."): SUM with GROUP BY, never bare per-row columns.
- UNANSWERABLE when: a needed column/place/year is not in the schema above, writes are asked, or the question is off-topic.
Q: {{question}}
Return ONLY: {{"sql": "..."}} or {{"sql": "UNANSWERABLE"}}."""


def _ollama(prompt_text: str) -> tuple[str, str]:
    import requests
    tags = requests.get("http://localhost:11434/api/tags", timeout=5).json()
    names = [m.get("name", "") for m in tags.get("models", []) if m.get("name")]
    if not names:
        raise RuntimeError("ollama has no models")
    want = os.getenv("LLM_MODEL", "")
    model = want if want in names else names[0]
    r = requests.post("http://localhost:11434/api/generate", json={
        "model": model, "stream": False, "format": "json",
        "options": {"temperature": 0}, "prompt": prompt_text}, timeout=300)
    r.raise_for_status()
    txt = (r.json().get("response") or "").strip()
    sql = "UNANSWERABLE"
    try:
        got = json.loads(txt).get("sql", "UNANSWERABLE") if txt.startswith("{") else ""
        if isinstance(got, str) and got:
            sql = got
    except Exception:
        m = re.search(r"\\{{[^{{}}]*\"sql\"[^{{}}]*\\}}", txt, re.I | re.S)
        if m:
            try:
                sql = json.loads(m.group(0)).get("sql", "UNANSWERABLE")
            except Exception:
                sql = "UNANSWERABLE"
    if not isinstance(sql, str) or (sql != "UNANSWERABLE" and not sql.strip().lower().startswith("select")):
        sql = "UNANSWERABLE"
    return sql, f"ollama:{model}"


def run_upload_sql(sql: str, max_rows: int = 100):
    safe = validate_sql(sql, max_rows)
    con = sqlite3.connect(f"file:{UPLOAD_DB}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    try:
        rows = con.execute(safe).fetchall()
        return [dict(r) for r in rows], safe
    finally:
        con.close()


def ask_any(question: str, table: str, catalog: dict, retries: int = 2) -> dict:
    t0 = time.time()
    template = generic_prompt(catalog)
    last_err = ""
    for attempt in range(1, retries + 1):
        prompt = template.replace("{question}", question + (f" [fix error: {last_err}]" if last_err else ""))
        try:
            sql, source = _ollama(prompt)
        except Exception as e:
            return {"answer": f"Model not reachable ({e}). Start Ollama with `ollama serve`.",
                    "sql": "", "rows": [], "attempts": attempt, "source": "none"}
        if sql == "UNANSWERABLE":
            return {"answer": "I can't answer this from the uploaded file's columns.",
                    "sql": sql, "rows": [], "attempts": attempt, "source": source}
        try:
            rows, safe = run_upload_sql(sql)
            if not rows:
                expl = "No rows matched your filters."
            else:
                first = rows[0]
                expl = f"Found {len(rows)} row(s)."
                vals = list(first.values())
                if len(vals) >= 2 and isinstance(vals[1], (int, float)):
                    expl += f" Top value = {vals[0]}: {vals[1]:,.2f}."
            return {"answer": expl, "sql": safe, "rows": rows, "attempts": attempt,
                    "source": source, "ms": int((time.time() - t0) * 1000)}
        except Exception as e:
            last_err = str(e)
    return {"answer": f"Couldn't build a valid query after {retries} tries. Last error: {last_err}",
            "sql": "", "rows": [], "attempts": retries, "source": "ollama"}


def pick_chart(df: "pd.DataFrame"):
    """Choose (x, y) for a bar chart, or None. Pure function for testing."""
    if df is None or df.empty or len(df.columns) < 2:
        return None
    num = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    cat = [c for c in df.columns if c not in num]
    if not num or not cat or len(df) > 100:
        return None
    return (cat[0], num[0])
