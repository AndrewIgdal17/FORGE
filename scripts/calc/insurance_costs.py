# Date: 2025-10-28
# Description: This script calculates operational insurance costs for transmission line assets.
#              Insurance premiums are based on insurable asset value (conductors, structures, converters)
#              and paid annually over the project lifetime.

from __future__ import annotations

# Standard library imports
import yaml
from typing import Dict, Any

from scripts.utils.smart_output import SmartOutputManager

# Local utility imports
from scripts.utils.smart_loaders import (
    load_project_technical_details,
    load_contingencies,
    load_financing_details,
    load_insurance_details,
    get_project_data_raw,
)
from scripts.utils.financial_utils import calculate_present_value, calculate_cod_year, calculate_growing_annuity_pv, calculate_nominal_growing_series
from scripts.utils.calculation_utils import normalize_construction_type_for_yaml
from scripts.calc.build_costs import load_costs
from scripts.utils.weighted_miles import calculate_weighted_miles
from scripts.utils.path_config import YAMLS_DIR
from scripts.utils.run_context import get_run_context

def calculate_insurance_costs(
    insurance_yaml: Dict[str, Any],
    conductor_cost_with_contingencies: float,
    structure_cost_with_contingencies: float,
    converter_cost_with_contingencies: float,
    project_lifetime: int,
    construction_type: str,
    wacc_real: float,
    delay_years: float,
    construction_years: float,
) -> Dict[str, float]:
    """
    Calculate operational insurance costs based on insurable asset value.

    Overhead/underground lines use a self-insurance reserve rate; subsea cables
    and converter stations use commercial property insurance rates.

    Premiums escalate at g_ins over the project lifetime (appendix §5).
    Nominal lifetime cost is the growing series; PV is the growing annuity
    discounted at real WACC from COD.

    Args:
        insurance_yaml: Loaded insurance YAML data
        conductor_cost_with_contingencies: Conductor cost with contingencies
        structure_cost_with_contingencies: Structure cost with contingencies
        converter_cost_with_contingencies: Converter cost with contingencies
        project_lifetime: Project lifetime in years
        construction_type: Construction type string (e.g. "Overhead", "Subsea")
        wacc_real: Real WACC used to discount the growing annuity
        delay_years: Years of delay before construction starts
        construction_years: Years of construction (premiums start at COD)

    Returns:
        dict: Contains insurable_value, annual_premium, premium_rate, line_rate,
              converter_rate, escalation_rate, nominal_lifetime_cost, insurance_pv
    """
    ins_cfg = insurance_yaml["insurance"]
    components = ins_cfg.get("insurable_components", {})

    # Look up rate by construction type (fall back to default)
    rate_by_type = ins_cfg.get("premium_rate_by_type", {})
    yaml_ct = normalize_construction_type_for_yaml(construction_type, context="environmental")
    line_rate = rate_by_type.get(yaml_ct, ins_cfg.get("premium_rate_default", 0.002))
    converter_rate = rate_by_type.get("converter", line_rate)

    # Explicit binary selectors (appendix §5 ξ_conductor, ξ_structure, ξ_converter)
    xi_conductor = 1.0 if components.get("conductors", True) else 0.0
    xi_structure = 1.0 if components.get("structures", True) else 0.0
    xi_converter = 1.0 if components.get("converters", True) else 0.0
    line_insurable = (
        xi_conductor * conductor_cost_with_contingencies
        + xi_structure * structure_cost_with_contingencies
    )
    converter_insurable = xi_converter * converter_cost_with_contingencies

    insurable_value = line_insurable + converter_insurable
    annual_premium = (line_insurable * line_rate) + (converter_insurable * converter_rate)
    premium_rate = annual_premium / insurable_value if insurable_value > 0 else 0.0

    escalation_rate = ins_cfg.get("escalation_rate", 0.02)
    nominal_lifetime_cost = calculate_nominal_growing_series(
        annual_amount=annual_premium,
        growth_rate=escalation_rate,
        project_lifetime=project_lifetime,
    )
    insurance_pv = calculate_growing_annuity_pv(
        annual_amount=annual_premium,
        growth_rate=escalation_rate,
        discount_rate=wacc_real,
        project_lifetime=project_lifetime,
        delay_years=delay_years,
        construction_years=construction_years,
    )

    return {
        "insurable_value": insurable_value,
        "annual_premium": annual_premium,
        "premium_rate": premium_rate,
        "line_rate": line_rate,
        "converter_rate": converter_rate,
        "escalation_rate": escalation_rate,
        "nominal_lifetime_cost": nominal_lifetime_cost,
        "insurance_pv": insurance_pv,
    }

def main() -> None:
    """Main function to calculate and display insurance costs."""
    # Load project specifications
    project_details = load_project_technical_details()

    # Construct category identifier
    from scripts.utils.calculation_utils import build_category_string

    category = build_category_string(project_details=project_details)

    ctx = get_run_context()
    if ctx is not None:
        number_of_converters = ctx.number_of_converters
    else:
        # Standalone fallback: read from YAML directly
        project_data = get_project_data_raw()
        project = project_data.get("project", {})
        if project_details.ac_dc == "DC":
            if "number_of_converters" not in project:
                raise KeyError("Missing 'number_of_converters' for DC project")
            number_of_converters = int(project["number_of_converters"])
        else:
            number_of_converters = 0

    # Load build costs to get insurable asset values
    _ctx = get_run_context()
    if _ctx is not None and _ctx.build_costs is not None:
        costs = _ctx.build_costs
    else:
        contingencies = load_contingencies()
        costs = load_costs(
            category,
            number_of_converters,
            contingencies,
            project_details.project_type,
        )

    # Load insurance parameters
    insurance_yaml = load_insurance_details()

    # Load financing parameters for present value calculation
    financing = load_financing_details()

    # Calculate operational insurance costs (growing series + growing annuity)
    results = calculate_insurance_costs(
        insurance_yaml,
        costs.conductor_cost_with_contingencies,
        costs.structure_cost_with_contingencies,
        costs.converter_cost_with_contingencies,
        project_details.project_lifetime,
        project_details.construction_type,
        financing.wacc_real,
        project_details.delay_years,
        project_details.construction_years,
    )

    from scripts.utils.run_context import add_derived
    add_derived({"insurable_value": results["insurable_value"]})

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
    print(f"  TOTAL NOMINAL COST: ${results['nominal_lifetime_cost']:,.2f}")
    print()

    print("[UTILITY PERSPECTIVE - Present Value]")
    print(f"  Discount Rate: {financing.wacc_real:.2%} (real WACC)")
    print(f"  Base Year: {financing.base_year}")
    print(f"  ---")
    print(f"  TOTAL PRESENT VALUE: ${results['insurance_pv']:,.2f}")
    print()
    print("NOTE: Operational risk-bearing cost is not AFUDC-eligible (operating expense).")
    print("=" * 80)

    # ========================================================================
    # CSV OUTPUT - Write results to batch summary and detail CSV
    # ========================================================================

    # Initialize CSV output manager
    csv_manager = SmartOutputManager()

    # Prepare operational insurance results dictionary for CSV
    csv_results = {
        "annual_premium": results["annual_premium"],
        "nominal_lifetime_cost": results["nominal_lifetime_cost"],
        "pv_total": results["insurance_pv"],
        "insurable_value": results["insurable_value"],
        "premium_rate": results["premium_rate"],
    }
    csv_manager.add_insurance_costs(csv_results)

    csv_manager.write_batch_summary()

if __name__ == "__main__":
    main()
