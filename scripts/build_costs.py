# Author: Andrew Igdal
# Date: 2025-10-27
# Description: This calculates the build costs for a transmission line project. Then adjusts it to terrian adjustment
# via the weighted_miles.py script


import pandas as pd
import yaml
import numpy as np
import argparse
import math
from weighted_miles import calculate_weighted_miles


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


def calculate_amortized_cost(principal, wacc_real, project_lifetime):
    """
    Calculate annual amortized cost using standard amortization formula.

    This converts a lump-sum cost into equal annual payments over the project lifetime.

    Args:
        principal: Initial cost (total build cost)
        wacc_real: Real weighted average cost of capital (discount rate)
        project_lifetime: Number of years to amortize over

    Returns:
        float: Annual amortized payment
    """
    if wacc_real == 0:
        return principal / project_lifetime

    # Standard amortization formula: A = P * [r(1+r)^n] / [(1+r)^n - 1]
    numerator = wacc_real * (1 + wacc_real) ** project_lifetime
    denominator = (1 + wacc_real) ** project_lifetime - 1

    return principal * numerator / denominator


def load_project_technical_details():
    """
    Load project technical details and construct category identifier.

    The category identifier follows the format:
    "construction_type/AC_or_DC/capacity_MW/conductor_type/converter_type"

    Returns:
        tuple: (category, delay_year, construction_years, project_lifetime, reconductoring, number_of_converters)
    """
    with open("../yamls/01_project_technical_details.yaml", "r") as file:
        project_details = yaml.load(file, Loader=yaml.FullLoader)

    # Extract project specifications
    construction_type = project_details["project"]["construction_type"]
    ac_dc = project_details["project"]["ac_dc"]
    capacity_mw = f"{project_details['project']['capacity_mw']}MW"
    conductor_type = project_details["project"]["conductor_type"]

    if ac_dc == "AC":
        converter_type = "NA"
        number_of_converters = 0
    else:
        converter_type = project_details["project"]["converter_type"]
        number_of_converters = project_details["project"]["number_of_converters"]

    reconductoring = project_details["project"]["reconductoring"]

    # Construct category identifier for row width lookup
    category = (
        f"{construction_type}/{ac_dc}/{capacity_mw}/{conductor_type}/{converter_type}"
    )

    # Extract timeline information
    delay_year = project_details["timeline"]["delay_years"]
    construction_years = project_details["timeline"]["construction_years"]
    project_lifetime = project_details["timeline"]["project_lifetime"]

    return (
        category,
        delay_year,
        construction_years,
        project_lifetime,
        reconductoring,
        number_of_converters,
    )


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


def load_contingencies():
    """
    Load contingencies for the comprehensive transmission cost calculator.

    Returns:
        dict: Dictionary containing contingency percentages for conductor, structure, and converter
    """
    with open("../yamls/03_financing.yaml", "r") as file:
        contingencies = yaml.load(file, Loader=yaml.FullLoader)["financial"][
            "contingencies"
        ]
    return contingencies


