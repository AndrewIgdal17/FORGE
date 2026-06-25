"""Run Vineyard Wind 1 CTCC scenarios: 6-year delay (actual) and 2-year delay (counterfactual).

Loads S9 as template, patches with VW1-specific inputs from the subsea case study
research document, runs both scenarios, and saves results.

Vineyard Wind 1: 800 MW HVAC subsea export cable, Barnstable MA.
Modeled at 657 MW (closest CTCC AC tier) with utilization adjusted to preserve throughput.
Construction type: Subsea. AC. Zero wildfire. Dual parallel cables (capacity_at_risk=0.5).
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


def patch_vineyard_wind_inputs(inputs: dict) -> dict:
    """Patch S9 inputs with Vineyard Wind 1 subsea cable values."""

    # --- Tab 01: Project Technical Details ---
    proj = inputs["01_project_technical_details"]
    proj["project"]["name"] = "VW1_Subsea_AC_657MW_SubseaCopper_NA"
    proj["project"]["construction_type"] = "Subsea"
    proj["project"]["ac_dc"] = "AC"
    proj["project"]["capacity_mw"] = 657  # actual: 800 MW; 657 is closest CTCC AC tier
    proj["project"]["conductor_type"] = "Subsea Copper Conductor"
    proj["project"]["converter_type"] = "NA"
    proj["project"]["number_of_converters"] = 0
    proj["project"]["converter_loss_percentage"] = None
    proj["project"]["line_utilization"] = 0.552  # 806 MW × 0.45 CF ÷ 657 MW — preserves 3.15 TWh/yr
    proj["project"]["value_of_load_per_mwh"] = 55.0
    proj["project"]["reconductoring"] = False
    proj["project"]["uses_existing_row"] = False
    proj["project"]["old_capacity_mw"] = None
    proj["project"]["old_conductor_type"] = None
    proj["project"]["old_ac_dc"] = None
    proj["timeline"]["construction_years"] = 2
    proj["timeline"]["delay_years"] = 6
    proj["timeline"]["project_lifetime"] = 30

    # --- Tab 02: Terrain Miles ---
    terrain = inputs["02_project_physical_details"]["terrain"]
    terrain["terrain_miles"] = {
        "forested": 0,
        "scrubbed_flat": 0,
        "wetland": 0,
        "farmland": 0,
        "desert_barren": 0,
        "urban": 5.3,
        "rolling_hills": 0,
        "mountain": 0,
        "subsea": 83,
    }

    # --- Tab 03: Financial ---
    fin = inputs["03_financing"]["financial"]
    fin["base_year"] = 2024
    fin["inflation_rate"] = 0.03
    fin["wacc_nominal"] = 0.075
    fin["social_discount_rate"] = 0.03
    fin["contingencies"]["conductor_contingency"] = 0.10
    fin["contingencies"]["structure_contingency"] = 0.0
    fin["contingencies"]["converter_contingency"] = 0.0
    fin["afudc"]["apply_afudc"] = True
    fin["afudc"]["delay_period_active_work"] = False
    fin["revenue"]["rate_based"]["enabled"] = True
    fin["revenue"]["rate_based"]["allowed_return_rate"] = 0.10

    # --- Tab 04: Insurance ---
    ins = inputs["04_insurance"]["insurance"]
    ins["premium_rate"] = 0.025
    ins["insurable_components"]["structures"] = False
    ins["insurable_components"]["converters"] = False

    # --- Tab 05: Delay Costs ---
    inputs["05_delays"]["annual_delay_costs"] = {
        "legal": 1500000,
        "admin": 600000,
        "labor": 500000,
        "material_and_equipment": 200000,
        "regulatory": 2500000,
        "public_relations": 400000,
        "project_management": 1500000,
        "miscellaneous": 300000,
    }

    # --- Tab 06: Wildfire ---
    # Subsea ignition_rate_multiplier is 0.0 in the template — wildfire EAC = $0.
    # No patches needed.

    # --- Tab 07: Outage ---
    out = inputs["07_outage_costs"]["outage"]
    out["capacity_at_risk_factor"] = 0.5
    out["risk_growth_rate"] = 0.0

    # --- Tab 11: ROW Zones ---
    row = inputs["11_project_row_details"]["right_of_way"]
    for zone_key in row:
        row[zone_key]["miles"] = 0
    row["zone_1"]["miles"] = 75
    row["zone_1"]["acquisition_cost"] = 0
    row["zone_1"]["rent_cost"] = 5.0
    row["zone_1"]["hold_cost"] = 0
    row["zone_2"]["miles"] = 8
    row["zone_2"]["acquisition_cost"] = 0
    row["zone_2"]["rent_cost"] = 0
    row["zone_2"]["hold_cost"] = 0
    row["zone_3"]["miles"] = 5.3
    row["zone_3"]["acquisition_cost"] = 5000
    row["zone_3"]["rent_cost"] = 0
    row["zone_3"]["hold_cost"] = 0

    # --- Tab 17: Congestion/Curtailment ---
    cc = inputs["17_congestion_curtailment_reductions"]
    gf = cc["greenfield_congestion_curtailment_reductions"]
    gf["congestion"]["constraints"]["flow_factor"] = 1.0
    gf["congestion"]["constraints"]["binding_hours"] = 500
    gf["congestion"]["constraints"]["average_exceedance"] = 200
    gf["congestion"]["constraints"]["near_binding_hours"] = 0
    gf["congestion"]["constraints"]["near_average_exceedance"] = 0
    gf["congestion"]["constraints"]["near_binding_relief_factor"] = 0.25
    gf["congestion"]["costs"]["average_congestion_price"] = 10
    gf["curtailment"]["curtailment_hours_total"] = 400
    gf["curtailment"]["average_curtailment_mw"] = 300
    gf["curtailment"]["average_curtailment_price"] = 77

    # --- Tab 18: Energy Source Mixes ---
    mix = inputs["18_energy_source_mix"]
    mix["energy_source_mix"] = {
        "coal": {"percentage": 0, "rate_of_change": 0.0},
        "oil": {"percentage": 0, "rate_of_change": 0.0},
        "natural_gas": {"percentage": 0, "rate_of_change": 0.0},
        "solar": {"percentage": 0, "rate_of_change": 0.0},
        "wind": {"percentage": 100, "rate_of_change": 0.0},
        "hydro": {"percentage": 0, "rate_of_change": 0.0},
        "nuclear": {"percentage": 0, "rate_of_change": 0.0},
        "other": {"percentage": 0, "rate_of_change": 0.0},
    }
    mix["counterfactual_energy_source_mix"] = {
        "coal": {"percentage": 1, "rate_of_change": -0.005},
        "oil": {"percentage": 2, "rate_of_change": -0.01},
        "natural_gas": {"percentage": 58, "rate_of_change": -0.01},
        "solar": {"percentage": 5, "rate_of_change": 0.02},
        "wind": {"percentage": 4, "rate_of_change": 0.01},
        "hydro": {"percentage": 7, "rate_of_change": 0.0},
        "nuclear": {"percentage": 22, "rate_of_change": -0.005},
        "other": {"percentage": 1, "rate_of_change": 0.0},
    }

    return inputs


def run_scenario(inputs: dict, scenario_id: str) -> dict:
    return run_calculation(
        combined_data=inputs,
        scenario_id=scenario_id,
        quiet=True,
    )


def save_ctcc_file(inputs: dict, results: dict, name: str, scenario_id: str):
    from datetime import datetime

    ctcc = {
        "version": "1.0",
        "customName": name,
        "inputs": inputs,
        "results": results,
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "scenario_id": scenario_id,
            "source": "vineyard_wind_case_study",
        },
    }
    out_path = REPO_ROOT / "scenarios" / f"{name}.ctcc"
    with open(out_path, "w") as f:
        json.dump(ctcc, f, indent=2, default=str)
    print(f"  Saved: {out_path}")


def fmt(val, prefix="$"):
    if abs(val) >= 1e9:
        return f"{prefix}{val/1e9:.2f}B"
    elif abs(val) >= 1e6:
        return f"{prefix}{val/1e6:.1f}M"
    else:
        return f"{prefix}{val:,.0f}"


def print_results(results: dict, label: str):
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
    print(f"  BCR Societal:                   {bcr.get('bcr_societal', 0):.3f}")
    print(f"  BCR System:                     {bcr.get('bcr_system', 0):.3f}")
    print(f"  BCR System + Delivered:         {bcr.get('bcr_system_delivered', 0):.3f}")
    print(f"  BCR Capital Only:               {bcr.get('bcr_capital', 0):.3f}")
    print(f"  BCR Capital + Delay:            {bcr.get('bcr_capital_and_delay', 0):.3f}")
    print(f"  BCR Utility:                    {bcr.get('bcr_utility', 0):.3f}")
    print(f"  BCR Ratepayer:                  {bcr.get('bcr_ratepayer', 0):.3f}")

    print(f"\n  --- EXCLUSION VARIANTS ---")
    excl_variants = [
        ("Excl. Wildfire", "bcr_excluding_wildfire_risk", "wildfire_pv", None),
        ("Excl. Outage", "bcr_excluding_outage_risk", "outage_pv", None),
        ("Excl. WF+Outage", "bcr_excluding_wildfire_risk_and_outage_risk", None, None),
        ("Excl. Avoided Emissions", "bcr_excluding_avoided_emissions", None, "benefits_avoided_emissions_pv"),
        ("Excl. AvEmis+Outage+WF", "bcr_excluding_avoided_emissions_and_wildfire_risk_and_outage_risk", None, None),
    ]
    for label, key, cost_excl, ben_excl in excl_variants:
        val = bcr.get(key, 0)
        parts = []
        if cost_excl:
            parts.append(f"excl cost={fmt(bcr.get(cost_excl, 0))}")
        if ben_excl:
            parts.append(f"excl benefit={fmt(bcr.get(ben_excl, 0))}")
        extra = f"  ({', '.join(parts)})" if parts else ""
        print(f"  {label:<30} {val:.3f}{extra}")

    print(f"\n  --- EXCLUDED PVs ---")
    print(f"  Wildfire PV:                    {fmt(bcr.get('wildfire_pv', 0))}")
    print(f"  Outage PV:                      {fmt(bcr.get('outage_pv', 0))}")
    print(f"  Avoided Emissions PV (benefit): {fmt(bcr.get('benefits_avoided_emissions_pv', 0))}")

    print(f"\n  --- SUMMARY ---")
    print(f"  Total costs PV:         {fmt(bcr.get('total_costs_pv', 0))}")
    print(f"  Total benefits PV:      {fmt(bcr.get('total_benefits_pv', 0))}")
    print(f"  Net benefit PV:         {fmt(bcr.get('net_benefit_pv', 0))}")


def main():
    print("Loading S9 template...")
    template = load_s9_template()

    # --- Scenario 1: VW1 with 6-year delay (actual BOEM permitting) ---
    print("\nBuilding VW1 (6-year delay) scenario...")
    inputs_delay6 = patch_vineyard_wind_inputs(copy.deepcopy(template["inputs"]))

    print("Running calculation (delay=6)...")
    results_delay6 = run_scenario(inputs_delay6, "VW1_Delay6")
    print_results(results_delay6, "Vineyard Wind 1 — 6-Year Delay (Actual)")

    # --- Scenario 2: VW1 with 2-year delay (streamlined BOEM counterfactual) ---
    print("\n\nBuilding VW1 (2-year delay, streamlined) counterfactual...")
    inputs_delay2 = copy.deepcopy(inputs_delay6)
    inputs_delay2["01_project_technical_details"]["timeline"]["delay_years"] = 2

    print("Running calculation (delay=2)...")
    results_delay2 = run_scenario(inputs_delay2, "VW1_Delay2")
    print_results(results_delay2, "Vineyard Wind 1 — 2-Year Delay (Streamlined Counterfactual)")

    # --- Save .ctcc files ---
    print("\n\nSaving scenario files...")
    save_ctcc_file(inputs_delay6, results_delay6, "VW1_Delay6", "VW1_Delay6")
    save_ctcc_file(inputs_delay2, results_delay2, "VW1_Delay2", "VW1_Delay2")

    # --- Comparison ---
    bcr6 = results_delay6["bcr"]
    bcr2 = results_delay2["bcr"]
    print(f"\n{'='*60}")
    print(f"  DELAY IMPACT COMPARISON (6-year vs 2-year)")
    print(f"{'='*60}")
    print(f"  BCR Societal: {bcr6.get('bcr_societal',0):.3f} (6yr) → {bcr2.get('bcr_societal',0):.3f} (2yr)")
    print(f"  BCR Utility: {bcr6.get('bcr_utility',0):.3f} (6yr) → {bcr2.get('bcr_utility',0):.3f} (2yr)")
    print(f"  BCR Cap+Del: {bcr6.get('bcr_capital_and_delay',0):.3f} (6yr) → {bcr2.get('bcr_capital_and_delay',0):.3f} (2yr)")
    print(f"  Net Benefit: {fmt(bcr6.get('net_benefit_pv',0))} (6yr) → {fmt(bcr2.get('net_benefit_pv',0))} (2yr)")
    delta = bcr2.get("net_benefit_pv", 0) - bcr6.get("net_benefit_pv", 0)
    print(f"  Social cost of 4 extra years: {fmt(delta)}")
    print(f"\n  Build cost PV (validation): {fmt(results_delay6['costs']['build']['total_pv'])}")
    print(f"  Target: ~$210-232M (Prysmian contract); CTCC uses generic rates")

    print("\nDone.")


if __name__ == "__main__":
    main()
