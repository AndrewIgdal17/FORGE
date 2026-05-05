# Author: Andrew Igdal
# Date: 2025-10-27
# Description: This script uses the energy_losses script to calculate the line losses for
# a reconductoring project and its original state. Then it calculates each years
# lossbenefit = (Lbase(t) - L reconductoring(t)) * price_per_mwh
#

from __future__ import annotations

import sys
import os
from dataclasses import dataclass
from typing import Dict, Any, Tuple, Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from smart_output import CTCCOutputManager

# Standard library imports
import yaml

# Local utility imports
from energy_losses import (
    get_total_energy_losses,
    load_physical_details,
    load_circuit_and_resistance_details,
    calculate_phase_current,
    full_load_adjusted,
    calculate_line_losses,
)
from financial_utils import calculate_present_value, calculate_cod_year
from calculation_utils import (
    to_percent,
    from_percent,
    build_category_string,
    calculate_converter_losses,
)
from constants import HOURS_PER_YEAR
from smart_loaders import (
    load_financing_details,
    load_project_technical_details as load_project_technical_details_centralized,
    get_project_data_raw,
)


@dataclass
class LineLossProjectDetails:
    """Project details specific to line loss cost calculations."""

    construction_type: str
    ac_dc: str
    capacity_mw: int
    conductor_type: str
    number_of_converters: int
    converter_type: str
    line_utilization_percent: float
    baseline_electricity_price: float
    wacc_real: float
    reconductoring: bool
    delay_years: float
    construction_years: int
    project_lifetime: int
    greenfield_comparison_capacity_mw: Optional[int]
    greenfield_comparison_conductor_type: Optional[str]


def load_project_details() -> LineLossProjectDetails:
    """
    Load project technical details with line_loss_costs specific fields.

    This function loads comprehensive project details from the technical details YAML file,
    including both standard project specifications and optional fields used for line loss
    cost calculations (such as greenfield comparison parameters).

    Args:
        None (reads from YAML file)

    Returns:
        LineLossProjectDetails: Dataclass containing all project details for line loss calculations
            - construction_type: Type of construction (e.g., "Overhead", "Subsea")
            - ac_dc: "AC" or "DC" designation
            - capacity_mw: Line capacity in MW
            - conductor_type: Type of conductor used
            - number_of_converters: Number of converter stations (DC projects only, else 0)
            - converter_type: Converter type (for DC projects) or "NA" for AC
            - line_utilization_percent: Line utilization as decimal (0-1)
            - baseline_electricity_price: Baseline electricity price in $/MWh
            - wacc_real: Real WACC for present value of thermal line loss cost (market-tracked)
            - reconductoring: True if reconductoring project, False for greenfield
            - delay_years: Number of years of project delay
            - construction_years: Number of years of construction
            - project_lifetime: Project operational lifetime in years
            - greenfield_comparison_capacity_mw: Optional comparison capacity for greenfield projects
            - greenfield_comparison_conductor_type: Optional comparison conductor type for greenfield projects

    Raises:
        FileNotFoundError: When project technical details YAML is not found
        ValueError: When YAML file is empty or invalid
        KeyError: When required keys are missing from the YAML structure

    Note:
        The last two tuple elements (greenfield_comparison_*) are optional and may be None
        if not specified in the YAML file. These are used for comparing different greenfield
        configurations in line loss cost calculations.
    """
    try:
        # Load from centralized loader (returns ProjectTechnicalDetails dataclass)
        from yaml_loaders import ProjectTechnicalDetails

        project_details_obj: ProjectTechnicalDetails = (
            load_project_technical_details_centralized()
        )

        # Extract values from dataclass
        construction_type = project_details_obj.construction_type
        ac_dc = project_details_obj.ac_dc
        capacity_mw = project_details_obj.capacity_mw
        conductor_type = project_details_obj.conductor_type
        converter_type = project_details_obj.converter_type
        line_utilization_percent = project_details_obj.line_utilization
        reconductoring = project_details_obj.reconductoring
        uses_existing_row = project_details_obj.uses_existing_row
        delay_years = project_details_obj.delay_years
        construction_years = project_details_obj.construction_years
        project_lifetime = project_details_obj.project_lifetime
        _converter_loss_percentage = project_details_obj.converter_loss_percentage

        # Get additional fields not in centralized loader
        project_details = get_project_data_raw()
        if not project_details:
            raise ValueError("Project technical details file is empty or invalid")
        if "project" not in project_details:
            raise KeyError("Missing 'project' key in project technical details")
        project = project_details["project"]

        baseline_electricity_price = project.get(
            "baseline_electricity_price_per_mwh", 0
        )
        financing = load_financing_details()
        wacc_real = financing.wacc_real

        # Get number_of_converters if DC
        if ac_dc == "DC":
            number_of_converters = project.get("number_of_converters", 0)
        else:
            number_of_converters = 0

        # Get greenfield comparison fields (optional, only for greenfield projects)
        greenfield_comparison_capacity_mw = project.get(
            "greenfield_comparison_capacity_mw", None
        )
        # Convert empty string to None
        if greenfield_comparison_capacity_mw == "":
            greenfield_comparison_capacity_mw = None
        greenfield_comparison_conductor_type = project.get(
            "greenfield_comparison_conductor_type", None
        )
        # Convert empty string to None
        if greenfield_comparison_conductor_type == "":
            greenfield_comparison_conductor_type = None
    except FileNotFoundError:
        raise FileNotFoundError(f"Project technical details not found")
    except yaml.YAMLError as e:
        raise ValueError(f"Error parsing project technical details: {e}")
    except KeyError as e:
        raise KeyError(f"Missing required key in project technical details: {e}")

    return LineLossProjectDetails(
        construction_type=construction_type,
        ac_dc=ac_dc,
        capacity_mw=capacity_mw,
        conductor_type=conductor_type,
        number_of_converters=number_of_converters,
        converter_type=converter_type,
        line_utilization_percent=line_utilization_percent,
        baseline_electricity_price=baseline_electricity_price,
        wacc_real=wacc_real,
        reconductoring=reconductoring,
        delay_years=delay_years,
        construction_years=construction_years,
        project_lifetime=project_lifetime,
        greenfield_comparison_capacity_mw=greenfield_comparison_capacity_mw,
        greenfield_comparison_conductor_type=greenfield_comparison_conductor_type,
    )


