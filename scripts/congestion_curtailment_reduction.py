# Author: Andrew Igdal
# Date: 2025-10-24
# Description: This script calculates the congestion reduction costs for a transmission line project.
#              It computes the congestion reduction costs for a transmission line over the project lifetime.

import pandas as pd
import yaml
import numpy as np
import argparse
import math
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from csv_output_manager import CTCCOutputManager

# Get info from project technical details
with open("../yamls/01_project_technical_details.yaml", "r") as file:
    project_details = yaml.load(file, Loader=yaml.FullLoader)
    construction_type = project_details["project"]["construction_type"]
    ac_dc = project_details["project"]["ac_dc"]
    capacity_mw = project_details["project"]["capacity_mw"]
    conductor_type = project_details["project"]["conductor_type"]

    if ac_dc == "AC":
        converter_type = "NA"
    else:
        converter_type = project_details["project"]["converter_type"]

    line_utilization = project_details["project"]["line_utilization"]
    reconductoring = project_details["project"]["reconductoring"]

    delay_years = project_details["timeline"]["delay_years"]
    construction_years = project_details["timeline"]["construction_years"]
    project_lifetime = project_details["timeline"]["project_lifetime"]


def load_project_technical_details():
    """
    Load project technical details and construct category identifier.

    The category identifier follows the format:
    "construction_type/AC_or_DC/capacity_MW/conductor_type/converter_type"

    Returns:
        tuple: (category, delay_year, construction_years, project_lifetime, reconductoring)
    """
    with open("../yamls/01_project_technical_details.yaml", "r") as file:
        project_details = yaml.load(file, Loader=yaml.FullLoader)

    # Extract project specifications
    construction_type = project_details["project"]["construction_type"]
    ac_dc = project_details["project"]["ac_dc"]
    capacity_mw = project_details["project"]["capacity_mw"]
    conductor_type = project_details["project"]["conductor_type"]
    converter_type = project_details["project"]["converter_type"]

    reconductoring = project_details["project"]["reconductoring"]

    old_capacity_mw = project_details["project"]["old_capacity_mw"]

    # Extract timeline information
    delay_years = project_details["timeline"]["delay_years"]
    construction_years = project_details["timeline"]["construction_years"]
    project_lifetime = project_details["timeline"]["project_lifetime"]

    return (
        delay_years,
        construction_years,
        project_lifetime,
        reconductoring,
        capacity_mw,
        old_capacity_mw,
    )


def load_congestion_reductions():
    """
    Load congestion reduction parameters from YAML file.

    Returns:
        tuple: (flow_factor, binding_hours, average_exceedance, near_binding_hours,
               near_average_exceedance, near_binding_relief_factor, saturation_factor,
               average_congestion_price)
    """
    with open("../yamls/17_congestion_reductions.yaml", "r") as file:
        congestion_reductions = yaml.load(file, Loader=yaml.FullLoader)
        flow_factor = congestion_reductions["greenfield_congestion_reductions"][
            "constraints"
        ]["flow_factor"]
        binding_hours = congestion_reductions["greenfield_congestion_reductions"][
            "constraints"
        ]["binding_hours"]
        average_exceedance = congestion_reductions["greenfield_congestion_reductions"][
            "constraints"
        ]["average_exceedance"]
        near_binding_hours = congestion_reductions["greenfield_congestion_reductions"][
            "constraints"
        ]["near_binding_hours"]
        near_average_exceedance = congestion_reductions[
            "greenfield_congestion_reductions"
        ]["constraints"]["near_average_exceedance"]
        near_binding_relief_factor = congestion_reductions[
            "greenfield_congestion_reductions"
        ]["constraints"]["near_binding_relief_factor"]
        saturation_factor = congestion_reductions["greenfield_congestion_reductions"][
            "constraints"
        ]["saturation_factor"]

        # costs
        average_congestion_price = congestion_reductions[
            "greenfield_congestion_reductions"
        ]["costs"]["average_congestion_price"]

    return (
        flow_factor,
        binding_hours,
        average_exceedance,
        near_binding_hours,
        near_average_exceedance,
        near_binding_relief_factor,
        saturation_factor,
        average_congestion_price,
    )


