# Date: 2025-10-24
# Description: This script calculates the congestion reduction costs for a transmission line project.
#              It computes the congestion reduction costs for a transmission line over the project lifetime.
#              Single-constraint congestion relief (curtailment is not a separate stream).

from __future__ import annotations

import logging

import pandas as pd
import numpy as np
import argparse
import math
from dataclasses import dataclass
from typing import Any

from forge.scripts.utils.smart_output import SmartOutputManager
from forge.scripts.utils.constants import MIN_DISCOUNT_RATE, HOURS_PER_YEAR
from forge.scripts.utils.streams import growing, pv, undiscounted
from forge.scripts.utils.smart_loaders import (
    load_congestion_reductions,
    load_project_technical_details as load_project_technical_details_centralized,
    load_financing_details,
    get_project_data_raw,
)

logger = logging.getLogger(__name__)

_SPREAD_PATH = (
    "01_project_technical_details.market_measurements.congestion_spread_per_mwh"
)
_ENERGY_PATH = (
    "01_project_technical_details.market_measurements.receiving_energy_value_per_mwh"
)


@dataclass
class CongestionProjectDetails:
    """Project technical details for congestion-reduction calculations."""

    delay_years: float
    construction_years: int
    project_lifetime: int
    project_type: str
    capacity_mw: int
    old_capacity_mw: int
    sending_source: str
    contract_price_per_mwh: float | None

@dataclass
class CongestionReductionResults:
    """Results from congestion reduction calculation."""

    effective_capacity_mw: float
    average_exceedance: float | None
    relief_mw: float
    # Congestion benefit (remedial). Zero on a dedicated line. None when the
    # margin spread is null.
    annual_congestion_benefit: float | None
    # Total remedial (= congestion only)
    annual_remedial_benefit: float | None

def _get_old_capacity_mw() -> int:
    """
    Helper function to get old_capacity_mw from project technical details.
    This is needed because the centralized loader doesn't return this field.

    Required (must be present and non-null) when project_type is 'reconductoring'
    or 'rebuild', since old_capacity_mw is used directly in the capacity-relief
    calculation for those project types. Left at 0 for greenfield projects,
    matching the YAML schema's own null default for that case (old_capacity_mw
    is unused for greenfield).
    """
    project_data = get_project_data_raw()
    project = project_data["project"]
    project_type = project["project_type"]
    old_capacity_mw = project.get("old_capacity_mw")
    if project_type in ("reconductoring", "rebuild") and old_capacity_mw is None:
        raise KeyError(
            "Missing 'old_capacity_mw' in project technical details YAML: "
            "required when project_type is 'reconductoring' or 'rebuild'"
        )
    return old_capacity_mw if old_capacity_mw is not None else 0


def _market_block() -> dict[str, Any]:
    """Route measurements. A missing block is four absent values."""
    block = get_project_data_raw().get("market_measurements") or {}
    return block if isinstance(block, dict) else {}


def _measurement(name: str) -> float | None:
    value = _market_block().get(name)
    if value is None:
        return None
    return float(value)


def load_project_technical_details() -> CongestionProjectDetails:
    """
    Load project technical details using centralized loaders.

    This function wraps the centralized loader and extracts only the fields
    needed for congestion-reduction calculations.

    Returns:
        CongestionProjectDetails: Project technical details dataclass
    """
    from forge.scripts.io.yaml_loaders import ProjectTechnicalDetails

    project_details: ProjectTechnicalDetails = (
        load_project_technical_details_centralized()
    )

    # Get old_capacity_mw separately (not in centralized loader return)
    old_capacity_mw = _get_old_capacity_mw()

    return CongestionProjectDetails(
        delay_years=project_details.delay_years,
        construction_years=project_details.construction_years,
        project_lifetime=project_details.project_lifetime,
        project_type=project_details.project_type,
        capacity_mw=project_details.capacity_mw,
        old_capacity_mw=old_capacity_mw,
        sending_source=project_details.sending_source,
        contract_price_per_mwh=project_details.contract_price_per_mwh,
    )

# load_financing_details is now imported from smart_loaders

