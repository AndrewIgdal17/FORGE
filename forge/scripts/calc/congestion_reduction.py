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
from typing import Dict, Any, Tuple

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


@dataclass
class CongestionProjectDetails:
    """Project technical details for congestion-reduction calculations."""

    delay_years: float
    construction_years: int
    project_lifetime: int
    project_type: str
    capacity_mw: int
    old_capacity_mw: int

@dataclass
class CongestionReductionResults:
    """Results from congestion reduction calculation."""

    effective_capacity_mw: float
    constrained_hours: float
    average_exceedance: float
    relief_mw: float
    # Congestion benefit (remedial)
    annual_congestion_benefit: float
    # Total remedial (= congestion only)
    annual_remedial_benefit: float

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


def require_value_of_load_per_mwh(project: Dict[str, Any]) -> float:
    """Return γ_load; fail loudly if the required delivered-energy parameter is missing."""
    if "value_of_load_per_mwh" not in project:
        raise KeyError(
            "Missing required parameter 'value_of_load_per_mwh' for delivered energy benefit"
        )
    return float(project["value_of_load_per_mwh"])


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
    )

# load_financing_details is now imported from smart_loaders

def calculate_congestion_reduction_costs(
    project_type: str,
    capacity_mw: int,
    old_capacity_mw: int,
    flow_factor: float,
    constrained_hours: float,
    average_exceedance: float,
    average_congestion_price: float,
) -> CongestionReductionResults:
    """
    Single-constraint congestion relief benefit.

    A transmission constraint binds for H hours/yr with average exceedance X MW.
    Congestion benefit uses the full constrained hours (no f / (1-f) split):

        B_cong = H * min(delta_C_eff, X) * gamma_cong

    Curtailment benefit is not modeled separately (would double-count MWh
    already valued under delivered energy).

    Args:
        project_type: "greenfield" | "reconductoring" | "rebuild"
        capacity_mw: New line capacity in MW (for greenfield) or upgraded capacity (for reconductoring)
        old_capacity_mw: Original capacity in MW (used for reconductoring and rebuild projects)
        flow_factor: Fraction of capacity that effectively relieves constraints (greenfield only)
        constrained_hours: H, hours per year the constraint binds
        average_exceedance: X, average MW exceedance during constrained hours
        average_congestion_price: gamma_cong, $/MWh redispatch cost

    Returns:
        CongestionReductionResults: Dataclass containing congestion reduction results
    """
    # Effective capacity
    if project_type == "greenfield":
        delta_C_eff = max(0.0, flow_factor * capacity_mw)
    else:
        delta_C_eff = max(0.0, capacity_mw - old_capacity_mw)

    H = max(0.0, float(constrained_hours))
    X = max(0.0, float(average_exceedance))

    # Core equation — full constrained hours (no congestion-fraction split)
    relief_mw = min(delta_C_eff, X)
    annual_congestion_benefit = H * relief_mw * average_congestion_price
    annual_remedial_benefit = annual_congestion_benefit

    return CongestionReductionResults(
        effective_capacity_mw=delta_C_eff,
        constrained_hours=H,
        average_exceedance=X,
        relief_mw=relief_mw,
        annual_congestion_benefit=annual_congestion_benefit,
        annual_remedial_benefit=annual_remedial_benefit,
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

    # Calculate congestion reduction costs
    congestion_results = calculate_congestion_reduction_costs(
        project_details_cc.project_type,
        project_details_cc.capacity_mw,
        project_details_cc.old_capacity_mw,
        params.flow_factor,
        params.constrained_hours,
        params.average_exceedance,
        params.average_congestion_price,
    )

    logger.info("=" * 60)
    logger.info("CONGESTION PHYSICAL RESULTS AND QUANTITIES")
    logger.info("=" * 60)
    logger.info(
        f"Effective capacity: {congestion_results.effective_capacity_mw:,.2f} MW"
    )
    logger.info(f"Constrained hours: {congestion_results.constrained_hours:,.0f} hrs/yr")
    logger.info(f"Average exceedance: {congestion_results.average_exceedance:,.2f} MW")
    logger.info(f"Relief MW (min of relief and exceedance): {congestion_results.relief_mw:,.2f} MW")

    # E_delivered_annual = Delta_C_effective * u * H
    # B_delivered_annual = E * gamma_electricity, the base-year amount.
    project_data = get_project_data_raw()
    project = project_data["project"]
    line_utilization = float(project["line_utilization"])
    value_of_load_per_mwh = require_value_of_load_per_mwh(project)
    delta_c_effective = congestion_results.effective_capacity_mw
    energy_delivered_annual_mwh_yr = (
        delta_c_effective * line_utilization * HOURS_PER_YEAR
    )
    delivered_benefit_annual = (
        energy_delivered_annual_mwh_yr * value_of_load_per_mwh
    )

    from forge.scripts.utils.run_context import get_run_context, get_run_state
    cap_params = get_run_state().inputs.get("20_capacity_value") or {}
    cap_results = calculate_capacity_value_benefit(
        delta_c_effective=delta_c_effective,
        capacity_credit=float(cap_params.get("capacity_credit", 0)),
        capacity_price=float(cap_params.get("capacity_price", 0)),
        applicability_gate=bool(cap_params.get("applicability_gate", False)),
        project_lifetime=project_details_cc.project_lifetime,
        delay_years=project_details_cc.delay_years,
        construction_years=project_details_cc.construction_years,
        wacc_real=financing.wacc_real,
        benefit_price_escalation_real=params.benefit_price_escalation_real,
    )

    ctx = get_run_context()
    g_benefit = params.benefit_price_escalation_real
    lifetime = int(project_details_cc.project_lifetime)
    congestion = _growing_benefit(
        congestion_results.annual_congestion_benefit,
        g_benefit,
        lifetime,
        ctx.social_discount_rate,
        financing.wacc_real,
        ctx.t_cod,
        ctx.horizon,
    )
    delivered = _growing_benefit(
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
    logger.info(f"Annual congestion benefit: ${congestion_results.annual_congestion_benefit:,.2f}")
    logger.info(f"Lifetime congestion benefit: ${congestion['nominal']:,.2f}")
    logger.info(f"Lifetime congestion benefit (social PV): ${congestion['pv']:,.2f}")
    logger.info(f"Lifetime congestion benefit (WACC PV): ${congestion['pv_wacc']:,.2f}")

    logger.info("")
    logger.info("=" * 60)
    logger.info("BENEFIT OF DELIVERED ENERGY")
    logger.info("=" * 60)
    logger.info(
        f"Energy delivered (annual): {energy_delivered_annual_mwh_yr:,.2f} MWh/yr"
    )
    logger.info(f"Annual benefit: ${delivered_benefit_annual:,.2f}")
    logger.info(f"Lifetime benefit (nominal): ${delivered['nominal']:,.2f}")
    logger.info(f"Lifetime benefit (social PV): ${delivered['pv']:,.2f}")
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
        "constrained_hours": congestion_results.constrained_hours,
        "relief_mw": congestion_results.relief_mw,
    }

    from forge.scripts.utils.run_context import add_derived
    add_derived({
        "effective_capacity_mw": congestion_results.effective_capacity_mw,
        "energy_delivered_annual_mwh_yr": energy_delivered_annual_mwh_yr,
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
