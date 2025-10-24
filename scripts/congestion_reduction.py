# Author: Andrew Igdal
# Date: 2025-10-24
# Description: This script calculates the congestion reduction costs for a transmission line project.
#              It computes the congestion reduction costs for a transmission line over the project lifetime.

import pandas as pd
import yaml
import numpy as np
import argparse


# Get info from project technical details
with open("../yamls/01_project_technical_details.yaml", "r") as file:
    project_details = yaml.load(file, Loader=yaml.FullLoader)
    construction_type = project_details["project"]["construction_type"]
    ac_dc = project_details["project"]["ac_dc"]
    capacity_mw = project_details["project"]["capacity_mw"]
    conductor_type = project_details["project"]["conductor_type"]
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
    total_pv = 0
    for year in range(round(start_year), round(start_year) + round(total_years)):
        total_pv += annual_cost / (1 + wacc_real) ** year
    return total_pv


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
):
    """
    Calculate the congestion reduction costs for a transmission line project.
    """
    if reconductoring == False:
        effective_capacity_relief = max(0, flow_factor * capacity_mw)

    else:
        effective_capacity_relief = max(0, capacity_mw - old_capacity_mw)

    energy_congestion_reduction = binding_hours * min(
        effective_capacity_relief, average_exceedance
    )
    energy_congestion_residual = binding_hours * max(
        0, average_exceedance - effective_capacity_relief
    )  # THIS IS ACTUALLY REMAINING CONGESTION. IF RESIDUAL CONGESTION EXISTS IT IS STILL A COST.

    annual_congestion_reduction_cost = (
        energy_congestion_reduction * average_congestion_price
    )
    annual_congestion_residual_cost = (
        energy_congestion_residual * average_congestion_price
    )  # THIS IS ACTUALLY THE COST OF THE REMAINING CONGESTION. IF RESIDUAL CONGESTION EXISTS IT IS STILL A COST.

    # near binding
    k = max(0.0, min(1.0, near_binding_relief_factor))
    near_hours = max(0.0, near_binding_hours)
    E_near = k * near_hours * effective_capacity_relief  #  MWh/yr

    annual_near_congestion_reduction_cost = E_near * average_congestion_price

    total_annual_congestion_reduction_cost = (
        annual_congestion_reduction_cost + annual_near_congestion_reduction_cost
    )
    total_annual_congestion_reduction_cost_haircut = (
        1 - saturation_factor
    ) * total_annual_congestion_reduction_cost

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

    return (
        lifetime_congestion_reduction_cost,
        lifetime_congestion_reduction_cost_haircut,
        lifetime_congestion_residual_cost,
        lifetime_congestion_reduction_cost_pv,
        lifetime_congestion_reduction_cost_haircut_pv,
        lifetime_congestion_residual_cost_pv,
        annual_congestion_reduction_cost,
        annual_congestion_residual_cost,
        effective_capacity_relief,
        energy_congestion_reduction,
        energy_congestion_residual,
        E_near,
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

    # Calculate congestion reduction costs
    (
        lifetime_congestion_reduction_cost,
        lifetime_congestion_reduction_cost_haircut,
        lifetime_congestion_residual_cost,
        lifetime_congestion_reduction_cost_pv,
        lifetime_congestion_reduction_cost_haircut_pv,
        lifetime_congestion_residual_cost_pv,
        annual_congestion_reduction_cost,
        annual_congestion_residual_cost,
        effective_capacity_relief,
        energy_congestion_reduction,
        energy_congestion_residual,
        E_near,
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


if __name__ == "__main__":
    main()
