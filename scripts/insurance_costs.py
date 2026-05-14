# Author: Andrew Igdal
# Date: 2025-10-28
# Description: This script calculates operational insurance costs for transmission line assets.
#              Insurance premiums are based on insurable asset value (conductors, structures, converters)
#              and paid annually over the project lifetime.

from __future__ import annotations

# Standard library imports
import yaml
import sys
import os
from typing import Dict, Any

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from smart_output import CTCCOutputManager

# Local utility imports
from smart_loaders import (
    load_project_technical_details,
    load_physical_details,
    load_contingencies,
    load_financing_details,
    load_insurance_details,
    get_project_data_raw,
)
from financial_utils import calculate_present_value, calculate_cod_year
from build_costs import load_costs
from weighted_miles import calculate_weighted_miles
from constants import TRANSMISSION_TYPE_DC
from path_config import YAMLS_DIR


def calculate_insurance_costs(
    insurance_yaml: Dict[str, Any],
    conductor_cost_with_contingencies: float,
    structure_cost_with_contingencies: float,
    converter_cost_with_contingencies: float,
    project_lifetime: int,
) -> Dict[str, float]:
    """
    Calculate operational insurance costs based on insurable asset value.

    Args:
        insurance_yaml: Loaded insurance YAML data
        conductor_cost_with_contingencies: Conductor cost with contingencies
        structure_cost_with_contingencies: Structure cost with contingencies
        converter_cost_with_contingencies: Converter cost with contingencies
        project_lifetime: Project lifetime in years

    Returns:
        dict: Contains insurable_value, annual_premium, nominal_cost, premium_rate
    """
    ins_cfg = insurance_yaml["insurance"]
    components = ins_cfg.get("insurable_components", {})

    # Calculate insurable asset value based on which components are insured
    insurable_value = 0.0

    if components.get("conductors", True):
        insurable_value += conductor_cost_with_contingencies

    if components.get("structures", True):
        insurable_value += structure_cost_with_contingencies

    if components.get("converters", True):
        insurable_value += converter_cost_with_contingencies

    premium_rate = ins_cfg.get("premium_rate", 0.002)

    # Calculate annual premium and lifetime cost
    annual_premium = insurable_value * premium_rate
    nominal_lifetime_cost = annual_premium * project_lifetime

    return {
        "insurable_value": insurable_value,
        "annual_premium": annual_premium,
        "premium_rate": premium_rate,
        "nominal_lifetime_cost": nominal_lifetime_cost,
    }



def main() -> None:
    """Main function to calculate and display insurance costs."""
    # Load project specifications
    project_details = load_project_technical_details()

    # Construct category identifier
    from calculation_utils import build_category_string

    category = build_category_string(project_details=project_details)

    # Determine number of converters
    if project_details.ac_dc == TRANSMISSION_TYPE_DC:
        try:
            project_details_data = get_project_data_raw()
            if "project" not in project_details_data:
                raise KeyError("Missing 'project' key in project technical details")
            if "number_of_converters" not in project_details_data["project"]:
                raise KeyError(
                    "Missing 'number_of_converters' key in project section of technical details"
                )
            number_of_converters = project_details_data["project"][
                "number_of_converters"
            ]
        except KeyError as e:
            raise KeyError(f"Missing required key in project technical details: {e}")
    else:
        number_of_converters = 0

    # Load build costs to get insurable asset values
    from run_context import get_run_context
    _ctx = get_run_context()
    if _ctx is not None and _ctx.build_costs is not None:
        costs = _ctx.build_costs
    else:
        total_miles = load_physical_details()
        contingencies = load_contingencies()
        costs = load_costs(
            category,
            total_miles,
            number_of_converters,
            contingencies,
            project_details.reconductoring,
        )

    # Load insurance parameters
    insurance_yaml = load_insurance_details()

    # Calculate operational insurance costs
    results = calculate_insurance_costs(
        insurance_yaml,
        costs.conductor_cost_with_contingencies,
        costs.structure_cost_with_contingencies,
        costs.converter_cost_with_contingencies,
        project_details.project_lifetime,
    )

    from run_context import add_derived
    add_derived({"insurable_value": results["insurable_value"]})

    # Load financing parameters for present value calculation
    financing = load_financing_details()


    # Calculate Present Value for operational insurance
    # Insurance payments start at COD (after construction) and continue for project lifetime
    insurance_start_year = calculate_cod_year(
        project_details.delay_years, project_details.construction_years
    )
    insurance_pv = calculate_present_value(
        results["annual_premium"],
        financing.wacc_real,
        project_details.project_lifetime,
        insurance_start_year,
    )


    # Display results
    print("=" * 80)
    print("OPERATIONAL INSURANCE COST CALCULATION RESULTS")
    print("=" * 80)
    print(f"Project Category: {category}")
    print(f"Construction Type: {project_details.construction_type}")
    print()

    print("INSURABLE ASSET VALUE:")
    ins_components = insurance_yaml["insurance"].get("insurable_components", {})
    if ins_components.get("conductors", True):
        print(f"  Conductor Costs: ${costs.conductor_cost_with_contingencies:,.2f}")
    if ins_components.get("structures", True):
        print(f"  Structure Costs: ${costs.structure_cost_with_contingencies:,.2f}")
    if ins_components.get("converters", True):
        print(f"  Converter Costs: ${costs.converter_cost_with_contingencies:,.2f}")
    print(f"  ---")
    print(f"  Total Insurable Value: ${results['insurable_value']:,.2f}")
    print()

    print("[NOMINAL VALUES]")
    print(f"  Premium Rate: {results['premium_rate']:.3%}")
    print(f"  Annual Premium: ${results['annual_premium']:,.2f}")
    print(f"  Project Lifetime: {project_details.project_lifetime} years")
    print(f"  ---")
    print(f"  TOTAL NOMINAL COST: ${results['nominal_lifetime_cost']:,.2f}")
    print()

    print("[UTILITY PERSPECTIVE - Present Value]")
    print(f"  Discount Rate: {financing.wacc_real:.2%} (real WACC)")
    print(f"  Base Year: {financing.base_year}")
    print(f"  Payment Start: Year {insurance_start_year:.1f} (at COD)")
    print(f"  ---")
    print(f"  TOTAL PRESENT VALUE: ${insurance_pv:,.2f}")
    print()
    print("NOTE: Operational insurance is not AFUDC-eligible (operating expense).")
    print("=" * 80)


    # ========================================================================
    # CSV OUTPUT - Write results to batch summary and detail CSV
    # ========================================================================

    # Initialize CSV output manager
    csv_manager = CTCCOutputManager()

    # Prepare operational insurance results dictionary for CSV
    csv_results = {
        "annual_premium": results["annual_premium"],
        "nominal_lifetime_cost": results["nominal_lifetime_cost"],
        "pv_total": insurance_pv,
        "insurable_value": results["insurable_value"],
        "premium_rate": results["premium_rate"],
    }
    csv_manager.add_insurance_costs(csv_results)


    csv_manager.write_batch_summary()


if __name__ == "__main__":
    main()
