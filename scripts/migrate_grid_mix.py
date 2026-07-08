"""One-time migration: rewrite '18_energy_source_mix' in every scenario .ctcc file
from the old two-mix structure (energy_source_mix / counterfactual_energy_source_mix)
to the new single-trajectory grid_mix structure (initial / rate_pre_cod / rate_post_cod).

Migration rule (Task 4a, design doc 2026-07-07__single-trajectory-grid-mix-redesign.md):
  - grid_mix.initial      = old counterfactual_energy_source_mix percentages
  - grid_mix.rate_pre_cod = old counterfactual_energy_source_mix rate_of_change
  - grid_mix.rate_post_cod = same as rate_pre_cod (identity placeholder; Task 4b
    will populate researched values)
  - Fallback: if counterfactual is absent or all-zero, use energy_source_mix
    percentages for initial and zero for both rates.

Run: cd repos/ctcc/scripts && python migrate_grid_mix.py
"""

from __future__ import annotations

import json
from pathlib import Path

SOURCES = ["coal", "oil", "natural_gas", "solar", "wind", "hydro", "nuclear", "other"]

SCENARIOS_DIR = Path(__file__).resolve().parent.parent / "scenarios"


def _all_zero(mix: dict | None) -> bool:
    if not mix:
        return True
    return all((mix.get(s, {}).get("percentage", 0) or 0) == 0 for s in SOURCES)


def migrate_mix_section(old: dict) -> dict:
    """Transform one 18_energy_source_mix input block to the new grid_mix format."""
    cf = old.get("counterfactual_energy_source_mix")
    esm = old.get("energy_source_mix")

    if not _all_zero(cf):
        initial = {s: cf.get(s, {}).get("percentage", 0) for s in SOURCES}
        rate_pre_cod = {s: cf.get(s, {}).get("rate_of_change", 0.0) for s in SOURCES}
    else:
        initial = {s: (esm or {}).get(s, {}).get("percentage", 0) for s in SOURCES}
        rate_pre_cod = {s: 0.0 for s in SOURCES}

    rate_post_cod = dict(rate_pre_cod)  # identity placeholder

    return {
        "grid_mix": {
            "initial": initial,
            "rate_pre_cod": rate_pre_cod,
            "rate_post_cod": rate_post_cod,
        }
    }


def migrate_file(path: Path) -> bool:
    """Migrate one .ctcc file in place. Returns True if it was changed."""
    with open(path, "r", encoding="utf-8") as f:
        ctcc = json.load(f)

    old_mix = ctcc.get("inputs", {}).get("18_energy_source_mix")
    if old_mix is None:
        print(f"  SKIP  {path.name}: no 18_energy_source_mix section")
        return False
    if "grid_mix" in old_mix:
        print(f"  SKIP  {path.name}: already migrated")
        return False

    ctcc["inputs"]["18_energy_source_mix"] = migrate_mix_section(old_mix)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(ctcc, f, indent=2, default=str)

    print(f"  DONE  {path.name}")
    return True


def main() -> None:
    ctcc_files = sorted(SCENARIOS_DIR.glob("*.ctcc"))
    print(f"Found {len(ctcc_files)} .ctcc files in {SCENARIOS_DIR}")
    migrated = 0
    for path in ctcc_files:
        if migrate_file(path):
            migrated += 1
    print(f"\nMigrated {migrated}/{len(ctcc_files)} files.")


if __name__ == "__main__":
    main()
