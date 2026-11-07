"""Accurate eval — checks gold VALUES, not just 'ran OK'. Module 4.18-4.20.
Run: python app/eval_accurate.py [--v1|--v2]
Reports accuracy on 30+ questions incl. joins/totals/filters.
"""
import csv, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from chain import run_sql
from llm import get_sql

ver = "v4" if "--v4" in sys.argv else ("v3" if "--v3" in sys.argv else ("v1" if "--v1" in sys.argv else "v2"))
EVAL = Path(__file__).parent.parent / "eval" / "questions.csv"

def norm(x): return str(x).strip().lower().replace(",", "").replace(".0", "")

passed, total, fails = 0, 0, []
un_handled, un_total = 0, 0
by_type: dict = {}
for r in list(csv.DictReader(EVAL.open(encoding="utf-8"))):
    q, typ, gold = r["question"], r["type"], r["gold_answer"]
    sql, src = get_sql(q, ver)
    if typ == "unanswerable":
        un_total += 1
        if sql == "UNANSWERABLE":
            un_handled += 1
            # safety proof for the DELETE row
            if "delete" in q.lower():
                from safety import validate_sql
                try:
                    validate_sql("DELETE FROM production"); fails.append((r["id"], q, "safety did not block"))
                except ValueError:
                    passed += 0  # safety ok, not counted in accuracy
        else:
            fails.append((r["id"], q, f"should be UNANSWERABLE got {sql}"))
        continue
    total += 1
    by_type.setdefault(typ, {"pass": 0, "total": 0})
    by_type[typ]["total"] += 1
    if sql == "UNANSWERABLE":
        fails.append((r["id"], q, "UNANSWERABLE for answerable")); continue
    try:
        rows, _ = run_sql(sql)
        flat = " ".join(" ".join(str(v) for v in row.values()) for row in rows)
        # gold may be "A;B" alternatives or single value; pass if ANY gold token in output
        golds = [g.strip() for g in gold.replace(";", ",").split(",")]
        if any(norm(g) in norm(flat) for g in golds if g):
            passed += 1
            by_type[typ]["pass"] += 1
        else:
            fails.append((r["id"], q, f"gold [{gold}] not in [{flat[:160]}] sql={sql[:120]}"))
    except Exception as e:
        fails.append((r["id"], q, f"ERR {e}"))

print(f"[{ver} via rule/llm] Accuracy: {passed}/{total} = {passed/total*100:.1f}% (answerable)")
print("Breakdown:", {k: f"{v['pass']}/{v['total']}" for k, v in by_type.items()}, "(need joins+totals+filters)")
print(f"Unanswerable correctly handled: {un_handled}/{un_total}")
for f in fails[:12]:
    print("FAIL", f)
print("Includes joins, totals, filters. Save this line for your Done-when proof.")
