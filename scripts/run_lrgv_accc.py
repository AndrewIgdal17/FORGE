"""Run LRGV reconductoring scenarios: ACCC upgrade and ACSR structure rebuild.

Builds inputs from canonical YAML defaults, patches with LRGV corridor parameters
extracted from the legacy case-study scenarios, runs both variants through the
calculation engine, and saves updated .ctcc files in the current format
(grid_mix, single-constraint congestion, no allowed_return_rate).
"""

import copy
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from scenario_utils import build_default_inputs, run_scenario, save_ctcc_file, fmt  # noqa: E402


def _patch_lrgv_common(inputs: dict) -> dict:
    """Shared LRGV corridor parameters (existing ROW, South Texas terrain, ERCOT grid)."""

    # --- 02: Terrain (~240 miles, South Texas) ---
    terrain = inputs["02_project_physical_details"]["terrain"]
    terrain["terrain_miles"] = {
        "forested": 0,
        "scrubbed_flat": 80,
        "wetland": 10,
        "farmland": 130,
        "desert_barren": 20,
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
    fin["afudc"]["delay_period_active_work"] = True
    fin["revenue"]["rate_based"]["enabled"] = True

    # --- 04: Insurance ---
    ins = inputs["04_insurance"]["insurance"]
    ins["insurable_components"]["conductors"] = True
    ins["insurable_components"]["structures"] = True
    ins["insurable_components"]["converters"] = True

    # --- 06: Wildfire (zeroed — low-fire South Texas coastal plain) ---
    wf = inputs["06_wildfire_costs"]["wildfire"]
    wf["severity_per_event"] = 0
    wf["risk_growth_rate"] = 0.0
    wf["base_ignition_rate"] = 0.0

    # --- 07: Outage (zeroed — case study focuses on reconductoring economics) ---
    out = inputs["07_outage_costs"]["outage"]
    out["risk_growth_rate"] = 0.0
    out["capacity_at_risk_factor"] = 0.0

    # --- 09: Environmental Mitigation ---
    env = inputs["09_environmental_mitigation"]["environmental_mitigation"]
    env["habitat_credit_cost_per_acre"] = {
        "forested": 30_000,
        "scrubbed_flat": 5_000,
        "desert_barren": 3_000,
        "rolling_hills": 5_000,
        "mountain": 30_000,
        "farmland": 2_000,
    }

    # --- 11: ROW (existing corridor — rent/hold, minimal acquisition) ---
    row = inputs["11_project_row_details"]["right_of_way"]
    for zone_key in row:
        row[zone_key]["miles"] = 0
        row[zone_key]["acquisition_cost"] = 0
        row[zone_key]["rent_cost"] = 0
        row[zone_key]["hold_cost"] = 0
    row["zone_1"]["miles"] = 200
    row["zone_1"]["acquisition_cost"] = 299
    row["zone_1"]["rent_cost"] = 9.70
    row["zone_1"]["hold_cost"] = 0.97
    row["zone_2"]["miles"] = 40
    row["zone_2"]["acquisition_cost"] = 579
    row["zone_2"]["rent_cost"] = 18.78
    row["zone_2"]["hold_cost"] = 1.878

    # --- 17: Congestion/Curtailment greenfield block (used when not reconductoring) ---
    cc = inputs["17_congestion_curtailment_reductions"]
    gf = cc["greenfield_congestion_curtailment_reductions"]
    gf["constraints"]["flow_factor"] = 0.80
    gf["constraints"]["constrained_hours"] = 1200
    gf["constraints"]["average_exceedance"] = 400
    gf["constraints"]["congestion_fraction"] = 1.00
    gf["prices"]["average_congestion_price"] = 15.0
    gf["prices"]["average_curtailment_price"] = 0

    rc = cc["reconductoring_congestion_curtailment_reductions"]
    rc["constraints"]["constrained_hours"] = 1200
    rc["constraints"]["average_exceedance"] = 400
    rc["constraints"]["congestion_fraction"] = 1.00
    rc["prices"]["average_congestion_price"] = 15.0
    rc["prices"]["average_curtailment_price"] = 0

    # --- 18: Grid Mix (same ERCOT region as Laredo newbuild) ---
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


def patch_lrgv_accc(inputs: dict) -> dict:
    """ACCC reconductoring: 1792 → 2598 MW on existing 345kV corridor."""

    inputs = _patch_lrgv_common(inputs)

    proj = inputs["01_project_technical_details"]
    proj["project"]["name"] = "AEP_LRGV_345kV_ACCC_Reconductoring"
    proj["project"]["construction_type"] = "Overhead"
    proj["project"]["ac_dc"] = "AC"
    proj["project"]["number_of_converters"] = 0
    proj["project"]["capacity_mw"] = 2598
    proj["project"]["conductor_type"] = "Advanced Aluminum Conductor"
    proj["project"]["converter_type"] = "NA"
    proj["project"]["converter_loss_percentage"] = None
    proj["project"]["line_utilization"] = 0.65
    proj["project"]["value_of_load_per_mwh"] = 42.0
    proj["project"]["reconductoring"] = True
    proj["project"]["uses_existing_row"] = True
    proj["project"]["old_capacity_mw"] = 1792
    proj["project"]["old_conductor_type"] = "Standard Aluminum Conductor"
    proj["project"]["old_ac_dc"] = "AC"
    proj["project"]["greenfield_comparison_capacity_mw"] = None
    proj["project"]["greenfield_comparison_conductor_type"] = "Standard Aluminum Conductor"
    proj["timeline"]["construction_years"] = 3
    proj["timeline"]["delay_years"] = 1
    proj["timeline"]["project_lifetime"] = 50

    inputs["05_delays"]["annual_base_delay_cost"] = 6_000_000

    return inputs


def patch_lrgv_acsr_rebuild(inputs: dict) -> dict:
    """ACSR structure rebuild: restore 1792 MW capacity on existing corridor."""

    inputs = _patch_lrgv_common(inputs)

    proj = inputs["01_project_technical_details"]
    proj["project"]["name"] = "AEP_LRGV_345kV_ACSR_Rebuild"
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
    proj["project"]["uses_existing_row"] = True
    proj["project"]["old_capacity_mw"] = None
    proj["project"]["old_conductor_type"] = None
    proj["project"]["old_ac_dc"] = None
    proj["project"]["greenfield_comparison_capacity_mw"] = None
    proj["project"]["greenfield_comparison_conductor_type"] = "Standard Aluminum Conductor"
    proj["timeline"]["construction_years"] = 5
    proj["timeline"]["delay_years"] = 2
    proj["timeline"]["project_lifetime"] = 50

    inputs["05_delays"]["annual_base_delay_cost"] = 10_000_000

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
    cap = benefits.get("capacity_value", {})
    print(f"  Capacity value:         {fmt(cap.get('capacity_value_pv', 0))}")
    print(f"  Capital recovery (transfer): {fmt(benefits['capital_recovery']['capital_recovery_pv'])}")

    print(f"\n  --- BCR RATIOS ---")
    print(f"  BCR Societal:                   {bcr.get('bcr_societal', 0):.3f}")
    print(f"  BCR System:                     {bcr.get('bcr_system', 0):.3f}")
    print(f"  BCR Utility:                    {bcr.get('bcr_utility', 0):.3f}")
    print(f"  BCR Ratepayer:                  {bcr.get('bcr_ratepayer', 0):.3f}")

    print(f"\n  --- SUMMARY ---")
    print(f"  Total costs PV:         {fmt(bcr.get('total_costs_pv', 0))}")
    print(f"  Total benefits PV:      {fmt(bcr.get('total_benefits_pv', 0))}")
    print(f"  Net benefit PV:         {fmt(bcr.get('net_benefit_pv', 0))}")


def main():
    print("Loading YAML defaults...")
    defaults = build_default_inputs()

    print("\nBuilding ACCC reconductoring scenario...")
    inputs_accc = patch_lrgv_accc(copy.deepcopy(defaults))
    print("Running calculation (ACCC)...")
    results_accc = run_scenario(inputs_accc, "AEP_LRGV_ACCC")
    print_results(results_accc, "AEP LRGV — ACCC Reconductoring (1yr delay)")

    print("\n\nBuilding ACSR structure rebuild scenario...")
    inputs_acsr = patch_lrgv_acsr_rebuild(copy.deepcopy(defaults))
    print("Running calculation (ACSR Rebuild)...")
    results_acsr = run_scenario(inputs_acsr, "AEP_LRGV_ACSR_Rebuild")
    print_results(results_acsr, "AEP LRGV — ACSR Structure Rebuild (2yr delay)")

    print("\n\nSaving scenario files...")
    save_ctcc_file(inputs_accc, results_accc, "AEP_LRGV_ACCC", "AEP_LRGV_ACCC")
    save_ctcc_file(inputs_acsr, results_acsr, "AEP_LRGV_ACSR_Rebuild", "AEP_LRGV_ACSR_Rebuild")

    bcr_accc = results_accc["bcr"]
    bcr_acsr = results_acsr["bcr"]
    print(f"\n{'='*60}")
    print(f"  COMPARISON: LRGV Reconductoring Options")
    print(f"{'='*60}")
    print(f"  {'Metric':<28} {'ACCC':>12} {'ACSR Rebuild':>14}")
    print(f"  {'-'*28} {'-'*12} {'-'*14}")
    print(
        f"  {'BCR Societal':<28} {bcr_accc.get('bcr_societal', 0):>12.3f}"
        f" {bcr_acsr.get('bcr_societal', 0):>14.3f}"
    )
    print(
        f"  {'BCR Utility':<28} {bcr_accc.get('bcr_utility', 0):>12.3f}"
        f" {bcr_acsr.get('bcr_utility', 0):>14.3f}"
    )
    print(
        f"  {'Net Benefit':<28} {fmt(bcr_accc.get('net_benefit_pv', 0)):>12}"
        f" {fmt(bcr_acsr.get('net_benefit_pv', 0)):>14}"
    )
    print(
        f"  {'Build Cost':<28} {fmt(results_accc['costs']['build']['total_pv']):>12}"
        f" {fmt(results_acsr['costs']['build']['total_pv']):>14}"
    )

    print("\nDone.")


if __name__ == "__main__":
    main()
