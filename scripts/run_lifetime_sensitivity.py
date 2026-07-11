"""Lifetime sensitivity analysis: sweep project_lifetime across FERC depreciation range.

Runs SunZia (17-yr delay) and CTT (2-yr delay) at project lifetimes of 40, 50, and 60 years.
FERC depreciation studies for transmission plant typically use average service lives of 45-65 years
(FERC Accounts 353-356). HVDC converter components have 35-40 year maintainable lives (Springer/CIGRE),
while overhead line structures last 60-80 years (UQ comparison study).

Outputs key BCR metrics for each lifetime value.
"""

import copy
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from ctcc import run_calculation  # noqa: E402

LIFETIMES = [40, 50, 60]


def load_scenario(name: str) -> dict:
    path = REPO_ROOT / "scenarios" / f"{name}.ctcc"
    with open(path) as f:
        return json.load(f)


def run_with_lifetime(inputs: dict, lifetime: int, scenario_id: str) -> dict:
    patched = copy.deepcopy(inputs)
    patched["01_project_technical_details"]["timeline"]["project_lifetime"] = lifetime
    return run_calculation(
        combined_data=patched,
        scenario_id=f"{scenario_id}_L{lifetime}",
        quiet=True,
    )


def extract_metrics(results: dict) -> dict:
    bcr = results["bcr"]
    costs = results["costs"]
    return {
        "bcr_societal": bcr.get("bcr_societal", 0),
        "bcr_system": bcr.get("bcr_system", 0),
        "bcr_capital_and_delay": bcr.get("bcr_capital_and_delay", 0),
        "bcr_utility": bcr.get("bcr_utility", 0),
        "bcr_excl_wf_outage": bcr.get("bcr_excluding_wildfire_risk_and_outage_risk", 0),
        "bcr_excl_avoided_emissions_and_outage": bcr.get("bcr_excluding_avoided_emissions_and_outage_risk", 0),
        "total_costs_pv": bcr.get("total_costs_pv", 0),
        "total_benefits_pv": bcr.get("total_benefits_pv", 0),
        "net_benefit_pv": bcr.get("net_benefit_pv", 0),
        "build_cost_pv": costs["build"]["total_pv"],
        "displacement_avoided_pv": bcr.get("displacement_avoided_cost_pv", 0),
    }


def fmt(val, prefix="$"):
    if abs(val) >= 1e9:
        return f"{prefix}{val/1e9:.2f}B"
    elif abs(val) >= 1e6:
        return f"{prefix}{val/1e6:.0f}M"
    else:
        return f"{prefix}{val:,.0f}"


def print_sensitivity_table(project_name: str, results_by_lifetime: dict):
    print(f"\n{'='*70}")
    print(f"  {project_name} — Lifetime Sensitivity (40 / 50 / 60 years)")
    print(f"{'='*70}")
    print(f"  {'Metric':<35} {'40 yr':>10} {'50 yr':>10} {'60 yr':>10}")
    print(f"  {'-'*35} {'-'*10} {'-'*10} {'-'*10}")

    metrics_to_show = [
        ("BCR Societal", "bcr_societal", "{:.3f}"),
        ("BCR System", "bcr_system", "{:.3f}"),
        ("BCR Capital + Delay", "bcr_capital_and_delay", "{:.2f}"),
        ("BCR Utility", "bcr_utility", "{:.3f}"),
        ("BCR Excl. WF+Outage", "bcr_excl_wf_outage", "{:.2f}"),
        ("BCR Excl. AvEmis+Outage", "bcr_excl_avoided_emissions_and_outage", "{:.3f}"),
        ("Net Benefit (PV)", "net_benefit_pv", "fmt"),
        ("Total Benefits (PV)", "total_benefits_pv", "fmt"),
        ("Total Costs (PV)", "total_costs_pv", "fmt"),
        ("Avoided Emissions (PV)", "displacement_avoided_pv", "fmt"),
    ]

    for label, key, format_str in metrics_to_show:
        vals = []
        for lt in LIFETIMES:
            v = results_by_lifetime[lt][key]
            if format_str == "fmt":
                vals.append(fmt(v))
            else:
                vals.append(format_str.format(v))
        print(f"  {label:<35} {vals[0]:>10} {vals[1]:>10} {vals[2]:>10}")


