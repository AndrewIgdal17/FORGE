# Date: 2025-10-29
# Description: This script calculates expected outage costs using simplified probabilistic
#              reliability approach with line-level outage rates, multiplicative duration model,
#              and interpolated value of lost load (VoLL).

from __future__ import annotations

import bisect
import logging

# Standard library imports
import yaml
from typing import Dict, Any, Tuple, List

from forge.scripts.utils.smart_output import SmartOutputManager

# Local utility imports
from forge.scripts.utils.constants import MIN_DISCOUNT_RATE, GROWTH_RATE_TOLERANCE
from forge.scripts.utils.smart_loaders import (
    get_project_data_raw,
    load_project_technical_details,
    load_outage_costs,
)
from forge.scripts.utils.financial_utils import validate_discount_rate
from forge.scripts.utils.streams import growing, pv, undiscounted
from forge.scripts.utils.calculation_utils import normalize_construction_type_for_yaml

logger = logging.getLogger(__name__)

SPREAD_PATH = (
    "01_project_technical_details.market_measurements.congestion_spread_per_mwh"
)


def _market_block() -> Dict[str, Any]:
    block = get_project_data_raw().get("market_measurements") or {}
    return block if isinstance(block, dict) else {}


def _congestion_spread() -> float | None:
    value = _market_block().get("congestion_spread_per_mwh")
    if value is None:
        return None
    return float(value)


def value_of_lost_load(duration_hours: float, points: list[dict[str, float]]) -> float:
    """Interpolate VoLL ($/MWh) at the outage duration from survey knot points."""
    if duration_hours < 0:
        raise ValueError("duration_hours must be non-negative")
    if len(points) < 2:
        raise ValueError("points must contain at least two entries")
    hours = [float(point["hours"]) for point in points]
    if any(hours[index] >= hours[index + 1] for index in range(len(hours) - 1)):
        raise ValueError("hours must be strictly increasing")
    if duration_hours <= hours[0]:
        return float(points[0]["value_per_mwh"])
    if duration_hours >= hours[-1]:
        return float(points[-1]["value_per_mwh"])
    index = bisect.bisect_right(hours, duration_hours) - 1
    if duration_hours == hours[index]:
        return float(points[index]["value_per_mwh"])
    h0, h1 = hours[index], hours[index + 1]
    v0 = float(points[index]["value_per_mwh"])
    v1 = float(points[index + 1]["value_per_mwh"])
    weight = (duration_hours - h0) / (h1 - h0)
    return v0 + weight * (v1 - v0)


