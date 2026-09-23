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
from smart_output import FORGEOutputManager

# Local utility imports
from smart_loaders import (
    load_project_technical_details,
    load_physical_details,
    load_contingencies,
    load_financing_details,
    load_insurance_details,
    get_project_data_raw,
)
from financial_utils import calculate_present_value, calculate_cod_year, calculate_growing_annuity_pv, calculate_nominal_growing_series
from calculation_utils import normalize_construction_type_for_yaml
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
    construction_type: str,
) -> Dict[str, float]:
    """
    Calculate operational insurance costs based on insurable asset value.

    Overhead/underground lines use a self-insurance reserve rate; subsea cables
    and converter stations use commercial property insurance rates.

    Args:
        insurance_yaml: Loaded insurance YAML data
        conductor_cost_with_contingencies: Conductor cost with contingencies
        structure_cost_with_contingencies: Structure cost with contingencies
        converter_cost_with_contingencies: Converter cost with contingencies
        project_lifetime: Project lifetime in years
        construction_type: Construction type string (e.g. "Overhead", "Subsea")

    Returns:
        dict: Contains insurable_value, annual_premium, premium_rate, line_rate,
              converter_rate, escalation_rate, nominal_lifetime_cost
    """
    ins_cfg = insurance_yaml["insurance"]
    components = ins_cfg.get("insurable_components", {})

    # Look up rate by construction type (fall back to default)
    rate_by_type = ins_cfg.get("premium_rate_by_type", {})
    yaml_ct = normalize_construction_type_for_yaml(construction_type, context="environmental")
    line_rate = rate_by_type.get(yaml_ct, ins_cfg.get("premium_rate_default", 0.002))
    converter_rate = rate_by_type.get("converter", line_rate)

    # Compute insurable values by component
    line_insurable = 0.0
    if components.get("conductors", True):
        line_insurable += conductor_cost_with_contingencies
    if components.get("structures", True):
        line_insurable += structure_cost_with_contingencies

    converter_insurable = 0.0
    if components.get("converters", True):
        converter_insurable += converter_cost_with_contingencies

    insurable_value = line_insurable + converter_insurable
    annual_premium = (line_insurable * line_rate) + (converter_insurable * converter_rate)
    premium_rate = annual_premium / insurable_value if insurable_value > 0 else 0.0

    escalation_rate = ins_cfg.get("escalation_rate", 0.0)
    nominal_lifetime_cost = annual_premium * project_lifetime

    return {
        "insurable_value": insurable_value,
        "annual_premium": annual_premium,
        "premium_rate": premium_rate,
        "line_rate": line_rate,
        "converter_rate": converter_rate,
        "escalation_rate": escalation_rate,
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
            project_details.project_type,
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
        project_details.construction_type,
    )

    from run_context import add_derived
    add_derived({"insurable_value": results["insurable_value"]})

    # Load financing parameters for present value calculation
    financing = load_financing_details()


    # Calculate Present Value for operational insurance using growing annuity
    # Premiums start at COD and escalate at real escalation_rate
    escalation_rate = results["escalation_rate"]
    insurance_pv = calculate_growing_annuity_pv(
        annual_amount=results["annual_premium"],
        growth_rate=escalation_rate,
        discount_rate=financing.wacc_real,
        project_lifetime=project_details.project_lifetime,
        delay_years=project_details.delay_years,
        construction_years=project_details.construction_years,
    )
    nominal_lifetime_cost = calculate_nominal_growing_series(
        annual_amount=results["annual_premium"],
        growth_rate=escalation_rate,
        project_lifetime=project_details.project_lifetime,
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
    print(f"  Line Rate ({results['line_rate']:.3%}) / Converter Rate ({results['converter_rate']:.3%})")
    print(f"  Blended Premium Rate: {results['premium_rate']:.3%}")
    print(f"  Annual Premium (Year 1): ${results['annual_premium']:,.2f}")
    print(f"  Escalation Rate: {results['escalation_rate']:.1%} real/yr")
    print(f"  Project Lifetime: {project_details.project_lifetime} years")
    print(f"  ---")
    print(f"  TOTAL NOMINAL COST: ${nominal_lifetime_cost:,.2f}")
    print()

    print("[UTILITY PERSPECTIVE - Present Value]")
    print(f"  Discount Rate: {financing.wacc_real:.2%} (real WACC)")
    print(f"  Base Year: {financing.base_year}")
    print(f"  ---")
    print(f"  TOTAL PRESENT VALUE: ${insurance_pv:,.2f}")
    print()
    print("NOTE: Operational risk-bearing cost is not AFUDC-eligible (operating expense).")
    print("=" * 80)


    # ========================================================================
    # CSV OUTPUT - Write results to batch summary and detail CSV
    # ========================================================================

    # Initialize CSV output manager
    csv_manager = FORGEOutputManager()

    # Prepare operational insurance results dictionary for CSV
    csv_results = {
        "annual_premium": results["annual_premium"],
        "nominal_lifetime_cost": nominal_lifetime_cost,
        "pv_total": insurance_pv,
        "insurable_value": results["insurable_value"],
        "premium_rate": results["premium_rate"],
    }
    csv_manager.add_insurance_costs(csv_results)


    csv_manager.write_batch_summary()


if __name__ == "__main__":
    main()
