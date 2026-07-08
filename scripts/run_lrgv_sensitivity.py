"""LRGV sensitivity sweeps: lifetime and discount rate.

Runs three LRGV scenarios at project lifetimes of 40/50/60 years
and social discount rates of 2%/3%/5%.

Scenarios:
  - AEP_LRGV_ACCC (ACCC reconductoring)
  - AEP_LRGV_ACSR_Rebuild (ACSR structure rebuild)
  - AEP_LRGV_Laredo_NewBuild (Laredo greenfield new build)
"""

import copy
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from ctcc import run_calculation  # noqa: E402

SCENARIOS = [
    ("AEP_LRGV_ACCC", "LRGV ACCC Reconductoring"),
    ("AEP_LRGV_ACSR_Rebuild", "LRGV ACSR Structure Rebuild"),
    ("AEP_LRGV_Laredo_NewBuild", "LRGV Laredo Greenfield New Build"),
]

LIFETIMES = [40, 50, 60]
DISCOUNT_RATES = [0.02, 0.03, 0.05]


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


def run_with_discount_rate(inputs: dict, rate: float, scenario_id: str) -> dict:
    patched = copy.deepcopy(inputs)
    patched["03_financing"]["financial"]["social_discount_rate"] = rate
    return run_calculation(
        combined_data=patched,
        scenario_id=f"{scenario_id}_dr{int(rate*100)}",
        quiet=True,
    )


def fmt(val, prefix="$"):
    if val is None:
        return "N/A"
    if abs(val) >= 1e9:
        return f"{prefix}{val/1e9:.2f}B"
    elif abs(val) >= 1e6:
        return f"{prefix}{val/1e6:.0f}M"
    else:
        return f"{prefix}{val:,.0f}"


def fmt_ratio(val):
    if val is None:
        return "N/A"
    return f"{val:.2f}"


def extract_lifetime_metrics(results: dict) -> dict:
    bcr = results["bcr"]
    return {
        "bcr_societal": bcr.get("bcr_societal", 0),
        "bcr_capital_and_delay": bcr.get("bcr_capital_and_delay", 0),
        "bcr_utility": bcr.get("bcr_utility", 0),
        "bcr_excl_wf_outage": bcr.get("bcr_excluding_wildfire_risk_and_outage_risk", 0),
        "bcr_excl_avemis_outage_wf": bcr.get("bcr_excluding_avoided_emissions_and_wildfire_risk_and_outage_risk", 0),
        "net_benefit_pv": bcr.get("net_benefit_pv", 0),
    }


def extract_discount_metrics(results: dict) -> dict:
    bcr = results["bcr"]
    return {
        "bcr_ratepayer": bcr.get("bcr_ratepayer", 0),
        "bcr_excl_wf_outage": bcr.get("bcr_excluding_wildfire_risk_and_outage_risk", 0),
        "bcr_excl_avemis_outage_wf": bcr.get("bcr_excluding_avoided_emissions_and_wildfire_risk_and_outage_risk", 0),
        "avoided_emissions_pv": bcr.get("benefits_avoided_emissions_pv", 0),
        "outage_pv": bcr.get("outage_pv", 0),
        "net_benefit_pv": bcr.get("net_benefit_pv", 0),
    }


def run_lifetime_sweep():
    print("=" * 70)
    print("  LIFETIME SENSITIVITY (40 / 50 / 60 years)")
    print("=" * 70)

    all_results = {}
    for scenario_name, label in SCENARIOS:
        print(f"\nLoading {scenario_name}...")
        data = load_scenario(scenario_name)
        inputs = data["inputs"]

        results_by_lt = {}
        for lt in LIFETIMES:
            print(f"  Running with lifetime={lt}...")
            r = run_with_lifetime(inputs, lt, scenario_name)
            results_by_lt[lt] = extract_lifetime_metrics(r)

        all_results[scenario_name] = (label, results_by_lt)

        # Print table
        print(f"\n  {label}")
        print(f"  {'Metric':<30} {'40 yr':>10} {'50 yr':>10} {'60 yr':>10}")
        print(f"  {'-'*30} {'-'*10} {'-'*10} {'-'*10}")
        metrics = [
            ("BCR Societal", "bcr_societal"),
            ("BCR Capital + Delay", "bcr_capital_and_delay"),
            ("BCR Utility", "bcr_utility"),
            ("BCR Excl. WF+Outage", "bcr_excl_wf_outage"),
            ("BCR Excl. AvEmis+Out+WF", "bcr_excl_avemis_outage_wf"),
            ("Net Benefit (PV)", "net_benefit_pv"),
        ]
        for m_label, key in metrics:
            vals = []
            for lt in LIFETIMES:
                v = results_by_lt[lt][key]
                if key == "net_benefit_pv":
                    vals.append(fmt(v))
                else:
                    vals.append(fmt_ratio(v))
            print(f"  {m_label:<30} {vals[0]:>10} {vals[1]:>10} {vals[2]:>10}")

    return all_results


def run_discount_sweep():
    print("\n" + "=" * 70)
    print("  SOCIAL DISCOUNT RATE SENSITIVITY (2% / 3% / 5%)")
    print("=" * 70)

    all_results = {}
    for scenario_name, label in SCENARIOS:
        print(f"\nLoading {scenario_name}...")
        data = load_scenario(scenario_name)
        inputs = data["inputs"]

        results_by_rate = {}
        for rate in DISCOUNT_RATES:
            pct = int(rate * 100)
            print(f"  Running at {pct}% discount rate...")
            r = run_with_discount_rate(inputs, rate, scenario_name)
            results_by_rate[rate] = extract_discount_metrics(r)

        all_results[scenario_name] = (label, results_by_rate)

        # Print table
        print(f"\n  {label}")
        print(f"  {'Metric':<30} {'2%':>12} {'3%':>12} {'5%':>12}")
        print(f"  {'-'*30} {'-'*12} {'-'*12} {'-'*12}")
        metrics = [
            ("BCR Ratepayer", "bcr_ratepayer"),
            ("BCR Excl. WF+Outage", "bcr_excl_wf_outage"),
            ("BCR Excl. AvEmis+Out+WF", "bcr_excl_avemis_outage_wf"),
            ("Avoided Emissions PV", "avoided_emissions_pv"),
            ("Outage PV", "outage_pv"),
            ("Net Benefit PV", "net_benefit_pv"),
        ]
        for m_label, key in metrics:
            vals = []
            for rate in DISCOUNT_RATES:
                v = results_by_rate[rate][key]
                if "pv" in key.lower() and key != "bcr_ratepayer":
                    vals.append(fmt(v))
                else:
                    vals.append(fmt_ratio(v))
            print(f"  {m_label:<30} {vals[0]:>12} {vals[1]:>12} {vals[2]:>12}")

    return all_results


def main():
    lt_results = run_lifetime_sweep()
    dr_results = run_discount_sweep()
    print("\n\nDone. All LRGV sensitivity sweeps complete.")
    return lt_results, dr_results


if __name__ == "__main__":
    main()
