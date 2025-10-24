# Author: Andrew Igdal
# Date: 2025-10-21
# Description: This script calculates the delay costs for a transmission line.
#              It computes the delay costs for a transmission line over the delay period.

import pandas as pd
import yaml
import numpy as np
import argparse
import math


def load_project_technical_details():
    """
    Load project technical details and construct category identifier.
    """
    with open("../yamls/01_project_technical_details.yaml", "r") as file:
        project_details = yaml.load(file, Loader=yaml.FullLoader)
    delay_year = project_details["timeline"]["delay_years"]
    return delay_year


def load_delay_costs():
    """
    Load delay costs from yaml file.
    """
    with open("../yamls/05_delays.yaml", "r") as file:
        delay_costs = yaml.load(file, Loader=yaml.FullLoader)
    return delay_costs


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


def main():
    """

    Main function to calculate and display delay costs.
    """
    delay_cost_df = load_delay_costs()
    delay_year = load_project_technical_details()

    legal = delay_cost_df["annual_delay_costs"]["legal"]
    admin = delay_cost_df["annual_delay_costs"]["admin"]
    labor = delay_cost_df["annual_delay_costs"]["labor"]
    material_and_equipment = delay_cost_df["annual_delay_costs"][
        "material_and_equipment"
    ]
    regulatory = delay_cost_df["annual_delay_costs"]["regulatory"]
    public_relations = delay_cost_df["annual_delay_costs"]["public_relations"]
    project_management = delay_cost_df["annual_delay_costs"]["project_management"]
    miscellaneous = delay_cost_df["annual_delay_costs"]["miscellaneous"]

    total_yearly_delay_cost = (
        legal
        + admin
        + labor
        + material_and_equipment
        + regulatory
        + public_relations
        + project_management
        + miscellaneous
    )
    total_delay_cost = total_yearly_delay_cost * delay_year

    inflation_rate, base_year, wacc_nominal, wacc_real = load_financing_details()

    total_delay_cost_pv = calculate_present_value(
        total_yearly_delay_cost,
        wacc_real,
        int(
            round(delay_year)
        ),  # Move rounding to the actual function, outside of main to prevent headaches
    )

    print("=" * 60)
    print("DELAY COST CALCULATION RESULTS")
    print("=" * 60)
    print(f"Delay year: {delay_year}")
    print(f"Total yearly delay cost: ${total_yearly_delay_cost:,.2f}")
    print(f"Total delay cost: ${total_delay_cost:,.2f}")

    print()
    print(
        f"PRESENT VALUES (discounted to base year (2025) using real WACC ({wacc_real:.2%})):"
    )

    print(f"TOTAL PRESENT VALUE DELAY COST: ${total_delay_cost_pv:,.2f}")
    print("=" * 60)


if __name__ == "__main__":
    main()
