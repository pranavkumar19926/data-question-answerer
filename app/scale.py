"""Scale benchmark — M2.8 Processing at Scale. Runs full eval N times, reports timing.
Run: python app/scale.py [--runs 3]
"""
import subprocess, sys, time, statistics
from pathlib import Path
ROOT = Path(__file__).parent.parent
runs = 3
if "--runs" in sys.argv:
    runs = int(sys.argv[sys.argv.index("--runs") + 1])

times = []
for i in range(1, runs + 1):
    t0 = time.time()
    r = subprocess.run([sys.executable, "app/eval_accurate.py"], cwd=ROOT, capture_output=True, text=True)
    dt = time.time() - t0
    times.append(dt)
    ok = "28/28" in (r.stdout or "")
    print(f"run {i}: {dt:.1f}s {'OK 28/28' if ok else 'CHECK OUTPUT'}")
    if r.returncode != 0:
        print(r.stdout[-800:] + r.stderr[-800:]); sys.exit(1)

print(f"\nScale: {runs} runs, mean {statistics.mean(times):.1f}s, "
      f"min {min(times):.1f}s, max {max(times):.1f}s for 32 Qs "
      f"(~{statistics.mean(times)/32*1000:.0f} ms/Q, rule demo; LLM will be slower)")
