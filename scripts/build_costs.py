# Author: Andrew Igdal
# Date: 2025-10-27
# Description: This calculates the build costs for a transmission line project. Then adjusts it to terrian adjustment
# via the weighted_miles.py script


# Standard library imports
import math
import yaml

# Local utility imports
from yaml_loaders import (
    load_project_technical_details,
    load_physical_details,
    load_contingencies,
    load_financing_details,
    load_cost_timing_patterns,
    load_afudc_config,
)
from financial_utils import (
    calculate_present_value,
    calculate_amortized_cost,
    calculate_afudc_rate,
    calculate_afudc_capitalized_cost,
)
from weighted_miles import calculate_weighted_miles


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
        construction_type,
        ac_dc,
        capacity_mw,
        conductor_type,
        converter_type,
        line_utilization,
        reconductoring,
        delay_year,
        construction_years,
        project_lifetime,
    ) = load_project_technical_details()

    # Construct category identifier
    category = (
        f"{construction_type}/{ac_dc}/{capacity_mw}MW/{conductor_type}/{converter_type}"
    )

    # Determine number of converters
    if ac_dc == "DC":
        # Load from YAML to get number_of_converters
        with open("../yamls/01_project_technical_details.yaml", "r") as file:
            pd = yaml.load(file, Loader=yaml.FullLoader)
        number_of_converters = pd["project"]["number_of_converters"]
    else:
        number_of_converters = 0

    total_miles = load_physical_details()
    contingencies = load_contingencies()
    inflation_rate, base_year, wacc_nominal, wacc_real = load_financing_details()

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

    # Load AFUDC configuration and timing patterns
    timing_patterns = load_cost_timing_patterns()["cost_timing_patterns"]
    apply_afudc, delay_active = load_afudc_config()

    # Load full financing YAML for AFUDC rate calculation
    with open("../yamls/03_financing.yaml", "r") as file:
        financing_yaml = yaml.load(file, Loader=yaml.FullLoader)
    afudc_rate, afudc_source = calculate_afudc_rate(financing_yaml)

    # ===== REGULATORY PERSPECTIVE: AFUDC Capitalization =====
    if apply_afudc:
        # Build costs are AFUDC-eligible and occur during construction
        (
            capitalized_cost_with_contingencies,
            afudc_amount,
        ) = calculate_afudc_capitalized_cost(
            total_cost_with_contingencies,
            timing_patterns["build_costs"],
            delay_year,
            construction_years,
            afudc_rate,
            delay_active,
        )

    # ===== SOCIETAL PERSPECTIVE: Present Value and Amortization =====
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

    print("[NOMINAL VALUES]")
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
    print(f"  TOTAL NOMINAL COST:       ${total_cost_with_contingencies:,.2f}")
    print()

    if apply_afudc:
        print("[REGULATORY PERSPECTIVE - AFUDC Capitalization]")
        print(f"  AFUDC Rate: {afudc_rate:.2%} ({afudc_source})")
        print(f"  Delay Period Active Work: {'Yes' if delay_active else 'No'}")
        print()
        print(
            f"  TOTAL CAPITALIZED COST (at COD): ${capitalized_cost_with_contingencies:,.2f}"
        )
        print(f"  Total AFUDC Amount: ${afudc_amount:,.2f}")
        print(
            f"    (Build costs incurred during {construction_years} year construction)"
        )
        print()

    print("[SOCIETAL PERSPECTIVE - Present Value & Amortization]")
    print(f"  Discount Rate: {wacc_real:.2%} (real WACC)")
    print(f"  Base Year: {base_year}")
    print()
    print("Amortized Costs (Annual Payments):")
    print(
        f"  Annual Payment (over {project_lifetime} years): ${annual_amortized_cost:,.2f}"
    )
    print(f"  PV of amortized payments (verification): ${pv_of_amortized:,.2f}")
    print("=" * 80)


if __name__ == "__main__":
    main()
