"""Run Vineyard Wind 1 CTCC scenarios: 6-year delay (actual) and 2-year delay (counterfactual).

Builds inputs from canonical YAML defaults, patches with VW1-specific inputs from the subsea
case study research document, runs both scenarios, and saves results.

Vineyard Wind 1: 800 MW HVAC subsea export cable, Barnstable MA.
Modeled at 657 MW (closest CTCC AC tier) with utilization adjusted to preserve throughput.
Construction type: Subsea. AC. Zero wildfire. Dual parallel cables (capacity_at_risk=0.5).
"""

import copy
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from scenario_utils import build_default_inputs, run_scenario, save_ctcc_file, fmt  # noqa: E402


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
    fin["social_discount_rate"] = 0.02
    fin["afudc"]["apply_afudc"] = True
    fin["afudc"]["delay_period_active_work"] = False
    fin["revenue"]["rate_based"]["enabled"] = True

    # --- Tab 04: Insurance ---
    ins = inputs["04_insurance"]["insurance"]
    ins["insurable_components"]["structures"] = False
    ins["insurable_components"]["converters"] = False

    # --- Tab 05: Delay Costs ---
    inputs["05_delays"]["annual_base_delay_cost"] = 10_000_000

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

    # --- Tab 17: Congestion/Curtailment (Approach B; offshore wind, mostly curtailment) ---
    cc = inputs["17_congestion_curtailment_reductions"]
    gf = cc["greenfield_congestion_curtailment_reductions"]
    gf["constraints"]["flow_factor"] = 1.0
    gf["constraints"]["constrained_hours"] = 500
    gf["constraints"]["average_exceedance"] = 200
    gf["constraints"]["congestion_fraction"] = 0.20  # offshore wind: mostly curtailment
    gf["prices"]["average_congestion_price"] = 10
    gf["prices"]["average_curtailment_price"] = 77

    # --- Tab 18: Grid Mix (single-trajectory model) ---
    # Sources: ISO-NE Air Emissions Report 2017; ISO-NE CELT 2017-2024; MA Clean
    # Energy Standard. Post-COD rates diverge from pre-COD because Vineyard Wind 1
    # (800 MW in a 30 GW system, 2.7%) roughly doubles ISO-NE's wind fleet
    # (~3% -> ~5.7% of generation), so wind growth doubles (+2%/yr -> +4%/yr);
    # gas marginally slows (+2%/yr -> +1%/yr) as it loses marginal-dispatch share.
    mix = inputs["18_energy_source_mix"]
    mix["grid_mix"] = {
        "initial": {
            "coal": 2, "oil": 1, "natural_gas": 49, "solar": 1,
            "wind": 3, "hydro": 8, "nuclear": 31, "other": 5,
        },
        "rate_pre_cod": {
            "coal": -0.10, "oil": -0.05, "natural_gas": 0.02, "solar": 0.10,
            "wind": 0.02, "hydro": 0.0, "nuclear": -0.02, "other": 0.0,
        },
        "rate_post_cod": {
            "coal": -0.10, "oil": -0.05, "natural_gas": 0.01, "solar": 0.10,
            "wind": 0.04, "hydro": 0.0, "nuclear": -0.02, "other": 0.0,
        },
    }

    return inputs


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
    print(f"  Capital recovery (transfer): {fmt(benefits['capital_recovery']['capital_recovery_pv'])}")

    print(f"\n  --- TRANSPARENCY ---")
    print(f"  Fac. emissions (proj):  {fmt(fac.get('fac_emissions_project_pv', 0))}")
    print(f"  Fac. emissions (no-line): {fmt(fac.get('fac_emissions_noline_pv', 0))}")

    print(f"\n  --- DELAY COSTS (embedded) ---")
    print(f"  Congestion delay cost:  {fmt(cc['congestion_delay_cost_pv'])}")
    print(f"  Curtailment delay cost: {fmt(cc['curtailment_delay_cost_pv'])}")

    print(f"\n  --- BCR RATIOS ---")
    print(f"  BCR Societal:                   {bcr.get('bcr_societal', 0):.3f}")
    print(f"  BCR System:                     {bcr.get('bcr_system', 0):.3f}")
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
    print("Loading YAML defaults...")
    defaults = build_default_inputs()

    # --- Scenario 1: VW1 with 6-year delay (actual BOEM permitting) ---
    print("\nBuilding VW1 (6-year delay) scenario...")
    inputs_delay6 = patch_vineyard_wind_inputs(copy.deepcopy(defaults))

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
    save_ctcc_file(inputs_delay6, results_delay6, "VW1_Delay6", "VW1_Delay6", source="vineyard_wind_case_study")
    save_ctcc_file(inputs_delay2, results_delay2, "VW1_Delay2", "VW1_Delay2", source="vineyard_wind_case_study")

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