def calculate_configuration_losses(
    construction_type: str,
    ac_dc: str,
    capacity_mw: int,
    conductor_type: str,
    converter_type: str,
    line_utilization_percent: float,
    project_lifetime: int,
    voltage_kv_override: Optional[float] = None,
) -> Tuple[float, float]:
    """
    Calculate line losses for a given configuration.

    Args:
        construction_type: Construction type (Overhead, Underground, etc.)
        ac_dc: "AC" or "DC"
        capacity_mw: Capacity in MW (numeric)
        conductor_type: Type of conductor
        converter_type: Converter type (for DC) or "NA" for AC
        line_utilization_percent: Line utilization as decimal (0-1)
        project_lifetime: Project lifetime in years
        voltage_kv_override: Optional voltage override (if None, looks up from category)

    Returns:
        tuple: (losses_mwh_per_year, lifetime_losses_mwh)
    """
    # Build category string for lookup
    category = build_category_string(
        construction_type, ac_dc, capacity_mw, conductor_type, converter_type
    )

    # Load physical details (line length)
    line_length = load_physical_details()

    # Load circuit and resistance details
    circuit = load_circuit_and_resistance_details(category)

    # Use override voltage if provided, otherwise use lookup voltage
    voltage_kv = (
        voltage_kv_override if voltage_kv_override is not None else circuit.voltage_kv
    )

    # Convert capacity_mw to string for calculate_phase_current
    capacity_mw_str = f"{capacity_mw}MW"

    # Calculate phase current and full load adjustment
    phase_current = calculate_phase_current(
        capacity_mw_str,
        voltage_kv,
        circuit.number_of_phases,
        circuit.number_of_circuits_poles,
        ac_dc,
    )
    full_load_adj = full_load_adjusted(line_utilization_percent)

    # Calculate line losses
    (
        losses_mwh_per_year,
        lifetime_losses_mwh,
        losses_mw_per_mile,
        resistance_per_mile,
        line_loss_per_mile_percent,
        total_line_loss_mw,
        total_line_loss_percent,
    ) = calculate_line_losses(
        phase_current,
        full_load_adj,
        circuit.AC_75_resistance,
        circuit.DC_20_resistance,
        ac_dc,
        circuit.number_of_circuits_poles,
        circuit.conductors_per_phase,
        circuit.number_of_phases,
        line_length,
        project_lifetime,
        capacity_mw,
        line_utilization_percent,
    )

    return losses_mwh_per_year, lifetime_losses_mwh


