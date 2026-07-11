"""Run LRGV Laredo New-Build scenario: hypothetical 345kV AC line, Laredo to Edinburg.

This is the third LRGV scenario — the alternative AEP identified but rejected
("could not be built until sometime after 2020"). Greenfield 200-mile 345kV AC
line through South Texas, requiring full new-corridor ROW acquisition.

Builds inputs from canonical YAML defaults, deep-copies, patches to greenfield
new-build parameters, runs calculation, and saves results.
"""

import copy
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from scenario_utils import build_default_inputs, run_scenario, save_ctcc_file, fmt  # noqa: E402


def patch_laredo_newbuild(inputs: dict) -> dict:
    """Patch template inputs with Laredo new-build greenfield parameters."""

    # --- 01: Project Technical Details ---
    proj = inputs["01_project_technical_details"]
    proj["project"]["name"] = "AEP_LRGV_Laredo_NewBuild_345kV_AC"
    proj["project"]["construction_type"] = "Overhead"
    proj["project"]["ac_dc"] = "AC"
    proj["project"]["number_of_converters"] = 0
    proj["project"]["capacity_mw"] = 1792
    proj["project"]["conductor_type"] = "Standard Aluminum Conductor"
    proj["project"]["converter_type"] = "NA"
    proj["project"]["converter_loss_percentage"] = None
    proj["project"]["line_utilization"] = 0.65
    proj["project"]["value_of_load_per_mwh"] = 42.0
    proj["project"]["reconductoring"] = False
    proj["project"]["uses_existing_row"] = False
    proj["project"]["old_capacity_mw"] = None
    proj["project"]["old_conductor_type"] = None
    proj["project"]["old_ac_dc"] = None
    proj["project"]["greenfield_comparison_capacity_mw"] = None
    proj["project"]["greenfield_comparison_conductor_type"] = "Standard Aluminum Conductor"
    proj["timeline"]["construction_years"] = 3
    proj["timeline"]["delay_years"] = 7
    proj["timeline"]["project_lifetime"] = 50

    # --- 02: Terrain (~200 miles, South Texas) ---
    terrain = inputs["02_project_physical_details"]["terrain"]
    terrain["terrain_miles"] = {
        "forested": 0,
        "scrubbed_flat": 80,
        "wetland": 5,
        "farmland": 100,
        "desert_barren": 15,
        "urban": 0,
        "rolling_hills": 0,
        "mountain": 0,
        "subsea": 0,
    }

    # --- 03: Financial ---
    fin = inputs["03_financing"]["financial"]
    fin["base_year"] = 2026
    fin["inflation_rate"] = 0.025
    fin["wacc_nominal"] = 0.067
    fin["social_discount_rate"] = 0.02
    fin["afudc"]["apply_afudc"] = True
    fin["afudc"]["delay_period_active_work"] = False
    fin["revenue"]["rate_based"]["enabled"] = True

    # --- 04: Insurance ---
    ins = inputs["04_insurance"]["insurance"]
    ins["insurable_components"]["conductors"] = True
    ins["insurable_components"]["structures"] = True
    ins["insurable_components"]["converters"] = True

    # --- 05: Delay Costs (annual, 7yr permitting for new corridor) ---
    inputs["05_delays"]["annual_base_delay_cost"] = 9_000_000

    # --- 06: Wildfire (zeroed — low-fire South Texas coastal plain) ---
    wf = inputs["06_wildfire_costs"]["wildfire"]
    wf["severity_per_event"] = 0
    wf["risk_growth_rate"] = 0.0
    wf["base_ignition_rate"] = 0.0

    # --- 07: Outage (zeroed — case study focuses on reconductoring economics) ---
    out = inputs["07_outage_costs"]["outage"]
    out["risk_growth_rate"] = 0.0
    out["capacity_at_risk_factor"] = 0.0

    # --- 09: Environmental Mitigation (greenfield — NOT zeroed) ---
    env = inputs["09_environmental_mitigation"]["environmental_mitigation"]
    env["habitat_credit_cost_per_acre"] = {
        "forested": 30_000,
        "scrubbed_flat": 5_000,
        "desert_barren": 3_000,
        "rolling_hills": 5_000,
        "mountain": 30_000,
        "farmland": 2_000,
    }

    # --- 11: ROW (NEW corridor — full acquisition required) ---
    row = inputs["11_project_row_details"]["right_of_way"]
    for zone_key in row:
        row[zone_key]["miles"] = 0
        row[zone_key]["acquisition_cost"] = 0
        row[zone_key]["rent_cost"] = 0
        row[zone_key]["hold_cost"] = 0
    row["zone_1"]["miles"] = 160
    row["zone_1"]["acquisition_cost"] = 3_000
    row["zone_1"]["rent_cost"] = 9.70
    row["zone_1"]["hold_cost"] = 2_000
    row["zone_2"]["miles"] = 40
    row["zone_2"]["acquisition_cost"] = 5_000
    row["zone_2"]["rent_cost"] = 18.78
    row["zone_2"]["hold_cost"] = 3_000

    # --- 17: Congestion/Curtailment (Approach B; same import constraint as LRGV) ---
    cc = inputs["17_congestion_curtailment_reductions"]
    gf = cc["greenfield_congestion_curtailment_reductions"]
    gf["constraints"]["flow_factor"] = 0.80
    gf["constraints"]["constrained_hours"] = 1200
    gf["constraints"]["average_exceedance"] = 400
    gf["constraints"]["congestion_fraction"] = 1.00  # load pocket (LRGV-type): pure congestion
    gf["prices"]["average_congestion_price"] = 15.0
    gf["prices"]["average_curtailment_price"] = 0

    # --- 18: Grid Mix (single-trajectory model; same ERCOT region as LRGV) ---
    # Sources: ERCOT CDR 2010; EIA Texas electricity profile 2010; Potomac
    # Economics IMM. rate_post_cod = rate_pre_cod: this is a congestion-relief
    # line, not a renewable corridor — it relieves import constraints to LRGV
    # but does not enable new generation or change system-level investment.
    mix = inputs["18_energy_source_mix"]
    mix["grid_mix"] = {
        "initial": {
            "coal": 39.5, "oil": 0.3, "natural_gas": 38, "solar": 0.1,
            "wind": 7.8, "hydro": 0.2, "nuclear": 13, "other": 1.1,
        },
        "rate_pre_cod": {
            "coal": -0.07, "oil": -0.02, "natural_gas": 0.025, "solar": 0.25,
            "wind": 0.10, "hydro": 0.0, "nuclear": -0.005, "other": 0.0,
        },
        "rate_post_cod": {
            "coal": -0.07, "oil": -0.02, "natural_gas": 0.025, "solar": 0.25,
            "wind": 0.10, "hydro": 0.0, "nuclear": -0.005, "other": 0.0,
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
    print(f"  BCR Utility:                    {bcr.get('bcr_utility', 0):.3f}")
    print(f"  BCR Ratepayer:                  {bcr.get('bcr_ratepayer', 0):.3f}")

    print(f"\n  --- EXCLUSION VARIANTS ---")
    for label_str, key in [
        ("Excl. Wildfire", "bcr_excluding_wildfire_risk"),
        ("Excl. Outage", "bcr_excluding_outage_risk"),
        ("Excl. WF+Outage", "bcr_excluding_wildfire_risk_and_outage_risk"),
        ("Excl. Avoided Emissions", "bcr_excluding_avoided_emissions"),
        ("Excl. AvEmis+Out+WF", "bcr_excluding_avoided_emissions_and_wildfire_risk_and_outage_risk"),
    ]:
        val = bcr.get(key, 0)
        if val:
            print(f"  {label_str:<30} {val:.3f}")

    print(f"\n  --- SUMMARY ---")
    print(f"  Total costs PV:         {fmt(bcr.get('total_costs_pv', 0))}")
    print(f"  Total benefits PV:      {fmt(bcr.get('total_benefits_pv', 0))}")
    print(f"  Net benefit PV:         {fmt(bcr.get('net_benefit_pv', 0))}")


def main():
    print("Loading YAML defaults...")
    defaults = build_default_inputs()

    print("\nBuilding Laredo New-Build (7-year delay) scenario...")
    inputs = patch_laredo_newbuild(copy.deepcopy(defaults))

    print("Running calculation...")
    results = run_scenario(inputs, "AEP_LRGV_Laredo_NewBuild")
    print_results(results, "AEP LRGV — Laredo New-Build 345kV AC (7yr delay)")

    print("\n\nSaving scenario file...")
    save_ctcc_file(inputs, results, "AEP_LRGV_Laredo_NewBuild", "AEP_LRGV_Laredo_NewBuild", source="aep_lrgv_laredo_newbuild_case_study")

    # --- Comparison with existing LRGV scenarios ---
    print(f"\n{'='*60}")
    print(f"  COMPARISON: LRGV Scenario Options")
    print(f"{'='*60}")

    bcr_nb = results["bcr"]
    for ref_name in ["AEP_LRGV_ACCC", "AEP_LRGV_ACSR_Rebuild"]:
        ref_path = REPO_ROOT / "scenarios" / f"{ref_name}.ctcc"
        if ref_path.exists():
            with open(ref_path) as f:
                ref = json.load(f)
            ref_bcr = ref["results"]["bcr"]
            print(f"\n  vs {ref_name}:")
            print(f"    BCR Societal: {ref_bcr.get('bcr_societal', 0):.3f} vs {bcr_nb.get('bcr_societal', 0):.3f} (new-build)")
            print(f"    BCR Utility:  {ref_bcr.get('bcr_utility', 0):.3f} vs {bcr_nb.get('bcr_utility', 0):.3f} (new-build)")
            print(f"    Net Benefit:  {fmt(ref_bcr.get('net_benefit_pv', 0))} vs {fmt(bcr_nb.get('net_benefit_pv', 0))} (new-build)")
            ref_build = ref["results"]["costs"]["build"]["total_pv"]
            nb_build = results["costs"]["build"]["total_pv"]
            print(f"    Build Cost:   {fmt(ref_build)} vs {fmt(nb_build)} (new-build)")

    print("\nDone.")


if __name__ == "__main__":
    main()
