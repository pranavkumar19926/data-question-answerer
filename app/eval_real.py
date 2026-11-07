"""Real-data eval — v5 prompt on real_crop_production (district-level, 2010-2017).
Run: python app/eval_real.py
Golds are district/state aggregates verified directly against db/app.db.
"""
import csv, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from chain import run_sql
from llm import get_sql

VER = "v6" if "--v6" in sys.argv else "v5"

EVAL = Path(__file__).parent.parent / "eval" / "real_questions.csv"

def norm(x): return str(x).strip().lower().replace(",", "").replace(".0", "")

passed, total, fails = 0, 0, []
un_handled, un_total = 0, 0
by_type: dict = {}
for r in list(csv.DictReader(EVAL.open(encoding="utf-8"))):
    q, typ, gold = r["question"], r["type"], r["gold_answer"]
    sql, src = get_sql(q, VER)
    if typ == "unanswerable":
        un_total += 1
        if sql == "UNANSWERABLE":
            un_handled += 1
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
        golds = [g.strip() for g in gold.replace(";", ",").split(",")]
        if any(norm(g) in norm(flat) for g in golds if g):
            passed += 1
            by_type[typ]["pass"] += 1
        else:
            fails.append((r["id"], q, f"gold [{gold}] not in [{flat[:160]}] sql={sql[:120]}"))
    except Exception as e:
        fails.append((r["id"], q, f"ERR {e}"))

print(f"[{VER} real-data] Accuracy: {passed}/{total} = {passed/total*100:.1f}% (answerable)")
print("Breakdown:", {k: f"{v['pass']}/{v['total']}" for k, v in by_type.items()})
print(f"Unanswerable correctly handled: {un_handled}/{un_total}")
for f in fails:
    print("FAIL", f)