def calculate_congestion_reduction_costs(
    project_type: str,
    sending_source: str,
    capacity_mw: int,
    old_capacity_mw: int,
    flow_factor: float | None,
    average_exceedance: float | None,
    congestion_spread_per_mwh: float | None,
) -> CongestionReductionResults:
    """Single-constraint congestion relief over all 8,760 hours.

    Effective capacity is ``flow_factor × capacity`` for a greenfield line on
    the regional margin, ``1 × capacity`` for a greenfield dedicated resource
    (an entered flow factor is ignored), and ``capacity − old_capacity`` for
    reconductoring or rebuild. Empty exceedance means relief equals that
    capacity. The annual benefit is earned only on the margin, and only when
    the measured spread is set. A dedicated line is a measured zero and does
    not read the spread.
    """
    if project_type == "greenfield" and sending_source == "dedicated":
        delta_c_eff = 1.0 * capacity_mw
    elif project_type == "greenfield":
        if flow_factor is None:
            raise ValueError(
                "flow_factor is required for a greenfield line on the regional margin"
            )
        delta_c_eff = max(0.0, flow_factor * capacity_mw)
    else:
        delta_c_eff = max(0.0, capacity_mw - old_capacity_mw)

    if average_exceedance is None:
        relief_mw = delta_c_eff
    else:
        relief_mw = min(delta_c_eff, average_exceedance)

    if sending_source == "margin":
        if congestion_spread_per_mwh is None:
            annual_congestion_benefit = None
        else:
            annual_congestion_benefit = (
                HOURS_PER_YEAR * relief_mw * congestion_spread_per_mwh
            )
    else:
        annual_congestion_benefit = 0.0

    return CongestionReductionResults(
        effective_capacity_mw=delta_c_eff,
        average_exceedance=average_exceedance,
        relief_mw=relief_mw,
        annual_congestion_benefit=annual_congestion_benefit,
        annual_remedial_benefit=annual_congestion_benefit,
    )


def _growing_benefit(
    annual: float,
    growth: float,
    lifetime: int,
    social_discount_rate: float,
    wacc_real: float,
    t_cod: int,
    horizon: int,
) -> Dict[str, Any]:
    """Benefit stream grown from year 1 and paid from COD.

    ``annual`` stays the base-year amount. Year ``t`` holds
    ``annual * (1 + growth) ** (t - 1)``.
    """
    stream = growing(annual, growth, t_cod, lifetime, horizon)
    return {
        "stream": stream,
        "nominal": undiscounted(stream),
        "pv": pv(stream, social_discount_rate),
        "pv_wacc": pv(stream, wacc_real),
    }


def _money_or_absent(
    annual: float | None,
    growth: float,
    lifetime: int,
    social_discount_rate: float,
    wacc_real: float,
    t_cod: int,
    horizon: int,
) -> dict[str, Any]:
    """A null annual is not available: the four money fields and the stream stay null."""
    if annual is None:
        return {"stream": None, "nominal": None, "pv": None, "pv_wacc": None}
    return _growing_benefit(
        annual, growth, lifetime, social_discount_rate, wacc_real, t_cod, horizon
    )


def _log_dollars(label: str, annual: float | None, money: dict[str, Any]) -> None:
    if annual is None:
        logger.info(f"{label}: not available")
        return
    logger.info(f"{label}: ${annual:,.2f}")
    logger.info(f"Lifetime {label.lower()} (nominal): ${money['nominal']:,.2f}")
    logger.info(f"Lifetime {label.lower()} (social PV): ${money['pv']:,.2f}")