def compute_design_comparison(
    project_details: LineLossProjectDetails,
) -> Dict[str, Any]:
    """
    Compare line losses between the primary project configuration and an
    alternative (comparison) configuration using three methods.

    Returns a structured dict with primary/comparison summaries and
    direct/counterfactual/normalized comparison results.
    """
    primary_losses_mwh_yr, _ = calculate_configuration_losses(
        project_details.construction_type,
        project_details.ac_dc,
        project_details.capacity_mw,
        project_details.conductor_type,
        project_details.converter_type,
        project_details.line_utilization_percent,
        project_details.project_lifetime,
    )

    comparison_losses_mwh_yr, _ = calculate_configuration_losses(
        project_details.construction_type,
        project_details.ac_dc,
        project_details.greenfield_comparison_capacity_mw,
        project_details.greenfield_comparison_conductor_type,
        project_details.converter_type,
        project_details.line_utilization_percent,
        project_details.project_lifetime,
    )

    counterfactual_losses_mwh_yr, _ = calculate_configuration_losses(
        project_details.construction_type,
        project_details.ac_dc,
        project_details.greenfield_comparison_capacity_mw,
        project_details.conductor_type,
        project_details.converter_type,
        project_details.line_utilization_percent,
        project_details.project_lifetime,
    )

    primary_delivered_mwh = (
        project_details.capacity_mw
        * project_details.line_utilization_percent
        * HOURS_PER_YEAR
    )
    comparison_delivered_mwh = (
        project_details.greenfield_comparison_capacity_mw
        * project_details.line_utilization_percent
        * HOURS_PER_YEAR
    )

    primary_loss_pct = to_percent(primary_losses_mwh_yr / primary_delivered_mwh)
    comparison_loss_pct = to_percent(comparison_losses_mwh_yr / comparison_delivered_mwh)

    price = project_details.baseline_electricity_price
    lifetime = project_details.project_lifetime

    start_year = calculate_cod_year(
        project_details.delay_years, project_details.construction_years
    )

    def _method(delta_mwh: float) -> Dict[str, float]:
        annual = delta_mwh * price
        return {
            "delta_mwh_yr": delta_mwh,
            "annual_cost": annual,
            "lifetime_nominal": annual * lifetime,
            "npv": calculate_present_value(
                annual, project_details.wacc_real, lifetime, start_year
            ),
        }

    direct = _method(primary_losses_mwh_yr - comparison_losses_mwh_yr)
    direct["description"] = (
        "Compare absolute losses at each configuration's capacity"
    )

    counterfactual = _method(counterfactual_losses_mwh_yr - comparison_losses_mwh_yr)
    counterfactual["description"] = (
        "Compare conductors at the same (comparison) capacity"
    )

    normalized_delta_mwh = (
        from_percent(primary_loss_pct - comparison_loss_pct)
        * comparison_delivered_mwh
    )
    normalized = _method(normalized_delta_mwh)
    normalized["description"] = (
        "Compare loss rates, weighted by comparison delivered energy"
    )

    return {
        "primary": {
            "capacity_mw": project_details.capacity_mw,
            "conductor_type": project_details.conductor_type,
            "losses_mwh_yr": primary_losses_mwh_yr,
            "loss_percent": primary_loss_pct,
            "delivered_mwh_yr": primary_delivered_mwh,
        },
        "comparison": {
            "capacity_mw": project_details.greenfield_comparison_capacity_mw,
            "conductor_type": project_details.greenfield_comparison_conductor_type,
            "losses_mwh_yr": comparison_losses_mwh_yr,
            "loss_percent": comparison_loss_pct,
            "delivered_mwh_yr": comparison_delivered_mwh,
        },
        "methods": {
            "direct": direct,
            "counterfactual": counterfactual,
            "normalized": normalized,
        },
        "parameters": {
            "electricity_price": price,
            "wacc_real": project_details.wacc_real,
            "project_lifetime": lifetime,
            "construction_type": project_details.construction_type,
            "ac_dc": project_details.ac_dc,
        },
    }


