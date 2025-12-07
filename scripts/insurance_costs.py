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
from typing import Dict, Any, Optional

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
from path_config import YAMLS_DIR


def calculate_insurance_costs(
    insurance_yaml: Dict[str, Any],
    conductor_cost_with_contingencies: float,
    structure_cost_with_contingencies: float,
    converter_cost_with_contingencies: float,
    construction_type: str,
    project_lifetime: int,
) -> Dict[str, float]:
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


def calculate_wildfire_liability_premium(
    insurance_yaml: Dict[str, Any],
    project_lifetime: int,
) -> Optional[Dict[str, float]]:
    """
    Calculate wildfire liability insurance premium using rate-on-line (ROL).

    ROL is the annual premium as a fraction of the liability limit.
    Premium = ROL × Liability Limit (annual)

    Args:
        insurance_yaml: Loaded insurance YAML data
        project_lifetime: Project lifetime in years

    Returns:
        dict: Contains liability_limit, rate_on_line, annual_premium, nominal_lifetime_cost
              Returns None if disabled or not configured
    """
    insurance = insurance_yaml.get("insurance", {})
    wildfire_liability = insurance.get("wildfire_liability", {})

    # Check if enabled
    if not wildfire_liability.get("enabled", False):
        return None

    # Get parameters
    liability_limit = wildfire_liability.get("liability_limit", 0)
    rate_on_line = wildfire_liability.get("rate_on_line", 0)

    # Validate parameters
    if liability_limit <= 0 or rate_on_line <= 0:
        return None

    # Calculate annual premium
    annual_premium = rate_on_line * liability_limit

    # Calculate lifetime cost (annual premium × project lifetime)
    nominal_lifetime_cost = annual_premium * project_lifetime

    return {
        "liability_limit": liability_limit,
        "rate_on_line": rate_on_line,
        "annual_premium": annual_premium,
        "nominal_lifetime_cost": nominal_lifetime_cost,
    }


def main() -> None:
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
        converter_loss_percentage,
    ) = load_project_technical_details()

    # Construct category identifier
    category = (
        f"{construction_type}/{ac_dc}/{capacity_mw}MW/{conductor_type}/{converter_type}"
    )

    # Determine number of converters
    if ac_dc == "DC":
        try:
            with open(YAMLS_DIR / "01_project_technical_details.yaml", "r") as file:
                project_details_data = yaml.safe_load(file)
            if not project_details_data:
                raise ValueError(
                    "Project technical details YAML file is empty or invalid"
                )
            if "project" not in project_details_data:
                raise KeyError(
                    "Missing 'project' key in project technical details YAML file"
                )
            if "number_of_converters" not in project_details_data["project"]:
                raise KeyError(
                    "Missing 'number_of_converters' key in project section of technical details YAML"
                )
            number_of_converters = project_details_data["project"][
                "number_of_converters"
            ]
        except FileNotFoundError:
            raise FileNotFoundError(
                f"Project technical details YAML not found at {YAMLS_DIR / '01_project_technical_details.yaml'}"
            )
        except yaml.YAMLError as e:
            raise ValueError(f"Error parsing project technical details YAML: {e}")
        except KeyError as e:
            raise KeyError(
                f"Missing required key in project technical details YAML: {e}"
            )
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

    # Calculate operational insurance costs
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

    # Calculate wildfire liability insurance (skip if flag is set)
    wildfire_liability_results = None
    if "CTCC_NO_WF_LIABILITY" not in os.environ:
        wildfire_liability_results = calculate_wildfire_liability_premium(
            insurance_yaml,
            project_lifetime,
        )

    # Calculate Present Value for operational insurance
    # Insurance payments start at COD (after construction) and continue for project lifetime
    insurance_start_year = delay_year + construction_years + 1
    insurance_pv = calculate_present_value(
        results["annual_premium"],
        wacc_real,
        project_lifetime,
        insurance_start_year,
    )

    # Calculate Present Value for wildfire liability (if enabled)
    wildfire_liability_pv = 0
    if wildfire_liability_results:
        wildfire_liability_pv = calculate_present_value(
            wildfire_liability_results["annual_premium"],
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

    # Display wildfire liability if enabled
    if wildfire_liability_results:
        print()
        print("=" * 80)
        print("WILDFIRE LIABILITY INSURANCE COST CALCULATION RESULTS")
        print("=" * 80)
        print(f"Liability Limit: ${wildfire_liability_results['liability_limit']:,.2f}")
        print(f"Rate-on-Line (ROL): {wildfire_liability_results['rate_on_line']:.2%}")
        print()
        print("[NOMINAL VALUES]")
        print(f"  Annual Premium: ${wildfire_liability_results['annual_premium']:,.2f}")
        print(f"  Project Lifetime: {project_lifetime} years")
        print(f"  ---")
        print(
            f"  TOTAL NOMINAL COST: ${wildfire_liability_results['nominal_lifetime_cost']:,.2f}"
        )
        print()
        print("[SOCIETAL PERSPECTIVE - Present Value]")
        print(f"  Discount Rate: {wacc_real:.2%} (real WACC)")
        print(f"  Base Year: {base_year}")
        print(f"  Payment Start: Year {insurance_start_year} (at COD)")
        print(f"  ---")
        print(f"  TOTAL PRESENT VALUE: ${wildfire_liability_pv:,.2f}")
        print()
        print(
            "NOTE: Wildfire liability insurance is not AFUDC-eligible (operating expense)."
        )
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

    # Add wildfire liability if enabled
    if wildfire_liability_results:
        wildfire_csv_results = {
            "annual_premium": wildfire_liability_results["annual_premium"],
            "nominal_lifetime_cost": wildfire_liability_results[
                "nominal_lifetime_cost"
            ],
            "pv_total": wildfire_liability_pv,
            "liability_limit": wildfire_liability_results["liability_limit"],
            "rate_on_line": wildfire_liability_results["rate_on_line"],
        }
        csv_manager.add_wildfire_liability_costs(wildfire_csv_results)

    csv_manager.write_batch_summary()


if __name__ == "__main__":
    main()
