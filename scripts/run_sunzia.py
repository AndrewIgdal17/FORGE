"""Run SunZia CTCC scenarios: 17-year delay (actual) and 2-year delay (counterfactual).

Builds inputs from canonical YAML defaults, patches with SunZia-specific values,
runs both scenarios through the calculation engine, and saves results.
"""

import copy
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from scenario_utils import build_default_inputs, run_scenario, save_ctcc_file, fmt  # noqa: E402


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
    proj["timeline"]["project_lifetime"] = 50

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
    fin["social_discount_rate"] = 0.02
    fin["afudc"]["apply_afudc"] = True
    fin["afudc"]["delay_period_active_work"] = False
    fin["revenue"]["rate_based"]["enabled"] = True

    # --- Tab 5: Delay Costs ---
    inputs["05_delays"]["annual_base_delay_cost"] = 15_000_000

    # Wildfire: uses YAML defaults (overhead, base_ignition_rate=0.002)

    # --- Tab 7: Outage ---
    out = inputs["07_outage_costs"]["outage"]
    out["capacity_at_risk_factor"] = 0.5
    out["risk_growth_rate"] = 0.0

    # --- Tab 17: Congestion/Curtailment ---
    cc = inputs["17_congestion_curtailment_reductions"]
    gf = cc["greenfield_congestion_curtailment_reductions"]
    gf["constraints"]["flow_factor"] = 1.0
    gf["constraints"]["constrained_hours"] = 4000
    gf["constraints"]["average_exceedance"] = 500
    gf["constraints"]["congestion_fraction"] = 0.30  # wind HVDC corridor: mostly curtailment
    gf["prices"]["average_congestion_price"] = 15
    gf["prices"]["average_curtailment_price"] = 41

    # --- Tab 18: Grid Mix (single-trajectory model) ---
    # Sources: EIA State Electricity Profiles 2008 (Table 5) for AZ+NM;
    # NM Energy Transition Act; APS/SRP/PNM IRPs. Post-COD rates diverge from
    # pre-COD because SunZia adds ~2,400 MW wind to a 30-35 GW region, accelerating
    # wind growth (+10%/yr -> +14%/yr) and coal decline (-4%/yr -> -5%/yr).
    mix = inputs["18_energy_source_mix"]
    mix["grid_mix"] = {
        "initial": {
            "coal": 45, "oil": 0, "natural_gas": 30, "solar": 0,
            "wind": 1, "hydro": 5, "nuclear": 19, "other": 0,
        },
        "rate_pre_cod": {
            "coal": -0.04, "oil": 0.0, "natural_gas": 0.01, "solar": 0.15,
            "wind": 0.10, "hydro": 0.0, "nuclear": 0.0, "other": 0.0,
        },
        "rate_post_cod": {
            "coal": -0.05, "oil": 0.0, "natural_gas": 0.01, "solar": 0.15,
            "wind": 0.14, "hydro": 0.0, "nuclear": 0.0, "other": 0.0,
        },
    }

    return inputs


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
    cap = benefits.get("capacity_value", {})
    print(f"  Capacity value:         {fmt(cap.get('capacity_value_pv', 0))}")
    print(f"  Capital recovery (transfer): {fmt(benefits['capital_recovery']['capital_recovery_pv'])}")

    print(f"\n  --- TRANSPARENCY ---")
    print(f"  Fac. emissions (proj):  {fmt(fac.get('fac_emissions_project_pv', 0))}")
    print(f"  Fac. emissions (no-line): {fmt(fac.get('fac_emissions_noline_pv', 0))}")

    print(f"\n  --- DELAY COSTS (embedded) ---")
    print(f"  Congestion delay cost:  {fmt(cc['congestion_delay_cost_pv'])}")
    print(f"  Curtailment delay cost: {fmt(cc['curtailment_delay_cost_pv'])}")

    print(f"\n  --- BCR RATIOS ---")
    print(f"  BCR Societal:                   {bcr.get('bcr_societal', 0):.3f}")
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

    # Print excluded PVs summary
    print(f"\n  --- EXCLUDED PVs ---")
    print(f"  Wildfire PV:                    {fmt(bcr.get('wildfire_pv', 0))}")
    print(f"  Outage PV:                      {fmt(bcr.get('outage_pv', 0))}")
    print(f"  Avoided Emissions PV (benefit): {fmt(bcr.get('benefits_avoided_emissions_pv', 0))}")

    print(f"\n  --- SUMMARY ---")
    print(f"  Total costs PV:         {fmt(bcr.get('total_costs_pv', 0))}")
    print(f"  Total benefits PV:      {fmt(bcr.get('total_benefits_pv', 0))}")
    print(f"  Net benefit PV:         {fmt(bcr.get('net_benefit_pv', 0))}")


