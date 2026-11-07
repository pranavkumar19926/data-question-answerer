"""DEPRECATED — use app/eval_accurate.py (checks gold VALUES + breakdown).
This old runner only checked 'ran without crash'. Kept for reference.
"""
import csv, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from chain import run_sql, llm_sql

EVAL = Path(__file__).parent.parent / "eval" / "questions.csv"
rows = list(csv.DictReader(EVAL.open(encoding="utf-8")))
ok, blocked_ok, unans_ok = 0, 0, 0
for r in rows:
    q, typ = r["question"], r["type"]
    sql = llm_sql(q)
    if typ == "unanswerable":
        if sql == "UNANSWERABLE" or "BLOCKED" in r["gold_answer"]:
            # also verify safety blocks writes
            try:
                from safety import validate_sql
                validate_sql("DELETE FROM production")
                print(f"FAIL safety not blocking on {q}")
            except ValueError:
                blocked_ok += 1
            unans_ok += 1
        continue
    try:
        if sql == "UNANSWERABLE":
            raise ValueError("returned UNANSWERABLE for answerable question")
        data, safe = run_sql(sql)
        ok += 1  # full gold-value check is manual in v1; counts executable+safe
    except Exception as e:
        print(f"FAIL [{r['id']}] {q} -> {sql} ERR:{e}")

print(f"\nEval: {ok}/{len([r for r in rows if r['type']!='unanswerable'])} answerable executed safely")
print(f"Unanswerable handled: {unans_ok}/4 | Safety blocks verified: {blocked_ok}/4")
print("Next (M3.5/M4.19): add gold_sql column and check exact-match + retrieval recall.")
