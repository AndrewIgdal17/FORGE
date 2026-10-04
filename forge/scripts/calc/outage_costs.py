# Date: 2025-10-29
# Description: This script calculates expected outage costs using simplified probabilistic
#              reliability approach with line-level outage rates, multiplicative duration model,
#              and piecewise value of lost load (VoLL).

from __future__ import annotations

import logging

# Standard library imports
import yaml
from typing import Dict, Any, Tuple, List

from forge.scripts.utils.smart_output import SmartOutputManager

# Local utility imports
from forge.scripts.utils.constants import MIN_DISCOUNT_RATE, GROWTH_RATE_TOLERANCE
from forge.scripts.utils.smart_loaders import (
    load_project_technical_details,
    load_outage_costs,
    get_financing_data_raw,
)
from forge.scripts.utils.financial_utils import calculate_growing_annuity_pv, validate_discount_rate, calculate_nominal_growing_series
from forge.scripts.utils.calculation_utils import normalize_construction_type_for_yaml

logger = logging.getLogger(__name__)


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
        dict: Contains expected_annual_loss, nominal_cost, pv_cost

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
    redispatch_cost = outage_config["redispatch_cost_per_mwh"]

    voll_tiers = outage_config["value_of_lost_load"]["tiers"]
    outage_duration = outage_config["outage_duration"]
    duration_multiplier_dict = outage_config["outage_duration_multiplier"]
    outage_rate_config = outage_config["outage_rate"]

    yaml_construction_type = normalize_construction_type_for_yaml(construction_type)

    total_miles = sum(terrain_miles.values())

    # Outage rate: overhead uses decomposition model, others use flat per-mile
    rate_entry = outage_rate_config[yaml_construction_type]
    if isinstance(rate_entry, dict):
        lambda_terminal = rate_entry["lambda_terminal"]
        lambda_per_mile = rate_entry["lambda_per_mile"]
        lambda_total = lambda_terminal + lambda_per_mile * total_miles
        outage_rate = lambda_total / total_miles if total_miles > 0 else lambda_per_mile
    else:
        outage_rate = float(rate_entry)
        lambda_total = total_miles * outage_rate
        lambda_terminal = 0.0
        lambda_per_mile = outage_rate

    # Effective duration (multiplicative model)
    dur_mult = duration_multiplier_dict[yaml_construction_type]
    duration_effective = outage_duration * dur_mult

    # MW lost per event
    mw_lost_per_event = capacity_at_risk * capacity_mw * line_utilization

    # Unserved energy per event (ρ = load_shed_fraction)
    unserved_mwh_per_event = rho * duration_effective * mw_lost_per_event

    # Two-tier cost per event: load-shed (VoLL) + redispatch (flat rate)
    mw_shed = rho * mw_lost_per_event
    mw_redisp = (1 - rho) * mw_lost_per_event
    cost_loadshed = calculate_voll_cost_piecewise(
        duration_effective, mw_shed, voll_tiers
    )
    cost_redispatch = mw_redisp * duration_effective * redispatch_cost
    cost_per_event = cost_loadshed + cost_redispatch

    # Expected annual loss
    expected_annual_loss = lambda_total * cost_per_event

    nominal_total = calculate_nominal_growing_series(
        annual_amount=expected_annual_loss,
        growth_rate=growth_rate,
        project_lifetime=project_lifetime,
    )

    pv_cost = calculate_growing_annuity_pv(
        annual_amount=expected_annual_loss,
        growth_rate=growth_rate,
        discount_rate=discount_rate,
        project_lifetime=project_lifetime,
        delay_years=delay_years,
        construction_years=construction_years,
    )

    return {
        "lambda_total": lambda_total,
        "expected_annual_loss": expected_annual_loss,
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

    from forge.scripts.utils.run_context import get_run_context
    ctx = get_run_context()
    if ctx is None:
        raise RuntimeError(
            f"{__name__} requires a RunContext. Run via forge.py or set up "
            "RunContext in your test fixture."
        )
    category = ctx.category_string

    from forge.scripts.utils.smart_loaders import load_terrain_miles, load_circuit_and_resistance_details
    terrain_miles = load_terrain_miles()
    circuit_details = load_circuit_and_resistance_details(category)

    outage_yaml = load_outage_costs()
    financing_yaml = get_financing_data_raw()

    # Social discount rate only — risk externalities use r_social (appendix hard-codes this)
    discount_rate = financing_yaml["financial"]["social_discount_rate"]
    discount_source = "social"

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

    from forge.scripts.utils.run_context import add_derived
    add_derived({
        "lambda_total_outage": results["lambda_total"],
        "expected_annual_loss_outage": results["expected_annual_loss"],
        "mw_lost_per_event": results["capacity_at_risk"] * project_details.capacity_mw,
        "construction_type_multiplier_outage_duration": results["duration_multiplier"],
    })

    logger.info("=" * 80)
    logger.info("EXPECTED OUTAGE COST CALCULATION RESULTS")
    logger.info("=" * 80)
    logger.info(f"Project Category: {category}")
    logger.info(f"Construction Type: {project_details.construction_type}")
    logger.info(f"Project Capacity: {project_details.capacity_mw} MW")
    logger.info(
        f"Capacity at Risk: {results['capacity_at_risk']*100:.1f}% (phi = {results['capacity_at_risk']:.2f})"
    )
    logger.info("")

    logger.info("[OUTAGE RELIABILITY ASSESSMENT]")
    logger.info("")
    logger.info("OUTAGE EXPOSURE (LINE-LEVEL):")
    logger.info(f"  Total Line Length: {results['total_miles']:.1f} miles")
    logger.info(f"  Outage Rate: {results['outage_rate']:.4f} outages/mi/yr")
    if results.get("lambda_terminal", 0) > 0:
        logger.info(f"  Model: decomposition (λ_terminal={results['lambda_terminal']:.2f} + λ_per_mile={results['lambda_per_mile']:.4f} × {results['total_miles']:.0f} mi)")
    logger.info(f"  Total Outages/Year: {results['lambda_total']:.4f} events/year")
    logger.info(f"  Base Duration: {results['outage_duration']:.1f}h")
    logger.info(f"  Duration Multiplier: {results['duration_multiplier']:.1f}x")
    logger.info(f"  Effective Duration: {results['duration_effective']:.1f}h")
    logger.info(f"  Unserved Energy/Event: {results['unserved_mwh_per_event']:,.0f} MWh")
    logger.info("")
    logger.info("TWO-TIER COST PER EVENT:")
    logger.info(f"  Load-shed fraction (rho): {results['rho']:.2f} ({'AC meshed' if project_details.ac_dc == 'AC' else 'DC point-to-point'})")
    logger.info(f"  Redispatch cost: ${results['redispatch_cost_per_mwh']:,.0f}/MWh")
    logger.info(f"  Load-shed cost/event: ${results['cost_loadshed']:,.0f}")
    logger.info(f"  Redispatch cost/event: ${results['cost_redispatch']:,.0f}")
    logger.info(f"  Total cost/event: ${results['cost_per_event']:,.0f}")
    logger.info("")

    logger.info("EXPECTED ANNUAL LOSS:")
    logger.info(f"  expected_annual_loss: ${results['expected_annual_loss']:,.2f}/year")
    logger.info("")

    logger.info("[NOMINAL VALUES]")
    logger.info(f"  Project Lifetime: {project_details.project_lifetime} years")
    logger.info(f"  Risk Growth Rate: {results['growth_rate']:.1%}/year")
    logger.info(f"  ---")
    logger.info(f"  TOTAL NOMINAL COST: ${results['nominal_total']:,.2f}")
    logger.info(f"    (Sum of growing annual costs, undiscounted)")
    logger.info("")

    logger.info("[SOCIETAL PERSPECTIVE - Present Value]")
    logger.info(f"  Discount Rate: {discount_rate:.2%} ({discount_source})")
    logger.info(f"  Growing Annuity Formula: Applied")
    if results["growth_rate"] > discount_rate:
        logger.warning(
            f"  ⚠️  WARNING: Risk growth rate ({results['growth_rate']:.2%}) > discount rate ({discount_rate:.2%})"
        )
        logger.info(f"      PV grows over time - risk is escalating faster than discounting!")
    logger.info(f"  ---")
    logger.info(f"  TOTAL PRESENT VALUE: ${results['pv_cost']:,.2f}")
    logger.info("")
    logger.info("NOTE: Outage costs are probabilistic future losses, not capital costs.")
    logger.info("      No AFUDC applies to expected loss calculations.")
    logger.info("=" * 80)

    csv_manager = SmartOutputManager()
    csv_manager.add_outage_costs(results)
    csv_manager.write_batch_summary()
