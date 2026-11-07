"""Regression — M4.21. One command proves Done-when. Run: python app/regression.py"""
import subprocess, sys
from pathlib import Path
ROOT = Path(__file__).parent.parent

def run(cmd):
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return r.returncode, (r.stdout or "") + (r.stderr or "")

steps = [["python", "app/eval_accurate.py"], ["python", "app/redteam.py"], ["python", "app/test_retry.py"]]
ok = True
report = ["# Regression report"]
for cmd in steps:
    code, out = run(cmd)
    print("$", " ".join(cmd), "-> exit", code)
    print(out[-1500:])
    report += [f"\n## {' '.join(cmd)} (exit {code})\n```\n{out[-2000:]}\n```"]
    ok = ok and code == 0
(ROOT / "regression_report.md").write_text("\n".join(report), encoding="utf-8")
print("\nWrote regression_report.md —", "ALL GREEN" if ok else "FAILURES PRESENT")
sys.exit(0 if ok else 1)