def main() -> None:
    """
    Main function to calculate and display congestion reduction costs.
    """
    # Load all required data
    project_details_cc = load_project_technical_details()

    # Load financing details
    financing = load_financing_details()

    # Load congestion reduction parameters
    params = load_congestion_reductions()

    # The spread is read only for a margin line. Dedicated congestion is zero.
    spread = (
        _measurement("congestion_spread_per_mwh")
        if project_details_cc.sending_source == "margin"
        else None
    )
    congestion_results = calculate_congestion_reduction_costs(
        project_details_cc.project_type,
        project_details_cc.sending_source,
        project_details_cc.capacity_mw,
        project_details_cc.old_capacity_mw,
        params.flow_factor,
        params.average_exceedance,
        spread,
    )

    logger.info("=" * 60)
    logger.info("CONGESTION PHYSICAL RESULTS AND QUANTITIES")
    logger.info("=" * 60)
    logger.info(
        f"Effective capacity: {congestion_results.effective_capacity_mw:,.2f} MW"
    )
    logger.info(f"Hours per year: {HOURS_PER_YEAR:,.0f}")
    if congestion_results.average_exceedance is None:
        logger.info("Average exceedance: empty (relief equals effective capacity)")
    else:
        logger.info(
            f"Average exceedance: {congestion_results.average_exceedance:,.2f} MW"
        )
    logger.info(f"Relief MW: {congestion_results.relief_mw:,.2f} MW")

    # E_deliv = delta_P_eff * utilization * 8760, for every line.
    # Benefit = 1[dedicated] * E_deliv * (value of load - contract price). No floor.
    project_data = get_project_data_raw()
    project = project_data["project"]
    line_utilization = float(project["line_utilization"])
    receiving_energy_value = _measurement("receiving_energy_value_per_mwh")
    delta_c_effective = congestion_results.effective_capacity_mw
    energy_delivered_annual_mwh_yr = (
        delta_c_effective * line_utilization * HOURS_PER_YEAR
    )
    if project_details_cc.sending_source == "dedicated":
        if receiving_energy_value is None:
            delivered_benefit_annual = None
        else:
            contract_price = project_details_cc.contract_price_per_mwh
            if contract_price is None:
                raise ValueError(
                    "contract_price_per_mwh is required for a dedicated resource"
                )
            delivered_benefit_annual = energy_delivered_annual_mwh_yr * (
                receiving_energy_value - contract_price
            )
    else:
        delivered_benefit_annual = 0.0

    from forge.scripts.utils.run_context import get_run_context, get_run_state
    cap_params = get_run_state().inputs.get("20_capacity_value") or {}
    capacity_gate = bool(cap_params.get("applicability_gate", False))
    cap_results = calculate_capacity_value_benefit(
        delta_c_effective=delta_c_effective,
        capacity_credit=float(cap_params.get("capacity_credit", 0)),
        capacity_price=float(cap_params.get("capacity_price", 0)),
        applicability_gate=capacity_gate,
        project_lifetime=project_details_cc.project_lifetime,
        delay_years=project_details_cc.delay_years,
        construction_years=project_details_cc.construction_years,
        wacc_real=financing.wacc_real,
        benefit_price_escalation_real=params.benefit_price_escalation_real,
    )

    ctx = get_run_context()
    g_benefit = params.benefit_price_escalation_real
    lifetime = int(project_details_cc.project_lifetime)
    congestion = _money_or_absent(
        congestion_results.annual_congestion_benefit,
        g_benefit,
        lifetime,
        ctx.social_discount_rate,
        financing.wacc_real,
        ctx.t_cod,
        ctx.horizon,
    )
    delivered = _money_or_absent(
        delivered_benefit_annual,
        g_benefit,
        lifetime,
        ctx.social_discount_rate,
        financing.wacc_real,
        ctx.t_cod,
        ctx.horizon,
    )
    capacity = _growing_benefit(
        cap_results["capacity_value_annual"],
        g_benefit,
        lifetime,
        ctx.social_discount_rate,
        financing.wacc_real,
        ctx.t_cod,
        ctx.horizon,
    )

    logger.info("")
    logger.info("=" * 60)
    logger.info("CONGESTION REDUCTION BENEFIT RESULTS")
    logger.info("=" * 60)
    _log_dollars(
        "Annual congestion benefit",
        congestion_results.annual_congestion_benefit,
        congestion,
    )

    logger.info("")
    logger.info("=" * 60)
    logger.info("BENEFIT OF DELIVERED ENERGY")
    logger.info("=" * 60)
    logger.info(
        f"Energy delivered (annual): {energy_delivered_annual_mwh_yr:,.2f} MWh/yr"
    )
    _log_dollars("Annual benefit", delivered_benefit_annual, delivered)
    logger.info("=" * 60)

    logger.info("")
    logger.info("=" * 60)
    logger.info("CAPACITY VALUE BENEFIT")
    logger.info("=" * 60)
    logger.info(f"Annual capacity value: ${cap_results['capacity_value_annual']:,.2f}")
    logger.info(f"Lifetime capacity value (nominal): ${capacity['nominal']:,.2f}")
    logger.info(f"Lifetime capacity value (social PV): ${capacity['pv']:,.2f}")
    logger.info("=" * 60)

    csv_manager = SmartOutputManager()
    results = {
        "congestion_benefit_annual": congestion_results.annual_congestion_benefit,
        "congestion_benefit_nominal": congestion["nominal"],
        "congestion_benefit_pv": congestion["pv"],
        "congestion_benefit_pv_wacc": congestion["pv_wacc"],
        "delivered_benefit_annual": delivered_benefit_annual,
        "delivered_benefit_nominal": delivered["nominal"],
        "delivered_benefit_pv": delivered["pv"],
        "delivered_benefit_pv_wacc": delivered["pv_wacc"],
        "energy_delivered_annual_mwh_yr": energy_delivered_annual_mwh_yr,
        "capacity_value_annual": cap_results["capacity_value_annual"],
        "capacity_value_nominal": capacity["nominal"],
        "capacity_value_pv": capacity["pv"],
        "capacity_value_pv_wacc": capacity["pv_wacc"],
        "streams": {
            "congestion_benefit": congestion["stream"],
            "delivered_energy_benefit": delivered["stream"],
            "capacity_value_benefit": capacity["stream"],
        },
        "effective_capacity_mw": congestion_results.effective_capacity_mw,
        "relief_mw": congestion_results.relief_mw,
        "availability": {
            "congestion_benefit": {
                "available": congestion_results.annual_congestion_benefit is not None,
                "missing_inputs": (
                    ()
                    if congestion_results.annual_congestion_benefit is not None
                    else (_SPREAD_PATH,)
                ),
                "applies": project_details_cc.sending_source == "margin",
            },
            "delivered_energy_benefit": {
                "available": delivered_benefit_annual is not None,
                "missing_inputs": (
                    ()
                    if delivered_benefit_annual is not None
                    else (_ENERGY_PATH,)
                ),
                "applies": project_details_cc.sending_source == "dedicated",
            },
            "capacity_value_benefit": {
                "available": True,
                "missing_inputs": (),
                "applies": capacity_gate,
            },
        },
    }

    from forge.scripts.utils.run_context import add_derived
    add_derived({
        "effective_capacity_mw": congestion_results.effective_capacity_mw,
        "energy_delivered_annual_mwh_yr": energy_delivered_annual_mwh_yr,
        "relief_mw": congestion_results.relief_mw,
    })

    csv_manager.add_congestion(results)
    csv_manager.write_batch_summary()

def calculate_capacity_value_benefit(
    delta_c_effective: float,
    capacity_credit: float,
    capacity_price: float,
    applicability_gate: bool,
    project_lifetime: int,
    delay_years: float,
    construction_years: int,
    wacc_real: float,
    benefit_price_escalation_real: float = 0.0,
) -> dict:
    """Capacity value: Net CONE × capacity credit × ΔC_eff × gate.

    Parametric screening proxy for resource adequacy contribution
    (Brattle 2013). Uses Net CONE to avoid double-counting with
    delivered energy benefit.

    Returns dict with capacity_value_annual and capacity_value_pv.
    capacity_value_pv is the WACC present value of the benefit stream.
    """
    g = benefit_price_escalation_real

    indicator_cap = 1.0 if (applicability_gate and capacity_credit > 0 and capacity_price > 0) else 0.0
    annual = delta_c_effective * capacity_credit * capacity_price * indicator_cap

    t_cod = int(delay_years) + int(construction_years) + 1
    lifetime = int(project_lifetime)
    stream = growing(annual, g, t_cod, lifetime, t_cod + lifetime - 1)

    return {
        "capacity_value_annual": annual,
        "capacity_value_pv": pv(stream, wacc_real),
    }
