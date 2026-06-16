"""Run CTT Panhandle CREZ scenarios: 2-year delay (actual) and 7-year delay (counterfactual).

Loads S1 as template (AC greenfield overhead), patches with CTT-specific inputs
from the CREZ research document, runs both scenarios, and saves results.

Scenario A: CTT_Actual_Delay2 — what actually happened (CREZ mandate, 2yr permitting)
Scenario B: CTT_Counterfactual_Delay7 — what would have happened without CREZ mandate
"""

import copy
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from ctcc import run_calculation  # noqa: E402


def load_s1_template() -> dict:
    s1_path = REPO_ROOT / "scenarios" / "S1 CA Rural Overhead AC.ctcc"
    with open(s1_path) as f:
        return json.load(f)


def patch_ctt_inputs(inputs: dict) -> dict:
    """Patch S1 inputs with CTT Panhandle CREZ values (Scenario A: actual 2yr delay)."""

    # --- 01: Project Technical Details ---
    proj = inputs["01_project_technical_details"]
    proj["project"]["name"] = "CTT_Panhandle_345kV_1792MW_AC"
    proj["project"]["construction_type"] = "Overhead"
    proj["project"]["ac_dc"] = "AC"
    proj["project"]["number_of_converters"] = 0
    proj["project"]["capacity_mw"] = 1792
    proj["project"]["conductor_type"] = "Standard Aluminum Conductor"
    proj["project"]["converter_type"] = "NA"
    proj["project"]["converter_loss_percentage"] = None
    proj["project"]["line_utilization"] = 0.45
    proj["project"]["value_of_load_per_mwh"] = 35.0
    proj["project"]["reconductoring"] = False
    proj["project"]["uses_existing_row"] = False
    proj["project"]["old_capacity_mw"] = None
    proj["project"]["old_conductor_type"] = None
    proj["project"]["old_ac_dc"] = None
    proj["project"]["greenfield_comparison_capacity_mw"] = None
    proj["project"]["greenfield_comparison_conductor_type"] = "Standard Aluminum Conductor"
    proj["timeline"]["construction_years"] = 2
    proj["timeline"]["delay_years"] = 2
    proj["timeline"]["project_lifetime"] = 50

    # --- 02: Terrain ---
    terrain = inputs["02_project_physical_details"]["terrain"]
    terrain["terrain_miles"] = {
        "forested": 0,
        "scrubbed_flat": 160,
        "wetland": 0,
        "farmland": 60,
        "desert_barren": 5,
        "urban": 0,
        "rolling_hills": 15,
        "mountain": 0,
        "subsea": 0,
    }

    # --- 03: Financial ---
    fin = inputs["03_financing"]["financial"]
    fin["inflation_rate"] = 0.025
    fin["base_year"] = 2026
    fin["wacc_nominal"] = 0.0693
    fin["social_discount_rate"] = 0.02
    fin["contingencies"]["conductor_contingency"] = 0.10
    fin["contingencies"]["structure_contingency"] = 0.10
    fin["contingencies"]["converter_contingency"] = 0.10
    fin["afudc"]["apply_afudc"] = True
    fin["afudc"]["delay_period_active_work"] = True
    fin["revenue"]["rate_based"]["enabled"] = True
    fin["revenue"]["rate_based"]["allowed_return_rate"] = 0.096

    # --- 05: Delay Costs (Scenario A: streamlined CREZ permitting) ---
    inputs["05_delays"]["annual_delay_costs"] = {
        "legal": 500000,
        "admin": 300000,
        "labor": 1000000,
        "material_and_equipment": 500000,
        "regulatory": 800000,
        "public_relations": 200000,
        "project_management": 1500000,
        "miscellaneous": 200000,
    }

    # --- 06: Wildfire (ZEROED) ---
    wf = inputs["06_wildfire_costs"]["wildfire"]
    wf["severity_per_event"] = 0
    wf["risk_growth_rate"] = 0.0
    wf["discount_rate_source"] = "social"
    wf["base_ignition_rate"] = 0.0

    # --- 07: Outage (ZEROED) ---
    out = inputs["07_outage_costs"]["outage"]
    out["risk_growth_rate"] = 0.0
    out["capacity_at_risk_factor"] = 1.0
    out["outage_rate"] = {"overhead": 0.0, "underground": 0.0, "subsea": 0.0}

    # --- 11: ROW Details ---
    row = inputs["11_project_row_details"]["right_of_way"]
    for zone_key in row:
        row[zone_key]["miles"] = 0
    row["zone_1"]["miles"] = 180
    row["zone_1"]["acquisition_cost"] = 299
    row["zone_1"]["rent_cost"] = 9.70
    row["zone_1"]["hold_cost"] = 0.97
    row["zone_2"]["miles"] = 50
    row["zone_2"]["acquisition_cost"] = 579
    row["zone_2"]["rent_cost"] = 18.78
    row["zone_2"]["hold_cost"] = 1.878
    row["zone_3"]["miles"] = 10
    row["zone_3"]["acquisition_cost"] = 1132
    row["zone_3"]["rent_cost"] = 36.72
    row["zone_3"]["hold_cost"] = 3.67

    # --- 16: Emissions ---
    em = inputs["16_emissions_reductions"]["emissions_reductions"]
    em["compensation_percent"] = 0.90
    em["societal_costs_per_kg"]["co2_cost_per_kg"] = 0.190
    em["societal_costs_per_kg"]["sox_cost_per_kg"] = 6.2
    em["societal_costs_per_kg"]["nox_cost_per_kg"] = 5.0

    # --- 17: Congestion/Curtailment ---
    cc = inputs["17_congestion_curtailment_reductions"]
    gf = cc["greenfield_congestion_curtailment_reductions"]
    gf["congestion"]["constraints"]["flow_factor"] = 0.50
    gf["congestion"]["constraints"]["binding_hours"] = 1800
    gf["congestion"]["constraints"]["average_exceedance"] = 600
    gf["congestion"]["constraints"]["near_binding_hours"] = 400
    gf["congestion"]["constraints"]["near_average_exceedance"] = 150
    gf["congestion"]["constraints"]["near_binding_relief_factor"] = 0.25
    gf["congestion"]["costs"]["average_congestion_price"] = 11.47
    gf["curtailment"]["curtailment_hours_total"] = 2500
    gf["curtailment"]["average_curtailment_mw"] = 500
    gf["curtailment"]["average_curtailment_price"] = 30

    # --- 18: Energy Source Mix ---
    mix = inputs["18_energy_source_mix"]
    mix["energy_source_mix"] = {
        "coal": {"percentage": 37, "rate_of_change": -0.06},
        "oil": {"percentage": 1, "rate_of_change": -0.05},
        "natural_gas": {"percentage": 41, "rate_of_change": 0.01},
        "solar": {"percentage": 1, "rate_of_change": 0.12},
        "wind": {"percentage": 8, "rate_of_change": 0.08},
        "hydro": {"percentage": 1, "rate_of_change": 0.0},
        "nuclear": {"percentage": 10, "rate_of_change": 0.0},
        "other": {"percentage": 1, "rate_of_change": 0.0},
    }
    mix["counterfactual_energy_source_mix"] = {
        "coal": {"percentage": 37, "rate_of_change": -0.02},
        "oil": {"percentage": 1, "rate_of_change": -0.03},
        "natural_gas": {"percentage": 41, "rate_of_change": 0.02},
        "solar": {"percentage": 1, "rate_of_change": 0.05},
        "wind": {"percentage": 8, "rate_of_change": 0.02},
        "hydro": {"percentage": 1, "rate_of_change": 0.0},
        "nuclear": {"percentage": 10, "rate_of_change": 0.0},
        "other": {"percentage": 1, "rate_of_change": 0.0},
    }

    return inputs


