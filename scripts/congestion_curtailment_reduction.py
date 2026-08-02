# Author: Andrew Igdal
# Date: 2025-10-24
# Description: This script calculates the congestion reduction costs for a transmission line project.
#              It computes the congestion reduction costs for a transmission line over the project lifetime.
#              Single-constraint, two-price decomposition.

from __future__ import annotations

import pandas as pd
import yaml
import numpy as np
import argparse
import math
import sys
import os
from dataclasses import dataclass
from typing import Dict, Any, Tuple

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from smart_output import CTCCOutputManager
from constants import MIN_DISCOUNT_RATE, HOURS_PER_YEAR
from financial_utils import calculate_present_value, calculate_cod_year, calculate_growing_annuity_pv, calculate_nominal_growing_series
from smart_loaders import (
    load_congestion_curtailment_reductions,
    load_project_technical_details as load_project_technical_details_centralized,
    load_financing_details,
    get_project_data_raw,
)


@dataclass
class CongestionProjectDetails:
    """Project technical details for congestion/curtailment calculations."""

    delay_years: float
    construction_years: int
    project_lifetime: int
    project_type: str
    capacity_mw: int
    old_capacity_mw: int


@dataclass
class CongestionReductionResults:
    """Results from congestion/curtailment calculation."""

    effective_capacity_relief: float
    constrained_hours: float
    average_exceedance: float
    congestion_fraction: float
    relief_mw: float
    # Congestion benefit
    annual_congestion_benefit: float
    lifetime_congestion_benefit: float
    lifetime_congestion_benefit_pv: float
    # Curtailment benefit
    annual_curtailment_benefit: float
    lifetime_curtailment_benefit: float
    lifetime_curtailment_benefit_pv: float
    # Total remedial
    annual_remedial_benefit: float
    lifetime_remedial_benefit_pv: float
    # Delay opportunity costs
    congestion_delay_cost_nominal: float
    congestion_delay_cost_pv: float
    curtailment_delay_cost_nominal: float
    curtailment_delay_cost_pv: float


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


def load_project_technical_details() -> CongestionProjectDetails:
    """
    Load project technical details using centralized loaders.

    This function wraps the centralized loader and extracts only the fields
    needed for congestion/curtailment calculations.

    Returns:
        CongestionProjectDetails: Project technical details dataclass
    """
    from yaml_loaders import ProjectTechnicalDetails

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
# calculate_present_value is now imported from financial_utils


