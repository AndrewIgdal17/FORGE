# Date: 2025-10-29
# Description: This script calculates expected wildfire costs using probabilistic risk approach.
#              Based on line-level ignition rate, construction type multiplier, event severity,
#              and present value of growing annuity over project lifetime.

from __future__ import annotations

# Standard library imports
import yaml
from typing import Dict, Any, Tuple

from scripts.utils.smart_output import SmartOutputManager

# Local utility imports
from scripts.utils.constants import MIN_DISCOUNT_RATE, GROWTH_RATE_TOLERANCE
from scripts.utils.smart_loaders import (
    load_project_technical_details,
    load_wildfire_costs,
    get_financing_data_raw,
)
from scripts.utils.financial_utils import calculate_growing_annuity_pv, validate_discount_rate, calculate_nominal_growing_series
from scripts.utils.calculation_utils import normalize_construction_type_for_yaml

def calculate_wildfire_costs(
    wildfire_yaml: Dict[str, Any],
    construction_type: str,
    terrain_miles: Dict[str, float],
    project_lifetime: int,
    social_discount_rate: float,
    delay_years: float = 0,
    construction_years: float = 0,
) -> Dict[str, Any]:
    """
    Calculate expected wildfire costs using line-level ignition rate.

    Args:
        wildfire_yaml: Loaded wildfire YAML data
        construction_type: Construction type (overhead, underground, etc.)
        terrain_miles: Dictionary of terrain type to miles (summed for total length)
        project_lifetime: Project lifetime in years
        social_discount_rate: Social discount rate for PV calculation (r_social)
        delay_years: Years of delay before construction starts
        construction_years: Years of construction

    Returns:
        dict: Contains lambda_total, EAL, nominal_cost, pv_cost

    Raises:
        ValueError: If social_discount_rate <= MIN_DISCOUNT_RATE (would cause division by zero)
    """
    validate_discount_rate(social_discount_rate)

    wildfire_config = wildfire_yaml["wildfire"]
    severity = wildfire_config["severity_per_event"]
    growth_rate = wildfire_config["risk_growth_rate"] or 0.0
    base_ignition_rate = wildfire_config["base_ignition_rate"]
    ignition_rate_multiplier = wildfire_config["ignition_rate_multiplier"]

    yaml_construction_type = normalize_construction_type_for_yaml(construction_type)
    construction_multiplier = ignition_rate_multiplier[yaml_construction_type]

    total_miles = sum(terrain_miles.values())

    # Effective rate and total annual events
    effective_rate = base_ignition_rate * construction_multiplier
    lambda_total = total_miles * effective_rate

    # Expected Annual Loss
    EAL = lambda_total * severity

    nominal_total = calculate_nominal_growing_series(
        annual_amount=EAL,
        growth_rate=growth_rate,
        project_lifetime=project_lifetime,
    )

    pv_cost = calculate_growing_annuity_pv(
        annual_amount=EAL,
        growth_rate=growth_rate,
        discount_rate=social_discount_rate,
        project_lifetime=project_lifetime,
        delay_years=delay_years,
        construction_years=construction_years,
    )

    return {
        "lambda_total": lambda_total,
        "EAL": EAL,
        "severity": severity,
        "growth_rate": growth_rate,
        "nominal_total": nominal_total,
        "pv_cost": pv_cost,
        "total_miles": total_miles,
        "base_ignition_rate": base_ignition_rate,
        "construction_multiplier": construction_multiplier,
    }

def main() -> None:
    """Main function to calculate and display wildfire costs."""
    project_details = load_project_technical_details()

    from scripts.utils.run_context import get_run_context
    ctx = get_run_context()
    if ctx is None:
        raise RuntimeError(
            f"{__name__} requires a RunContext. Run via forge.py or set up "
            "RunContext in your test fixture."
        )
    category = ctx.category_string

    from scripts.utils.smart_loaders import load_terrain_miles
    terrain_miles = load_terrain_miles()

    wildfire_yaml = load_wildfire_costs()
    financing_yaml = get_financing_data_raw()

    # Social discount rate only — risk externalities use r_social (appendix hard-codes this)
    social_discount_rate = financing_yaml["financial"]["social_discount_rate"]
    discount_source = "social discount rate"

    results = calculate_wildfire_costs(
        wildfire_yaml,
        project_details.construction_type,
        terrain_miles,
        project_details.project_lifetime,
        social_discount_rate,
        delay_years=project_details.delay_years,
        construction_years=project_details.construction_years,
    )

    from scripts.utils.run_context import add_derived
    add_derived({
        "lambda_total_wildfire": results["lambda_total"],
        "EAL_wildfire": results["EAL"],
        "construction_type_multiplier_wildfire": results["construction_multiplier"],
    })

    print("=" * 80)
    print("EXPECTED WILDFIRE COST CALCULATION RESULTS")
    print("=" * 80)
    print(f"Project Category: {category}")
    print(f"Construction Type: {project_details.construction_type}")
    print()

    print("[WILDFIRE RISK ASSESSMENT]")
    print()
    print("IGNITION EXPOSURE (LINE-LEVEL):")
    print(f"  Total Line Length: {results['total_miles']:.1f} miles")
    print(f"  Base Ignition Rate: {results['base_ignition_rate']:.6f} events/mi/yr (overhead baseline)")
    print(f"  Construction Multiplier: {results['construction_multiplier']:.2f}x")
    print(f"  Effective Rate: {results['base_ignition_rate'] * results['construction_multiplier']:.6f} events/mi/yr")
    print(f"  Total Annual Events: {results['lambda_total']:.6f} events/year")
    print()

    print("EVENT SEVERITY:")
    print(f"  Mean Loss per Event: ${results['severity']:,.0f}")
    print()

    print("EXPECTED ANNUAL LOSS:")
    print(f"  EAL = lambda * S: ${results['EAL']:,.2f}/year")
    print()

    print("[NOMINAL VALUES]")
    print(f"  Project Lifetime: {project_details.project_lifetime} years")
    print(f"  Risk Growth Rate: {results['growth_rate']:.1%}/year")
    print(f"  ---")
    print(f"  TOTAL NOMINAL COST: ${results['nominal_total']:,.2f}")
    print(f"    (Sum of growing annual costs, undiscounted)")
    print()

    print("[SOCIETAL PERSPECTIVE - Present Value]")
    print(f"  Discount Rate: {social_discount_rate:.2%} ({discount_source})")
    print(f"  Growing Annuity Formula: Applied")
    if results["growth_rate"] > social_discount_rate:
        print(
            f"  ⚠️  WARNING: Risk growth rate ({results['growth_rate']:.2%}) > discount rate ({social_discount_rate:.2%})"
        )
        print(f"      PV grows over time - risk is escalating faster than discounting!")
    print(f"  ---")
    print(f"  TOTAL PRESENT VALUE: ${results['pv_cost']:,.2f}")
    print()
    print("NOTE: Wildfire costs are probabilistic future losses, not capital costs.")
    print("      No AFUDC applies to expected loss calculations.")
    print("=" * 80)

    csv_manager = SmartOutputManager()
    csv_manager.add_wildfire_costs(results)
    csv_manager.write_batch_summary()

if __name__ == "__main__":
    main()
