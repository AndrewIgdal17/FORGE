# Author: Andrew Igdal
# Date: 2025-10-28
# Description: This script calculates operational insurance costs for transmission line assets.
#              Insurance premiums are based on insurable asset value (conductors, structures, converters)
#              and paid annually over the project lifetime.

# Standard library imports
import yaml
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from csv_output_manager import CTCCOutputManager

# Local utility imports
from yaml_loaders import (
    load_project_technical_details,
    load_physical_details,
    load_contingencies,
    load_financing_details,
    load_insurance_details,
)
from financial_utils import calculate_present_value
from build_costs import load_costs
from weighted_miles import calculate_weighted_miles


def calculate_insurance_costs(
    insurance_yaml,
    conductor_cost_with_contingencies,
    structure_cost_with_contingencies,
    converter_cost_with_contingencies,
    construction_type,
    project_lifetime,
):
    """
    Calculate operational insurance costs based on insurable asset value.

    Args:
        insurance_yaml: Loaded insurance YAML data
        conductor_cost_with_contingencies: Conductor cost with contingencies
        structure_cost_with_contingencies: Structure cost with contingencies
        converter_cost_with_contingencies: Converter cost with contingencies
        construction_type: Type of construction (overhead, underground, subsea)
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

    # Determine premium rate (construction type specific or default)
    premium_by_type = ins_cfg.get("premium_by_construction_type", {})
    premium_rate = premium_by_type.get(
        construction_type.lower(), ins_cfg.get("premium_rate", 0.002)
    )

    # Calculate annual premium and lifetime cost
    annual_premium = insurable_value * premium_rate
    nominal_lifetime_cost = annual_premium * project_lifetime

    return {
        "insurable_value": insurable_value,
        "annual_premium": annual_premium,
        "premium_rate": premium_rate,
        "nominal_lifetime_cost": nominal_lifetime_cost,
    }


def main():
    """Main function to calculate and display insurance costs."""
    # Load project specifications
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
        with open("../yamls/01_project_technical_details.yaml", "r") as file:
            pd = yaml.load(file, Loader=yaml.FullLoader)
        number_of_converters = pd["project"]["number_of_converters"]
    else:
        number_of_converters = 0

    # Load build costs to get insurable asset values
    total_miles = load_physical_details()
    contingencies = load_contingencies()

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

    # Load insurance parameters
    insurance_yaml = load_insurance_details()

    # Calculate insurance costs
    results = calculate_insurance_costs(
        insurance_yaml,
        conductor_cost_with_contingencies,
        structure_cost_with_contingencies,
        converter_cost_with_contingencies,
        construction_type,
        project_lifetime,
    )

    # Load financing parameters for present value calculation
    inflation_rate, base_year, wacc_nominal, wacc_real = load_financing_details()

    # Calculate Present Value
    # Insurance payments start at COD (after construction) and continue for project lifetime
    insurance_start_year = delay_year + construction_years
    insurance_pv = calculate_present_value(
        results["annual_premium"],
        wacc_real,
        project_lifetime,
        insurance_start_year,
    )

    # Display results
    print("=" * 80)
    print("OPERATIONAL INSURANCE COST CALCULATION RESULTS")
    print("=" * 80)
    print(f"Project Category: {category}")
    print(f"Construction Type: {construction_type}")
    print()

    print("INSURABLE ASSET VALUE:")
    ins_components = insurance_yaml["insurance"].get("insurable_components", {})
    if ins_components.get("conductors", True):
        print(f"  Conductor Costs: ${conductor_cost_with_contingencies:,.2f}")
    if ins_components.get("structures", True):
        print(f"  Structure Costs: ${structure_cost_with_contingencies:,.2f}")
    if ins_components.get("converters", True):
        print(f"  Converter Costs: ${converter_cost_with_contingencies:,.2f}")
    print(f"  ---")
    print(f"  Total Insurable Value: ${results['insurable_value']:,.2f}")
    print()

    print("[NOMINAL VALUES]")
    print(f"  Premium Rate: {results['premium_rate']:.3%}")
    print(f"  Annual Premium: ${results['annual_premium']:,.2f}")
    print(f"  Project Lifetime: {project_lifetime} years")
    print(f"  ---")
    print(f"  TOTAL NOMINAL COST: ${results['nominal_lifetime_cost']:,.2f}")
    print()

    print("[SOCIETAL PERSPECTIVE - Present Value]")
    print(f"  Discount Rate: {wacc_real:.2%} (real WACC)")
    print(f"  Base Year: {base_year}")
    print(f"  Payment Start: Year {insurance_start_year} (at COD)")
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
    
    # Prepare results dictionary for CSV
    csv_results = {
        "annual_premium": results["annual_premium"],
        "nominal_lifetime_cost": results["nominal_lifetime_cost"],
        "pv_total": insurance_pv,
        "insurable_value": results["insurable_value"],
        "premium_rate": results["premium_rate"],
    }
    
    # Write to CSV
    csv_manager.add_insurance_costs(csv_results)
    csv_manager.write_batch_summary()


if __name__ == "__main__":
    main()