def calculate_congestion_reduction_costs(
    project_type: str,
    capacity_mw: int,
    old_capacity_mw: int,
    flow_factor: float,
    constrained_hours: float,
    average_exceedance: float,
    congestion_fraction: float,
    average_congestion_price: float,
    average_curtailment_price: float,
    project_lifetime: int,
    delay_years: float,
    construction_years: int,
    wacc_real: float,
    benefit_price_escalation_real: float = 0.0,
) -> CongestionReductionResults:
    """
    Single-constraint, two-price decomposition.

    A single transmission constraint binds for H hours/yr with an average exceedance
    of X MW. A fraction f of those constrained hours resolve as redispatch
    (congestion); the remainder (1-f) resolve as renewable curtailment. Both
    consequences draw on the same effective capacity relief, so there is no
    separate allocation step and no double-counting between the two benefit
    streams.

        B_cong = H * f * min(delta_C_eff, X) * gamma_cong
        B_curt = H * (1-f) * min(delta_C_eff, X) * gamma_curt

    Args:
        project_type: "greenfield" | "reconductoring" | "rebuild"
        capacity_mw: New line capacity in MW (for greenfield) or upgraded capacity (for reconductoring)
        old_capacity_mw: Original capacity in MW (used for reconductoring and rebuild projects)
        flow_factor: Fraction of capacity that effectively relieves constraints (greenfield only)
        constrained_hours: H, hours per year the constraint binds
        average_exceedance: X, average MW exceedance during constrained hours
        congestion_fraction: f, fraction of constrained hours resolved via redispatch (0-1)
        average_congestion_price: gamma_cong, $/MWh redispatch cost
        average_curtailment_price: gamma_curt, $/MWh foregone energy value
        project_lifetime: Project operational lifetime in years
        delay_years: Number of years of project delay before construction
        construction_years: Number of years of construction
        wacc_real: Real weighted average cost of capital (discount rate)
        benefit_price_escalation_real: Real annual growth rate for benefit prices (decimal, default 0.0)

    Returns:
        CongestionReductionResults: Dataclass containing all congestion and curtailment reduction results
    """
    g = benefit_price_escalation_real

    # Effective capacity relief
    if project_type == "greenfield":
        delta_C_eff = max(0.0, flow_factor * capacity_mw)
    else:
        delta_C_eff = max(0.0, capacity_mw - old_capacity_mw)

    H = max(0.0, float(constrained_hours))
    X = max(0.0, float(average_exceedance))
    f = max(0.0, min(1.0, float(congestion_fraction)))

    # Core equations
    relief_mw = min(delta_C_eff, X)
    annual_congestion_benefit = H * f * relief_mw * average_congestion_price
    annual_curtailment_benefit = H * (1 - f) * relief_mw * average_curtailment_price
    annual_remedial_benefit = annual_congestion_benefit + annual_curtailment_benefit

    # Lifetime (nominal growing series) and PV (growing annuity)
    cod_year = calculate_cod_year(delay_years, construction_years)

    lifetime_congestion_benefit = calculate_nominal_growing_series(
        annual_congestion_benefit, g, project_lifetime
    )
    lifetime_congestion_benefit_pv = calculate_growing_annuity_pv(
        annual_congestion_benefit, g, wacc_real, project_lifetime,
        delay_years=delay_years, construction_years=construction_years,
    )

    lifetime_curtailment_benefit = calculate_nominal_growing_series(
        annual_curtailment_benefit, g, project_lifetime
    )
    lifetime_curtailment_benefit_pv = calculate_growing_annuity_pv(
        annual_curtailment_benefit, g, wacc_real, project_lifetime,
        delay_years=delay_years, construction_years=construction_years,
    )

    lifetime_remedial_benefit_pv = (
        lifetime_congestion_benefit_pv + lifetime_curtailment_benefit_pv
    )

    # Delay opportunity costs — delay period starts at year 1 (no additional delay shift)
    delay_construction_years = delay_years + construction_years
    congestion_delay_cost_nominal = calculate_nominal_growing_series(
        annual_congestion_benefit, g, delay_construction_years
    )
    congestion_delay_cost_pv = calculate_growing_annuity_pv(
        annual_congestion_benefit, g, wacc_real, delay_construction_years,
    )
    curtailment_delay_cost_nominal = calculate_nominal_growing_series(
        annual_curtailment_benefit, g, delay_construction_years
    )
    curtailment_delay_cost_pv = calculate_growing_annuity_pv(
        annual_curtailment_benefit, g, wacc_real, delay_construction_years,
    )

    return CongestionReductionResults(
        effective_capacity_relief=delta_C_eff,
        constrained_hours=H,
        average_exceedance=X,
        congestion_fraction=f,
        relief_mw=relief_mw,
        annual_congestion_benefit=annual_congestion_benefit,
        lifetime_congestion_benefit=lifetime_congestion_benefit,
        lifetime_congestion_benefit_pv=lifetime_congestion_benefit_pv,
        annual_curtailment_benefit=annual_curtailment_benefit,
        lifetime_curtailment_benefit=lifetime_curtailment_benefit,
        lifetime_curtailment_benefit_pv=lifetime_curtailment_benefit_pv,
        annual_remedial_benefit=annual_remedial_benefit,
        lifetime_remedial_benefit_pv=lifetime_remedial_benefit_pv,
        congestion_delay_cost_nominal=congestion_delay_cost_nominal,
        congestion_delay_cost_pv=congestion_delay_cost_pv,
        curtailment_delay_cost_nominal=curtailment_delay_cost_nominal,
        curtailment_delay_cost_pv=curtailment_delay_cost_pv,
    )