def main():
    print("Loading YAML defaults...")
    defaults = build_default_inputs()

    # --- Scenario 1: SunZia with 17-year delay ---
    print("\nBuilding SunZia (17-year delay) scenario...")
    inputs_delay17 = patch_sunzia_inputs(copy.deepcopy(defaults))

    print("Running calculation (delay=17)...")
    results_delay17 = run_scenario(inputs_delay17, "SunZia_Delay17")
    print_results(results_delay17, "SunZia — 17-Year Delay (Actual)")

    # --- Scenario 2: SunZia with 2-year delay (CREZ-style counterfactual) ---
    # "What if SunZia had gotten a CREZ-style streamlined 2-year permitting process?"
    print("\n\nBuilding SunZia (2-year delay, CREZ-style) counterfactual...")
    inputs_delay2 = copy.deepcopy(inputs_delay17)
    inputs_delay2["01_project_technical_details"]["timeline"]["delay_years"] = 2

    print("Running calculation (delay=2)...")
    results_delay2 = run_scenario(inputs_delay2, "SunZia_Delay2")
    print_results(results_delay2, "SunZia — 2-Year Delay (CREZ-Style Counterfactual)")

    # --- Save .ctcc files ---
    print("\n\nSaving scenario files...")
    save_ctcc_file(inputs_delay17, results_delay17, "SunZia_Delay17", "SunZia_Delay17", source="sunzia_case_study")
    save_ctcc_file(inputs_delay2, results_delay2, "SunZia_Delay2", "SunZia_Delay2", source="sunzia_case_study")

    # --- Comparison ---
    bcr17 = results_delay17["bcr"]
    bcr2 = results_delay2["bcr"]
    print(f"\n{'='*60}")
    print(f"  DELAY IMPACT COMPARISON (17-year vs 2-year)")
    print(f"{'='*60}")
    print(f"  {'Metric':<20} {'17yr':>10} {'2yr':>10}")
    print(f"  {'-'*20} {'-'*10} {'-'*10}")
    print(
        f"  {'BCR Societal':<20} {bcr17.get('bcr_societal', 0):>10.3f}"
        f" {bcr2.get('bcr_societal', 0):>10.3f}"
    )
    print(
        f"  {'BCR Utility':<20} {bcr17.get('bcr_utility', 0):>10.3f}"
        f" {bcr2.get('bcr_utility', 0):>10.3f}"
    )
    print(
        f"  {'Net Benefit':<20} {fmt(bcr17.get('net_benefit_pv', 0)):>10}"
        f" {fmt(bcr2.get('net_benefit_pv', 0)):>10}"
    )
    delta_17_to_2 = bcr2.get("net_benefit_pv", 0) - bcr17.get("net_benefit_pv", 0)
    print(f"  Social cost of 15 extra years (17→2): {fmt(delta_17_to_2)}")
    print(f"\n  Build cost PV (validation): {fmt(results_delay17['costs']['build']['total_pv'])}")
    print(f"  Target: $1.6-1.8B (reported $1.8-2.0B at 3,000 MW)")

    print("\nDone.")


if __name__ == "__main__":
    main()
