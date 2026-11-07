"""Cost summary — M2.9. Reads logs/queries.jsonl, prints counts/cost/latency.
Run: python app/costs.py
"""
import json
from pathlib import Path
LOG = Path(__file__).parent.parent / "logs" / "queries.jsonl"
if not LOG.exists():
    print("No logs yet. Ask a question first: python app/chain.py \"...\" ")
    raise SystemExit(0)
rows = [json.loads(l) for l in LOG.read_text(encoding="utf-8").splitlines() if l.strip()]
ok = sum(1 for r in rows if r.get("status") == "ok")
un = sum(1 for r in rows if r.get("status") == "unanswerable")
fail = sum(1 for r in rows if r.get("status") == "failed")
ms = [r.get("ms", 0) for r in rows if "ms" in r]
cost = sum(r.get("cost_usd", 0) for r in rows)
print(f"requests: {len(rows)} (ok {ok}, unanswerable {un}, failed {fail})")
print(f"latency ms: mean {sum(ms)/max(len(ms),1):.0f}, max {max(ms) if ms else 0}")
print(f"est. LLM cost USD total: {cost:.6f} (rule demo = 0; openai adds ~$0.0003/Q)")
print(f"log file: logs/queries.jsonl")