def load_curtailment_reductions():
    with open("../yamls/18_curtailment_reductions.yaml", "r") as f:
        y = yaml.load(f, Loader=yaml.FullLoader)["curtailment_reductions"]

    Hc_tot = float(y.get("curtailment_hours_total", 0))
    avg_curt_mw = float(y.get("average_curtailment_mw", 0))
    avg_curt_price = float(y.get("average_curtailment_price", 0))
    curtailment_saturation_factor = float(y.get("curtailment_saturation_factor", 0))
    return Hc_tot, avg_curt_mw, avg_curt_price, curtailment_saturation_factor


def load_financing_details():
    """
    Load financing parameters and calculate real WACC using Fisher equation.

    Returns:
        tuple: (inflation_rate, base_year, wacc_nominal, wacc_real)
    """
    with open("../yamls/03_financing.yaml", "r") as file:
        financing_data = yaml.load(file, Loader=yaml.FullLoader)

    inflation_rate = financing_data["financial"]["inflation_rate"]
    base_year = financing_data["financial"]["base_year"]
    wacc_nominal = financing_data["financial"]["wacc_nominal"]

    # Use Fisher equation to convert nominal WACC to real WACC
    wacc_real = (1 + wacc_nominal) / (1 + inflation_rate) - 1

    return inflation_rate, base_year, wacc_nominal, wacc_real


def calculate_present_value(annual_cost, wacc_real, total_years, start_year=1):
    """
    Calculate the present value of annual payments over a given time period.

    Args:
        annual_cost (float): Annual cost amount
        wacc_real (float): Real weighted average cost of capital (discount rate)
        total_years (int): Number of years over which payments occur
        start_year (int): Year when payments begin (default: 1)

    Returns:
        float: Present value of the payment stream
    """
    n_full_years = math.floor(total_years)
    frac = total_years - n_full_years
    total_pv = 0
    for year in range(n_full_years):
        t = start_year + year
        total_pv += annual_cost / (1 + wacc_real) ** t

    if frac > 0:
        t_frac = start_year + n_full_years + frac
        total_pv += annual_cost * frac / (1 + wacc_real) ** t_frac

    return total_pv


def allocate_curtailment_then_congestion(
    ΔC_eff_mw: float,
    # binding inputs
    binding_hours_total: float,
    average_exceedance_mw: float,
    # curtailment inputs
    curtailment_hours_total: float,
    average_curtailment_mw: float,
    average_curtailment_price: float,
):
    """
    Allocate effective capacity relief between curtailment and congestion to avoid double-counting.

    Returns:
        dict: Allocation results including curtailment benefits and congestion capacity splits
    """
    Hb = max(0.0, float(binding_hours_total))
    X = max(0.0, float(average_exceedance_mw))
    Hc = max(0.0, float(curtailment_hours_total))
    ΔC = max(0.0, float(ΔC_eff_mw))
    Cc = max(0.0, float(average_curtailment_mw))
    λc = max(0.0, float(average_curtailment_price))

    # Curtailment relief (MWh/yr); if Hc==0 or Cc==0, this is zero.
    E_curt = Hc * min(ΔC, Cc)
    curt_benefit = E_curt * λc

    if Hb <= 0:
        # No binding hours; nothing to value under congestion.
        return {
            "E_curt_mwh_yr": E_curt,
            "curtailment_benefit_$_yr": curt_benefit,
            "theta_overlap": 0.0,
            "H_bc": 0.0,
            "H_bnon": 0.0,
            "ΔC_used_bc_mw": 0.0,
            "ΔC_remain_bc_mw": ΔC,
        }

    # Overlap proxy between binding and curtailment time
    theta = min(1.0, Hc / Hb) if Hc > 0 else 0.0
    H_bc = theta * Hb
    H_bnon = (1.0 - theta) * Hb

    # Headroom consumed by curtailment in overlap hours (MW basis)
    ΔC_used_bc = min(ΔC, Cc)
    ΔC_remain_bc = max(0.0, ΔC - ΔC_used_bc)

    return {
        "E_curt_mwh_yr": E_curt,
        "curtailment_benefit_$_yr": curt_benefit,
        "theta_overlap": theta,
        "H_bc": H_bc,
        "H_bnon": H_bnon,
        "ΔC_used_bc_mw": ΔC_used_bc,
        "ΔC_remain_bc_mw": ΔC_remain_bc,
    }


