# Author: Andrew Igdal
# Date: 2025-10-24
# Description: This script calculates the congestion reduction costs for a transmission line project.
#              It computes the congestion reduction costs for a transmission line over the project lifetime.

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
from constants import MIN_DISCOUNT_RATE
from financial_utils import calculate_present_value, calculate_cod_year
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
    reconductoring: bool
    capacity_mw: int
    old_capacity_mw: int


@dataclass
class CongestionReductionResults:
    """Results from congestion and curtailment reduction cost calculations."""
    # Congestion lifetime values
    lifetime_congestion_reduction_cost: float
    lifetime_congestion_reduction_cost_haircut: float
    lifetime_residual_exceedance_cost: float
    lifetime_congestion_reduction_cost_pv: float
    lifetime_congestion_reduction_cost_haircut_pv: float
    lifetime_residual_exceedance_cost_pv: float
    # Congestion annual values
    annual_congestion_reduction_cost_raw: float
    annual_residual_exceedance_cost: float
    # Capacity and energy metrics
    effective_capacity_relief: float
    energy_congestion_reduction: float
    energy_residual_exceedance: float
    E_near: float
    # Delay/construction costs
    lifetime_congestion_during_delay_and_construction_cost: float
    lifetime_congestion_during_delay_and_construction_pv: float
    # Curtailment values
    E_curt: float
    annual_curtailment_benefit: float
    annual_curtailment_benefit_haircut: float
    lifetime_curtailment_benefit: float
    lifetime_curtailment_benefit_pv: float
    lifetime_curtailment_benefit_haircut: float
    lifetime_curtailment_benefit_haircut_pv: float
    lifetime_curtailment_during_delay_and_construction_cost: float
    lifetime_curtailment_during_delay_and_construction_pv: float
    # Allocation metrics
    theta_overlap: float
    H_bc: float
    H_bnon: float
    ΔC_rem: float


def _get_old_capacity_mw() -> int:
    """
    Helper function to get old_capacity_mw from project technical details.
    This is needed because the centralized loader doesn't return this field.
    """
    project_data = get_project_data_raw()
    return project_data["project"].get("old_capacity_mw", 0)


def load_project_technical_details() -> CongestionProjectDetails:
    """
    Load project technical details using centralized loaders.

    This function wraps the centralized loader and extracts only the fields
    needed for congestion/curtailment calculations.

    Returns:
        CongestionProjectDetails: Project technical details dataclass
    """
    from yaml_loaders import ProjectTechnicalDetails
    project_details: ProjectTechnicalDetails = load_project_technical_details_centralized()

    # Get old_capacity_mw separately (not in centralized loader return)
    old_capacity_mw = _get_old_capacity_mw()

    return CongestionProjectDetails(
        delay_years=project_details.delay_years,
        construction_years=project_details.construction_years,
        project_lifetime=project_details.project_lifetime,
        reconductoring=project_details.reconductoring,
        capacity_mw=project_details.capacity_mw,
        old_capacity_mw=old_capacity_mw,
    )


# load_financing_details is now imported from smart_loaders
# calculate_present_value is now imported from financial_utils


