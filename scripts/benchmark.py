"""Benchmark: run each case study 20 times and report median time."""
import json
import statistics
import sys
import time
from pathlib import Path

# `python scripts/benchmark.py` puts scripts/ on sys.path, not the package root.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import forge

SCENARIOS_DIR = forge.get_scenarios_path()


def main():
    template = forge.get_defaults_template()
    results = {}

    for forge_file in sorted(SCENARIOS_DIR.glob("*.forge")):
        with open(forge_file) as f:
            document = json.load(f)
        changes = forge.diff_changes(document["inputs"])
        resolved = forge.resolve_inputs(changes)

        times = []
        for i in range(20):
            t0 = time.perf_counter()
            forge.run_calculation(resolved, scenario_id=f"{forge_file.stem}_{i}")
            elapsed = time.perf_counter() - t0
            times.append(elapsed)

        median = statistics.median(times)
        results[forge_file.stem] = median
        print(f"  {forge_file.stem:40s}  {median*1000:7.1f} ms (median of 20)")

    overall = statistics.median(results.values())
    print(f"\n  {'Overall median':40s}  {overall*1000:7.1f} ms")
    print(f"\n  Target: < {0.60/5*1000:.0f} ms (1/5 of 600 ms baseline)")
    meets = overall < 0.120
    print(f"  Meets target: {'yes' if meets else 'no'}")


if __name__ == "__main__":
    main()
