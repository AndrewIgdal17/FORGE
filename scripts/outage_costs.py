# Author: Andrew Igdal
# Date: 2025-10-29
# Description: This script calculates expected outage costs using simplified probabilistic
#              reliability approach with direct outage rates, multiplicative duration model,
#              and piecewise value of lost load (VoLL).

from __future__ import annotations

# Standard library imports
import yaml
import sys
import os
from typing import Dict, Any, Tuple, List

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from smart_output import CTCCOutputManager

# Local utility imports
from constants import MIN_DISCOUNT_RATE, GROWTH_RATE_TOLERANCE
from smart_loaders import (
    load_project_technical_details,
    load_physical_details,
    load_financing_details,
    load_outage_costs,
    get_physical_data_raw,
    get_financing_data_raw,
)
from financial_utils import get_discount_rate_from_config, calculate_growing_annuity_pv, validate_discount_rate, calculate_nominal_growing_series
from calculation_utils import normalize_construction_type_for_yaml




def calculate_voll_cost_piecewise(
    duration_hours: float, mw_lost: float, tiers: List[Dict[str, Any]]
) -> float:
    """
    Calculate total cost using piecewise VoLL.
    Hours 0-4 at tier 1, hours 4-24 at tier 2, hours 24+ at tier 3.

    Args:
        duration_hours: Duration of outage in hours
        mw_lost: MW capacity lost during outage
        tiers: List of tier dicts with max_hours and value_per_mwh

    Returns:
        float: Total cost ($) for the outage
    """
    total_cost = 0
    hours_remaining = duration_hours
    prev_threshold = 0

    for tier in tiers:
        max_hours = float("inf") if tier["max_hours"] == ".inf" else tier["max_hours"]
        value_per_mwh = tier["value_per_mwh"]

        hours_in_tier = min(hours_remaining, max_hours - prev_threshold)
        if hours_in_tier > 0:
            mwh_in_tier = hours_in_tier * mw_lost
            total_cost += mwh_in_tier * value_per_mwh
            hours_remaining -= hours_in_tier
            prev_threshold = max_hours
        if hours_remaining <= 0:
            break

    return total_cost


def calculate_outage_costs(
    outage_yaml: Dict[str, Any],
    construction_type: str,
    terrain_miles: Dict[str, float],
    capacity_mw: int,
    project_lifetime: int,
    discount_rate: float,
    delay_years: float = 0,
    construction_years: float = 0,
) -> Dict[str, Any]:
    """
    Calculate expected outage costs using simplified outage rate model.

    Args:
        outage_yaml: Loaded outage YAML data
        construction_type: Construction type (overhead, underground, subsea)
        terrain_miles: Dictionary of terrain type to miles
        capacity_mw: Project capacity in MW
        project_lifetime: Project lifetime in years
        discount_rate: Discount rate for PV calculation
        delay_years: Years of delay before construction starts
        construction_years: Years of construction

    Returns:
        dict: Contains EAC, outage_by_terrain, nominal_cost, pv_cost

    Raises:
        ValueError: If discount_rate <= MIN_DISCOUNT_RATE (would cause division by zero)
    """
    # Validate discount_rate to prevent division by zero
    validate_discount_rate(discount_rate)

    outage_config = outage_yaml["outage"]
    growth_rate = outage_config["risk_growth_rate"] or 0.0
    capacity_at_risk = outage_config["capacity_at_risk_factor"]
    voll_tiers = outage_config["value_of_lost_load"]["tiers"]
    duration_by_terrain = outage_config["outage_duration_by_terrain"]
    duration_multiplier = outage_config["outage_duration_multiplier"]
    outage_rates = outage_config["outage_rates"]

    # Map construction type to YAML keys
    yaml_construction_type = normalize_construction_type_for_yaml(construction_type)

    # Calculate outages and costs by terrain
    outage_by_terrain = {}
    lambda_total = 0.0
    EAC = 0.0

    for terrain, miles in terrain_miles.items():
        if miles > 0:
            # Step 1: Outages per year for this terrain
            outage_rate = outage_rates[yaml_construction_type].get(terrain, 0.0)
            lambda_segment = miles * outage_rate

            # Step 2: Effective duration (multiplicative model)
            H_base = duration_by_terrain.get(terrain, 0)
            duration_mult = duration_multiplier.get(yaml_construction_type, 1.0)
            H_eff = H_base * duration_mult

            # Step 3: MW lost per event
            mw_lost_per_event = capacity_at_risk * capacity_mw

            # Step 4: Unserved energy per event
            unserved_mwh_per_event = H_eff * mw_lost_per_event

            # Step 5: Cost per event (piecewise VoLL)
            cost_per_event = calculate_voll_cost_piecewise(
                H_eff, mw_lost_per_event, voll_tiers
            )

            # Step 6: Annual cost for this terrain
            annual_cost = lambda_segment * cost_per_event

            outage_by_terrain[terrain] = {
                "miles": miles,
                "outage_rate": outage_rate,
                "outages_per_year": lambda_segment,
                "duration_base": H_base,
                "duration_multiplier": duration_mult,
                "duration_effective": H_eff,
                "unserved_mwh_per_event": unserved_mwh_per_event,
                "cost_per_event": cost_per_event,
                "annual_cost": annual_cost,
            }

            lambda_total += lambda_segment
            EAC += annual_cost

    # Calculate nominal total cost (sum of growing annual costs)
    nominal_total = calculate_nominal_growing_series(
        annual_amount=EAC,
        growth_rate=growth_rate,
        project_lifetime=project_lifetime,
    )

    # Present value with growing annuity (with delay period discounting)
    pv_cost = calculate_growing_annuity_pv(
        annual_amount=EAC,
        growth_rate=growth_rate,
        discount_rate=discount_rate,
        project_lifetime=project_lifetime,
        delay_years=delay_years,
        construction_years=construction_years,
    )

    return {
        "lambda_total": lambda_total,
        "EAC": EAC,
        "outage_by_terrain": outage_by_terrain,
        "capacity_at_risk": capacity_at_risk,
        "growth_rate": growth_rate,
        "nominal_total": nominal_total,
        "pv_cost": pv_cost,
    }