def run_scenario(inputs: dict, scenario_id: str) -> dict:
    """Run a single scenario and return results."""
    return run_calculation(
        combined_data=inputs,
        scenario_id=scenario_id,
        quiet=True,
    )


def save_ctcc_file(inputs: dict, results: dict, name: str, scenario_id: str):
    """Save a complete .ctcc file with inputs, results, and metadata."""
    from datetime import datetime

    ctcc = {
        "version": "1.0",
        "customName": name,
        "inputs": inputs,
        "results": results,
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "scenario_id": scenario_id,
            "source": "ctt_panhandle_crez_case_study",
        },
    }
    out_path = REPO_ROOT / "scenarios" / f"{name}.ctcc"
    with open(out_path, "w") as f:
        json.dump(ctcc, f, indent=2, default=str)
    print(f"  Saved: {out_path}")


def fmt(val, prefix="$"):
    """Format large numbers with B/M suffixes."""
    if abs(val) >= 1e9:
        return f"{prefix}{val/1e9:.2f}B"
    elif abs(val) >= 1e6:
        return f"{prefix}{val/1e6:.1f}M"
    else:
        return f"{prefix}{val:,.0f}"


def print_results(results: dict, label: str):
    """Print key results for a scenario."""
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")

    costs = results["costs"]
    benefits = results["benefits"]
    bcr = results["bcr"]

    print(f"\n  --- COSTS (PV) ---")
    print(f"  Build (capital):        {fmt(costs['build']['total_pv'])}")
    print(f"  ROW (capital):          {fmt(costs['row']['row_capital_pv'])}")
    print(f"  Environmental:          {fmt(costs['environmental']['total_pv'])}")
    print(f"  Insurance:              {fmt(costs['insurance']['pv_total'])}")
    print(f"  O&M:                    {fmt(costs['oandm']['total_pv'])}")
    print(f"  ROW rent:               {fmt(costs['row']['row_rent_pv'])}")
    print(f"  Line losses:            {fmt(costs['line_loss']['total_pv'])}")
    print(f"  Delay (base):           {fmt(costs['delay']['total_pv'])}")
    print(f"  Wildfire:               {fmt(costs['wildfire']['pv_cost'])}")
    print(f"  Outage:                 {fmt(costs['outage']['pv_cost'])}")
    print(f"  Emissions (loss-comp):  {fmt(costs['emissions']['total_pv'])}")
    print(f"  Facilitated emissions:  {fmt(costs['facilitated_emissions']['fac_emissions_project_pv'])}")

    cc = benefits["congestion_curtailment"]
    print(f"\n  --- BENEFITS (PV) ---")
    print(f"  Congestion relief:      {fmt(cc['congestion_benefit_pv'])}")
    print(f"  Curtailment relief:     {fmt(cc['curtailment_benefit_pv'])}")
    print(f"  Delivered energy:       {fmt(cc['delivered_benefit_pv'])}")
    print(f"  Revenue (transfer):     {fmt(benefits['revenue']['revenue_pv'])}")

    print(f"\n  --- DELAY COSTS (embedded in benefits) ---")
    print(f"  Congestion delay cost:  {fmt(cc['congestion_delay_cost_pv'])}")
    print(f"  Curtailment delay cost: {fmt(cc['curtailment_delay_cost_pv'])}")

    print(f"\n  --- BCR RATIOS ---")
    print(f"  BCR System (societal):  {bcr.get('bcr_system', 'N/A'):.3f}")
    print(f"  BCR Capital Only:       {bcr.get('bcr_capital', 'N/A'):.3f}")
    if "bcr_capital_and_delay" in bcr:
        print(f"  BCR Capital + Delay:    {bcr['bcr_capital_and_delay']:.3f}")
    print(f"  BCR Utility:            {bcr.get('bcr_utility', 'N/A'):.3f}")
    print(f"  BCR Ratepayer:          {bcr.get('bcr_ratepayer', 'N/A'):.3f}")
    excl_wf = bcr.get("bcr_excluding_wildfire_risk")
    if excl_wf:
        print(f"  BCR Excl. Wildfire:     {excl_wf:.3f}")
    excl_both = bcr.get("bcr_excluding_wildfire_risk_and_outage_risk")
    if excl_both:
        print(f"  BCR Excl. WF+Outage:   {excl_both:.3f}")

    print(f"\n  --- SUMMARY ---")
    print(f"  Total costs PV:         {fmt(bcr.get('total_costs_pv', 0))}")
    print(f"  Total benefits PV:      {fmt(bcr.get('total_benefits_pv', 0))}")
    print(f"  Net benefit PV:         {fmt(bcr.get('net_benefit_pv', 0))}")


