"""Record golden fixtures for every bundled case study under the current release.

Run once on the last 1.x release before any spec-4 refactoring:
    python scripts/record_golden.py
"""
from __future__ import annotations

import json
from pathlib import Path

import forge

GOLDEN_DIR = Path(__file__).resolve().parent.parent / "test" / "golden"

# Keys excluded from comparison: they change per run or per install
EXCLUDED_KEYS = {"timestamp", "provenance"}


def _strip_excluded(obj, excluded=EXCLUDED_KEYS):
    if isinstance(obj, dict):
        return {k: _strip_excluded(v, excluded) for k, v in obj.items() if k not in excluded}
    if isinstance(obj, list):
        return [_strip_excluded(v, excluded) for v in obj]
    return obj


def main():
    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
    template = forge.get_defaults_template()
    scenarios_dir = forge.get_scenarios_path()

    for forge_file in sorted(scenarios_dir.glob("*.forge")):
        with open(forge_file) as f:
            document = json.load(f)
        full_inputs = document["inputs"]
        changes = forge.diff_changes(full_inputs)
        resolved = forge.resolve_inputs(changes)
        results = forge.run_calculation(resolved, scenario_id=forge_file.stem)
        clean = _strip_excluded(results)

        out = GOLDEN_DIR / f"{forge_file.stem}.json"
        out.write_text(forge.canonical_dumps(clean) + "\n")
        print(f"  Recorded: {out.name}")

    print(f"\n{len(list(GOLDEN_DIR.glob('*.json')))} golden fixtures written to {GOLDEN_DIR}")


if __name__ == "__main__":
    main()