def load_costs(
    category, total_miles, number_of_converters, contingencies, reconductoring
):
    """
    Load the costs for the comprehensive transmission cost calculator.

    Args:
        category: Project category identifier
        total_miles: Total miles of transmission line
        number_of_converters: Number of converters needed
        contingencies: Dictionary of contingency percentages
        reconductoring: Boolean indicating if this is a reconductoring project

    Returns:
        tuple: (total_cost, total_cost_with_contingencies, conductor_cost, structure_cost,
                converter_cost, conductor_cost_with_contingencies, structure_cost_with_contingencies,
                converter_cost_with_contingencies, weighted_miles, average_terrain_multiplier)
    """
    with open("../yamls/10_project_category_build_costs.yaml", "r") as file:
        costs = yaml.load(file, Loader=yaml.FullLoader)[
            "project_categories_build_costs"
        ]

    weighted_miles, average_terrain_multiplier = calculate_weighted_miles()

    variable_conductor_cost_per_mile = costs[category][
        "variable_conductor_cost_per_mile"
    ]
    fixed_conductor_cost = costs[category]["fixed_conductor_cost"]
    variable_structure_cost_per_mile = costs[category][
        "variable_structure_cost_per_mile"
    ]
    fixed_converter_cost = costs[category]["fixed_converter_cost"]

    conductor_cost = (
        variable_conductor_cost_per_mile * weighted_miles
    ) + fixed_conductor_cost

    # If reconductoring, structure and converter costs = 0
    if reconductoring:
        structure_cost = 0
        converter_cost = 0
    else:
        structure_cost = variable_structure_cost_per_mile * weighted_miles
        converter_cost = fixed_converter_cost * number_of_converters

    total_cost = conductor_cost + structure_cost + converter_cost

    conductor_cost_with_contingencies = conductor_cost * (
        1 + contingencies["conductor_contingency"]
    )
    structure_cost_with_contingencies = structure_cost * (
        1 + contingencies["structure_contingency"]
    )
    converter_cost_with_contingencies = converter_cost * (
        1 + contingencies["converter_contingency"]
    )

    total_cost_with_contingencies = (
        conductor_cost_with_contingencies
        + structure_cost_with_contingencies
        + converter_cost_with_contingencies
    )

    return (
        total_cost,
        total_cost_with_contingencies,
        conductor_cost,
        structure_cost,
        converter_cost,
        conductor_cost_with_contingencies,
        structure_cost_with_contingencies,
        converter_cost_with_contingencies,
        weighted_miles,
        average_terrain_multiplier,
    )


def main():
    """
    Main function to calculate and display build costs.
    """
    (
        category,
        delay_year,
        construction_years,
        project_lifetime,
        reconductoring,
        number_of_converters,
    ) = load_project_technical_details()
    total_miles = load_physical_details()
    contingencies = load_contingencies()
    _, _, _, wacc_real = load_financing_details()

    (
        total_cost,
        total_cost_with_contingencies,
        conductor_cost,
        structure_cost,
        converter_cost,
        conductor_cost_with_contingencies,
        structure_cost_with_contingencies,
        converter_cost_with_contingencies,
        weighted_miles,
        average_terrain_multiplier,
    ) = load_costs(
        category, total_miles, number_of_converters, contingencies, reconductoring
    )

    # Calculate amortized cost
    annual_amortized_cost = calculate_amortized_cost(
        total_cost_with_contingencies, wacc_real, project_lifetime
    )

    # Verify amortization: discount the annual payments back to present value
    # This should equal the original cost
    pv_of_amortized = calculate_present_value(
        annual_amortized_cost, wacc_real, project_lifetime
    )

    # Format and display results
    print("=" * 80)
    print("TRANSMISSION LINE BUILD COSTS ANALYSIS")
    print("=" * 80)
    print()
    print("Project Metrics:")
    print(f"  Total Miles:              {total_miles:,.2f} miles")
    print(f"  Weighted Miles:           {weighted_miles:,.2f} miles")
    print(f"  Terrain Multiplier:       {average_terrain_multiplier:.2f}")
    print()
    print("Base Build Costs:")
    print(f"  Conductor Costs:          ${conductor_cost:,.2f}")
    print(f"  Structure Costs:          ${structure_cost:,.2f}")
    print(f"  Converter Costs:          ${converter_cost:,.2f}")
    print("  " + "-" * 52)
    print(f"  Total Base Cost:          ${total_cost:,.2f}")
    print()
    print("Costs with Contingencies:")
    print(f"  Conductor Costs:          ${conductor_cost_with_contingencies:,.2f}")
    print(f"  Structure Costs:          ${structure_cost_with_contingencies:,.2f}")
    print(f"  Converter Costs:          ${converter_cost_with_contingencies:,.2f}")
    print("  " + "-" * 52)
    print(f"  Total with Contingencies: ${total_cost_with_contingencies:,.2f}")
    print()
    print("Amortized Costs (Annual Payments):")
    print(
        f"  Annual Payment (over {project_lifetime} years): ${annual_amortized_cost:,.2f}"
    )
    print(f"  Using WACC (real): {wacc_real:.2%}")
    print(f"  PV of amortized payments (verification): ${pv_of_amortized:,.2f}")
    print("=" * 80)


if __name__ == "__main__":
    main()