def allocate_curtailment_then_congestion(
    ΔC_eff_mw: float,
    # binding inputs
    binding_hours_total: float,
    average_exceedance_mw: float,
    # curtailment inputs
    curtailment_hours_total: float,
    average_curtailment_mw: float,
    average_curtailment_price: float,
) -> Dict[str, float]:
    """
    Allocate effective capacity relief between curtailment and congestion to avoid double-counting.

    This function prevents double-counting of benefits when the same capacity relief addresses
    both curtailment and congestion constraints. It first allocates capacity to curtailment relief,
    then allocates remaining capacity to congestion relief, accounting for temporal overlap
    between binding hours (congestion) and curtailment hours.

    Algorithm:
    1. Calculate curtailment relief energy and benefit using available capacity
    2. Determine temporal overlap (theta) between binding and curtailment hours
    3. Split binding hours into overlap (H_bc) and non-overlap (H_bnon) periods
    4. Calculate capacity consumed by curtailment in overlap hours
    5. Return remaining capacity for congestion relief allocation

    Args:
        ΔC_eff_mw: Effective capacity relief in MW (available to address constraints)
        binding_hours_total: Total hours per year when transmission constraints are binding
        average_exceedance_mw: Average MW by which constraints are exceeded during binding hours
        curtailment_hours_total: Total hours per year with curtailment events
        average_curtailment_mw: Average MW curtailed per curtailment event
        average_curtailment_price: Average price of curtailment in $/MWh

    Returns:
        dict: Allocation results with the following keys:
            - "E_curt_mwh_yr": Curtailment relief energy in MWh per year
            - "curtailment_benefit_$_yr": Annual curtailment benefit in $ per year
            - "theta_overlap": Temporal overlap fraction between binding and curtailment hours (0-1)
            - "H_bc": Binding hours that overlap with curtailment hours
            - "H_bnon": Binding hours that don't overlap with curtailment hours
            - "ΔC_used_bc_mw": Capacity consumed by curtailment in overlap hours (MW)
            - "ΔC_remain_bc_mw": Remaining capacity available for congestion relief after curtailment (MW)
    """
    Hb = max(0.0, float(binding_hours_total))
    X = max(0.0, float(average_exceedance_mw))
    Hc = max(0.0, float(curtailment_hours_total))
    ΔC = max(0.0, float(ΔC_eff_mw))
    Cc = max(0.0, float(average_curtailment_mw))
    λc = max(0.0, float(average_curtailment_price))

    # Curtailment relief (MWh/yr); if Hc==0 or Cc==0, this is zero.
    E_curt = Hc * min(ΔC, Cc)
    curt_benefit = E_curt * λc

    if Hb <= 0:
        # No binding hours; nothing to value under congestion.
        return {
            "E_curt_mwh_yr": E_curt,
            "curtailment_benefit_$_yr": curt_benefit,
            "theta_overlap": 0.0,
            "H_bc": 0.0,
            "H_bnon": 0.0,
            "ΔC_used_bc_mw": 0.0,
            "ΔC_remain_bc_mw": ΔC,
        }

    # Overlap proxy between binding and curtailment time
    theta = min(1.0, Hc / Hb) if Hc > 0 else 0.0
    H_bc = theta * Hb
    H_bnon = (1.0 - theta) * Hb

    # Headroom consumed by curtailment in overlap hours (MW basis)
    ΔC_used_bc = min(ΔC, Cc)
    ΔC_remain_bc = max(0.0, ΔC - ΔC_used_bc)

    return {
        "E_curt_mwh_yr": E_curt,
        "curtailment_benefit_$_yr": curt_benefit,
        "theta_overlap": theta,
        "H_bc": H_bc,
        "H_bnon": H_bnon,
        "ΔC_used_bc_mw": ΔC_used_bc,
        "ΔC_remain_bc_mw": ΔC_remain_bc,
    }


