"""Run SunZia CTCC scenarios: 17-year delay (actual) and 0-year delay (counterfactual).

Loads S9 as template, patches with SunZia-specific inputs from the research document,
runs both scenarios through the calculation engine, and saves results.
"""

import copy
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from ctcc import run_calculation  # noqa: E402


def load_s9_template() -> dict:
    s9_path = REPO_ROOT / "scenarios" / "S9 Wind HVDC Standard.ctcc"
    with open(s9_path) as f:
        return json.load(f)


def patch_sunzia_inputs(inputs: dict) -> dict:
    """Patch S9 inputs with SunZia-specific values."""

    # --- Tab 1: Project Technical Details ---
    proj = inputs["01_project_technical_details"]
    proj["project"]["name"] = "SunZia_HVDC_2400MW_StandardAluminum_VSC"
    proj["project"]["construction_type"] = "Overhead"
    proj["project"]["ac_dc"] = "DC"
    proj["project"]["capacity_mw"] = 2400
    proj["project"]["conductor_type"] = "Standard Aluminum Conductor"
    proj["project"]["converter_type"] = "VSC Converter"
    proj["project"]["number_of_converters"] = 2
    proj["project"]["converter_loss_percentage"] = None
    proj["project"]["line_utilization"] = 0.67
    proj["project"]["value_of_load_per_mwh"] = 30.0
    proj["project"]["reconductoring"] = False
    proj["project"]["uses_existing_row"] = False
    proj["project"]["old_capacity_mw"] = None
    proj["project"]["old_conductor_type"] = None
    proj["project"]["old_ac_dc"] = None
    proj["timeline"]["construction_years"] = 3
    proj["timeline"]["delay_years"] = 17
    proj["timeline"]["project_lifetime"] = 40

    # --- Tab 2: Terrain Miles ---
    terrain = inputs["02_project_physical_details"]["terrain"]
    terrain["terrain_miles"] = {
        "forested": 0,
        "scrubbed_flat": 100,
        "wetland": 0,
        "farmland": 10,
        "desert_barren": 350,
        "urban": 0,
        "rolling_hills": 60,
        "mountain": 30,
        "subsea": 0,
    }

    # --- Tab 2: ROW Zones ---
    row = inputs["11_project_row_details"]["right_of_way"]
    for zone_key in row:
        row[zone_key]["miles"] = 0
    row["zone_1"]["miles"] = 183
    row["zone_1"]["acquisition_cost"] = 299
    row["zone_1"]["rent_cost"] = 9.70
    row["zone_1"]["hold_cost"] = 0.97
    row["zone_2"]["miles"] = 220
    row["zone_2"]["acquisition_cost"] = 579
    row["zone_2"]["rent_cost"] = 18.78
    row["zone_2"]["hold_cost"] = 1.878
    row["zone_3"]["miles"] = 147
    row["zone_3"]["acquisition_cost"] = 1132
    row["zone_3"]["rent_cost"] = 36.72
    row["zone_3"]["hold_cost"] = 3.67

    # --- Tab 3: Financial ---
    fin = inputs["03_financing"]["financial"]
    fin["base_year"] = 2025
    fin["inflation_rate"] = 0.03
    fin["wacc_nominal"] = 0.075
    fin["social_discount_rate"] = 0.03
    fin["contingencies"]["conductor_contingency"] = 0.10
    fin["contingencies"]["structure_contingency"] = 0.10
    fin["contingencies"]["converter_contingency"] = 0.10
    fin["afudc"]["apply_afudc"] = True
    fin["afudc"]["delay_period_active_work"] = False
    fin["revenue"]["rate_based"]["enabled"] = True
    fin["revenue"]["rate_based"]["allowed_return_rate"] = 0.10

    # --- Tab 5: Delay Costs ---
    inputs["05_delays"]["annual_delay_costs"] = {
        "legal": 2500000,
        "admin": 800000,
        "labor": 1000000,
        "material_and_equipment": 500000,
        "regulatory": 3000000,
        "public_relations": 500000,
        "project_management": 2000000,
        "miscellaneous": 500000,
    }

    # --- Tab 6: Wildfire ---
    wf = inputs["06_wildfire_costs"]["wildfire"]
    wf["severity_per_event"] = 500000000
    wf["risk_growth_rate"] = 0.01
    wf["discount_rate_source"] = "social"

    # --- Tab 7: Outage ---
    out = inputs["07_outage_costs"]["outage"]
    out["capacity_at_risk_factor"] = 1.0
    out["risk_growth_rate"] = 0.0

    # --- Tab 17: Congestion/Curtailment ---
    cc = inputs["17_congestion_curtailment_reductions"]
    gf = cc["greenfield_congestion_curtailment_reductions"]
    gf["congestion"]["constraints"]["flow_factor"] = 1.0
    gf["congestion"]["constraints"]["binding_hours"] = 4000
    gf["congestion"]["constraints"]["average_exceedance"] = 500
    gf["congestion"]["constraints"]["near_binding_hours"] = 0
    gf["congestion"]["constraints"]["near_average_exceedance"] = 0
    gf["congestion"]["constraints"]["near_binding_relief_factor"] = 0.25
    gf["congestion"]["costs"]["average_congestion_price"] = 15
    gf["curtailment"]["curtailment_hours_total"] = 2000
    gf["curtailment"]["average_curtailment_mw"] = 800
    gf["curtailment"]["average_curtailment_price"] = 41

    # --- Tab 18: Energy Source Mix ---
    mix = inputs["18_energy_source_mix"]
    mix["energy_source_mix"] = {
        "coal": {"percentage": 0, "rate_of_change": 0.0},
        "oil": {"percentage": 0, "rate_of_change": 0.0},
        "natural_gas": {"percentage": 5, "rate_of_change": -0.01},
        "solar": {"percentage": 0, "rate_of_change": 0.0},
        "wind": {"percentage": 95, "rate_of_change": 0.01},
        "hydro": {"percentage": 0, "rate_of_change": 0.0},
        "nuclear": {"percentage": 0, "rate_of_change": 0.0},
        "other": {"percentage": 0, "rate_of_change": 0.0},
    }
    mix["counterfactual_energy_source_mix"] = {
        "coal": {"percentage": 8, "rate_of_change": -0.03},
        "oil": {"percentage": 0, "rate_of_change": 0.0},
        "natural_gas": {"percentage": 48, "rate_of_change": -0.01},
        "solar": {"percentage": 9, "rate_of_change": 0.02},
        "wind": {"percentage": 2, "rate_of_change": 0.01},
        "hydro": {"percentage": 5, "rate_of_change": 0.0},
        "nuclear": {"percentage": 28, "rate_of_change": 0.0},
        "other": {"percentage": 0, "rate_of_change": 0.0},
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
            "source": "sunzia_case_study",
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

    cc = benefits["congestion_curtailment"]
    fac = benefits.get("facilitated_emissions", {})
    print(f"\n  --- BENEFITS (PV) ---")
    print(f"  Congestion relief:      {fmt(cc['congestion_benefit_pv'])}")
    print(f"  Curtailment relief:     {fmt(cc['curtailment_benefit_pv'])}")
    print(f"  Delivered energy:       {fmt(cc['delivered_benefit_pv'])}")
    print(f"  Avoided emissions:      {fmt(fac.get('displacement_avoided_cost_pv', 0))}")
    print(f"  Revenue (transfer):     {fmt(benefits['revenue']['revenue_pv'])}")

    print(f"\n  --- TRANSPARENCY ---")
    print(f"  Fac. emissions (proj):  {fmt(fac.get('fac_emissions_project_pv', 0))}")
    print(f"  Fac. emissions (no-line): {fmt(fac.get('fac_emissions_noline_pv', 0))}")

    print(f"\n  --- DELAY COSTS (embedded) ---")
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
    print("Loading S9 template...")
    template = load_s9_template()

    # --- Scenario 1: SunZia with 17-year delay ---
    print("\nBuilding SunZia (17-year delay) scenario...")
    inputs_delay17 = patch_sunzia_inputs(copy.deepcopy(template["inputs"]))

    print("Running calculation (delay=17)...")
    results_delay17 = run_scenario(inputs_delay17, "SunZia_Delay17")
    print_results(results_delay17, "SunZia — 17-Year Delay (Actual)")

    # --- Scenario 2: SunZia with 0-year delay (counterfactual) ---
    print("\n\nBuilding SunZia (no delay) counterfactual...")
    inputs_nodelay = copy.deepcopy(inputs_delay17)
    inputs_nodelay["01_project_technical_details"]["timeline"]["delay_years"] = 0
    inputs_nodelay["05_delays"]["annual_delay_costs"] = {
        "legal": 0, "admin": 0, "labor": 0,
        "material_and_equipment": 0, "regulatory": 0,
        "public_relations": 0, "project_management": 0,
        "miscellaneous": 0,
    }

    print("Running calculation (delay=0)...")
    results_nodelay = run_scenario(inputs_nodelay, "SunZia_NoDelay")
    print_results(results_nodelay, "SunZia — No Delay (Counterfactual)")

    # --- Save .ctcc files ---
    print("\n\nSaving scenario files...")
    save_ctcc_file(inputs_delay17, results_delay17, "SunZia_Delay17", "SunZia_Delay17")
    save_ctcc_file(inputs_nodelay, results_nodelay, "SunZia_NoDelay", "SunZia_NoDelay")

    # --- Comparison ---
    bcr17 = results_delay17["bcr"]
    bcr0 = results_nodelay["bcr"]
    print(f"\n{'='*60}")
    print(f"  DELAY IMPACT COMPARISON")
    print(f"{'='*60}")
    print(f"  BCR System:  {bcr17.get('bcr_system',0):.3f} (17yr) → {bcr0.get('bcr_system',0):.3f} (0yr)")
    print(f"  Net Benefit: {fmt(bcr17.get('net_benefit_pv',0))} (17yr) → {fmt(bcr0.get('net_benefit_pv',0))} (0yr)")
    delta = bcr0.get("net_benefit_pv", 0) - bcr17.get("net_benefit_pv", 0)
    print(f"  Social cost of delay: {fmt(delta)}")
    print(f"\n  Build cost PV (validation): {fmt(results_delay17['costs']['build']['total_pv'])}")
    print(f"  Target: $1.6-1.8B (reported $1.8-2.0B at 3,000 MW)")

    print("\nDone.")


if __name__ == "__main__":
    main()