def main() -> None:
    """Main function to calculate and display outage costs."""
    # Load project specifications
    project_details = load_project_technical_details()

    # Construct category identifier
    from calculation_utils import build_category_string
    category = build_category_string(project_details=project_details)

    # Load terrain details
    from smart_loaders import load_terrain_miles
    terrain_miles = load_terrain_miles()

    # Load outage parameters
    outage_yaml = load_outage_costs()

    # Load financing data for discount rate
    financing_yaml = get_financing_data_raw()

    # Get discount rate
    discount_rate, discount_source = get_discount_rate_from_config(
        outage_yaml, financing_yaml, rate_key="discount_rate_type"
    )

    # Calculate outage costs
    results = calculate_outage_costs(
        outage_yaml,
        project_details.construction_type,
        terrain_miles,
        project_details.capacity_mw,
        project_details.project_lifetime,
        discount_rate,
        delay_years=project_details.delay_years,
        construction_years=project_details.construction_years,
    )

    from run_context import add_derived
    _out_dur_mult = next(
        (d["duration_multiplier"] for d in results["outage_by_terrain"].values()),
        1.0,
    )
    add_derived({
        "lambda_total_outage": results["lambda_total"],
        "EAC_outage": results["EAC"],
        "mw_lost_per_event": results["capacity_at_risk"] * project_details.capacity_mw,
        "construction_type_multiplier_outage_duration": _out_dur_mult,
    })

    # Display results
    print("=" * 80)
    print("EXPECTED OUTAGE COST CALCULATION RESULTS")
    print("=" * 80)
    print(f"Project Category: {category}")
    print(f"Construction Type: {project_details.construction_type}")
    print(f"Project Capacity: {project_details.capacity_mw} MW")
    print(
        f"Capacity at Risk: {results['capacity_at_risk']*100:.1f}% (phi = {results['capacity_at_risk']:.2f})"
    )
    print()

    print("[OUTAGE RELIABILITY ASSESSMENT]")
    print()
    print("OUTAGE EXPOSURE BY TERRAIN:")
    for terrain, data in results["outage_by_terrain"].items():
        print(f"  {terrain.replace('_', ' ').title():20} ({data['miles']:5.1f} mi):")
        print(f"    Outage Rate: {data['outage_rate']:.4f} outages/mi/yr")
        print(f"    Outages/Year: {data['outages_per_year']:.4f}")
        print(
            f"    Duration: {data['duration_base']:.1f}h (base) x {data['duration_multiplier']:.1f} = {data['duration_effective']:.1f}h"
        )
        print(f"    Unserved Energy/Event: {data['unserved_mwh_per_event']:,.0f} MWh")
        print(f"    Cost/Event (piecewise VoLL): ${data['cost_per_event']:,.0f}")
        print(f"    Annual Cost: ${data['annual_cost']:,.2f}/yr")
        print()
    print(f"  {'-' * 76}")
    print(f"  Total Outages/Year: {results['lambda_total']:.4f} events/year")
    print()

    print("EXPECTED ANNUAL COST:")
    print(f"  EAC: ${results['EAC']:,.2f}/year")
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
    print("NOTE: Outage costs are probabilistic future losses, not capital costs.")
    print("      No AFUDC applies to expected loss calculations.")
    print("=" * 80)

    # ========================================================================
    # CSV OUTPUT - Write results to batch summary and detail CSV
    # ========================================================================

    # Initialize CSV output manager
    csv_manager = CTCCOutputManager()

    # Write to CSV (results dict already has all needed values)
    csv_manager.add_outage_costs(results)
    csv_manager.write_batch_summary()


if __name__ == "__main__":
    main()
