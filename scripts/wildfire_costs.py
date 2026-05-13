# Author: Andrew Igdal
# Date: 2025-10-29
# Description: This script calculates expected wildfire costs using probabilistic risk approach.
#              Based on ignition rates by terrain/construction type, event severity, and
#              present value of growing annuity over project lifetime.

from __future__ import annotations

# Standard library imports
import yaml
import sys
import os
from typing import Dict, Any, Tuple

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from smart_output import CTCCOutputManager

# Local utility imports
from constants import MIN_DISCOUNT_RATE, GROWTH_RATE_TOLERANCE
from smart_loaders import (
    load_project_technical_details,
    load_physical_details,
    load_financing_details,
    load_wildfire_costs,
    get_physical_data_raw,
    get_financing_data_raw,
)
from financial_utils import get_discount_rate_from_config, calculate_growing_annuity_pv, validate_discount_rate, calculate_nominal_growing_series
from calculation_utils import normalize_construction_type_for_yaml




def calculate_wildfire_costs(
    wildfire_yaml: Dict[str, Any],
    construction_type: str,
    terrain_miles: Dict[str, float],
    project_lifetime: int,
    discount_rate: float,
    delay_years: float = 0,
    construction_years: float = 0,
) -> Dict[str, Any]:
    """
    Calculate expected wildfire costs using segment-based ignition rates.

    Args:
        wildfire_yaml: Loaded wildfire YAML data
        construction_type: Construction type (overhead, underground, etc.)
        terrain_miles: Dictionary of terrain type to miles
        project_lifetime: Project lifetime in years
        discount_rate: Discount rate for PV calculation
        delay_years: Years of delay before construction starts
        construction_years: Years of construction

    Returns:
        dict: Contains lambda_total, EAL, lambda_by_terrain, nominal_cost, pv_cost

    Raises:
        ValueError: If discount_rate <= MIN_DISCOUNT_RATE (would cause division by zero)
    """
    # Validate discount_rate to prevent division by zero
    validate_discount_rate(discount_rate)

    wildfire_config = wildfire_yaml["wildfire"]
    severity = wildfire_config["severity_per_event"]
    growth_rate = wildfire_config["risk_growth_rate"]
    ignition_rates_by_terrain = wildfire_config["ignition_rates_by_terrain"]
    ignition_rate_multiplier = wildfire_config["ignition_rate_multiplier"]

    # Map construction type to YAML keys
    yaml_construction_type = normalize_construction_type_for_yaml(construction_type)

    # Get construction type multiplier
    construction_multiplier = ignition_rate_multiplier.get(yaml_construction_type, 1.0)

    # Step 1 & 2: Calculate segment-specific and total event rates
    # Using multiplicative model: effective_rate = base_rate x construction_multiplier
    lambda_by_terrain = {}
    lambda_total = 0.0

    for terrain, miles in terrain_miles.items():
        if miles > 0:
            base_rate = ignition_rates_by_terrain.get(terrain, 0.0)
            f_i_t = base_rate * construction_multiplier  # Effective ignition rate
            lambda_segment = miles * f_i_t  # events/year for this terrain
            lambda_by_terrain[terrain] = {
                "miles": miles,
                "base_rate": base_rate,
                "construction_multiplier": construction_multiplier,
                "rate_per_mile": f_i_t,
                "events_per_year": lambda_segment,
            }
            lambda_total += lambda_segment

    # Step 3: Calculate Expected Annual Loss (EAL)
    EAL = lambda_total * severity

    # Calculate nominal total cost (sum of growing annual costs)
    nominal_total = calculate_nominal_growing_series(
        annual_amount=EAL,
        growth_rate=growth_rate,
        project_lifetime=project_lifetime,
    )

    # Step 4: Present value with growing annuity (with delay period discounting)
    pv_cost = calculate_growing_annuity_pv(
        annual_amount=EAL,
        growth_rate=growth_rate,
        discount_rate=discount_rate,
        project_lifetime=project_lifetime,
        delay_years=delay_years,
        construction_years=construction_years,
    )

    return {
        "lambda_total": lambda_total,
        "EAL": EAL,
        "lambda_by_terrain": lambda_by_terrain,
        "severity": severity,
        "growth_rate": growth_rate,
        "nominal_total": nominal_total,
        "pv_cost": pv_cost,
    }