def main():
    # --- SunZia (17-year delay) ---
    print("Loading SunZia_Delay17...")
    sunzia = load_scenario("SunZia_Delay17")
    sunzia_inputs = sunzia["inputs"]

    sunzia_results = {}
    for lt in LIFETIMES:
        print(f"  Running SunZia with lifetime={lt}...")
        r = run_with_lifetime(sunzia_inputs, lt, "SunZia_Delay17")
        sunzia_results[lt] = extract_metrics(r)

    print_sensitivity_table("SunZia (17-year delay, actual)", sunzia_results)

    # --- SunZia (2-year delay, CREZ-style) ---
    print("\nLoading SunZia_Delay2...")
    sunzia2 = load_scenario("SunZia_Delay2")
    sunzia2_inputs = sunzia2["inputs"]

    sunzia2_results = {}
    for lt in LIFETIMES:
        print(f"  Running SunZia (2yr) with lifetime={lt}...")
        r = run_with_lifetime(sunzia2_inputs, lt, "SunZia_Delay2")
        sunzia2_results[lt] = extract_metrics(r)

    print_sensitivity_table("SunZia (2-year delay, CREZ-style)", sunzia2_results)

    # --- CTT (2-year delay, actual) ---
    print("\nLoading CTT_Actual_Delay2...")
    ctt = load_scenario("CTT_Actual_Delay2")
    ctt_inputs = ctt["inputs"]

    ctt_results = {}
    for lt in LIFETIMES:
        print(f"  Running CTT with lifetime={lt}...")
        r = run_with_lifetime(ctt_inputs, lt, "CTT_Delay2")
        ctt_results[lt] = extract_metrics(r)

    print_sensitivity_table("CTT CREZ (2-year delay, actual)", ctt_results)

    # --- CTT (7-year delay, counterfactual) ---
    print("\nLoading CTT_Counterfactual_Delay7...")
    ctt7 = load_scenario("CTT_Counterfactual_Delay7")
    ctt7_inputs = ctt7["inputs"]

    ctt7_results = {}
    for lt in LIFETIMES:
        print(f"  Running CTT (7yr) with lifetime={lt}...")
        r = run_with_lifetime(ctt7_inputs, lt, "CTT_Delay7")
        ctt7_results[lt] = extract_metrics(r)

    print_sensitivity_table("CTT CREZ (7-year delay, counterfactual)", ctt7_results)

    # --- TBC (4-year delay, actual) ---
    print("\nLoading TBC_Delay4...")
    tbc = load_scenario("TBC_Delay4")
    tbc_inputs = tbc["inputs"]

    tbc_results = {}
    for lt in LIFETIMES:
        print(f"  Running TBC with lifetime={lt}...")
        r = run_with_lifetime(tbc_inputs, lt, "TBC_Delay4")
        tbc_results[lt] = extract_metrics(r)

    print_sensitivity_table("Trans Bay Cable (4-year delay, actual)", tbc_results)

    # --- TBC (0-year delay, counterfactual) ---
    print("\nLoading TBC_NoDelay...")
    tbc0 = load_scenario("TBC_NoDelay")
    tbc0_inputs = tbc0["inputs"]

    tbc0_results = {}
    for lt in LIFETIMES:
        print(f"  Running TBC (0yr) with lifetime={lt}...")
        r = run_with_lifetime(tbc0_inputs, lt, "TBC_NoDelay")
        tbc0_results[lt] = extract_metrics(r)

    print_sensitivity_table("Trans Bay Cable (0-year delay, counterfactual)", tbc0_results)

    # --- VW1 (6-year delay, actual) ---
    vw1_lifetimes = [25, 30, 40]
    print("\nLoading VW1_Delay6...")
    vw1 = load_scenario("VW1_Delay6")
    vw1_inputs = vw1["inputs"]

    vw1_results = {}
    for lt in vw1_lifetimes:
        print(f"  Running VW1 with lifetime={lt}...")
        r = run_with_lifetime(vw1_inputs, lt, "VW1_Delay6")
        vw1_results[lt] = extract_metrics(r)

    print(f"\n{'='*70}")
    print(f"  Vineyard Wind 1 (6-year delay, actual) — Lifetime Sensitivity (25 / 30 / 40 years)")
    print(f"{'='*70}")
    print(f"  {'Metric':<35} {'25 yr':>10} {'30 yr':>10} {'40 yr':>10}")
    print(f"  {'-'*35} {'-'*10} {'-'*10} {'-'*10}")
    for label, key, format_str in [
        ("BCR Societal", "bcr_societal", "{:.3f}"),
        ("BCR System", "bcr_system", "{:.3f}"),
        ("BCR Capital + Delay", "bcr_capital_and_delay", "{:.2f}"),
        ("BCR Utility", "bcr_utility", "{:.3f}"),
        ("BCR Excl. WF+Outage", "bcr_excl_wf_outage", "{:.2f}"),
        ("BCR Excl. AvEmis+Outage", "bcr_excl_avoided_emissions_and_outage", "{:.3f}"),
        ("Net Benefit (PV)", "net_benefit_pv", "fmt"),
        ("Total Benefits (PV)", "total_benefits_pv", "fmt"),
        ("Total Costs (PV)", "total_costs_pv", "fmt"),
        ("Avoided Emissions (PV)", "displacement_avoided_pv", "fmt"),
    ]:
        vals = []
        for lt in vw1_lifetimes:
            v = vw1_results[lt][key]
            vals.append(fmt(v) if format_str == "fmt" else format_str.format(v))
        print(f"  {label:<35} {vals[0]:>10} {vals[1]:>10} {vals[2]:>10}")

    # --- VW1 (2-year delay, counterfactual) ---
    print("\nLoading VW1_Delay2...")
    vw1_2 = load_scenario("VW1_Delay2")
    vw1_2_inputs = vw1_2["inputs"]

    vw1_2_results = {}
    for lt in vw1_lifetimes:
        print(f"  Running VW1 (2yr) with lifetime={lt}...")
        r = run_with_lifetime(vw1_2_inputs, lt, "VW1_Delay2")
        vw1_2_results[lt] = extract_metrics(r)

    print(f"\n{'='*70}")
    print(f"  Vineyard Wind 1 (2-year delay, streamlined) — Lifetime Sensitivity (25 / 30 / 40 years)")
    print(f"{'='*70}")
    print(f"  {'Metric':<35} {'25 yr':>10} {'30 yr':>10} {'40 yr':>10}")
    print(f"  {'-'*35} {'-'*10} {'-'*10} {'-'*10}")
    for label, key, format_str in [
        ("BCR Societal", "bcr_societal", "{:.3f}"),
        ("BCR System", "bcr_system", "{:.3f}"),
        ("BCR Capital + Delay", "bcr_capital_and_delay", "{:.2f}"),
        ("BCR Utility", "bcr_utility", "{:.3f}"),
        ("BCR Excl. WF+Outage", "bcr_excl_wf_outage", "{:.2f}"),
        ("BCR Excl. AvEmis+Outage", "bcr_excl_avoided_emissions_and_outage", "{:.3f}"),
        ("Net Benefit (PV)", "net_benefit_pv", "fmt"),
        ("Total Benefits (PV)", "total_benefits_pv", "fmt"),
        ("Total Costs (PV)", "total_costs_pv", "fmt"),
        ("Avoided Emissions (PV)", "displacement_avoided_pv", "fmt"),
    ]:
        vals = []
        for lt in vw1_lifetimes:
            v = vw1_2_results[lt][key]
            vals.append(fmt(v) if format_str == "fmt" else format_str.format(v))
        print(f"  {label:<35} {vals[0]:>10} {vals[1]:>10} {vals[2]:>10}")

    print("\nDone.")


if __name__ == "__main__":
    main()
