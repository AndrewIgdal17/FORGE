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
from typing import Dict, Any, Tuple

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from smart_output import CTCCOutputManager
from smart_loaders import (
    load_congestion_reductions,
    load_project_technical_details as load_project_technical_details_centralized,
    load_curtailment_reductions,
    load_financing_details,
    get_input_mode,
)
from path_config import YAMLS_DIR


def _get_old_capacity_mw() -> int:
    """
    Helper function to get old_capacity_mw from project technical details.
    This is needed because the centralized loader doesn't return this field.
    """
    input_mode = get_input_mode()
    if input_mode == "json":
        from json_loaders import _data_source

        project_data = _data_source.get_data("01_project_technical_details")
        return project_data["project"].get("old_capacity_mw", 0)
    else:
        # YAML mode
        with open(YAMLS_DIR / "01_project_technical_details.yaml", "r") as file:
            project_details = yaml.safe_load(file)
        return project_details["project"].get("old_capacity_mw", 0)


def load_project_technical_details() -> Tuple[float, int, int, bool, int, int]:
    """
    Load project technical details using centralized loaders.

    This function wraps the centralized loader and extracts only the fields
    needed for congestion/curtailment calculations.

    Returns:
        tuple: A 6-element tuple containing:
            - delay_years: Number of years of project delay before construction
            - construction_years: Number of years of construction
            - project_lifetime: Project operational lifetime in years
            - reconductoring: True if this is a reconductoring project, False for greenfield
            - capacity_mw: New line capacity in MW
            - old_capacity_mw: Original capacity in MW (for reconductoring projects)
    """
    # Load from centralized loader (returns 11 values)
    # Indices: 0=construction_type, 1=ac_dc, 2=capacity_mw, 3=conductor_type,
    #          4=converter_type, 5=line_utilization, 6=reconductoring,
    #          7=delay_years, 8=construction_years, 9=project_lifetime, 10=converter_loss_percentage
    (
        _construction_type,
        _ac_dc,
        capacity_mw,
        _conductor_type,
        _converter_type,
        _line_utilization,
        reconductoring,
        delay_years,
        construction_years,
        project_lifetime,
        _converter_loss_percentage,
    ) = load_project_technical_details_centralized()

    # Get old_capacity_mw separately (not in centralized loader return)
    old_capacity_mw = _get_old_capacity_mw()

    return (
        delay_years,
        construction_years,
        project_lifetime,
        reconductoring,
        capacity_mw,
        old_capacity_mw,
    )


# load_curtailment_reductions is now imported from smart_loaders


# load_financing_details is now imported from smart_loaders


