"""Discount-rate sensitivity analysis for SunZia and CTT CREZ scenarios.

Patches social_discount_rate to 2%, 3%, 5% and reports BCR metrics.
"""

import copy
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from ctcc import run_calculation  # noqa: E402

SCENARIOS = [
    "SunZia_Delay17",
    "SunZia_Delay2",
    "CTT_Actual_Delay2",
    "CTT_Counterfactual_Delay7",
    "TBC_Delay4",
    "TBC_NoDelay",
    "VW1_Delay6",
    "VW1_Delay2",
]

DISCOUNT_RATES = [0.02, 0.03, 0.05]

METRICS = [
    ("BCR Utility",                      "bcr_utility",      "ratio"),
    ("BCR Ratepayer",                    "bcr_ratepayer",    "ratio"),
    ("BCR Excl. WF+Outage",             "bcr_excluding_wildfire_risk_and_outage_risk", "ratio"),
    ("BCR Excl. Avoided Emis.",         "bcr_excluding_avoided_emissions", "ratio"),
    ("BCR Excl. AvEmis+WF+Out",        "bcr_excluding_avoided_emissions_and_wildfire_risk_and_outage_risk", "ratio"),
    ("Total Costs PV",                   "total_costs_pv",   "dollar"),
    ("Total Benefits PV",               "total_benefits_pv", "dollar"),
    ("Net Benefit PV",                   "net_benefit_pv",    "dollar"),
    ("Avoided Emissions PV",            "benefits_avoided_emissions_pv", "dollar"),
    ("Wildfire PV",                      "wildfire_pv",       "dollar"),
    ("Outage PV",                        "outage_pv",         "dollar"),
]


def load_scenario(name: str) -> dict:
    path = REPO_ROOT / "scenarios" / f"{name}.ctcc"
    with open(path) as f:
        return json.load(f)


def run_with_discount_rate(inputs: dict, rate: float, scenario_id: str) -> dict:
    patched = copy.deepcopy(inputs)
    patched["03_financing"]["financial"]["social_discount_rate"] = rate
    return run_calculation(combined_data=patched, scenario_id=scenario_id, quiet=True)


def fmt_dollar(val):
    if val is None:
        return "N/A"
    return f"${val / 1e9:,.3f}B"


def fmt_ratio(val):
    if val is None:
        return "N/A"
    return f"{val:.3f}"


def print_scenario_table(name: str, results_by_rate: dict):
    col_w = 16
    print(f"\n{'=' * 78}")
    print(f"  DISCOUNT-RATE SENSITIVITY: {name}")
    print(f"{'=' * 78}")

    header = f"  {'Metric':<35}"
    for rate in DISCOUNT_RATES:
        header += f"{int(rate * 100)}%".rjust(col_w)
    print(header)
    print("  " + "-" * (35 + col_w * len(DISCOUNT_RATES)))

    for label, key, kind in METRICS:
        row = f"  {label:<35}"
        for rate in DISCOUNT_RATES:
            bcr = results_by_rate[rate]["bcr"]
            val = bcr.get(key)
            if kind == "dollar":
                row += fmt_dollar(val).rjust(col_w)
            else:
                row += fmt_ratio(val).rjust(col_w)
        print(row)


def main():
    all_results = {}

    for scenario in SCENARIOS:
        print(f"Loading {scenario}...")
        data = load_scenario(scenario)
        inputs = data["inputs"]
        all_results[scenario] = {}

        for rate in DISCOUNT_RATES:
            pct = int(rate * 100)
            print(f"  Running at {pct}% discount rate...")
            result = run_with_discount_rate(inputs, rate, f"{scenario}_dr{pct}")
            all_results[scenario][rate] = result

        print_scenario_table(scenario, all_results[scenario])

    print("\nDone.")


if __name__ == "__main__":
    main()