def calculate_congestion_reduction_costs(
    reconductoring: bool,
    capacity_mw: int,
    old_capacity_mw: int,
    flow_factor: float,
    binding_hours: int,
    average_exceedance: int,
    near_binding_hours: int,
    near_average_exceedance: int,
    near_binding_relief_factor: float,
    saturation_factor: float,
    average_congestion_price: float,
    residual_exceedance_value: float | None,
    project_lifetime: int,
    delay_years: int,
    construction_years: int,
    wacc_real: float,
    curtailment_hours_total: float,
    average_curtailment_mw: float,
    average_curtailment_price: float,
    curtailment_saturation_factor: float,
) -> CongestionReductionResults:
    """
    Calculate congestion and curtailment reduction benefits and costs for a transmission project.

    This function computes the economic benefits from reducing transmission constraints (congestion
    and curtailment) and the costs of residual constraints. It handles both greenfield and
    reconductoring projects, allocates capacity relief between curtailment and congestion to
    avoid double-counting, and calculates both full-value and conservative (haircut) estimates.

    The algorithm:
    1. Calculates effective capacity relief (greenfield: flow_factor * capacity; reconductoring: capacity - old_capacity)
    2. Allocates capacity relief between curtailment and congestion using allocate_curtailment_then_congestion()
    3. Calculates congestion reduction energy (MWh/yr) for binding hours, near-binding hours, and residual
    4. Applies saturation factors to monetized values (conservative estimates)
    5. Calculates present values using real WACC, starting after construction completion
    6. Calculates opportunity costs during delay/construction periods

    Args:
        reconductoring: True if this is a reconductoring project, False for greenfield
        capacity_mw: New line capacity in MW (for greenfield) or upgraded capacity (for reconductoring)
        old_capacity_mw: Original capacity in MW (only used for reconductoring projects)
        flow_factor: Fraction of capacity that effectively relieves constraints (greenfield only)
        binding_hours: Number of hours per year when transmission constraints are binding
        average_exceedance: Average MW by which constraints are exceeded during binding hours
        near_binding_hours: Number of hours per year when constraints are near-binding
        near_average_exceedance: Average MW exceedance during near-binding hours
        near_binding_relief_factor: Fraction of capacity relief applied to near-binding hours (0-1)
        saturation_factor: Conservative multiplier for congestion benefits (0-1, where 1 = no haircut)
        average_congestion_price: Average price of congestion in $/MWh
        residual_exceedance_value: Price per MWh for residual exceedance ($/MWh, None = use average_congestion_price)
        project_lifetime: Project operational lifetime in years
        delay_years: Number of years of project delay before construction
        construction_years: Number of years of construction
        wacc_real: Real weighted average cost of capital (discount rate)
        curtailment_hours_total: Total hours per year with curtailment events
        average_curtailment_mw: Average MW curtailed per curtailment event
        average_curtailment_price: Average price of curtailment in $/MWh
        curtailment_saturation_factor: Conservative multiplier for curtailment benefits (0-1)

    Returns:
        CongestionReductionResults: Dataclass containing all congestion and curtailment reduction results
            - lifetime_congestion_reduction_cost: Nominal lifetime congestion reduction benefit ($)
            - lifetime_congestion_reduction_cost_haircut: Conservative lifetime congestion benefit ($)
            - lifetime_residual_exceedance_cost: Nominal lifetime residual exceedance cost ($)
            - lifetime_congestion_reduction_cost_pv: PV of congestion reduction benefit ($)
            - lifetime_congestion_reduction_cost_haircut_pv: PV of conservative congestion benefit ($)
            - lifetime_residual_exceedance_cost_pv: PV of residual exceedance cost ($)
            - annual_congestion_reduction_cost_raw: Annual congestion reduction benefit ($/yr)
            - annual_residual_exceedance_cost: Annual residual exceedance cost ($/yr)
            - effective_capacity_relief: Effective capacity relief in MW
            - energy_congestion_reduction: Total congestion reduction energy (MWh/yr)
            - energy_residual_exceedance: Residual exceedance energy (MWh/yr)
            - E_near: Near-binding congestion reduction energy (MWh/yr)
            - lifetime_congestion_during_delay_and_construction_cost: Nominal congestion cost during delay/construction ($)
            - lifetime_congestion_during_delay_and_construction_pv: PV of congestion cost during delay/construction ($)
            - E_curt: Curtailment reduction energy (MWh/yr)
            - annual_curtailment_benefit: Annual curtailment reduction benefit ($/yr)
            - annual_curtailment_benefit_haircut: Conservative annual curtailment benefit ($/yr)
            - lifetime_curtailment_benefit: Nominal lifetime curtailment benefit ($)
            - lifetime_curtailment_benefit_pv: PV of curtailment benefit ($)
            - lifetime_curtailment_benefit_haircut: Conservative lifetime curtailment benefit ($)
            - lifetime_curtailment_benefit_haircut_pv: PV of conservative curtailment benefit ($)
            - lifetime_curtailment_during_delay_and_construction_cost: Nominal curtailment cost during delay/construction ($)
            - lifetime_curtailment_during_delay_and_construction_pv: PV of curtailment cost during delay/construction ($)
            - theta_overlap: Overlap fraction between binding and curtailment hours (0-1)
            - H_bc: Binding hours that overlap with curtailment hours
            - H_bnon: Binding hours that don't overlap with curtailment hours
            - ΔC_rem: Remaining capacity relief after curtailment allocation (MW)
    """
    if reconductoring == False:
        effective_capacity_relief = max(0, flow_factor * capacity_mw)
    else:
        effective_capacity_relief = max(0, capacity_mw - old_capacity_mw)

    # Allocate capacity relief between curtailment and congestion
    alloc = allocate_curtailment_then_congestion(
        ΔC_eff_mw=effective_capacity_relief,
        binding_hours_total=binding_hours,
        average_exceedance_mw=average_exceedance,
        curtailment_hours_total=curtailment_hours_total,
        average_curtailment_mw=average_curtailment_mw,
        average_curtailment_price=average_curtailment_price,
    )

    # Curtailment results
    E_curt = alloc["E_curt_mwh_yr"]
    annual_curtailment_benefit = alloc["curtailment_benefit_$_yr"]

    # Congestion split with no double counting
    H_bc = alloc["H_bc"]
    H_bnon = alloc["H_bnon"]
    ΔC_rem = alloc["ΔC_remain_bc_mw"]

    # Congestion relief energy (MWh/yr) on overlap & non-overlap binding hours
    E_cong_bc = H_bc * min(ΔC_rem, average_exceedance)
    E_cong_non = H_bnon * min(effective_capacity_relief, average_exceedance)

    # Near-binding add (unchanged)
    k = max(0.0, min(1.0, near_binding_relief_factor))
    near_hours = max(0.0, near_binding_hours)
    E_near = k * near_hours * effective_capacity_relief  #  MWh/yr

    # Total congestion energy
    energy_congestion_reduction = E_cong_bc + E_cong_non + E_near

    # Monetize congestion ($/yr) — apply saturation haircut to $ only
    annual_congestion_reduction_cost_raw = (
        energy_congestion_reduction * average_congestion_price
    )
    annual_congestion_reduction_cost_haircut = (
        1 - saturation_factor
    ) * annual_congestion_reduction_cost_raw

    # Residual exceedance energy (MWh/yr) on binding hours
    # Residual uses physical capacity relief for ALL binding hours, regardless of allocation
    total_binding_hours = H_bc + H_bnon
    residual_exceedance_per_hour = max(0.0, average_exceedance - effective_capacity_relief)
    energy_residual_exceedance = total_binding_hours * residual_exceedance_per_hour

    # Use residual_exceedance_value (default to average_congestion_price if None)
    residual_exceedance_value_used = residual_exceedance_value if residual_exceedance_value is not None else average_congestion_price
    annual_residual_exceedance_cost = energy_residual_exceedance * residual_exceedance_value_used

    # Apply curtailment saturation factor
    annual_curtailment_benefit_haircut = (
        1 - curtailment_saturation_factor
    ) * annual_curtailment_benefit

    total_annual_congestion_reduction_cost = annual_congestion_reduction_cost_raw
    total_annual_congestion_reduction_cost_haircut = (
        annual_congestion_reduction_cost_haircut
    )

    lifetime_congestion_reduction_cost = (
        total_annual_congestion_reduction_cost * project_lifetime
    )
    lifetime_congestion_reduction_cost_pv = calculate_present_value(
        total_annual_congestion_reduction_cost,
        wacc_real,
        project_lifetime,
        start_year=calculate_cod_year(delay_years, construction_years),
    )

    lifetime_congestion_reduction_cost_haircut = (
        total_annual_congestion_reduction_cost_haircut * project_lifetime
    )
    lifetime_congestion_reduction_cost_haircut_pv = calculate_present_value(
        total_annual_congestion_reduction_cost_haircut,
        wacc_real,
        project_lifetime,
        start_year=calculate_cod_year(delay_years, construction_years),
    )

    lifetime_residual_exceedance_cost = (
        annual_residual_exceedance_cost * project_lifetime
    )
    lifetime_residual_exceedance_cost_pv = calculate_present_value(
        annual_residual_exceedance_cost,
        wacc_real,
        project_lifetime,
        start_year=calculate_cod_year(delay_years, construction_years),
    )

    # Delay/construction opportunity costs should mirror allocated relief
    # to avoid double-counting when congestion and curtailment overlap.
    annual_congestion_during_delay_and_construction_cost = (
        annual_congestion_reduction_cost_raw
    )

    lifetime_congestion_during_delay_and_construction_cost = (
        annual_congestion_during_delay_and_construction_cost
        * (delay_years + construction_years)
    )
    lifetime_congestion_during_delay_and_construction_pv = calculate_present_value(
        annual_congestion_during_delay_and_construction_cost,
        wacc_real,
        delay_years + construction_years,
        start_year=1,
    )

    # Curtailment lifetime calculations
    lifetime_curtailment_benefit = annual_curtailment_benefit * project_lifetime
    lifetime_curtailment_benefit_pv = calculate_present_value(
        annual_curtailment_benefit,
        wacc_real,
        project_lifetime,
        start_year=calculate_cod_year(delay_years, construction_years),
    )

    lifetime_curtailment_benefit_haircut = (
        annual_curtailment_benefit_haircut * project_lifetime
    )
    lifetime_curtailment_benefit_haircut_pv = calculate_present_value(
        annual_curtailment_benefit_haircut,
        wacc_real,
        project_lifetime,
        start_year=calculate_cod_year(delay_years, construction_years),
    )

    # Curtailment costs during delay period (allocated, curtailment-first)
    annual_curtailment_during_delay_and_construction_cost = annual_curtailment_benefit

    lifetime_curtailment_during_delay_and_construction_cost = (
        annual_curtailment_during_delay_and_construction_cost
        * (delay_years + construction_years)
    )
    lifetime_curtailment_during_delay_and_construction_pv = calculate_present_value(
        annual_curtailment_during_delay_and_construction_cost,
        wacc_real,
        delay_years + construction_years,
        start_year=1,
    )

    return CongestionReductionResults(
        lifetime_congestion_reduction_cost=lifetime_congestion_reduction_cost,
        lifetime_congestion_reduction_cost_haircut=lifetime_congestion_reduction_cost_haircut,
        lifetime_residual_exceedance_cost=lifetime_residual_exceedance_cost,
        lifetime_congestion_reduction_cost_pv=lifetime_congestion_reduction_cost_pv,
        lifetime_congestion_reduction_cost_haircut_pv=lifetime_congestion_reduction_cost_haircut_pv,
        lifetime_residual_exceedance_cost_pv=lifetime_residual_exceedance_cost_pv,
        annual_congestion_reduction_cost_raw=annual_congestion_reduction_cost_raw,
        annual_residual_exceedance_cost=annual_residual_exceedance_cost,
        effective_capacity_relief=effective_capacity_relief,
        energy_congestion_reduction=energy_congestion_reduction,
        energy_residual_exceedance=energy_residual_exceedance,
        E_near=E_near,
        lifetime_congestion_during_delay_and_construction_cost=lifetime_congestion_during_delay_and_construction_cost,
        lifetime_congestion_during_delay_and_construction_pv=lifetime_congestion_during_delay_and_construction_pv,
        E_curt=E_curt,
        annual_curtailment_benefit=annual_curtailment_benefit,
        annual_curtailment_benefit_haircut=annual_curtailment_benefit_haircut,
        lifetime_curtailment_benefit=lifetime_curtailment_benefit,
        lifetime_curtailment_benefit_pv=lifetime_curtailment_benefit_pv,
        lifetime_curtailment_benefit_haircut=lifetime_curtailment_benefit_haircut,
        lifetime_curtailment_benefit_haircut_pv=lifetime_curtailment_benefit_haircut_pv,
        lifetime_curtailment_during_delay_and_construction_cost=lifetime_curtailment_during_delay_and_construction_cost,
        lifetime_curtailment_during_delay_and_construction_pv=lifetime_curtailment_during_delay_and_construction_pv,
        theta_overlap=alloc["theta_overlap"],
        H_bc=H_bc,
        H_bnon=H_bnon,
        ΔC_rem=ΔC_rem,
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
        project_details_cc.reconductoring,
        project_details_cc.capacity_mw,
        project_details_cc.old_capacity_mw,
        params.flow_factor,
        params.binding_hours,
        params.average_exceedance,
        params.near_binding_hours,
        params.near_average_exceedance,
        params.near_binding_relief_factor,
        params.saturation_factor,
        params.average_congestion_price,
        params.residual_exceedance_value,
        project_details_cc.project_lifetime,
        project_details_cc.delay_years,
        project_details_cc.construction_years,
        financing.wacc_real,
        params.curtailment_hours_total,
        params.average_curtailment_mw,
        params.average_curtailment_price,
        params.curtailment_saturation_factor,
    )

    print("=" * 60)
    print("CONGESTION ENERGY REDUCTION RELIEF PHYSICAL RESULTS AND QUANTITIES")
    print("=" * 60)
    print(f"Effective capacity relief: {congestion_results.effective_capacity_relief:,.2f} MW")
    print(f"Energy congestion reduction: {congestion_results.energy_congestion_reduction:,.2f} MWh/yr")
    print(f"Energy residual exceedance: {congestion_results.energy_residual_exceedance:,.2f} MWh/yr")
    print(f"E_near: {congestion_results.E_near:,.2f} MWh/yr")

    print()
    print("=" * 60)
    print("CONGESTION DURING DELAY AND CONSTRUCTION RESULTS AND QUANTITIES")
    print("=" * 60)

    print(
        f"Lifetime congestion during delay and construction cost: ${congestion_results.lifetime_congestion_during_delay_and_construction_cost:,.2f}"
    )
    print(
        f"Lifetime congestion during delay and construction PV: ${congestion_results.lifetime_congestion_during_delay_and_construction_pv:,.2f}"
    )

    print()
    print("=" * 60)
    print("CURTAILMENT REDUCTION RESULTS AND QUANTITIES")
    print("=" * 60)
    print(f"Curtailment energy reduction: {congestion_results.E_curt:,.2f} MWh/yr")
    print(f"Annual curtailment benefit: ${congestion_results.annual_curtailment_benefit:,.2f}")
    print(
        f"Annual curtailment benefit haircut: ${congestion_results.annual_curtailment_benefit_haircut:,.2f}"
    )
    print(f"Overlap factor (theta): {congestion_results.theta_overlap:.3f}")
    print(f"Binding hours (overlap): {congestion_results.H_bc:,.0f} hrs/yr")
    print(f"Binding hours (non-overlap): {congestion_results.H_bnon:,.0f} hrs/yr")
    print(f"Remaining capacity for congestion: {congestion_results.ΔC_rem:,.2f} MW")

    print()
    print("=" * 60)
    print("CURTAILMENT DURING DELAY AND CONSTRUCTION RESULTS")
    print("=" * 60)
    print(
        f"Lifetime curtailment during delay and construction cost: ${congestion_results.lifetime_curtailment_during_delay_and_construction_cost:,.2f}"
    )
    print(
        f"Lifetime curtailment during delay and construction PV: ${congestion_results.lifetime_curtailment_during_delay_and_construction_pv:,.2f}"
    )

    print()
    print("=" * 60)
    print("CURTAILMENT REDUCTION COST CALCULATION RESULTS")
    print("=" * 60)
    print(f"Lifetime curtailment benefit: ${congestion_results.lifetime_curtailment_benefit:,.2f}")
    print(
        f"Lifetime curtailment benefit haircut: ${congestion_results.lifetime_curtailment_benefit_haircut:,.2f}"
    )

    print()
    print(
        f"PRESENT VALUES (discounted to base year ({financing.base_year}) using real WACC ({financing.wacc_real:.2%})):"
    )
    print(f"Lifetime curtailment benefit PV: ${congestion_results.lifetime_curtailment_benefit_pv:,.2f}")
    print(
        f"Lifetime curtailment benefit haircut PV: ${congestion_results.lifetime_curtailment_benefit_haircut_pv:,.2f}"
    )

    print()
    print("=" * 60)
    print("CONGESTION REDUCTION COST CALCULATION RESULTS")
    print("=" * 60)
    print(
        f"Lifetime congestion reduction cost: ${congestion_results.lifetime_congestion_reduction_cost:,.2f}"
    )
    print(
        f"Lifetime congestion reduction cost haircut: ${congestion_results.lifetime_congestion_reduction_cost_haircut:,.2f}"
    )
    print(
        f"Lifetime residual exceedance cost: ${congestion_results.lifetime_residual_exceedance_cost:,.2f}"
    )

    print()

    print(
        f"PRESENT VALUES (discounted to base year ({financing.base_year}) using real WACC ({financing.wacc_real:.2%})):"
    )
    print(
        f"Lifetime congestion reduction cost PV: ${congestion_results.lifetime_congestion_reduction_cost_pv:,.2f}"
    )
    print(
        f"Lifetime congestion reduction cost haircut PV: ${congestion_results.lifetime_congestion_reduction_cost_haircut_pv:,.2f}"
    )
    print(
        f"Lifetime residual exceedance cost PV: ${congestion_results.lifetime_residual_exceedance_cost_pv:,.2f}"
    )
    print("=" * 60)

    # ========================================================================
    # CSV OUTPUT - Write results to batch summary and detail CSV
    # ========================================================================

    # Initialize CSV output manager
    csv_manager = CTCCOutputManager()

    # Prepare results dictionary with all calculated values
    results = {
        # BENEFITS - Congestion reduction (operational benefits)
        "congestion_benefit_annual": congestion_results.annual_congestion_reduction_cost_raw,
        "congestion_benefit_nominal": congestion_results.lifetime_congestion_reduction_cost,
        "congestion_benefit_pv": congestion_results.lifetime_congestion_reduction_cost_pv,
        "congestion_benefit_haircut_annual": congestion_results.annual_congestion_reduction_cost_raw
        * (1 - params.saturation_factor),
        "congestion_benefit_haircut_nominal": congestion_results.lifetime_congestion_reduction_cost_haircut,
        "congestion_benefit_haircut_pv": congestion_results.lifetime_congestion_reduction_cost_haircut_pv,
        # BENEFITS - Curtailment reduction (operational benefits)
        "curtailment_benefit_annual": congestion_results.annual_curtailment_benefit,
        "curtailment_benefit_nominal": congestion_results.lifetime_curtailment_benefit,
        "curtailment_benefit_pv": congestion_results.lifetime_curtailment_benefit_pv,
        "curtailment_benefit_haircut_annual": congestion_results.annual_curtailment_benefit_haircut,
        "curtailment_benefit_haircut_nominal": congestion_results.lifetime_curtailment_benefit_haircut,
        "curtailment_benefit_haircut_pv": congestion_results.lifetime_curtailment_benefit_haircut_pv,
        # COSTS - Delay/construction opportunity costs
        "congestion_delay_cost_nominal": congestion_results.lifetime_congestion_during_delay_and_construction_cost,
        "congestion_delay_cost_pv": congestion_results.lifetime_congestion_during_delay_and_construction_pv,
        "curtailment_delay_cost_nominal": congestion_results.lifetime_curtailment_during_delay_and_construction_cost,
        "curtailment_delay_cost_pv": congestion_results.lifetime_curtailment_during_delay_and_construction_pv,
        # COSTS - Residual unrelieved exceedance
        "residual_exceedance_annual": congestion_results.annual_residual_exceedance_cost,
        "residual_exceedance_nominal": congestion_results.lifetime_residual_exceedance_cost,
        "residual_exceedance_pv": congestion_results.lifetime_residual_exceedance_cost_pv,
        # Physical metrics (for reference)
        "effective_capacity_relief_mw": congestion_results.effective_capacity_relief,
        "energy_congestion_reduction_mwh_yr": congestion_results.energy_congestion_reduction,
        "energy_residual_exceedance_mwh_yr": congestion_results.energy_residual_exceedance,
        "energy_curtailment_reduction_mwh_yr": congestion_results.E_curt,
        "theta_overlap": congestion_results.theta_overlap,
        "binding_hours_overlap": congestion_results.H_bc,
        "binding_hours_non_overlap": congestion_results.H_bnon,
        "remaining_capacity_mw": congestion_results.ΔC_rem,
    }

    # Write to CSV/JSON
    csv_manager.add_congestion_curtailment(results)
    csv_manager.write_batch_summary()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        raise