def calculate_congestion_reduction_costs(
    reconductoring: bool,
    capacity_mw: int,
    old_capacity_mw: int,
    flow_factor: float,
    binding_hours: int,
    average_exceedance: int,
    near_binding_hours: int,
    near_average_exceedance: int,
    near_binding_relief_factor: float,
    saturation_factor: float,
    average_congestion_price: float,
    project_lifetime: int,
    delay_years: int,
    construction_years: int,
    wacc_real: float,
    curtailment_hours_total: float,
    average_curtailment_mw: float,
    average_curtailment_price: float,
    curtailment_saturation_factor: float,
):
    """
    Calculate the congestion reduction costs for a transmission line project.
    """
    if reconductoring == False:
        effective_capacity_relief = max(0, flow_factor * capacity_mw)
    else:
        effective_capacity_relief = max(0, capacity_mw - old_capacity_mw)

    # Allocate capacity relief between curtailment and congestion
    alloc = allocate_curtailment_then_congestion(
        ΔC_eff_mw=effective_capacity_relief,
        binding_hours_total=binding_hours,
        average_exceedance_mw=average_exceedance,
        curtailment_hours_total=curtailment_hours_total,
        average_curtailment_mw=average_curtailment_mw,
        average_curtailment_price=average_curtailment_price,
    )

    # Curtailment results
    E_curt = alloc["E_curt_mwh_yr"]
    annual_curtailment_benefit = alloc["curtailment_benefit_$_yr"]

    # Congestion split with no double counting
    H_bc = alloc["H_bc"]
    H_bnon = alloc["H_bnon"]
    ΔC_rem = alloc["ΔC_remain_bc_mw"]

    # Congestion relief energy (MWh/yr) on overlap & non-overlap binding hours
    E_cong_bc = H_bc * min(ΔC_rem, average_exceedance)
    E_cong_non = H_bnon * min(effective_capacity_relief, average_exceedance)

    # Near-binding add (unchanged)
    k = max(0.0, min(1.0, near_binding_relief_factor))
    near_hours = max(0.0, near_binding_hours)
    E_near = k * near_hours * effective_capacity_relief  #  MWh/yr

    # Total congestion energy
    energy_congestion_reduction = E_cong_bc + E_cong_non + E_near

    # Monetize congestion ($/yr) — apply saturation haircut to $ only
    annual_congestion_reduction_cost_raw = (
        energy_congestion_reduction * average_congestion_price
    )
    annual_congestion_reduction_cost_haircut = (
        1 - saturation_factor
    ) * annual_congestion_reduction_cost_raw

    # Residual congestion energy (MWh/yr) on binding hours
    energy_congestion_residual = H_bc * max(
        0.0, average_exceedance - ΔC_rem
    ) + H_bnon * max(0.0, average_exceedance - effective_capacity_relief)
    annual_congestion_residual_cost = (
        energy_congestion_residual * average_congestion_price
    )

    # Apply curtailment saturation factor
    annual_curtailment_benefit_haircut = (
        1 - curtailment_saturation_factor
    ) * annual_curtailment_benefit

    total_annual_congestion_reduction_cost = annual_congestion_reduction_cost_raw
    total_annual_congestion_reduction_cost_haircut = (
        annual_congestion_reduction_cost_haircut
    )

    lifetime_congestion_reduction_cost = (
        total_annual_congestion_reduction_cost * project_lifetime
    )
    lifetime_congestion_reduction_cost_pv = calculate_present_value(
        total_annual_congestion_reduction_cost,
        wacc_real,
        project_lifetime,
        start_year=delay_years + construction_years,
    )

    lifetime_congestion_reduction_cost_haircut = (
        total_annual_congestion_reduction_cost_haircut * project_lifetime
    )
    lifetime_congestion_reduction_cost_haircut_pv = calculate_present_value(
        total_annual_congestion_reduction_cost_haircut,
        wacc_real,
        project_lifetime,
        start_year=delay_years + construction_years,
    )

    lifetime_congestion_residual_cost = (
        annual_congestion_residual_cost * project_lifetime
    )
    lifetime_congestion_residual_cost_pv = calculate_present_value(
        annual_congestion_residual_cost,
        wacc_real,
        project_lifetime,
        start_year=delay_years + construction_years,
    )

    annual_congestion_during_delay_and_construction = binding_hours * average_exceedance
    annual_congestion_during_delay_and_construction_cost = (
        annual_congestion_during_delay_and_construction * average_congestion_price
    )

    lifetime_congestion_during_delay_and_construction_cost = (
        annual_congestion_during_delay_and_construction_cost
        * (delay_years + construction_years)
    )
    lifetime_congestion_during_delay_and_construction_pv = calculate_present_value(
        annual_congestion_during_delay_and_construction_cost,
        wacc_real,
        delay_years + construction_years,
        start_year=1,
    )

    # Curtailment lifetime calculations
    lifetime_curtailment_benefit = annual_curtailment_benefit * project_lifetime
    lifetime_curtailment_benefit_pv = calculate_present_value(
        annual_curtailment_benefit,
        wacc_real,
        project_lifetime,
        start_year=delay_years + construction_years,
    )

    lifetime_curtailment_benefit_haircut = (
        annual_curtailment_benefit_haircut * project_lifetime
    )
    lifetime_curtailment_benefit_haircut_pv = calculate_present_value(
        annual_curtailment_benefit_haircut,
        wacc_real,
        project_lifetime,
        start_year=delay_years + construction_years,
    )

    # Curtailment costs during delay period
    annual_curtailment_during_delay_and_construction = (
        curtailment_hours_total * average_curtailment_mw
    )
    annual_curtailment_during_delay_and_construction_cost = (
        annual_curtailment_during_delay_and_construction * average_curtailment_price
    )

    lifetime_curtailment_during_delay_and_construction_cost = (
        annual_curtailment_during_delay_and_construction_cost
        * (delay_years + construction_years)
    )
    lifetime_curtailment_during_delay_and_construction_pv = calculate_present_value(
        annual_curtailment_during_delay_and_construction_cost,
        wacc_real,
        delay_years + construction_years,
        start_year=1,
    )

    return (
        lifetime_congestion_reduction_cost,
        lifetime_congestion_reduction_cost_haircut,
        lifetime_congestion_residual_cost,
        lifetime_congestion_reduction_cost_pv,
        lifetime_congestion_reduction_cost_haircut_pv,
        lifetime_congestion_residual_cost_pv,
        annual_congestion_reduction_cost_raw,
        annual_congestion_residual_cost,
        effective_capacity_relief,
        energy_congestion_reduction,
        energy_congestion_residual,
        E_near,
        lifetime_congestion_during_delay_and_construction_cost,
        lifetime_congestion_during_delay_and_construction_pv,
        # Curtailment values
        E_curt,
        annual_curtailment_benefit,
        annual_curtailment_benefit_haircut,
        lifetime_curtailment_benefit,
        lifetime_curtailment_benefit_pv,
        lifetime_curtailment_benefit_haircut,
        lifetime_curtailment_benefit_haircut_pv,
        lifetime_curtailment_during_delay_and_construction_cost,
        lifetime_curtailment_during_delay_and_construction_pv,
        # Allocation metrics
        alloc["theta_overlap"],
        H_bc,
        H_bnon,
        ΔC_rem,
    )


