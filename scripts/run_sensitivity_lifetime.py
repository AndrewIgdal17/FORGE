"""Run project lifetime sensitivity for SunZia and CTT CREZ scenarios.

SunZia: 35, 40, 50 years (HVDC converter-limited to overhead-line range)
CTT: 45, 50, 60 years (FERC depreciation study range for AC overhead)

Outputs key BCR metrics at each lifetime value.
"""

import copy
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from ctcc import run_calculation  # noqa: E402


def load_scenario(name: str) -> dict:
    path = REPO_ROOT / "scenarios" / f"{name}.ctcc"
    with open(path) as f:
        return json.load(f)


def run_with_lifetime(inputs: dict, lifetime: int, scenario_id: str) -> dict:
    patched = copy.deepcopy(inputs)
    patched["01_project_technical_details"]["timeline"]["project_lifetime"] = lifetime
    return run_calculation(combined_data=patched, scenario_id=scenario_id, quiet=True)


def fmt_b(val):
    return f"${val/1e9:.2f}B"


def fmt_ratio(val):
    if val is None:
        return "N/A"
    return f"{val:.2f}"


def print_sensitivity_table(name: str, lifetimes: list, results_list: list):
    print(f"\n{'='*70}")
    print(f"  LIFETIME SENSITIVITY: {name}")
    print(f"{'='*70}")
    header = f"  {'Metric':<30}" + "".join(f"{'  ' + str(l) + ' yr':<12}" for l in lifetimes)
    print(header)
    print("  " + "-" * (30 + 12 * len(lifetimes)))

    metrics = [
        ("BCR Societal", "bcr_societal"),
        ("BCR Utility", "bcr_utility"),
        ("BCR Ratepayer", "bcr_ratepayer"),
        ("BCR Excl. WF+Outage", "bcr_excluding_wildfire_risk_and_outage_risk"),
        ("Net Benefit PV", "net_benefit_pv"),
        ("Total Costs PV", "total_costs_pv"),
        ("Total Benefits PV", "total_benefits_pv"),
    ]

    for label, key in metrics:
        row = f"  {label:<30}"
        for r in results_list:
            val = r["bcr"].get(key)
            if val is None:
                row += f"{'  N/A':<12}"
            elif "pv" in key.lower():
                row += f"{'  ' + fmt_b(val):<12}"
            else:
                row += f"{'  ' + fmt_ratio(val):<12}"
        print(row)


def main():
    # --- SunZia sensitivity (35, 40, 50 years) ---
    print("Loading SunZia_Delay17...")
    sunzia = load_scenario("SunZia_Delay17")
    sunzia_inputs = sunzia["inputs"]

    sunzia_lifetimes = [35, 40, 50]
    sunzia_results = []
    for lt in sunzia_lifetimes:
        print(f"  Running SunZia at {lt} years...")
        r = run_with_lifetime(sunzia_inputs, lt, f"SunZia_{lt}yr")
        sunzia_results.append(r)

    print_sensitivity_table("SunZia (17-year delay)", sunzia_lifetimes, sunzia_results)

    # Also run with 2-year delay for comparison
    print("\nLoading SunZia_Delay2...")
    sunzia2 = load_scenario("SunZia_Delay2")
    sunzia2_inputs = sunzia2["inputs"]

    sunzia2_results = []
    for lt in sunzia_lifetimes:
        print(f"  Running SunZia (2yr delay) at {lt} years...")
        r = run_with_lifetime(sunzia2_inputs, lt, f"SunZia_2yr_{lt}yr")
        sunzia2_results.append(r)

    print_sensitivity_table("SunZia (2-year delay, CREZ-style)", sunzia_lifetimes, sunzia2_results)

    # --- CTT sensitivity (45, 50, 60 years) ---
    print("\nLoading CTT_Actual_Delay2...")
    ctt = load_scenario("CTT_Actual_Delay2")
    ctt_inputs = ctt["inputs"]

    ctt_lifetimes = [45, 50, 60]
    ctt_results = []
    for lt in ctt_lifetimes:
        print(f"  Running CTT at {lt} years...")
        r = run_with_lifetime(ctt_inputs, lt, f"CTT_{lt}yr")
        ctt_results.append(r)

    print_sensitivity_table("CTT CREZ (2-year delay)", ctt_lifetimes, ctt_results)

    # CTT counterfactual (7-year delay)
    print("\nLoading CTT_Counterfactual_Delay7...")
    ctt7 = load_scenario("CTT_Counterfactual_Delay7")
    ctt7_inputs = ctt7["inputs"]

    ctt7_results = []
    for lt in ctt_lifetimes:
        print(f"  Running CTT (7yr delay) at {lt} years...")
        r = run_with_lifetime(ctt7_inputs, lt, f"CTT_7yr_{lt}yr")
        ctt7_results.append(r)

    print_sensitivity_table("CTT CREZ (7-year delay counterfactual)", ctt_lifetimes, ctt7_results)

    # --- Summary comparison ---
    print(f"\n{'='*70}")
    print(f"  SUMMARY: BCR Societal across lifetime assumptions")
    print(f"{'='*70}")
    print(f"  {'Scenario':<35}{'Low':<10}{'Base':<10}{'High':<10}")
    print(f"  {'-'*65}")
    print(f"  {'SunZia 17yr delay':<35}{fmt_ratio(sunzia_results[0]['bcr']['bcr_societal']):<10}{fmt_ratio(sunzia_results[1]['bcr']['bcr_societal']):<10}{fmt_ratio(sunzia_results[2]['bcr']['bcr_societal']):<10}")
    print(f"  {'SunZia 2yr delay (CREZ)':<35}{fmt_ratio(sunzia2_results[0]['bcr']['bcr_societal']):<10}{fmt_ratio(sunzia2_results[1]['bcr']['bcr_societal']):<10}{fmt_ratio(sunzia2_results[2]['bcr']['bcr_societal']):<10}")
    print(f"  {'CTT 2yr delay':<35}{fmt_ratio(ctt_results[0]['bcr']['bcr_societal']):<10}{fmt_ratio(ctt_results[1]['bcr']['bcr_societal']):<10}{fmt_ratio(ctt_results[2]['bcr']['bcr_societal']):<10}")
    print(f"  {'CTT 7yr delay':<35}{fmt_ratio(ctt7_results[0]['bcr']['bcr_societal']):<10}{fmt_ratio(ctt7_results[1]['bcr']['bcr_societal']):<10}{fmt_ratio(ctt7_results[2]['bcr']['bcr_societal']):<10}")
    print(f"\n  Lifetimes: SunZia [{sunzia_lifetimes}], CTT [{ctt_lifetimes}]")

    print("\nDone.")


if __name__ == "__main__":
    main()
