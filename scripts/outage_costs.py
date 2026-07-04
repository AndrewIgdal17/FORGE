# Author: Andrew Igdal
# Date: 2025-10-29
# Description: This script calculates expected outage costs using simplified probabilistic
#              reliability approach with line-level outage rates, multiplicative duration model,
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
    Iterates over an arbitrary number of duration tiers, each with a max_hours
    threshold and a value_per_mwh rate.

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
        max_hours = float("inf") if tier["max_hours"] in (".inf", None) else tier["max_hours"]
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
    number_of_circuits_poles: int = 1,
    line_utilization: float = 1.0,
    ac_dc: str = "AC",
) -> Dict[str, Any]:
    """
    Calculate expected outage costs using line-level outage rate model.

    Args:
        outage_yaml: Loaded outage YAML data
        construction_type: Construction type (overhead, underground, subsea)
        terrain_miles: Dictionary of terrain type to miles (summed for total length)
        capacity_mw: Project capacity in MW
        project_lifetime: Project lifetime in years
        discount_rate: Discount rate for PV calculation
        delay_years: Years of delay before construction starts
        construction_years: Years of construction
        number_of_circuits_poles: Number of circuits (AC) or poles (DC); used to
            auto-derive phi = 1/N_poles when capacity_at_risk_factor is "auto"
        line_utilization: Average fraction of line capacity in use (0-1)
        ac_dc: "AC" or "DC"; used to auto-derive rho when load_shed_fraction is "auto"

    Returns:
        dict: Contains EAC, nominal_cost, pv_cost

    Raises:
        ValueError: If discount_rate <= MIN_DISCOUNT_RATE (would cause division by zero)
    """
    validate_discount_rate(discount_rate)

    outage_config = outage_yaml["outage"]
    growth_rate = outage_config["risk_growth_rate"] or 0.0
    phi_config = outage_config.get("capacity_at_risk_factor", "auto")
    if phi_config in ("auto", None):
        capacity_at_risk = 1.0 / number_of_circuits_poles
    else:
        capacity_at_risk = float(phi_config)
    rho_config = outage_config.get("load_shed_fraction", "auto")
    if rho_config in ("auto", None):
        rho = 0.05 if ac_dc == "AC" else 0.80
    else:
        rho = float(rho_config)
    redispatch_cost = outage_config.get("redispatch_cost_per_mwh", 20)

    voll_tiers = outage_config["value_of_lost_load"]["tiers"]
    outage_duration = outage_config.get("outage_duration", 6)
    duration_multiplier_dict = outage_config["outage_duration_multiplier"]
    outage_rate_config = outage_config.get(
        "outage_rate",
        {"overhead": 0.015, "underground": 0.004, "subsea": 0.0007},
    )

    yaml_construction_type = normalize_construction_type_for_yaml(construction_type)

    total_miles = sum(terrain_miles.values())

    # Outage rate: overhead uses decomposition model, others use flat per-mile
    rate_entry = outage_rate_config.get(yaml_construction_type, 0.015)
    if isinstance(rate_entry, dict):
        lambda_terminal = rate_entry.get("lambda_terminal", 0.3)
        lambda_per_mile = rate_entry.get("lambda_per_mile", 0.012)
        lambda_total = lambda_terminal + lambda_per_mile * total_miles
        outage_rate = lambda_total / total_miles if total_miles > 0 else lambda_per_mile
    else:
        outage_rate = float(rate_entry)
        lambda_total = total_miles * outage_rate
        lambda_terminal = 0.0
        lambda_per_mile = outage_rate

    # Effective duration (multiplicative model)
    dur_mult = duration_multiplier_dict.get(yaml_construction_type, 1.0)
    duration_effective = outage_duration * dur_mult

    # MW lost per event
    mw_lost_per_event = capacity_at_risk * capacity_mw * line_utilization

    # Unserved energy per event
    unserved_mwh_per_event = duration_effective * mw_lost_per_event

    # Two-tier cost per event: load-shed (VoLL) + redispatch (flat rate)
    mw_shed = rho * mw_lost_per_event
    mw_redisp = (1 - rho) * mw_lost_per_event
    cost_loadshed = calculate_voll_cost_piecewise(
        duration_effective, mw_shed, voll_tiers
    )
    cost_redispatch = mw_redisp * duration_effective * redispatch_cost
    cost_per_event = cost_loadshed + cost_redispatch

    # Expected Annual Cost
    EAC = lambda_total * cost_per_event

    nominal_total = calculate_nominal_growing_series(
        annual_amount=EAC,
        growth_rate=growth_rate,
        project_lifetime=project_lifetime,
    )

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
        "capacity_at_risk": capacity_at_risk,
        "growth_rate": growth_rate,
        "nominal_total": nominal_total,
        "pv_cost": pv_cost,
        "total_miles": total_miles,
        "outage_rate": outage_rate,
        "lambda_terminal": lambda_terminal,
        "lambda_per_mile": lambda_per_mile,
        "outage_duration": outage_duration,
        "duration_multiplier": dur_mult,
        "duration_effective": duration_effective,
        "cost_per_event": cost_per_event,
        "cost_loadshed": cost_loadshed,
        "cost_redispatch": cost_redispatch,
        "rho": rho,
        "redispatch_cost_per_mwh": redispatch_cost,
        "unserved_mwh_per_event": unserved_mwh_per_event,
    }