def main() -> None:
    """Main function to calculate line loss costs for reconductoring projects."""

    project_details = load_project_details()

    print("=" * 70)
    print("LINE LOSS COST CALCULATOR")
    print("=" * 70)
    print()

    if not project_details.reconductoring:
        print("Greenfield project detected - calculating line loss costs.")
        print()

        comparison_capacity = project_details.greenfield_comparison_capacity_mw
        has_comparison = (
            comparison_capacity is not None
            and comparison_capacity != 0
            and comparison_capacity != ""
        )

        if has_comparison:
            comparison_result = compute_design_comparison(project_details)
            print("Design comparison computed — 3 methods.")
            for name, method in comparison_result["methods"].items():
                print(
                    f"  {name}: delta {method['delta_mwh_yr']:,.1f} MWh/yr, "
                    f"NPV ${method['npv']:,.0f}"
                )
            print()

        start_year = calculate_cod_year(
            project_details.delay_years, project_details.construction_years
        )

        loss_data = get_total_energy_losses()
        primary_line_mwh = loss_data["losses_mwh_per_year"]
        primary_converter_mwh = loss_data.get("total_converter_losses_mwh", 0)
        primary_total_mwh = loss_data["total_losses_mwh_per_year"]
        price = project_details.baseline_electricity_price

        primary_annual_loss_cost = primary_total_mwh * price
        primary_lifetime_nominal_cost = (
            primary_annual_loss_cost * project_details.project_lifetime
        )
        primary_pv_loss_cost = calculate_present_value(
            primary_annual_loss_cost,
            project_details.wacc_real,
            project_details.project_lifetime,
            start_year,
        )

        primary_line_annual = primary_line_mwh * price
        primary_converter_annual = primary_converter_mwh * price
        primary_line_pv = calculate_present_value(
            primary_line_annual,
            project_details.wacc_real,
            project_details.project_lifetime,
            start_year,
        )
        primary_converter_pv = calculate_present_value(
            primary_converter_annual,
            project_details.wacc_real,
            project_details.project_lifetime,
            start_year,
        )

        csv_manager = CTCCOutputManager()
        results = {
            "annual_cost": primary_annual_loss_cost,
            "total_nominal": primary_lifetime_nominal_cost,
            "total_afudc": 0,
            "total_pv": primary_pv_loss_cost,
            "line_loss_mwh_yr": primary_line_mwh,
            "converter_loss_mwh_yr": primary_converter_mwh,
            "total_loss_mwh_yr": primary_total_mwh,
            "line_annual_cost": primary_line_annual,
            "converter_annual_cost": primary_converter_annual,
            "line_cost_pv": primary_line_pv,
            "converter_cost_pv": primary_converter_pv,
            "line_nominal_total": primary_line_annual
            * project_details.project_lifetime,
            "converter_nominal_total": primary_converter_annual
            * project_details.project_lifetime,
        }
        csv_manager.add_line_loss_costs(results)
        if has_comparison:
            csv_manager.add_design_comparison(comparison_result)
        csv_manager.write_batch_summary()
        return

    # Load baseline configuration details using helper
    try:
        raw_project_data = get_project_data_raw()
        if not raw_project_data:
            raise ValueError("Project technical details file is empty or invalid")
        if "project" not in raw_project_data:
            raise KeyError("Missing 'project' key in project technical details")
        project = raw_project_data["project"]
        required_keys = ["old_capacity_mw", "old_conductor_type", "old_ac_dc"]
        for key in required_keys:
            if key not in project:
                raise KeyError(
                    f"Missing '{key}' key in project section of technical details"
                )
        old_capacity_mw = project["old_capacity_mw"]
        old_conductor_type = project["old_conductor_type"]
        old_ac_dc = project["old_ac_dc"]
    except FileNotFoundError:
        raise FileNotFoundError(f"Project technical details not found")
    except yaml.YAMLError as e:
        raise ValueError(f"Error parsing project technical details: {e}")
    except KeyError as e:
        raise KeyError(f"Missing required key in project technical details: {e}")

    # For DC to DC, keep the same converter type
    if project_details.ac_dc == "DC" and old_ac_dc == "DC":
        old_converter_type = project_details.converter_type
    elif old_ac_dc == "AC":
        old_converter_type = "NA"
    else:
        old_converter_type = project_details.converter_type

    print(f"PROJECT CONFIGURATION")
    print("-" * 70)
    print(f"Construction Type: {project_details.construction_type}")
    print(
        f"Line Utilization: {to_percent(project_details.line_utilization_percent):.1f}%"
    )
    print(f"Project Lifetime: {project_details.project_lifetime} years")
    print(f"Electricity Price: ${project_details.baseline_electricity_price:.2f}/MWh")
    print()

    print(f"BASELINE CONFIGURATION (Old)")
    print("-" * 70)
    print(f"Capacity: {old_capacity_mw} MW")
    print(f"AC/DC: {old_ac_dc}")
    print(f"Conductor Type: {old_conductor_type}")
    print()

    # Calculate baseline losses (line only from configuration)
    baseline_losses_mwh_per_year, baseline_lifetime_losses_mwh = (
        calculate_configuration_losses(
            project_details.construction_type,
            old_ac_dc,
            old_capacity_mw,
            old_conductor_type,
            old_converter_type,
            project_details.line_utilization_percent,
            project_details.project_lifetime,
        )
    )
    # Baseline converter losses (for DC reconductoring)
    num_converters = project_details.number_of_converters if old_ac_dc == "DC" else 0
    (
        _baseline_conv_mw,
        baseline_converter_losses_mwh,
        _baseline_conv_pct,
    ) = calculate_converter_losses(
        num_converters,
        old_converter_type,
        project_details.line_utilization_percent,
        old_capacity_mw,
        old_ac_dc,
    )
    baseline_total_losses_mwh_per_year = (
        baseline_losses_mwh_per_year + baseline_converter_losses_mwh
    )

    print(f"NEW CONFIGURATION (After Reconductoring)")
    print("-" * 70)
    print(f"Capacity: {project_details.capacity_mw} MW")
    print(f"AC/DC: {project_details.ac_dc}")
    print(f"Conductor Type: {project_details.conductor_type}")
    print()

    # Look up old voltage for reconductoring (physical towers unchanged)
    old_category = build_category_string(
        project_details.construction_type,
        old_ac_dc,
        old_capacity_mw,
        old_conductor_type,
        old_converter_type,
    )
    old_circuit = load_circuit_and_resistance_details(old_category)
    old_voltage_kv = old_circuit.voltage_kv

    # Calculate new configuration losses (line only) using OLD voltage (towers unchanged)
    new_losses_mwh_per_year, new_lifetime_losses_mwh = calculate_configuration_losses(
        project_details.construction_type,
        project_details.ac_dc,
        project_details.capacity_mw,
        project_details.conductor_type,
        project_details.converter_type,
        project_details.line_utilization_percent,
        project_details.project_lifetime,
        voltage_kv_override=old_voltage_kv,  # Use old voltage since towers unchanged
    )
    # New config total (line + converter) for cost written to batch and breakdown
    new_loss_data = get_total_energy_losses()
    new_line_mwh = new_loss_data["losses_mwh_per_year"]
    new_converter_mwh = new_loss_data.get("total_converter_losses_mwh", 0)
    new_total_mwh = new_loss_data["total_losses_mwh_per_year"]

    # Calculate counterfactual baseline losses (old conductor at new capacity @ old voltage)
    # This ensures both use the same voltage for fair comparison (informational only)
    (
        counterfactual_baseline_losses_mwh_per_year,
        counterfactual_baseline_lifetime_losses_mwh,
    ) = calculate_configuration_losses(
        project_details.construction_type,
        old_ac_dc,
        project_details.capacity_mw,  # Use NEW capacity
        old_conductor_type,
        old_converter_type,
        project_details.line_utilization_percent,
        project_details.project_lifetime,
        voltage_kv_override=old_voltage_kv,  # Use old voltage for fair comparison
    )

    # Calculate delivered energy for each configuration
    baseline_delivered_mwh = (
        old_capacity_mw * project_details.line_utilization_percent * HOURS_PER_YEAR
    )
    new_delivered_mwh = (
        project_details.capacity_mw
        * project_details.line_utilization_percent
        * HOURS_PER_YEAR
    )

    # Calculate loss percentages
    baseline_loss_percent = to_percent(
        baseline_losses_mwh_per_year / baseline_delivered_mwh
    )
    new_loss_percent = to_percent(new_losses_mwh_per_year / new_delivered_mwh)

    # METHOD 1: Direct Comparison - Compare absolute losses
    direct_loss_reduction_mwh = baseline_losses_mwh_per_year - new_losses_mwh_per_year
    direct_annual_benefit = (
        direct_loss_reduction_mwh * project_details.baseline_electricity_price
    )
    direct_lifetime_benefit = direct_annual_benefit * project_details.project_lifetime

    # METHOD 2: Counterfactual Comparison - Compare old vs new conductor at new capacity
    counterfactual_loss_reduction_mwh = (
        counterfactual_baseline_losses_mwh_per_year - new_losses_mwh_per_year
    )
    counterfactual_annual_benefit = (
        counterfactual_loss_reduction_mwh * project_details.baseline_electricity_price
    )
    counterfactual_lifetime_benefit = (
        counterfactual_annual_benefit * project_details.project_lifetime
    )

    # METHOD 3: Normalized (Per MWh) Comparison
    # Apply the difference in loss percentages to the new delivered energy
    normalized_loss_reduction_mwh = (
        from_percent(baseline_loss_percent - new_loss_percent) * new_delivered_mwh
    )
    normalized_annual_benefit = (
        normalized_loss_reduction_mwh * project_details.baseline_electricity_price
    )
    normalized_lifetime_benefit = (
        normalized_annual_benefit * project_details.project_lifetime
    )

    # Line losses start at first year of operation (COD)
    start_year = calculate_cod_year(
        project_details.delay_years, project_details.construction_years
    )

    # Calculate NPVs for all three methods
    direct_npv = calculate_present_value(
        direct_annual_benefit,
        project_details.wacc_real,
        project_details.project_lifetime,
        start_year,
    )
    counterfactual_npv = calculate_present_value(
        counterfactual_annual_benefit,
        project_details.wacc_real,
        project_details.project_lifetime,
        start_year,
    )
    normalized_npv = calculate_present_value(
        normalized_annual_benefit,
        project_details.wacc_real,
        project_details.project_lifetime,
        start_year,
    )

    # Print results
    print("=" * 70)
    print("LINE LOSS COST RESULTS")
    print("=" * 70)
    print()

    print("LOSS COMPARISON:")
    print("-" * 70)
    print(f"Baseline (Old Config): {baseline_losses_mwh_per_year:,.2f} MWh/year")
    print(f"  Capacity: {old_capacity_mw} MW | Loss Rate: {baseline_loss_percent:.2f}%")
    print()
    print(f"New Configuration: {new_losses_mwh_per_year:,.2f} MWh/year")
    print(
        f"  Capacity: {project_details.capacity_mw} MW | Loss Rate: {new_loss_percent:.2f}%"
    )
    print()
    print(
        f"Counterfactual (Old Conductor @ New Capacity): {counterfactual_baseline_losses_mwh_per_year:,.2f} MWh/year"
    )
    print()

    print("=" * 70)
    print("METHOD 1: DIRECT COMPARISON")
    print("=" * 70)
    print("Compares: Baseline losses @ old capacity vs. New losses @ new capacity")
    print()
    print("NOMINAL VALUES:")
    print(f"  Loss Reduction: {direct_loss_reduction_mwh:,.2f} MWh/year")
    print(f"  Annual Benefit: ${direct_annual_benefit:,.2f}/year")
    print(f"  Lifetime Benefit: ${direct_lifetime_benefit:,.2f}")
    print()
    print("DISCOUNTED VALUES (NPV):")
    print(f"  Discount Rate: {to_percent(project_details.wacc_real):.1f}% (real WACC)")
    print(f"  Start Year: {start_year:.1f} years")
    print(f"  Net Present Value: ${direct_npv:,.2f}")
    print()

    print("=" * 70)
    print("METHOD 2: COUNTERFACTUAL COMPARISON")
    print("=" * 70)
    print("Compares: Old conductor @ new capacity vs. New conductor @ new capacity")
    print()
    print("NOMINAL VALUES:")
    print(f"  Loss Reduction: {counterfactual_loss_reduction_mwh:,.2f} MWh/year")
    print(f"  Annual Benefit: ${counterfactual_annual_benefit:,.2f}/year")
    print(f"  Lifetime Benefit: ${counterfactual_lifetime_benefit:,.2f}")
    print()
    print("DISCOUNTED VALUES (NPV):")
    print(f"  Discount Rate: {to_percent(project_details.wacc_real):.1f}% (real WACC)")
    print(f"  Start Year: {start_year:.1f} years")
    print(f"  Net Present Value: ${counterfactual_npv:,.2f}")
    print()

    print("=" * 70)
    print("METHOD 3: NORMALIZED (PER MWH) COMPARISON")
    print("=" * 70)
    print("Compares: Loss percentages weighted by delivered energy")
    print()
    print("NOMINAL VALUES:")
    print(f"  Loss Reduction: {normalized_loss_reduction_mwh:,.2f} MWh/year")
    print(f"  Annual Benefit: ${normalized_annual_benefit:,.2f}/year")
    print(f"  Lifetime Benefit: ${normalized_lifetime_benefit:,.2f}")
    print()
    print("DISCOUNTED VALUES (NPV):")
    print(f"  Discount Rate: {to_percent(project_details.wacc_real):.1f}% (real WACC)")
    print(f"  Start Year: {start_year:.1f} years")
    print(f"  Net Present Value: ${normalized_npv:,.2f}")
    print()

    print("=" * 70)

    # ========================================================================
    # CSV OUTPUT - Write results to batch summary and detail CSV
    # ========================================================================
    # Use NEW configuration's total losses (line + converter for DC) for BCR

    csv_manager = CTCCOutputManager()
    price = project_details.baseline_electricity_price

    new_line_annual_cost = new_line_mwh * price
    new_converter_annual_cost = new_converter_mwh * price
    new_total_annual_cost = new_total_mwh * price
    new_lifetime_nominal_cost = new_total_annual_cost * project_details.project_lifetime
    new_line_pv = calculate_present_value(
        new_line_annual_cost,
        project_details.wacc_real,
        project_details.project_lifetime,
        start_year,
    )
    new_converter_pv = calculate_present_value(
        new_converter_annual_cost,
        project_details.wacc_real,
        project_details.project_lifetime,
        start_year,
    )
    new_pv_loss_cost = calculate_present_value(
        new_total_annual_cost,
        project_details.wacc_real,
        project_details.project_lifetime,
        start_year,
    )

    results = {
        "annual_cost": new_total_annual_cost,
        "total_nominal": new_lifetime_nominal_cost,
        "total_afudc": 0,
        "total_pv": new_pv_loss_cost,
        "line_loss_mwh_yr": new_line_mwh,
        "converter_loss_mwh_yr": new_converter_mwh,
        "total_loss_mwh_yr": new_total_mwh,
        "line_annual_cost": new_line_annual_cost,
        "converter_annual_cost": new_converter_annual_cost,
        "line_cost_pv": new_line_pv,
        "converter_cost_pv": new_converter_pv,
        "line_nominal_total": new_line_annual_cost * project_details.project_lifetime,
        "converter_nominal_total": new_converter_annual_cost
        * project_details.project_lifetime,
    }

    csv_manager.add_line_loss_costs(results)
    csv_manager.write_batch_summary()


if __name__ == "__main__":
    main()
