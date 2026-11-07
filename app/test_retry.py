"""Failure-injection test — proves retry/self-correct (M2.7 + M4.14) without an LLM key.
Simulates: 1st LLM output = bad SQL (unknown column), 2nd = good SQL.
Expects answer() to succeed on attempt 2.
Run: python app/test_retry.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import llm
from chain import answer

calls = {"n": 0}
real_get_sql = llm.get_sql

def flaky(question: str, prompt_version: str = "v2"):
    calls["n"] += 1
    if calls["n"] == 1:
        return "SELECT nonsense_col FROM production LIMIT 100", "mock-llm"
    return real_get_sql(question.replace(" [fix error:", " #"), prompt_version)

llm.get_sql = flaky

out = answer("Production of rice in Punjab in 2022?", retries=3)
print(f"attempts: {out.get('attempts')}, rows: {out.get('rows')}")
assert out.get("attempts") == 2, f"expected retry to attempt 2, got {out}"
assert out.get("rows") and out["rows"][0].get("production_tonnes") == 13800000.0, out
print("PASS retry: bad SQL on attempt 1, fixed on attempt 2 (13800000.0)")

# attempt-limit proof: always-bad LLM must fail cleanly after N tries
llm.get_sql = lambda q, v="v2": ("SELECT bad FROM bad", "mock-llm")
out2 = answer("Production of rice in Punjab in 2022?", retries=2)
assert out2.get("attempts") == 2 and not out2.get("rows"), out2
print("PASS limit: gives up after 2 tries with clean message")