def calculate_present_value(
    annual_cost: float, wacc_real: float, total_years: float, start_year: int = 1
) -> float:
    """
    Calculate the present value of annual payments over a given time period.

    Args:
        annual_cost (float): Annual cost amount
        wacc_real (float): Real weighted average cost of capital (discount rate)
        total_years (int): Number of years over which payments occur
        start_year (int): Year when payments begin (default: 1)

    Returns:
        float: Present value of the payment stream

    Raises:
        ValueError: If wacc_real <= -0.99 (would cause division by zero)
    """
    # Validate discount rate to prevent division by zero
    if wacc_real <= -0.99:
        raise ValueError(
            f"Invalid wacc_real: {wacc_real}. "
            f"Value must be > -0.99 to prevent division by zero in financial calculations. "
            f"A rate of {wacc_real} would cause (1 + wacc_real) to be <= 0, leading to invalid calculations."
        )

    n_full_years = math.floor(total_years)
    frac = total_years - n_full_years
    total_pv = 0
    for year in range(n_full_years):
        t = start_year + year
        total_pv += annual_cost / (1 + wacc_real) ** t

    if frac > 0:
        t_frac = start_year + n_full_years + frac
        total_pv += annual_cost * frac / (1 + wacc_real) ** t_frac

    return total_pv


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
    project_lifetime: int,
    delay_years: int,
    construction_years: int,
    wacc_real: float,
    curtailment_hours_total: float,
    average_curtailment_mw: float,
    average_curtailment_price: float,
    curtailment_saturation_factor: float,
) -> Dict[str, float]:
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
        project_lifetime: Project operational lifetime in years
        delay_years: Number of years of project delay before construction
        construction_years: Number of years of construction
        wacc_real: Real weighted average cost of capital (discount rate)
        curtailment_hours_total: Total hours per year with curtailment events
        average_curtailment_mw: Average MW curtailed per curtailment event
        average_curtailment_price: Average price of curtailment in $/MWh
        curtailment_saturation_factor: Conservative multiplier for curtailment benefits (0-1)

    Returns:
        tuple: A 25-element tuple containing:
            - lifetime_congestion_reduction_cost: Nominal lifetime congestion reduction benefit ($)
            - lifetime_congestion_reduction_cost_haircut: Conservative lifetime congestion benefit ($)
            - lifetime_congestion_residual_cost: Nominal lifetime residual congestion cost ($)
            - lifetime_congestion_reduction_cost_pv: PV of congestion reduction benefit ($)
            - lifetime_congestion_reduction_cost_haircut_pv: PV of conservative congestion benefit ($)
            - lifetime_congestion_residual_cost_pv: PV of residual congestion cost ($)
            - annual_congestion_reduction_cost_raw: Annual congestion reduction benefit ($/yr)
            - annual_congestion_residual_cost: Annual residual congestion cost ($/yr)
            - effective_capacity_relief: Effective capacity relief in MW
            - energy_congestion_reduction: Total congestion reduction energy (MWh/yr)
            - energy_congestion_residual: Residual congestion energy (MWh/yr)
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
    # #region agent log
    import json, os

    try:
        log_path = "/Users/ai17/Documents/UT Austin/Research/Webber Energy Group/Comprehensive Transmission Cost Calculator/Python Version/.cursor/debug.log"
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        with open(log_path, "a") as f:
            f.write(
                json.dumps(
                    {
                        "id": "log_calc_entry",
                        "timestamp": int(__import__("time").time() * 1000),
                        "location": "congestion_curtailment_reduction.py:569",
                        "message": "calculate_congestion_reduction_costs entry",
                        "data": {
                            "reconductoring": reconductoring,
                            "capacity_mw": capacity_mw,
                            "old_capacity_mw": old_capacity_mw,
                            "binding_hours": binding_hours,
                            "average_exceedance": average_exceedance,
                        },
                        "sessionId": "debug-session",
                        "runId": "run1",
                        "hypothesisId": "D",
                    }
                )
                + "\n"
            )
    except Exception as e:
        pass
    # #endregion
    if reconductoring == False:
        effective_capacity_relief = max(0, flow_factor * capacity_mw)
    else:
        effective_capacity_relief = max(0, capacity_mw - old_capacity_mw)
    # #region agent log
    try:
        log_path = "/Users/ai17/Documents/UT Austin/Research/Webber Energy Group/Comprehensive Transmission Cost Calculator/Python Version/.cursor/debug.log"
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        with open(log_path, "a") as f:
            f.write(
                json.dumps(
                    {
                        "id": "log_effective_capacity",
                        "timestamp": int(__import__("time").time() * 1000),
                        "location": "congestion_curtailment_reduction.py:572",
                        "message": "effective_capacity_relief calculated",
                        "data": {
                            "effective_capacity_relief": effective_capacity_relief
                        },
                        "sessionId": "debug-session",
                        "runId": "run1",
                        "hypothesisId": "D",
                    }
                )
                + "\n"
            )
    except Exception as e:
        pass
    # #endregion

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
    # #region agent log
    import json, os

    try:
        log_path = "/Users/ai17/Documents/UT Austin/Research/Webber Energy Group/Comprehensive Transmission Cost Calculator/Python Version/.cursor/debug.log"
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        with open(log_path, "a") as f:
            f.write(
                json.dumps(
                    {
                        "id": "log_energy_calc",
                        "timestamp": int(__import__("time").time() * 1000),
                        "location": "congestion_curtailment_reduction.py:603",
                        "message": "energy congestion reduction calculated",
                        "data": {
                            "E_cong_bc": E_cong_bc,
                            "E_cong_non": E_cong_non,
                            "E_near": E_near,
                            "energy_congestion_reduction": energy_congestion_reduction,
                            "H_bc": H_bc,
                            "H_bnon": H_bnon,
                            "deltaC_rem": ΔC_rem,
                        },
                        "sessionId": "debug-session",
                        "runId": "run1",
                        "hypothesisId": "E",
                    }
                )
                + "\n"
            )
    except Exception as e:
        pass
    # #endregion

    # Monetize congestion ($/yr) — apply saturation haircut to $ only
    annual_congestion_reduction_cost_raw = (
        energy_congestion_reduction * average_congestion_price
    )
    annual_congestion_reduction_cost_haircut = (
        1 - saturation_factor
    ) * annual_congestion_reduction_cost_raw

    # Residual congestion energy (MWh/yr) on binding hours
    energy_congestion_residual = H_bc * max(
        0.0, average_exceedance - ΔC_rem
    ) + H_bnon * max(0.0, average_exceedance - effective_capacity_relief)
    annual_congestion_residual_cost = (
        energy_congestion_residual * average_congestion_price
    )

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
        start_year=delay_years + construction_years + 1,
    )

    lifetime_congestion_reduction_cost_haircut = (
        total_annual_congestion_reduction_cost_haircut * project_lifetime
    )
    lifetime_congestion_reduction_cost_haircut_pv = calculate_present_value(
        total_annual_congestion_reduction_cost_haircut,
        wacc_real,
        project_lifetime,
        start_year=delay_years + construction_years + 1,
    )

    lifetime_congestion_residual_cost = (
        annual_congestion_residual_cost * project_lifetime
    )
    lifetime_congestion_residual_cost_pv = calculate_present_value(
        annual_congestion_residual_cost,
        wacc_real,
        project_lifetime,
        start_year=delay_years + construction_years + 1,
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
        start_year=delay_years + construction_years + 1,
    )

    lifetime_curtailment_benefit_haircut = (
        annual_curtailment_benefit_haircut * project_lifetime
    )
    lifetime_curtailment_benefit_haircut_pv = calculate_present_value(
        annual_curtailment_benefit_haircut,
        wacc_real,
        project_lifetime,
        start_year=delay_years + construction_years + 1,
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

    return (
        lifetime_congestion_reduction_cost,
        lifetime_congestion_reduction_cost_haircut,
        lifetime_congestion_residual_cost,
        lifetime_congestion_reduction_cost_pv,
        lifetime_congestion_reduction_cost_haircut_pv,
        lifetime_congestion_residual_cost_pv,
        annual_congestion_reduction_cost_raw,
        annual_congestion_residual_cost,
        effective_capacity_relief,
        energy_congestion_reduction,
        energy_congestion_residual,
        E_near,
        lifetime_congestion_during_delay_and_construction_cost,
        lifetime_congestion_during_delay_and_construction_pv,
        # Curtailment values
        E_curt,
        annual_curtailment_benefit,
        annual_curtailment_benefit_haircut,
        lifetime_curtailment_benefit,
        lifetime_curtailment_benefit_pv,
        lifetime_curtailment_benefit_haircut,
        lifetime_curtailment_benefit_haircut_pv,
        lifetime_curtailment_during_delay_and_construction_cost,
        lifetime_curtailment_during_delay_and_construction_pv,
        # Allocation metrics
        alloc["theta_overlap"],
        H_bc,
        H_bnon,
        ΔC_rem,
    )


def main() -> None:
    """
    Main function to calculate and display congestion reduction costs.
    """
    # Load all required data
    (
        delay_years,
        construction_years,
        project_lifetime,
        reconductoring,
        capacity_mw,
        old_capacity_mw,
    ) = load_project_technical_details()

    # Load congestion reduction parameters
    (
        flow_factor,
        binding_hours,
        average_exceedance,
        near_binding_hours,
        near_average_exceedance,
        near_binding_relief_factor,
        saturation_factor,
        average_congestion_price,
    ) = load_congestion_reductions()

    # Load financing details
    inflation_rate, base_year, wacc_nominal, wacc_real = load_financing_details()

    # Load curtailment reduction parameters
    (
        curtailment_hours_total,
        average_curtailment_mw,
        average_curtailment_price,
        curtailment_saturation_factor,
    ) = load_curtailment_reductions()

    # Calculate congestion reduction costs
    (
        lifetime_congestion_reduction_cost,
        lifetime_congestion_reduction_cost_haircut,
        lifetime_congestion_residual_cost,
        lifetime_congestion_reduction_cost_pv,
        lifetime_congestion_reduction_cost_haircut_pv,
        lifetime_congestion_residual_cost_pv,
        annual_congestion_reduction_cost_raw,
        annual_congestion_residual_cost,
        effective_capacity_relief,
        energy_congestion_reduction,
        energy_congestion_residual,
        E_near,
        lifetime_congestion_during_delay_and_construction_cost,
        lifetime_congestion_during_delay_and_construction_pv,
        # Curtailment values
        E_curt,
        annual_curtailment_benefit,
        annual_curtailment_benefit_haircut,
        lifetime_curtailment_benefit,
        lifetime_curtailment_benefit_pv,
        lifetime_curtailment_benefit_haircut,
        lifetime_curtailment_benefit_haircut_pv,
        lifetime_curtailment_during_delay_and_construction_cost,
        lifetime_curtailment_during_delay_and_construction_pv,
        # Allocation metrics
        theta_overlap,
        H_bc,
        H_bnon,
        ΔC_rem,
    ) = calculate_congestion_reduction_costs(
        reconductoring,
        capacity_mw,
        old_capacity_mw,
        flow_factor,
        binding_hours,
        average_exceedance,
        near_binding_hours,
        near_average_exceedance,
        near_binding_relief_factor,
        saturation_factor,
        average_congestion_price,
        project_lifetime,
        delay_years,
        construction_years,
        wacc_real,
        curtailment_hours_total,
        average_curtailment_mw,
        average_curtailment_price,
        curtailment_saturation_factor,
    )

    print("=" * 60)
    print("CONGESTION ENERGY REDUCTION RELIEF PHYSICAL RESULTS AND QUANTITIES")
    print("=" * 60)
    print(f"Effective capacity relief: {effective_capacity_relief:,.2f} MW")
    print(f"Energy congestion reduction: {energy_congestion_reduction:,.2f} MWh/yr")
    print(f"Energy congestion residual: {energy_congestion_residual:,.2f} MWh/yr")
    print(f"E_near: {E_near:,.2f} MWh/yr")

    print()
    print("=" * 60)
    print("CONGESTION DURING DELAY AND CONSTRUCTION RESULTS AND QUANTITIES")
    print("=" * 60)

    print(
        f"Lifetime congestion during delay and construction cost: ${lifetime_congestion_during_delay_and_construction_cost:,.2f}"
    )
    print(
        f"Lifetime congestion during delay and construction PV: ${lifetime_congestion_during_delay_and_construction_pv:,.2f}"
    )

    print()
    print("=" * 60)
    print("CURTAILMENT REDUCTION RESULTS AND QUANTITIES")
    print("=" * 60)
    print(f"Curtailment energy reduction: {E_curt:,.2f} MWh/yr")
    print(f"Annual curtailment benefit: ${annual_curtailment_benefit:,.2f}")
    print(
        f"Annual curtailment benefit haircut: ${annual_curtailment_benefit_haircut:,.2f}"
    )
    print(f"Overlap factor (theta): {theta_overlap:.3f}")
    print(f"Binding hours (overlap): {H_bc:,.0f} hrs/yr")
    print(f"Binding hours (non-overlap): {H_bnon:,.0f} hrs/yr")
    print(f"Remaining capacity for congestion: {ΔC_rem:,.2f} MW")

    print()
    print("=" * 60)
    print("CURTAILMENT DURING DELAY AND CONSTRUCTION RESULTS")
    print("=" * 60)
    print(
        f"Lifetime curtailment during delay and construction cost: ${lifetime_curtailment_during_delay_and_construction_cost:,.2f}"
    )
    print(
        f"Lifetime curtailment during delay and construction PV: ${lifetime_curtailment_during_delay_and_construction_pv:,.2f}"
    )

    print()
    print("=" * 60)
    print("CURTAILMENT REDUCTION COST CALCULATION RESULTS")
    print("=" * 60)
    print(f"Lifetime curtailment benefit: ${lifetime_curtailment_benefit:,.2f}")
    print(
        f"Lifetime curtailment benefit haircut: ${lifetime_curtailment_benefit_haircut:,.2f}"
    )

    print()
    print(
        f"PRESENT VALUES (discounted to base year (2025) using real WACC ({wacc_real:.2%})):"
    )
    print(f"Lifetime curtailment benefit PV: ${lifetime_curtailment_benefit_pv:,.2f}")
    print(
        f"Lifetime curtailment benefit haircut PV: ${lifetime_curtailment_benefit_haircut_pv:,.2f}"
    )

    print()
    print("=" * 60)
    print("CONGESTION REDUCTION COST CALCULATION RESULTS")
    print("=" * 60)
    print(
        f"Lifetime congestion reduction cost: ${lifetime_congestion_reduction_cost:,.2f}"
    )
    print(
        f"Lifetime congestion reduction cost haircut: ${lifetime_congestion_reduction_cost_haircut:,.2f}"
    )
    print(
        f"Lifetime congestion residual cost: ${lifetime_congestion_residual_cost:,.2f}"
    )

    print()

    print(
        f"PRESENT VALUES (discounted to base year (2025) using real WACC ({wacc_real:.2%})):"
    )
    print(
        f"Lifetime congestion reduction cost PV: ${lifetime_congestion_reduction_cost_pv:,.2f}"
    )
    print(
        f"Lifetime congestion reduction cost haircut PV: ${lifetime_congestion_reduction_cost_haircut_pv:,.2f}"
    )
    print(
        f"Lifetime congestion residual cost PV: ${lifetime_congestion_residual_cost_pv:,.2f}"
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
        "congestion_benefit_annual": annual_congestion_reduction_cost_raw,
        "congestion_benefit_nominal": lifetime_congestion_reduction_cost,
        "congestion_benefit_pv": lifetime_congestion_reduction_cost_pv,
        "congestion_benefit_haircut_annual": annual_congestion_reduction_cost_raw
        * (1 - saturation_factor),
        "congestion_benefit_haircut_nominal": lifetime_congestion_reduction_cost_haircut,
        "congestion_benefit_haircut_pv": lifetime_congestion_reduction_cost_haircut_pv,
        # BENEFITS - Curtailment reduction (operational benefits)
        "curtailment_benefit_annual": annual_curtailment_benefit,
        "curtailment_benefit_nominal": lifetime_curtailment_benefit,
        "curtailment_benefit_pv": lifetime_curtailment_benefit_pv,
        "curtailment_benefit_haircut_annual": annual_curtailment_benefit_haircut,
        "curtailment_benefit_haircut_nominal": lifetime_curtailment_benefit_haircut,
        "curtailment_benefit_haircut_pv": lifetime_curtailment_benefit_haircut_pv,
        # COSTS - Delay/construction opportunity costs
        "congestion_delay_cost_nominal": lifetime_congestion_during_delay_and_construction_cost,
        "congestion_delay_cost_pv": lifetime_congestion_during_delay_and_construction_pv,
        "curtailment_delay_cost_nominal": lifetime_curtailment_during_delay_and_construction_cost,
        "curtailment_delay_cost_pv": lifetime_curtailment_during_delay_and_construction_pv,
        # COSTS - Residual unrelieved congestion
        "residual_congestion_annual": annual_congestion_residual_cost,
        "residual_congestion_nominal": lifetime_congestion_residual_cost,
        "residual_congestion_pv": lifetime_congestion_residual_cost_pv,
        # Physical metrics (for reference)
        "effective_capacity_relief_mw": effective_capacity_relief,
        "energy_congestion_reduction_mwh_yr": energy_congestion_reduction,
        "energy_congestion_residual_mwh_yr": energy_congestion_residual,
        "energy_curtailment_reduction_mwh_yr": E_curt,
        "theta_overlap": theta_overlap,
        "binding_hours_overlap": H_bc,
        "binding_hours_non_overlap": H_bnon,
        "remaining_capacity_mw": ΔC_rem,
    }

    # Write to CSV
    csv_manager.add_congestion_curtailment(results)
    csv_manager.write_batch_summary()


if __name__ == "__main__":
    main()
