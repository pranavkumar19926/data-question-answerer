"""CLI chain: question -> SQL -> safety -> run (read-only) -> explain.
Works WITHOUT an API key (rule demo) and WITH OpenAI/Ollama via LangChain if installed.
Run: python app/chain.py "Top 2 states by wheat production in 2022?"
"""
import json, sqlite3, sys, time
from pathlib import Path
try:
    from trace import log_event, estimate_cost
except ImportError:
    from app.trace import log_event, estimate_cost
from safety import validate_sql

ROOT = Path(__file__).parent.parent
DB = ROOT / "db" / "app.db"
CATALOG = json.loads((Path(__file__).parent / "catalog.json").read_text())

def run_sql(sql: str, max_rows: int = 100):
    safe = validate_sql(sql, max_rows)
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    try:
        rows = con.execute(safe).fetchall()
        return [dict(r) for r in rows], safe
    finally:
        con.close()

def llm_sql(question: str, prompt_version: str = "v2") -> str:
    """Try OpenAI/Ollama via llm.py, else rule demo. Returns SQL or UNANSWERABLE."""
    try:
        from llm import get_sql  # same folder
    except ImportError:
        from app.llm import get_sql
    sql, source = get_sql(question, prompt_version)
    if source != "rule":
        print(f"[llm source: {source}]")
    else:
        print("[llm: rule demo — set OPENAI_API_KEY or run ollama serve for real LLM]")
    return sql

def answer(question: str, retries: int = 3, prompt_version: str = "v2"):
    t0 = time.time()
    last_err = ""
    for attempt in range(1, retries + 1):
        sql = llm_sql(question + (f" [fix error: {last_err}]" if last_err else ""), prompt_version)
        if sql == "UNANSWERABLE":
            out = {"answer": "I can't answer this from the data. I have states, crops, production (2021-2022).",
                    "sql": sql, "rows": [], "attempts": attempt}
            log_event({"q": question, "sql": sql, "status": "unanswerable",
                       "attempts": attempt, "ms": int((time.time()-t0)*1000), "cost_usd": 0})
            return out
        try:
            rows, safe = run_sql(sql)
            # Explainer (Module 2.6 + 3.4): answer + figures
            if not rows:
                expl = "No rows matched your filters."
            else:
                first = rows[0]
                expl = f"Found {len(rows)} row(s). First row: {first}."
                vals = list(first.values())
                if "total" in first and len(vals) >= 2:
                    expl += f" Top value = {vals[0]}: {vals[1]:,.0f} tonnes."
                elif "total" in first:
                    expl += f" Total = {vals[0]:,.0f} tonnes."
            out = {"answer": expl, "sql": safe, "rows": rows, "attempts": attempt}
            log_event({"q": question, "sql": safe, "status": "ok", "rows": len(rows),
                       "attempts": attempt, "ms": int((time.time()-t0)*1000),
                       "cost_usd": estimate_cost(len(question)+2000, len(safe))})
            return out
        except Exception as e:
            last_err = str(e)
            print(f"Attempt {attempt} failed: {e}")
    out = {"answer": f"Couldn't build a valid query after {retries} tries. Last error: {last_err}",
                    "sql": "", "rows": [], "attempts": retries}
    log_event({"q": question, "sql": "", "status": "failed", "error": last_err,
               "attempts": retries, "ms": int((time.time()-t0)*1000), "cost_usd": 0})
    return out

def stream_print(text: str, delay: float = 0.015):
    """Token-stream demo (M2.3). Works for rule or LLM text."""
    import sys as _sys
    for ch in text:
        _sys.stdout.write(ch)
        _sys.stdout.flush()
        try:
            import time as _t
            _t.sleep(delay)
        except Exception:
            pass
    print()

if __name__ == "__main__":
    args = sys.argv[1:]
    stream = "--stream" in args
    args = [a for a in args if a != "--stream"]
    ver = "v2"
    for v in ("v1", "v2", "v3", "v4", "v5", "v6"):
        if f"--{v}" in args:
            ver = v
            args = [a for a in args if a != f"--{v}"]
    if "--real" in args:  # shortcut: real district data uses v6
        ver = "v6"
        args = [a for a in args if a != "--real"]
    q = " ".join(args) or "Top 2 states by wheat production in 2022?"
    out = answer(q, prompt_version=ver)
    if stream:
        print("SQL:", out.get("sql"))
        stream_print("Answer: " + out.get("answer", ""))
        print(json.dumps({"rows": out.get("rows", []), "attempts": out.get("attempts")}, indent=2, default=str))
    else:
        print(json.dumps(out, indent=2, default=str))
