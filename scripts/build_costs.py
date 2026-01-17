# Author: Andrew Igdal
# Date: 2025-10-27
# Description: This calculates the build costs for a transmission line project. Then adjusts it to terrian adjustment
# via the weighted_miles.py script

from __future__ import annotations

# Standard library imports
import math
import yaml
import sys
import os
from typing import Dict, Tuple

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from smart_output import CTCCOutputManager

# Local utility imports
from smart_loaders import (
    load_project_technical_details,
    load_physical_details,
    load_contingencies,
    load_financing_details,
    load_cost_timing_patterns,
    load_afudc_config,
    get_project_data_raw,
    get_financing_data_raw,
)
from financial_utils import (
    calculate_present_value,
    calculate_amortized_cost,
    calculate_afudc_rate,
    calculate_afudc_capitalized_cost,
    validate_discount_rate,
)
from weighted_miles import calculate_weighted_miles
from path_config import YAMLS_DIR


def load_costs(
    category: str,
    total_miles: float,
    number_of_converters: int,
    contingencies: Dict[str, float],
    reconductoring: bool,
) -> Tuple[float, float, float, float, float, float, float, float, float, float]:
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
    try:
        with open(YAMLS_DIR / "10_project_category_build_costs.yaml", "r") as file:
            data = yaml.safe_load(file)
        if not data:
            raise ValueError("Build costs YAML file is empty or invalid")
        if "project_categories_build_costs" not in data:
            raise KeyError(
                "Missing 'project_categories_build_costs' key in build costs YAML file"
            )
        costs = data["project_categories_build_costs"]
        if category not in costs:
            raise KeyError(f"Category '{category}' not found in build costs YAML")
        required_keys = [
            "variable_conductor_cost_per_mile",
            "fixed_conductor_cost",
            "variable_structure_cost_per_mile",
            "fixed_converter_cost",
        ]
        for key in required_keys:
            if key not in costs[category]:
                raise KeyError(
                    f"Missing '{key}' key for category '{category}' in build costs YAML"
                )
    except FileNotFoundError:
        raise FileNotFoundError(
            f"Build costs YAML not found at {YAMLS_DIR / '10_project_category_build_costs.yaml'}"
        )
    except yaml.YAMLError as e:
        raise ValueError(f"Error parsing build costs YAML: {e}")
    except KeyError as e:
        raise KeyError(f"Missing required key in build costs YAML: {e}")

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


def main() -> None:
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
        converter_loss_percentage,
    ) = load_project_technical_details()

    # Construct category identifier
    category = (
        f"{construction_type}/{ac_dc}/{capacity_mw}MW/{conductor_type}/{converter_type}"
    )

    # Determine number of converters
    if ac_dc == "DC":
        # Load project data to get number_of_converters
        try:
            project_details_data = get_project_data_raw()
            if "project" not in project_details_data:
                raise KeyError(
                    "Missing 'project' key in project technical details"
                )
            if "number_of_converters" not in project_details_data["project"]:
                raise KeyError(
                    "Missing 'number_of_converters' key in project section of technical details"
                )
            number_of_converters = project_details_data["project"][
                "number_of_converters"
            ]
        except KeyError as e:
            raise KeyError(
                f"Missing required key in project technical details: {e}"
            )
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

    # Load full financing data for AFUDC rate calculation
    financing_yaml = get_financing_data_raw()
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

    # ===== SOCIETAL PERSPECTIVE: Present Value Discounting =====
    # Build costs: spread evenly over construction period
    # Annual cost during construction years
    construction_start_year = delay_year + 1
    if construction_years > 0:
        annual_build_cost = total_cost_with_contingencies / construction_years
        build_cost_pv = calculate_present_value(
            annual_build_cost, wacc_real, construction_years, construction_start_year
        )
    else:
        # Validate wacc_real before direct use to prevent division by zero
        validate_discount_rate(wacc_real, "wacc_real")
        # If construction_years is 0, treat as one-time cost at construction_start_year
        build_cost_pv = (
            total_cost_with_contingencies / (1 + wacc_real) ** construction_start_year
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

    print("[SOCIETAL PERSPECTIVE - Present Value]")
    print(f"  Discount Rate: {wacc_real:.2%} (real WACC)")
    print(f"  Base Year: {base_year}")
    print()
    print("Build costs incurred during construction period:")
    if construction_years > 0:
        print(
            f"  Annual Cost (over {construction_years} year(s) construction): ${annual_build_cost:,.2f}"
        )
        print(
            f"  Construction Period: Year {construction_start_year} to Year {construction_start_year + construction_years - 1}"
        )
    else:
        print(f"  One-time cost at Year {construction_start_year}")
    print(f"  Build Cost PV: ${build_cost_pv:,.2f}")
    print("=" * 80)

    # ========================================================================
    # CSV OUTPUT - Write results to batch summary and detail CSV
    # ========================================================================

    # Initialize CSV output manager
    csv_manager = CTCCOutputManager()

    # Prepare results dictionary
    results = {
        "total_nominal": total_cost_with_contingencies,
        "total_afudc": capitalized_cost_with_contingencies if apply_afudc else 0,
        "total_pv": build_cost_pv,
        "conductor_nominal": conductor_cost_with_contingencies,
        "structure_nominal": structure_cost_with_contingencies,
        "converter_nominal": converter_cost_with_contingencies,
        "conductor_afudc": 0,  # Component-level AFUDC not calculated separately
        "structure_afudc": 0,
        "converter_afudc": 0,
    }

    # Write to CSV
    csv_manager.add_build_costs(results)
    csv_manager.write_batch_summary()


if __name__ == "__main__":
    main()