def calculate_outage_costs(
    outage_yaml: Dict[str, Any],
    construction_type: str,
    terrain_miles: Dict[str, float],
    capacity_mw: int,
    project_lifetime: int,
    discount_rate: float,
    delay_years: float = 0,
    *,
    construction_years: float,
    number_of_circuits_poles: int = 1,
    line_utilization: float = 1.0,
    t_cod: int | None = None,
    horizon: int | None = None,
    sending_source: str,
    congestion_spread_per_mwh: float | None,
) -> Dict[str, Any]:
    """
    Calculate expected outage costs using line-level outage rate model.

    Args:
        outage_yaml: Loaded outage YAML data
        construction_type: Construction type (overhead, underground)
        terrain_miles: Dictionary of terrain type to miles (summed for total length)
        capacity_mw: Project capacity in MW
        project_lifetime: Project lifetime in years
        discount_rate: Discount rate for PV calculation
        delay_years: Years of delay before construction starts
        construction_years: Years of construction. Required keyword.
        number_of_circuits_poles: Number of circuits (AC) or poles (DC); used to
            auto-derive phi = 1/N_poles when capacity_at_risk_factor is "auto"
        line_utilization: Average fraction of line capacity in use (0-1)

    Returns:
        dict: Contains expected_annual_loss, nominal_cost, pv_cost

    Raises:
        TypeError: If construction_years is omitted
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
    load_shed_fraction = float(outage_config["load_shed_fraction"])
    redispatch_applies = sending_source == "margin"

    voll_points = outage_config["value_of_lost_load"]["points"]
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

        # Unserved energy per event (load-shed share of lost flow)
    unserved_mwh_per_event = load_shed_fraction * duration_effective * mw_lost_per_event

    # Two-tier cost per event: load-shed (VoLL) + redispatch (congestion spread)
    mw_shed = load_shed_fraction * mw_lost_per_event
    mw_redisp = (1 - load_shed_fraction) * mw_lost_per_event
    voll_per_mwh = value_of_lost_load(duration_effective, voll_points)
    cost_loadshed = mw_shed * duration_effective * voll_per_mwh

    if redispatch_applies and congestion_spread_per_mwh is not None:
        spread = float(congestion_spread_per_mwh)
        cost_redispatch: float | None = mw_redisp * duration_effective * spread
    else:
        spread = congestion_spread_per_mwh
        cost_redispatch = None

    if t_cod is None:
        t_cod = int(delay_years) + int(construction_years) + 1
    lifetime = int(project_lifetime)
    if horizon is None:
        horizon = t_cod + lifetime - 1

    annual_load_shed = lambda_total * cost_loadshed
    stream_load_shed = growing(
        annual_load_shed, growth_rate, int(t_cod), lifetime, int(horizon)
    )
    nominal_load_shed = undiscounted(stream_load_shed)
    pv_load_shed = pv(stream_load_shed, discount_rate)

    if cost_redispatch is not None:
        annual_redispatch: float | None = lambda_total * cost_redispatch
        stream_redispatch = growing(
            annual_redispatch, growth_rate, int(t_cod), lifetime, int(horizon)
        )
        nominal_redispatch: float | None = undiscounted(stream_redispatch)
        pv_redispatch: float | None = pv(stream_redispatch, discount_rate)
        cost_per_event = cost_loadshed + cost_redispatch
        expected_annual_loss = annual_load_shed + annual_redispatch
        nominal_total = nominal_load_shed + nominal_redispatch
    else:
        annual_redispatch = None
        stream_redispatch = None
        nominal_redispatch = None
        pv_redispatch = None
        cost_per_event = cost_loadshed
        expected_annual_loss = annual_load_shed
        nominal_total = nominal_load_shed

    pv_cost = pv_load_shed + (pv_redispatch if pv_redispatch is not None else 0.0)

    if not redispatch_applies:
        redispatch_availability = {
            "available": True,
            "applies": False,
            "missing_inputs": (),
        }
    elif congestion_spread_per_mwh is None:
        redispatch_availability = {
            "available": False,
            "applies": True,
            "missing_inputs": (SPREAD_PATH,),
        }
    else:
        redispatch_availability = {
            "available": True,
            "applies": True,
            "missing_inputs": (),
        }

    return {
        "lambda_total": lambda_total,
        "mw_lost_per_event": mw_lost_per_event,
        "load_shed_fraction": load_shed_fraction,
        "expected_annual_loss": expected_annual_loss,
        "annual_load_shed": annual_load_shed,
        "annual_redispatch": annual_redispatch,
        "capacity_at_risk": capacity_at_risk,
        "growth_rate": growth_rate,
        "nominal_total": nominal_total,
        "nominal_load_shed": nominal_load_shed,
        "nominal_redispatch": nominal_redispatch,
        "pv_cost": pv_cost,
        "pv_load_shed": pv_load_shed,
        "pv_redispatch": pv_redispatch,
        "streams": {
            "outage_load_shed": stream_load_shed,
            "outage_redispatch": stream_redispatch,
        },
        "availability": {
            "outage_load_shed": {"available": True, "applies": True, "missing_inputs": ()},
            "outage_redispatch": redispatch_availability,
        },
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
        "voll_per_mwh": voll_per_mwh,
        "congestion_spread_per_mwh": spread,
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

    # Social discount rate only — risk externalities use r_social from RunContext
    discount_rate = ctx.social_discount_rate
    discount_source = "social"

    project_data = get_project_data_raw()
    sending_source = project_data["project"]["sending_source"]
    if sending_source == "margin":
        spread = _congestion_spread()
    else:
        spread = None

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
        t_cod=ctx.t_cod,
        horizon=ctx.horizon,
        sending_source=sending_source,
        congestion_spread_per_mwh=spread,
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
    logger.info(f"  Load-shed fraction: {results['load_shed_fraction']:.2f}")
    spread = results["congestion_spread_per_mwh"]
    redispatch_avail = results["availability"]["outage_redispatch"]
    if not redispatch_avail["applies"]:
        logger.info("  Redispatch: does not apply (not a margin line)")
    elif spread is None:
        logger.info("  Redispatch: not available (no measured congestion spread)")
    else:
        logger.info(f"  Congestion spread: ${spread:,.2f}/MWh")
    logger.info(f"  Load-shed cost/event: ${results['cost_loadshed']:,.0f}")
    if results["cost_redispatch"] is not None:
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