def main() -> None:
    """Main function to calculate and display outage costs."""
    project_details = load_project_technical_details()

    from calculation_utils import build_category_string
    category = build_category_string(project_details=project_details)

    from smart_loaders import load_terrain_miles, load_circuit_and_resistance_details
    terrain_miles = load_terrain_miles()
    circuit_details = load_circuit_and_resistance_details(category)

    outage_yaml = load_outage_costs()
    financing_yaml = get_financing_data_raw()

    discount_rate, discount_source = get_discount_rate_from_config(
        outage_yaml, financing_yaml, rate_key="discount_rate_type"
    )

    results = calculate_outage_costs(
        outage_yaml,
        project_details.construction_type,
        terrain_miles,
        project_details.capacity_mw,
        project_details.project_lifetime,
        discount_rate,
        delay_years=project_details.delay_years,
        construction_years=project_details.construction_years,
        number_of_circuits_poles=circuit_details.number_of_circuits_poles,
        line_utilization=project_details.line_utilization,
        ac_dc=project_details.ac_dc,
    )

    from run_context import add_derived
    add_derived({
        "lambda_total_outage": results["lambda_total"],
        "EAC_outage": results["EAC"],
        "mw_lost_per_event": results["capacity_at_risk"] * project_details.capacity_mw,
        "construction_type_multiplier_outage_duration": results["duration_multiplier"],
    })

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
    print("OUTAGE EXPOSURE (LINE-LEVEL):")
    print(f"  Total Line Length: {results['total_miles']:.1f} miles")
    print(f"  Outage Rate: {results['outage_rate']:.4f} outages/mi/yr")
    if results.get("lambda_terminal", 0) > 0:
        print(f"  Model: decomposition (λ_terminal={results['lambda_terminal']:.2f} + λ_per_mile={results['lambda_per_mile']:.4f} × {results['total_miles']:.0f} mi)")
    print(f"  Total Outages/Year: {results['lambda_total']:.4f} events/year")
    print(f"  Base Duration: {results['outage_duration']:.1f}h")
    print(f"  Duration Multiplier: {results['duration_multiplier']:.1f}x")
    print(f"  Effective Duration: {results['duration_effective']:.1f}h")
    print(f"  Unserved Energy/Event: {results['unserved_mwh_per_event']:,.0f} MWh")
    print()
    print("TWO-TIER COST PER EVENT:")
    print(f"  Load-shed fraction (rho): {results['rho']:.2f} ({'AC meshed' if project_details.ac_dc == 'AC' else 'DC point-to-point'})")
    print(f"  Redispatch cost: ${results['redispatch_cost_per_mwh']:,.0f}/MWh")
    print(f"  Load-shed cost/event: ${results['cost_loadshed']:,.0f}")
    print(f"  Redispatch cost/event: ${results['cost_redispatch']:,.0f}")
    print(f"  Total cost/event: ${results['cost_per_event']:,.0f}")
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

    csv_manager = CTCCOutputManager()
    csv_manager.add_outage_costs(results)
    csv_manager.write_batch_summary()


if __name__ == "__main__":
    main()