def main():
    print("Loading S1 template...")
    template = load_s1_template()

    # --- Scenario A: CTT with 2-year delay (actual CREZ mandate) ---
    print("\nBuilding CTT Panhandle (2-year delay, actual) scenario...")
    inputs_actual = patch_ctt_inputs(copy.deepcopy(template["inputs"]))

    print("Running calculation (delay=2, actual)...")
    results_actual = run_scenario(inputs_actual, "CTT_Actual_Delay2")
    print_results(results_actual, "CTT Panhandle — 2-Year Delay (Actual CREZ)")

    # --- Scenario B: CTT with 7-year delay (counterfactual, no CREZ mandate) ---
    print("\n\nBuilding CTT Panhandle (7-year delay, counterfactual) scenario...")
    inputs_counterfactual = copy.deepcopy(inputs_actual)
    inputs_counterfactual["01_project_technical_details"]["timeline"]["delay_years"] = 7
    inputs_counterfactual["05_delays"]["annual_delay_costs"] = {
        "legal": 2000000,
        "admin": 600000,
        "labor": 1500000,
        "material_and_equipment": 1000000,
        "regulatory": 2500000,
        "public_relations": 1000000,
        "project_management": 2500000,
        "miscellaneous": 900000,
    }

    print("Running calculation (delay=7, counterfactual)...")
    results_cf = run_scenario(inputs_counterfactual, "CTT_Counterfactual_Delay7")
    print_results(results_cf, "CTT Panhandle — 7-Year Delay (Counterfactual)")

    # --- Save .ctcc files ---
    print("\n\nSaving scenario files...")
    save_ctcc_file(inputs_actual, results_actual, "CTT_Actual_Delay2", "CTT_Actual_Delay2")
    save_ctcc_file(
        inputs_counterfactual, results_cf, "CTT_Counterfactual_Delay7", "CTT_Counterfactual_Delay7"
    )

    # --- Comparison ---
    bcr_a = results_actual["bcr"]
    bcr_b = results_cf["bcr"]
    print(f"\n{'='*60}")
    print(f"  DELAY IMPACT COMPARISON: CTT Panhandle CREZ")
    print(f"{'='*60}")
    print(f"  BCR System:  {bcr_a.get('bcr_system',0):.3f} (2yr) vs {bcr_b.get('bcr_system',0):.3f} (7yr)")
    print(f"  Net Benefit: {fmt(bcr_a.get('net_benefit_pv',0))} (2yr) vs {fmt(bcr_b.get('net_benefit_pv',0))} (7yr)")
    delta_nb = bcr_a.get("net_benefit_pv", 0) - bcr_b.get("net_benefit_pv", 0)
    print(f"  Value of CREZ mandate (avoided delay cost): {fmt(delta_nb)}")

    # Delay-specific costs
    cc_a = results_actual["benefits"]["congestion_curtailment"]
    cc_b = results_cf["benefits"]["congestion_curtailment"]
    forgone_cong = cc_b["congestion_delay_cost_pv"] - cc_a["congestion_delay_cost_pv"]
    forgone_curt = cc_b["curtailment_delay_cost_pv"] - cc_a["curtailment_delay_cost_pv"]
    delay_cost_a = results_actual["costs"]["delay"]["total_pv"]
    delay_cost_b = results_cf["costs"]["delay"]["total_pv"]
    print(f"\n  --- DELAY DECOMPOSITION ---")
    print(f"  Direct delay costs:     {fmt(delay_cost_a)} (2yr) vs {fmt(delay_cost_b)} (7yr)")
    print(f"  Additional forgone congestion relief: {fmt(forgone_cong)}")
    print(f"  Additional forgone curtailment relief: {fmt(forgone_curt)}")
    print(f"  Total social cost of 5 extra years: {fmt(delta_nb)}")

    # Validation against actuals
    build_pv = results_actual["costs"]["build"]["total_pv"]
    print(f"\n  --- VALIDATION ---")
    print(f"  CTCC build cost PV:     {fmt(build_pv)}")
    print(f"  CTT actual all-in cost: ~$450M (2013$), ~$560M (2026$, 2.5% inflation)")
    print(f"  CTCC annual benefits:   {fmt((cc_a['congestion_benefit_pv'] + cc_a['curtailment_benefit_pv']) / 50)}/yr (approx)")
    print(f"  Observed CTT benefits:  $110M-$220M/year (estimated attribution)")

    print("\nDone.")


if __name__ == "__main__":
    main()
