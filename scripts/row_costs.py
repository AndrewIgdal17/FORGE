# Author: Andrew Igdal
# Date: 2025-10-20
# Description: This script calculates the right-of-way costs for a transmission line.
#              It computes acquisition, holding, and rental costs for transmission line ROW
#              across different zones and terrain types, then calculates present values.

import pandas as pd
import yaml
import numpy as np
import argparse
import math


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
    capacity_mw = f"{project_details['project']['capacity_mw']}MW"
    conductor_type = project_details["project"]["conductor_type"]
    converter_type = project_details["project"]["converter_type"]

    reconductoring = project_details["project"]["reconductoring"]

    # Construct category identifier for row width lookup
    category = (
        f"{construction_type}/{ac_dc}/{capacity_mw}/{conductor_type}/{converter_type}"
    )

    # Extract timeline information
    delay_year = project_details["timeline"]["delay_years"]
    construction_years = project_details["timeline"]["construction_years"]
    project_lifetime = project_details["timeline"]["project_lifetime"]

    return category, delay_year, construction_years, project_lifetime, reconductoring


def load_row_widths(category):
    """
    Load row width for the specified project category.

    Args:
        category (str): Project category identifier

    Returns:
        float: Row width in feet
    """
    with open("../yamls/20_project_category_row_widths.yaml", "r") as file:
        row_widths_data = yaml.load(file, Loader=yaml.FullLoader)

    row_width_feet = row_widths_data["project_categories_row_widths"][category][
        "row_width_feet"
    ]
    return row_width_feet


def load_physical_details():
    """
    Load physical project details and calculate total miles.

    Returns:
        float: Total miles of transmission line across all terrain types
    """
    with open("../yamls/02_project_physical_details.yaml", "r") as file:
        physical_details = yaml.load(file, Loader=yaml.FullLoader)

    # Sum miles across all terrain types to get total line length
    total_miles = sum(physical_details["terrain"]["terrain_miles"].values())
    return total_miles


def calculate_zone_costs(row_width_feet):
    """
    Calculate ROW costs for each zone where the transmission line passes.

    Args:
        row_width_feet (float): Width of right-of-way in feet

    Returns:
        tuple: (yearly_holding_cost, acquisition_cost, yearly_rent_cost, total_acres)
    """
    with open("../yamls/11_project_row_details.yaml", "r") as file:
        row_details = yaml.load(file, Loader=yaml.FullLoader)

    yearly_holding_cost = 0
    acquisition_cost = 0
    yearly_rent_cost = 0

    # Process each zone that has non-zero miles
    for zone_number, zone_details in row_details["right_of_way"].items():
        zone_miles = zone_details["miles"]

        if zone_miles > 0:
            # Convert miles and feet to acres: (miles * feet_per_mile * width_feet) / square_feet_per_acre
            zone_acres = (zone_miles * 5280 * row_width_feet) / 43560

            # Accumulate costs for this zone
            acquisition_cost += zone_acres * zone_details["acquisition_cost"]
            yearly_rent_cost += zone_acres * zone_details["rent_cost"]
            yearly_holding_cost += zone_acres * zone_details["hold_cost"]

    # Calculate total acres across all zones
    total_acres = sum(
        (zone_details["miles"] * 5280 * row_width_feet) / 43560
        for zone_details in row_details["right_of_way"].values()
        if zone_details["miles"] > 0
    )

    return yearly_holding_cost, acquisition_cost, yearly_rent_cost, total_acres


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


def main():
    """
    Main function to calculate and display ROW costs.
    """
    # Load project specifications and timeline
    category, delay_year, construction_years, project_lifetime, reconductoring = (
        load_project_technical_details()
    )

    # Load row width for this project category
    row_width_feet = load_row_widths(category)

    # Load physical details (total miles)
    total_miles = load_physical_details()

    # Calculate costs for each zone
    yearly_holding_cost, acquisition_cost, yearly_rent_cost, total_acres = (
        calculate_zone_costs(row_width_feet)
    )

    # Load financing parameters
    inflation_rate, base_year, wacc_nominal, wacc_real = load_financing_details()

    # Define timing parameters
    rent_start_year = delay_year + 1
    rent_total_years = project_lifetime + construction_years

    if reconductoring:
        total_holding_cost = 0
        acquisition_cost = 0
        total_rent_cost = yearly_rent_cost * (project_lifetime + construction_years)
        total_nominal_cost = total_holding_cost + acquisition_cost + total_rent_cost

        # present values
        total_holding_cost_pv = 0
        total_acquisition_cost_pv = 0
        total_rent_cost_pv = calculate_present_value(
            yearly_rent_cost, wacc_real, int(rent_total_years), int(rent_start_year)
        )

    else:
        # Calculate total nominal costs over project lifetime
        total_holding_cost = yearly_holding_cost * delay_year
        total_rent_cost = yearly_rent_cost * (project_lifetime + construction_years)
        total_nominal_cost = total_holding_cost + acquisition_cost + total_rent_cost
        # Calculate present values of all costs
        # Holding costs: incurred annually during delay period
        total_holding_cost_pv = calculate_present_value(
            yearly_holding_cost, wacc_real, int(delay_year)
        )

        # Acquisition costs: one-time payment at end of delay period
        total_acquisition_cost_pv = acquisition_cost / (1 + wacc_real) ** delay_year

        # Rent costs: incurred annually during operation period
        total_rent_cost_pv = calculate_present_value(
            yearly_rent_cost, wacc_real, int(rent_total_years), int(rent_start_year)
        )

    # Display results
    print("=" * 60)
    print("RIGHT-OF-WAY COST CALCULATION RESULTS")
    print("=" * 60)
    print(f"Project Category: {category}")
    print(f"Total Miles: {total_miles:.2f}")
    print(f"Row Width: {row_width_feet:.1f} feet")
    print(f"Total Acres: {total_acres:.2f}")
    print()

    print("NOMINAL VALUES (undiscounted):")
    print(f"  Holding Cost: ${total_holding_cost:,.2f}")
    print(f"  Acquisition Cost: ${acquisition_cost:,.2f}")
    print(f"  Rent Cost: ${total_rent_cost:,.2f}")
    print()
    print(f"TOTAL NOMINAL ROW Cost: ${total_nominal_cost:,.2f}")
    print()

    print(
        f"PRESENT VALUES (discounted to base year (2025) using real WACC ({wacc_real:.2%})):"
    )
    print(f"  Holding Cost PV: ${total_holding_cost_pv:,.2f}")
    print(f"  Acquisition Cost PV: ${total_acquisition_cost_pv:,.2f}")
    print(f"  Rent Cost PV: ${total_rent_cost_pv:,.2f}")
    print()

    total_pv_cost = (
        total_holding_cost_pv + total_acquisition_cost_pv + total_rent_cost_pv
    )
    print(f"TOTAL PRESENT VALUE ROW COST: ${total_pv_cost:,.2f}")
    print("=" * 60)


if __name__ == "__main__":
    main()
