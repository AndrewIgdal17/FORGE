"""Run Trans Bay Cable CTCC scenarios: 4-year delay (actual) and 0-year delay (counterfactual).

Builds inputs from canonical YAML defaults, patches with TBC-specific inputs from the
research document (underground-project-data-research.md), runs both scenarios, and saves results.

Trans Bay Cable: 53-mile, 400 MW (modeled as 500 MW), ±200 kV HVDC submarine cable
under San Francisco Bay. Subsea construction type — first subsea CTCC case study.
"""

import copy
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from scenario_utils import build_default_inputs, run_scenario, save_ctcc_file, fmt  # noqa: E402


def patch_tbc_inputs(inputs: dict) -> dict:
    """Patch S9 inputs with Trans Bay Cable-specific values."""

    # --- Section 01: Project Technical Details ---
    proj = inputs["01_project_technical_details"]
    proj["project"]["name"] = "TBC_400MW_SubseaCu_VSC"
    proj["project"]["construction_type"] = "Subsea"
    proj["project"]["ac_dc"] = "DC"
    proj["project"]["capacity_mw"] = 500  # nearest dropdown; actual 400 MW
    proj["project"]["conductor_type"] = "Subsea Copper Conductor"
    proj["project"]["converter_type"] = "VSC Converter"
    proj["project"]["number_of_converters"] = 2
    proj["project"]["converter_loss_percentage"] = None  # default 1.0% for VSC
    proj["project"]["line_utilization"] = 0.56
    proj["project"]["value_of_load_per_mwh"] = 55.0
    proj["project"]["reconductoring"] = False
    proj["project"]["uses_existing_row"] = False
    proj["project"]["old_capacity_mw"] = None
    proj["project"]["old_conductor_type"] = None
    proj["project"]["old_ac_dc"] = None
    proj["timeline"]["construction_years"] = 3
    proj["timeline"]["delay_years"] = 4
    proj["timeline"]["project_lifetime"] = 40

    # --- Section 02: Terrain Miles (all subsea) ---
    terrain = inputs["02_project_physical_details"]["terrain"]
    terrain["terrain_miles"] = {
        "forested": 0,
        "scrubbed_flat": 0,
        "wetland": 0,
        "farmland": 0,
        "desert_barren": 0,
        "urban": 0,
        "rolling_hills": 0,
        "mountain": 0,
        "subsea": 53,
    }

    # --- Section 03: Financial ---
    fin = inputs["03_financing"]["financial"]
    fin["base_year"] = 2025
    fin["inflation_rate"] = 0.03
    fin["wacc_nominal"] = 0.085
    fin["social_discount_rate"] = 0.02
    fin["afudc"]["apply_afudc"] = True
    fin["afudc"]["delay_period_active_work"] = False
    fin["revenue"]["rate_based"]["enabled"] = True

    # --- Section 04: Insurance ---
    ins = inputs["04_insurance"]["insurance"]
    ins["insurable_components"]["conductors"] = True
    ins["insurable_components"]["structures"] = False
    ins["insurable_components"]["converters"] = True

    # --- Section 05: Delay Costs (annual, total $6.0M/yr) ---
    inputs["05_delays"]["annual_base_delay_cost"] = 6_000_000

    # --- Section 06: Wildfire (zero risk for subsea) ---
    wf = inputs["06_wildfire_costs"]["wildfire"]
    wf["severity_per_event"] = 0
    wf["risk_growth_rate"] = 0.015

    # --- Section 07: Outage ---
    # TBC provides ~40-50% of SF peak power but SF has backup AC paths.
    # During the 2014 anchor strike (4-month repair), SF had zero customer
    # outages. The VoLL tiers assume short outages causing cascading failures;
    # for submarine cables, long repairs don't cause unserved energy because
    # the grid redispatches. We model:
    #   capacity_at_risk = 0.5 (TBC supplies ~50% of SF; backup paths can
    #     partially compensate but margin is reduced)
    #   subsea duration multiplier = 4x (effective 24 hrs customer-facing
    #     impact per event, not the 60-day cable repair time)
    out = inputs["07_outage_costs"]["outage"]
    out["capacity_at_risk_factor"] = 0.5
    out["risk_growth_rate"] = 0.0
    out["outage_duration_multiplier"]["subsea"] = 4.0

    # --- Section 11: ROW Zones (submarine corridor, zero land costs) ---
    row = inputs["11_project_row_details"]["right_of_way"]
    for zone_key in row:
        row[zone_key]["miles"] = 0
        row[zone_key]["acquisition_cost"] = 0
        row[zone_key]["rent_cost"] = 0
        row[zone_key]["hold_cost"] = 0
    row["zone_1"]["miles"] = 53

    # --- Section 17: Congestion/Curtailment (load pocket, congestion-dominated) ---
    cc = inputs["17_congestion_curtailment_reductions"]
    gf = cc["greenfield_congestion_curtailment_reductions"]
    gf["constraints"]["flow_factor"] = 1.0
    gf["constraints"]["constrained_hours"] = 2000
    gf["constraints"]["average_exceedance"] = 200
    gf["constraints"]["congestion_fraction"] = 0.80  # load pocket (LRGV/SF-type): congestion-dominated
    gf["prices"]["average_congestion_price"] = 25
    gf["prices"]["average_curtailment_price"] = 35

    # --- Section 18: Grid Mix (single-trajectory model) ---
    # Sources: CEC California Electrical Energy Generation (QFER CEC-1304) 2005;
    # SB 1368; SB 1078/107 RPS; CAISO 2011 LCR Study. rate_post_cod = rate_pre_cod:
    # a 400 MW reliability cable in a 55 GW system (~0.7% of capacity) does not
    # change fleet evolution. TBC enables Potrero retirement (~200 MW gas peaker),
    # but that is 0.5% of CA's gas fleet — negligible at system scale.
    mix = inputs["18_energy_source_mix"]
    mix["grid_mix"] = {
        "initial": {
            "coal": 12.4, "oil": 0.0, "natural_gas": 42.6, "solar": 0.3,
            "wind": 1.9, "hydro": 17.7, "nuclear": 16.0, "other": 9.1,
        },
        "rate_pre_cod": {
            "coal": -0.30, "oil": 0.00, "natural_gas": -0.01, "solar": 0.25,
            "wind": 0.07, "hydro": 0.00, "nuclear": -0.04, "other": -0.02,
        },
        "rate_post_cod": {
            "coal": -0.30, "oil": 0.00, "natural_gas": -0.01, "solar": 0.25,
            "wind": 0.07, "hydro": 0.00, "nuclear": -0.04, "other": -0.02,
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

    # --- Scenario 1: TBC with 4-year delay (actual) ---
    print("\nBuilding Trans Bay Cable (4-year delay) scenario...")
    inputs_delay4 = patch_tbc_inputs(copy.deepcopy(defaults))

    print("Running calculation (delay=4)...")
    results_delay4 = run_scenario(inputs_delay4, "TBC_Delay4")
    print_results(results_delay4, "Trans Bay Cable — 4-Year Delay (Actual)")

    # --- Scenario 2: TBC with 0-year delay (counterfactual) ---
    print("\n\nBuilding Trans Bay Cable (0-year delay) counterfactual...")
    inputs_nodelay = copy.deepcopy(inputs_delay4)
    inputs_nodelay["01_project_technical_details"]["timeline"]["delay_years"] = 0

    print("Running calculation (delay=0)...")
    results_nodelay = run_scenario(inputs_nodelay, "TBC_NoDelay")
    print_results(results_nodelay, "Trans Bay Cable — 0-Year Delay (Counterfactual)")

    # --- Save .ctcc files ---
    print("\n\nSaving scenario files...")
    save_ctcc_file(inputs_delay4, results_delay4, "TBC_Delay4", "TBC_Delay4", source="tbc_case_study")
    save_ctcc_file(inputs_nodelay, results_nodelay, "TBC_NoDelay", "TBC_NoDelay", source="tbc_case_study")

    # --- Comparison ---
    bcr4 = results_delay4["bcr"]
    bcr0 = results_nodelay["bcr"]
    print(f"\n{'='*60}")
    print(f"  DELAY IMPACT COMPARISON (4-year vs 0-year)")
    print(f"{'='*60}")
    print(f"  BCR Societal: {bcr4.get('bcr_societal',0):.3f} (4yr) → {bcr0.get('bcr_societal',0):.3f} (0yr)")
    print(f"  BCR Utility: {bcr4.get('bcr_utility',0):.3f} (4yr) → {bcr0.get('bcr_utility',0):.3f} (0yr)")
    print(f"  Net Benefit: {fmt(bcr4.get('net_benefit_pv',0))} (4yr) → {fmt(bcr0.get('net_benefit_pv',0))} (0yr)")
    delta = bcr0.get("net_benefit_pv", 0) - bcr4.get("net_benefit_pv", 0)
    print(f"  Social cost of 4-year delay: {fmt(abs(delta))}")

    # --- TBC-specific validation ---
    print(f"\n  --- COST VALIDATION ---")
    build_pv = results_delay4["costs"]["build"]["total_pv"]
    print(f"  Build cost PV (CTCC):   {fmt(build_pv)}")
    print(f"  Actual total project:   $505M (includes civil works, site, community payments)")
    rev_pv = results_delay4["benefits"]["capital_recovery"]["capital_recovery_pv"]
    print(f"  Capital recovery PV (CTCC): {fmt(rev_pv)}")
    print(f"  Actual TRR:             ~$130M/yr (FERC-approved)")

    print("\nDone.")


if __name__ == "__main__":
    main()