def main() -> None:
    """Main function to calculate and display wildfire costs."""
    # Load project specifications
    project_details = load_project_technical_details()

    # Construct category identifier
    from calculation_utils import build_category_string
    category = build_category_string(project_details=project_details)

    # Load terrain details
    from smart_loaders import load_terrain_miles
    terrain_miles = load_terrain_miles()

    # Load wildfire parameters
    wildfire_yaml = load_wildfire_costs()

    # Load financing data for discount rate
    financing_yaml = get_financing_data_raw()

    # Get discount rate
    discount_rate, discount_source = get_discount_rate_from_config(
        wildfire_yaml, financing_yaml, rate_key="discount_rate_source"
    )

    # Calculate wildfire costs
    results = calculate_wildfire_costs(
        wildfire_yaml,
        project_details.construction_type,
        terrain_miles,
        project_details.project_lifetime,
        discount_rate,
        delay_years=project_details.delay_years,
        construction_years=project_details.construction_years,
    )

    from run_context import add_derived
    _wf_mult = next(
        (d["construction_multiplier"] for d in results["lambda_by_terrain"].values()),
        1.0,
    )
    add_derived({
        "lambda_total_wildfire": results["lambda_total"],
        "EAL_wildfire": results["EAL"],
        "construction_type_multiplier_wildfire": _wf_mult,
    })

    # Display results
    print("=" * 80)
    print("EXPECTED WILDFIRE COST CALCULATION RESULTS")
    print("=" * 80)
    print(f"Project Category: {category}")
    print(f"Construction Type: {project_details.construction_type}")
    print()

    print("[WILDFIRE RISK ASSESSMENT]")
    print()
    print("IGNITION EXPOSURE BY TERRAIN:")
    for terrain, data in results["lambda_by_terrain"].items():
        print(f"  {terrain.replace('_', ' ').title():20} ({data['miles']:5.1f} mi):")
        print(
            f"    Base Rate: {data['base_rate']:.6f} events/mi/yr (overhead baseline)"
        )
        print(f"    Construction Multiplier: {data['construction_multiplier']:.2f}x")
        print(
            f"    Effective Rate: {data['rate_per_mile']:.6f} events/mi/yr ({data['base_rate']:.6f} x {data['construction_multiplier']:.2f})"
        )
        print(f"    Events/Year: {data['events_per_year']:.6f}")
        print()
    print(f"  {'-' * 76}")
    print(f"  {'Total Annual Events:':20} {results['lambda_total']:.6f} events/year")
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
    print(f"  Discount Rate: {discount_rate:.2%} ({discount_source})")
    print(f"  Growing Annuity Formula: Applied")
    if results["growth_rate"] > discount_rate:
        print(
            f"  ⚠️  WARNING: Risk growth rate ({results['growth_rate']:.2%}) > discount rate ({discount_rate:.2%})"
        )
        print(f"      PV grows over time - risk is escalating faster than discounting!")
    print(f"  ---")
    print(f"  TOTAL PRESENT VALUE: ${results['pv_cost']:,.2f}")
    print()
    print("NOTE: Wildfire costs are probabilistic future losses, not capital costs.")
    print("      No AFUDC applies to expected loss calculations.")
    print("=" * 80)

    # ========================================================================
    # CSV OUTPUT - Write results to batch summary and detail CSV
    # ========================================================================

    # Initialize CSV output manager
    csv_manager = CTCCOutputManager()

    # Write to CSV (results dict already has all needed values)
    csv_manager.add_wildfire_costs(results)
    csv_manager.write_batch_summary()


if __name__ == "__main__":
    main()
