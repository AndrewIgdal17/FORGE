"""Run CTT Panhandle CREZ scenarios: 2-year delay (actual) and 7-year delay (counterfactual).

Builds inputs from canonical YAML defaults, patches with CTT-specific inputs
from the CREZ research document, runs both scenarios, and saves results.

Scenario A: CTT_Actual_Delay2 — what actually happened (CREZ mandate, 2yr permitting)
Scenario B: CTT_Counterfactual_Delay7 — what would have happened without CREZ mandate
"""

import copy
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from scenario_utils import build_default_inputs, run_scenario, save_ctcc_file, fmt  # noqa: E402


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
    fin["afudc"]["apply_afudc"] = True
    fin["afudc"]["delay_period_active_work"] = True
    fin["revenue"]["rate_based"]["enabled"] = True

    # --- 05: Delay Costs (Scenario A: streamlined CREZ permitting) ---
    inputs["05_delays"]["annual_base_delay_cost"] = 5_000_000

    # --- 06: Wildfire (ZEROED) ---
    wf = inputs["06_wildfire_costs"]["wildfire"]
    wf["severity_per_event"] = 0
    wf["risk_growth_rate"] = 0.0
    wf["base_ignition_rate"] = 0.0

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

    # --- 17: Congestion/Curtailment (Approach B) ---
    cc = inputs["17_congestion_curtailment_reductions"]
    gf = cc["greenfield_congestion_curtailment_reductions"]
    gf["constraints"]["flow_factor"] = 0.50
    gf["constraints"]["constrained_hours"] = 1800
    gf["constraints"]["average_exceedance"] = 600
    gf["constraints"]["congestion_fraction"] = 0.05  # wind corridor (CREZ-type): near-pure curtailment
    gf["prices"]["average_congestion_price"] = 11.47
    gf["prices"]["average_curtailment_price"] = 30

    # --- 18: Grid Mix (single-trajectory model) ---
    # Sources: ERCOT 2008 Annual Report; ERCOT CDR 2008-2024; Potomac Economics
    # IMM; Baker Institute CREZ report (2020). CREZ is the outlier case study: a
    # system-transforming $6.9B program that unlocked 18,500 MW of West Texas
    # wind. Wind went from 5% to 24% of ERCOT generation (2008-2023); post-COD
    # coal decline accelerated 2.5x due to merit-order displacement by cheap wind.
    mix = inputs["18_energy_source_mix"]
    mix["grid_mix"] = {
        "initial": {
            "coal": 37, "oil": 0.3, "natural_gas": 43, "solar": 0.1,
            "wind": 5, "hydro": 0.2, "nuclear": 13, "other": 1.4,
        },
        "rate_pre_cod": {
            "coal": -0.025, "oil": -0.02, "natural_gas": 0.013, "solar": 0.25,
            "wind": 0.035, "hydro": 0.0, "nuclear": -0.005, "other": 0.0,
        },
        "rate_post_cod": {
            "coal": -0.063, "oil": -0.02, "natural_gas": 0.0, "solar": 0.33,
            "wind": 0.11, "hydro": 0.0, "nuclear": -0.018, "other": -0.01,
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
    print(f"  Capital recovery (transfer): {fmt(benefits['capital_recovery']['capital_recovery_pv'])}")

    print(f"\n  --- TRANSPARENCY ---")
    print(f"  Fac. emissions (proj):  {fmt(fac.get('fac_emissions_project_pv', 0))}")
    print(f"  Fac. emissions (no-line): {fmt(fac.get('fac_emissions_noline_pv', 0))}")

    print(f"\n  --- DELAY COSTS (embedded in benefits) ---")
    print(f"  Congestion delay cost:  {fmt(cc['congestion_delay_cost_pv'])}")
    print(f"  Curtailment delay cost: {fmt(cc['curtailment_delay_cost_pv'])}")

    print(f"\n  --- BCR RATIOS ---")
    print(f"  BCR Societal:           {bcr.get('bcr_societal', 'N/A'):.3f}")
    print(f"  BCR System:             {bcr.get('bcr_system', 'N/A'):.3f}")
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
    print("Loading YAML defaults...")
    defaults = build_default_inputs()

    # --- Scenario A: CTT with 2-year delay (actual CREZ mandate) ---
    print("\nBuilding CTT Panhandle (2-year delay, actual) scenario...")
    inputs_actual = patch_ctt_inputs(copy.deepcopy(defaults))

    print("Running calculation (delay=2, actual)...")
    results_actual = run_scenario(inputs_actual, "CTT_Actual_Delay2")
    print_results(results_actual, "CTT Panhandle — 2-Year Delay (Actual CREZ)")

    # --- Scenario B: CTT with 7-year delay (counterfactual, no CREZ mandate) ---
    print("\n\nBuilding CTT Panhandle (7-year delay, counterfactual) scenario...")
    inputs_counterfactual = copy.deepcopy(inputs_actual)
    inputs_counterfactual["01_project_technical_details"]["timeline"]["delay_years"] = 7
    inputs_counterfactual["05_delays"]["annual_base_delay_cost"] = 8_000_000

    print("Running calculation (delay=7, counterfactual)...")
    results_cf = run_scenario(inputs_counterfactual, "CTT_Counterfactual_Delay7")
    print_results(results_cf, "CTT Panhandle — 7-Year Delay (Counterfactual)")

    # --- Save .ctcc files ---
    print("\n\nSaving scenario files...")
    save_ctcc_file(inputs_actual, results_actual, "CTT_Actual_Delay2", "CTT_Actual_Delay2", source="ctt_panhandle_crez_case_study")
    save_ctcc_file(
        inputs_counterfactual, results_cf, "CTT_Counterfactual_Delay7", "CTT_Counterfactual_Delay7", source="ctt_panhandle_crez_case_study"
    )

    # --- Comparison ---
    bcr_a = results_actual["bcr"]
    bcr_b = results_cf["bcr"]
    print(f"\n{'='*60}")
    print(f"  DELAY IMPACT COMPARISON: CTT Panhandle CREZ")
    print(f"{'='*60}")
    print(f"  BCR Societal: {bcr_a.get('bcr_societal',0):.3f} (2yr) vs {bcr_b.get('bcr_societal',0):.3f} (7yr)")
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
