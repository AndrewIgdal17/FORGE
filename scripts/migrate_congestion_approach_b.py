"""One-off migration: rewrite the 17_congestion_curtailment_reductions block of
the case-study .ctcc scenario files from the old greenfield congestion/curtailment
structure to the new Approach B (single-constraint, two-price decomposition)
structure.

Only touches the 9 named case-study scenario files (NOT the S1-S11 generic
scenarios). Run once; safe to re-run (it is idempotent given the same source
files, but it is designed to run against the OLD structure only).
"""

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCENARIOS_DIR = REPO_ROOT / "scenarios"

# file stem -> congestion_fraction (f)
CONGESTION_FRACTION = {
    "SunZia_Delay17": 0.30,
    "SunZia_Delay2": 0.30,
    "CTT_Actual_Delay2": 0.05,
    "CTT_Counterfactual_Delay7": 0.05,
    "TBC_NoDelay": 0.80,
    "TBC_Delay4": 0.80,
    "AEP_LRGV_Laredo_NewBuild": 1.00,
    "VW1_Delay2": 0.20,
    "VW1_Delay6": 0.20,
}


def migrate_file(stem: str, fraction: float) -> None:
    path = SCENARIOS_DIR / f"{stem}.ctcc"
    with open(path) as f:
        data = json.load(f)

    old_block = data["inputs"]["17_congestion_curtailment_reductions"]
    old_gf = old_block["greenfield_congestion_curtailment_reductions"]

    flow_factor = old_gf["congestion"]["constraints"]["flow_factor"]
    constrained_hours = old_gf["congestion"]["constraints"]["binding_hours"]
    average_exceedance = old_gf["congestion"]["constraints"]["average_exceedance"]
    average_congestion_price = old_gf["congestion"]["costs"]["average_congestion_price"]
    average_curtailment_price = old_gf["curtailment"]["average_curtailment_price"]

    new_block = {
        "greenfield_congestion_curtailment_reductions": {
            "constraints": {
                "flow_factor": flow_factor,
                "constrained_hours": constrained_hours,
                "average_exceedance": average_exceedance,
                "congestion_fraction": fraction,
            },
            "prices": {
                "average_congestion_price": average_congestion_price,
                "average_curtailment_price": average_curtailment_price,
            },
        },
        "reconductoring_congestion_curtailment_reductions": {
            "constraints": {
                "constrained_hours": 0,
                "average_exceedance": 0,
                "congestion_fraction": 0.5,
            },
            "prices": {
                "average_congestion_price": 0,
                "average_curtailment_price": 0,
            },
        },
    }

    data["inputs"]["17_congestion_curtailment_reductions"] = new_block

    with open(path, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")

    print(
        f"  {stem}: flow_factor={flow_factor}, constrained_hours={constrained_hours}, "
        f"average_exceedance={average_exceedance}, f={fraction}, "
        f"congestion_price={average_congestion_price}, curtailment_price={average_curtailment_price}"
    )


def main():
    print("Migrating case-study .ctcc scenario files to Approach B structure...")
    for stem, fraction in CONGESTION_FRACTION.items():
        migrate_file(stem, fraction)
    print("Done.")


if __name__ == "__main__":
    main()