def main():
    """
    Main function to calculate and display congestion reduction costs.
    """
    # Load all required data
    (
        delay_years,
        construction_years,
        project_lifetime,
        reconductoring,
        capacity_mw,
        old_capacity_mw,
    ) = load_project_technical_details()

    # Load congestion reduction parameters
    (
        flow_factor,
        binding_hours,
        average_exceedance,
        near_binding_hours,
        near_average_exceedance,
        near_binding_relief_factor,
        saturation_factor,
        average_congestion_price,
    ) = load_congestion_reductions()

    # Load financing details
    inflation_rate, base_year, wacc_nominal, wacc_real = load_financing_details()

    # Load curtailment reduction parameters
    (
        curtailment_hours_total,
        average_curtailment_mw,
        average_curtailment_price,
        curtailment_saturation_factor,
    ) = load_curtailment_reductions()

    # Calculate congestion reduction costs
    (
        lifetime_congestion_reduction_cost,
        lifetime_congestion_reduction_cost_haircut,
        lifetime_congestion_residual_cost,
        lifetime_congestion_reduction_cost_pv,
        lifetime_congestion_reduction_cost_haircut_pv,
        lifetime_congestion_residual_cost_pv,
        annual_congestion_reduction_cost_raw,
        annual_congestion_residual_cost,
        effective_capacity_relief,
        energy_congestion_reduction,
        energy_congestion_residual,
        E_near,
        lifetime_congestion_during_delay_and_construction_cost,
        lifetime_congestion_during_delay_and_construction_pv,
        # Curtailment values
        E_curt,
        annual_curtailment_benefit,
        annual_curtailment_benefit_haircut,
        lifetime_curtailment_benefit,
        lifetime_curtailment_benefit_pv,
        lifetime_curtailment_benefit_haircut,
        lifetime_curtailment_benefit_haircut_pv,
        lifetime_curtailment_during_delay_and_construction_cost,
        lifetime_curtailment_during_delay_and_construction_pv,
        # Allocation metrics
        theta_overlap,
        H_bc,
        H_bnon,
        ΔC_rem,
    ) = calculate_congestion_reduction_costs(
        reconductoring,
        capacity_mw,
        old_capacity_mw,
        flow_factor,
        binding_hours,
        average_exceedance,
        near_binding_hours,
        near_average_exceedance,
        near_binding_relief_factor,
        saturation_factor,
        average_congestion_price,
        project_lifetime,
        delay_years,
        construction_years,
        wacc_real,
        curtailment_hours_total,
        average_curtailment_mw,
        average_curtailment_price,
        curtailment_saturation_factor,
    )

    print("=" * 60)
    print("CONGESTION ENERGY REDUCTION RELIEF PHYSICAL RESULTS AND QUANTITIES")
    print("=" * 60)
    print(f"Effective capacity relief: {effective_capacity_relief:,.2f} MW")
    print(f"Energy congestion reduction: {energy_congestion_reduction:,.2f} MWh/yr")
    print(f"Energy congestion residual: {energy_congestion_residual:,.2f} MWh/yr")
    print(f"E_near: {E_near:,.2f} MWh/yr")

    print()
    print("=" * 60)
    print("CONGESTION DURING DELAY AND CONSTRUCTION RESULTS AND QUANTITIES")
    print("=" * 60)

    print(
        f"Lifetime congestion during delay and construction cost: ${lifetime_congestion_during_delay_and_construction_cost:,.2f}"
    )
    print(
        f"Lifetime congestion during delay and construction PV: ${lifetime_congestion_during_delay_and_construction_pv:,.2f}"
    )

    print()
    print("=" * 60)
    print("CURTAILMENT REDUCTION RESULTS AND QUANTITIES")
    print("=" * 60)
    print(f"Curtailment energy reduction: {E_curt:,.2f} MWh/yr")
    print(f"Annual curtailment benefit: ${annual_curtailment_benefit:,.2f}")
    print(
        f"Annual curtailment benefit haircut: ${annual_curtailment_benefit_haircut:,.2f}"
    )
    print(f"Overlap factor (theta): {theta_overlap:.3f}")
    print(f"Binding hours (overlap): {H_bc:,.0f} hrs/yr")
    print(f"Binding hours (non-overlap): {H_bnon:,.0f} hrs/yr")
    print(f"Remaining capacity for congestion: {ΔC_rem:,.2f} MW")

    print()
    print("=" * 60)
    print("CURTAILMENT DURING DELAY AND CONSTRUCTION RESULTS")
    print("=" * 60)
    print(
        f"Lifetime curtailment during delay and construction cost: ${lifetime_curtailment_during_delay_and_construction_cost:,.2f}"
    )
    print(
        f"Lifetime curtailment during delay and construction PV: ${lifetime_curtailment_during_delay_and_construction_pv:,.2f}"
    )

    print()
    print("=" * 60)
    print("CURTAILMENT REDUCTION COST CALCULATION RESULTS")
    print("=" * 60)
    print(f"Lifetime curtailment benefit: ${lifetime_curtailment_benefit:,.2f}")
    print(
        f"Lifetime curtailment benefit haircut: ${lifetime_curtailment_benefit_haircut:,.2f}"
    )

    print()
    print(
        f"PRESENT VALUES (discounted to base year (2025) using real WACC ({wacc_real:.2%})):"
    )
    print(f"Lifetime curtailment benefit PV: ${lifetime_curtailment_benefit_pv:,.2f}")
    print(
        f"Lifetime curtailment benefit haircut PV: ${lifetime_curtailment_benefit_haircut_pv:,.2f}"
    )

    print()
    print("=" * 60)
    print("CONGESTION REDUCTION COST CALCULATION RESULTS")
    print("=" * 60)
    print(
        f"Lifetime congestion reduction cost: ${lifetime_congestion_reduction_cost:,.2f}"
    )
    print(
        f"Lifetime congestion reduction cost haircut: ${lifetime_congestion_reduction_cost_haircut:,.2f}"
    )
    print(
        f"Lifetime congestion residual cost: ${lifetime_congestion_residual_cost:,.2f}"
    )

    print()

    print(
        f"PRESENT VALUES (discounted to base year (2025) using real WACC ({wacc_real:.2%})):"
    )
    print(
        f"Lifetime congestion reduction cost PV: ${lifetime_congestion_reduction_cost_pv:,.2f}"
    )
    print(
        f"Lifetime congestion reduction cost haircut PV: ${lifetime_congestion_reduction_cost_haircut_pv:,.2f}"
    )
    print(
        f"Lifetime congestion residual cost PV: ${lifetime_congestion_residual_cost_pv:,.2f}"
    )
    print("=" * 60)

    # ========================================================================
    # CSV OUTPUT - Write results to batch summary and detail CSV
    # ========================================================================
    
    # Initialize CSV output manager
    csv_manager = CTCCOutputManager()
    
    # Prepare results dictionary with all calculated values
    results = {
        # BENEFITS - Congestion reduction (operational benefits)
        "congestion_benefit_annual": annual_congestion_reduction_cost_raw,
        "congestion_benefit_nominal": lifetime_congestion_reduction_cost,
        "congestion_benefit_pv": lifetime_congestion_reduction_cost_pv,
        "congestion_benefit_haircut_annual": annual_congestion_reduction_cost_raw * (1 - saturation_factor),
        "congestion_benefit_haircut_nominal": lifetime_congestion_reduction_cost_haircut,
        "congestion_benefit_haircut_pv": lifetime_congestion_reduction_cost_haircut_pv,
        
        # BENEFITS - Curtailment reduction (operational benefits)
        "curtailment_benefit_annual": annual_curtailment_benefit,
        "curtailment_benefit_nominal": lifetime_curtailment_benefit,
        "curtailment_benefit_pv": lifetime_curtailment_benefit_pv,
        "curtailment_benefit_haircut_annual": annual_curtailment_benefit_haircut,
        "curtailment_benefit_haircut_nominal": lifetime_curtailment_benefit_haircut,
        "curtailment_benefit_haircut_pv": lifetime_curtailment_benefit_haircut_pv,
        
        # COSTS - Delay/construction opportunity costs
        "congestion_delay_cost_nominal": lifetime_congestion_during_delay_and_construction_cost,
        "congestion_delay_cost_pv": lifetime_congestion_during_delay_and_construction_pv,
        "curtailment_delay_cost_nominal": lifetime_curtailment_during_delay_and_construction_cost,
        "curtailment_delay_cost_pv": lifetime_curtailment_during_delay_and_construction_pv,
        
        # COSTS - Residual unrelieved congestion
        "residual_congestion_annual": annual_congestion_residual_cost,
        "residual_congestion_nominal": lifetime_congestion_residual_cost,
        "residual_congestion_pv": lifetime_congestion_residual_cost_pv,
        
        # Physical metrics (for reference)
        "effective_capacity_relief_mw": effective_capacity_relief,
        "energy_congestion_reduction_mwh_yr": energy_congestion_reduction,
        "energy_congestion_residual_mwh_yr": energy_congestion_residual,
        "energy_curtailment_reduction_mwh_yr": E_curt,
        "theta_overlap": theta_overlap,
        "binding_hours_overlap": H_bc,
        "binding_hours_non_overlap": H_bnon,
        "remaining_capacity_mw": ΔC_rem,
    }
    
    # Write to CSV
    csv_manager.add_congestion_curtailment(results)
    csv_manager.write_batch_summary()


if __name__ == "__main__":
    main()