def main() -> None:
    """
    Main function to calculate and display congestion reduction costs.
    """
    # Load all required data
    project_details_cc = load_project_technical_details()

    # Load financing details
    financing = load_financing_details()

    # Load congestion and curtailment reduction parameters (merged)
    params = load_congestion_curtailment_reductions()

    # Calculate congestion reduction costs
    congestion_results = calculate_congestion_reduction_costs(
        project_details_cc.project_type,
        project_details_cc.capacity_mw,
        project_details_cc.old_capacity_mw,
        params.flow_factor,
        params.constrained_hours,
        params.average_exceedance,
        params.congestion_fraction,
        params.average_congestion_price,
        params.average_curtailment_price,
        project_details_cc.project_lifetime,
        project_details_cc.delay_years,
        project_details_cc.construction_years,
        financing.wacc_real,
        params.benefit_price_escalation_real,
    )

    print("=" * 60)
    print("CONGESTION/CURTAILMENT PHYSICAL RESULTS AND QUANTITIES")
    print("=" * 60)
    print(
        f"Effective capacity relief: {congestion_results.effective_capacity_relief:,.2f} MW"
    )
    print(f"Constrained hours: {congestion_results.constrained_hours:,.0f} hrs/yr")
    print(f"Average exceedance: {congestion_results.average_exceedance:,.2f} MW")
    print(f"Congestion fraction (f): {congestion_results.congestion_fraction:.3f}")
    print(f"Relief MW (min of relief and exceedance): {congestion_results.relief_mw:,.2f} MW")

    print()
    print("=" * 60)
    print("CONGESTION REDUCTION BENEFIT RESULTS")
    print("=" * 60)
    print(f"Annual congestion benefit: ${congestion_results.annual_congestion_benefit:,.2f}")
    print(
        f"Lifetime congestion benefit: ${congestion_results.lifetime_congestion_benefit:,.2f}"
    )
    print(
        f"PRESENT VALUE (discounted to base year ({financing.base_year}) using real WACC ({financing.wacc_real:.2%})):"
    )
    print(
        f"Lifetime congestion benefit PV: ${congestion_results.lifetime_congestion_benefit_pv:,.2f}"
    )

    print()
    print("=" * 60)
    print("CURTAILMENT REDUCTION BENEFIT RESULTS")
    print("=" * 60)
    print(
        f"Annual curtailment benefit: ${congestion_results.annual_curtailment_benefit:,.2f}"
    )
    print(
        f"Lifetime curtailment benefit: ${congestion_results.lifetime_curtailment_benefit:,.2f}"
    )
    print(
        f"PRESENT VALUE (discounted to base year ({financing.base_year}) using real WACC ({financing.wacc_real:.2%})):"
    )
    print(
        f"Lifetime curtailment benefit PV: ${congestion_results.lifetime_curtailment_benefit_pv:,.2f}"
    )

    print()
    print("=" * 60)
    print("TOTAL REMEDIAL BENEFIT (CONGESTION + CURTAILMENT)")
    print("=" * 60)
    print(f"Annual remedial benefit: ${congestion_results.annual_remedial_benefit:,.2f}")
    print(
        f"Lifetime remedial benefit PV: ${congestion_results.lifetime_remedial_benefit_pv:,.2f}"
    )

    print()
    print("=" * 60)
    print("DELAY/CONSTRUCTION OPPORTUNITY COSTS")
    print("=" * 60)
    print(
        f"Congestion delay cost (nominal): ${congestion_results.congestion_delay_cost_nominal:,.2f}"
    )
    print(
        f"Congestion delay cost (PV): ${congestion_results.congestion_delay_cost_pv:,.2f}"
    )
    print(
        f"Curtailment delay cost (nominal): ${congestion_results.curtailment_delay_cost_nominal:,.2f}"
    )
    print(
        f"Curtailment delay cost (PV): ${congestion_results.curtailment_delay_cost_pv:,.2f}"
    )
    print("=" * 60)

    # ========================================================================
    # Benefit of delivered energy
    # ========================================================================
    # E_delivered_annual = Delta_C_effective * u * H; B_delivered_annual = E * gamma_electricity;
    # Nominal lifetime = B_annual * T_lifetime; PV from COD at real WACC.
    project_data = get_project_data_raw()
    project = project_data["project"]
    line_utilization = float(project["line_utilization"])
    value_of_load_per_mwh = float(
        project.get("value_of_load_per_mwh", 0.0)
    )
    delta_c_effective = congestion_results.effective_capacity_relief
    energy_delivered_annual_mwh_yr = (
        delta_c_effective * line_utilization * HOURS_PER_YEAR
    )
    delivered_benefit_annual = (
        energy_delivered_annual_mwh_yr * value_of_load_per_mwh
    )
    delivered_benefit_nominal = calculate_nominal_growing_series(
        delivered_benefit_annual,
        params.benefit_price_escalation_real,
        project_details_cc.project_lifetime,
    )
    cod_year = calculate_cod_year(
        project_details_cc.delay_years, project_details_cc.construction_years
    )
    delivered_benefit_pv = calculate_growing_annuity_pv(
        delivered_benefit_annual,
        params.benefit_price_escalation_real,
        financing.wacc_real,
        project_details_cc.project_lifetime,
        delay_years=project_details_cc.delay_years,
        construction_years=project_details_cc.construction_years,
    )

    print()
    print("=" * 60)
    print("BENEFIT OF DELIVERED ENERGY")
    print("=" * 60)
    print(
        f"Energy delivered (annual): {energy_delivered_annual_mwh_yr:,.2f} MWh/yr"
    )
    print(f"Annual benefit: ${delivered_benefit_annual:,.2f}")
    print(f"Lifetime benefit (nominal): ${delivered_benefit_nominal:,.2f}")
    print(f"Lifetime benefit (PV): ${delivered_benefit_pv:,.2f}")
    print("=" * 60)

    # ========================================================================
    # CSV OUTPUT - Write results to batch summary and detail CSV
    # ========================================================================

    # Initialize CSV output manager
    csv_manager = CTCCOutputManager()

    # Prepare results dictionary with all calculated values
    results = {
        # BENEFITS - Congestion reduction (operational benefits)
        "congestion_benefit_annual": congestion_results.annual_congestion_benefit,
        "congestion_benefit_nominal": congestion_results.lifetime_congestion_benefit,
        "congestion_benefit_pv": congestion_results.lifetime_congestion_benefit_pv,
        # BENEFITS - Curtailment reduction (operational benefits)
        "curtailment_benefit_annual": congestion_results.annual_curtailment_benefit,
        "curtailment_benefit_nominal": congestion_results.lifetime_curtailment_benefit,
        "curtailment_benefit_pv": congestion_results.lifetime_curtailment_benefit_pv,
        # BENEFITS - Delivered energy (throughput value at value of load)
        "delivered_benefit_annual": delivered_benefit_annual,
        "delivered_benefit_nominal": delivered_benefit_nominal,
        "delivered_benefit_pv": delivered_benefit_pv,
        "energy_delivered_annual_mwh_yr": energy_delivered_annual_mwh_yr,
        # COSTS - Delay/construction opportunity costs
        "congestion_delay_cost_nominal": congestion_results.congestion_delay_cost_nominal,
        "congestion_delay_cost_pv": congestion_results.congestion_delay_cost_pv,
        "curtailment_delay_cost_nominal": congestion_results.curtailment_delay_cost_nominal,
        "curtailment_delay_cost_pv": congestion_results.curtailment_delay_cost_pv,
        # Physical metrics (for reference)
        "effective_capacity_relief_mw": congestion_results.effective_capacity_relief,
        "congestion_fraction": congestion_results.congestion_fraction,
        "constrained_hours": congestion_results.constrained_hours,
        "relief_mw": congestion_results.relief_mw,
    }

    # ========================================================================
    # Capacity value benefit
    # ========================================================================
    from path_config import YAMLS_DIR
    cap_yaml_path = YAMLS_DIR / "20_capacity_value.yaml"
    cap_params: dict = {}
    if cap_yaml_path.exists():
        with open(cap_yaml_path) as _f:
            cap_params = yaml.safe_load(_f) or {}

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

    results["capacity_value_annual"] = cap_results["capacity_value_annual"]
    results["capacity_value_nominal"] = cap_results["capacity_value_nominal"]
    results["capacity_value_pv"] = cap_results["capacity_value_pv"]

    print()
    print("=" * 60)
    print("CAPACITY VALUE BENEFIT")
    print("=" * 60)
    print(f"Annual capacity value: ${cap_results['capacity_value_annual']:,.2f}")
    print(f"Lifetime capacity value (nominal): ${cap_results['capacity_value_nominal']:,.2f}")
    print(f"Lifetime capacity value (PV): ${cap_results['capacity_value_pv']:,.2f}")
    print("=" * 60)

    from run_context import add_derived
    add_derived({
        "effective_capacity_relief": congestion_results.effective_capacity_relief,
        "energy_delivered_annual_mwh_yr": energy_delivered_annual_mwh_yr,
    })

    # Write to CSV/JSON
    csv_manager.add_congestion_curtailment(results)
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

    Returns dict with capacity_value_annual, capacity_value_nominal,
    and capacity_value_pv.
    """
    g = benefit_price_escalation_real

    if not applicability_gate or capacity_credit <= 0 or capacity_price <= 0:
        return {
            "capacity_value_annual": 0.0,
            "capacity_value_nominal": 0.0,
            "capacity_value_pv": 0.0,
        }

    annual = delta_c_effective * capacity_credit * capacity_price

    nominal = calculate_nominal_growing_series(annual, g, project_lifetime)

    pv = calculate_growing_annuity_pv(
        annual, g, wacc_real, project_lifetime,
        delay_years=delay_years,
        construction_years=construction_years,
    )

    return {
        "capacity_value_annual": annual,
        "capacity_value_nominal": nominal,
        "capacity_value_pv": pv,
    }


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        raise
