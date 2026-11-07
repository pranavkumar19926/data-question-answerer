"""Query log + cost/trace — Module 2.9. JSONL, no deps."""
import json, time
from pathlib import Path

LOG = Path(__file__).parent.parent / "logs" / "queries.jsonl"

def log_event(ev: dict) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    ev = {"t": time.strftime("%Y-%m-%dT%H:%M:%S"), **ev}
    with LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(ev, default=str) + "\n")

def estimate_cost(prompt_chars: int, completion_chars: int) -> float:
    # rough gpt-4o-mini pricing: $0.15/1M in, $0.60/1M out — rule demo costs 0
    return round(prompt_chars / 1e6 * 0.15 + completion_chars / 1e6 * 0.60, 6)
