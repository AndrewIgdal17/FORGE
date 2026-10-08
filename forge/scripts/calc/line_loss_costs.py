# Date: 2025-10-27
# Description: This script uses the energy_losses script to calculate the line losses for
# a reconductoring project and its original state. Then it calculates each years
# lossbenefit = (Lbase(t) - L reconductoring(t)) * price_per_mwh
#

from __future__ import annotations

import logging

from dataclasses import dataclass
from typing import Tuple, Optional

from forge.scripts.utils.smart_output import SmartOutputManager

# Standard library imports
import yaml

# Local utility imports
from forge.scripts.calc.energy_losses import (
    get_total_energy_losses,
    load_physical_details,
    load_circuit_and_resistance_details,
    calculate_phase_current,
    full_load_adjusted,
    calculate_line_losses,
)
from forge.scripts.utils.financial_utils import (
    calculate_growing_annuity_pv,
    calculate_nominal_growing_series,
    calculate_cod_year,
)
from forge.scripts.utils.calculation_utils import (
    to_percent,
    from_percent,
    build_category_string,
    calculate_converter_losses,
)
from forge.scripts.utils.constants import HOURS_PER_YEAR
from forge.scripts.utils.smart_loaders import (
    load_financing_details,
    load_project_technical_details as load_project_technical_details_centralized,
    get_project_data_raw,
    load_congestion_reductions,
)
from forge.scripts.utils.run_context import get_run_context

logger = logging.getLogger(__name__)


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
    value_of_load: float
    wacc_real: float
    benefit_price_escalation_real: float
    project_type: str  # "greenfield" | "reconductoring" | "rebuild"
    delay_years: float
    construction_years: int
    project_lifetime: int

def load_project_details() -> LineLossProjectDetails:
    """
    Load project technical details with line_loss_costs specific fields.

    This function loads comprehensive project details from the technical details YAML file,
    including the standard project specifications used for line loss cost calculations.

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
            - value_of_load: Value of load in $/MWh
            - wacc_real: Real WACC for present value of thermal line loss cost (market-tracked)
            - benefit_price_escalation_real: Real annual escalation rate applied to v_load
              for welfare consistency with the benefit-of-delivered-energy valuation (g_benefit)
            - project_type: "greenfield" | "reconductoring" | "rebuild"
            - delay_years: Number of years of project delay
            - construction_years: Number of years of construction
            - project_lifetime: Project operational lifetime in years

    Raises:
        FileNotFoundError: When project technical details YAML is not found
        ValueError: When YAML file is empty or invalid
        KeyError: When required keys are missing from the YAML structure
    """
    try:
        # Load from centralized loader (returns ProjectTechnicalDetails dataclass)
        from forge.scripts.io.yaml_loaders import ProjectTechnicalDetails

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
        project_type = project_details_obj.project_type
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

        value_of_load = project.get(
            "value_of_load_per_mwh", 0
        )
        financing = load_financing_details()
        wacc_real = financing.wacc_real
        congestion_params = load_congestion_reductions()
        benefit_price_escalation_real = congestion_params.benefit_price_escalation_real

        ctx = get_run_context()
        if ctx is None:
            raise RuntimeError(
                f"{__name__} requires a RunContext. Run via forge.py or set up "
                "RunContext in your test fixture."
            )
        number_of_converters = ctx.number_of_converters
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
        value_of_load=value_of_load,
        wacc_real=wacc_real,
        benefit_price_escalation_real=benefit_price_escalation_real,
        project_type=project_type,
        delay_years=delay_years,
        construction_years=construction_years,
        project_lifetime=project_lifetime,
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
        circuit.alpha_20,
        ac_dc,
        circuit.number_of_circuits_poles,
        circuit.conductors_per_phase,
        circuit.number_of_phases,
        line_length,
        project_lifetime,
        capacity_mw,
        line_utilization_percent,
        voltage_kv,
        construction_type,
    )

    return losses_mwh_per_year, lifetime_losses_mwh

def main() -> None:
    """Main function to calculate line loss costs for reconductoring projects."""

    project_details = load_project_details()

    logger.info("=" * 70)
    logger.info("LINE LOSS COST CALCULATOR")
    logger.info("=" * 70)
    logger.info("")

    if project_details.project_type == "greenfield":
        logger.info("Greenfield project detected - calculating line loss costs.")
        logger.info("")

        g_benefit = project_details.benefit_price_escalation_real

        loss_data = get_total_energy_losses()
        primary_line_mwh = loss_data["losses_mwh_per_year"]
        primary_converter_mwh = loss_data.get("total_converter_losses_mwh", 0)
        primary_total_mwh = loss_data["total_losses_mwh_per_year"]
        price = project_details.value_of_load

        primary_annual_loss_cost = primary_total_mwh * price
        primary_lifetime_nominal_cost = calculate_nominal_growing_series(
            primary_annual_loss_cost, g_benefit, project_details.project_lifetime
        )
        primary_pv_loss_cost = calculate_growing_annuity_pv(
            primary_annual_loss_cost,
            g_benefit,
            project_details.wacc_real,
            project_details.project_lifetime,
            delay_years=project_details.delay_years,
            construction_years=project_details.construction_years,
        )

        primary_line_annual = primary_line_mwh * price
        primary_converter_annual = primary_converter_mwh * price
        primary_line_pv = calculate_growing_annuity_pv(
            primary_line_annual,
            g_benefit,
            project_details.wacc_real,
            project_details.project_lifetime,
            delay_years=project_details.delay_years,
            construction_years=project_details.construction_years,
        )
        primary_converter_pv = calculate_growing_annuity_pv(
            primary_converter_annual,
            g_benefit,
            project_details.wacc_real,
            project_details.project_lifetime,
            delay_years=project_details.delay_years,
            construction_years=project_details.construction_years,
        )

        csv_manager = SmartOutputManager()
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
            "line_nominal_total": calculate_nominal_growing_series(
                primary_line_annual, g_benefit, project_details.project_lifetime
            ),
            "converter_nominal_total": calculate_nominal_growing_series(
                primary_converter_annual, g_benefit, project_details.project_lifetime
            ),
        }
        csv_manager.add_line_loss_costs(results)
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

    logger.info(f"PROJECT CONFIGURATION")
    logger.info("-" * 70)
    logger.info(f"Construction Type: {project_details.construction_type}")
    logger.info(
        f"Line Utilization: {to_percent(project_details.line_utilization_percent):.1f}%"
    )
    logger.info(f"Project Lifetime: {project_details.project_lifetime} years")
    logger.info(f"Value of Load: ${project_details.value_of_load:.2f}/MWh")
    logger.info("")

    logger.info(f"BASELINE CONFIGURATION (Old)")
    logger.info("-" * 70)
    logger.info(f"Capacity: {old_capacity_mw} MW")
    logger.info(f"AC/DC: {old_ac_dc}")
    logger.info(f"Conductor Type: {old_conductor_type}")
    logger.info("")

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

    logger.info(f"NEW CONFIGURATION (After Reconductoring)")
    logger.info("-" * 70)
    logger.info(f"Capacity: {project_details.capacity_mw} MW")
    logger.info(f"AC/DC: {project_details.ac_dc}")
    logger.info(f"Conductor Type: {project_details.conductor_type}")
    logger.info("")

    # Look up old voltage (only relevant for reconductoring, where the physical
    # towers are unchanged; rebuild replaces structures, so the new configuration
    # uses its own standard voltage class instead of this override).
    old_category = build_category_string(
        project_details.construction_type,
        old_ac_dc,
        old_capacity_mw,
        old_conductor_type,
        old_converter_type,
    )
    old_circuit = load_circuit_and_resistance_details(old_category)
    old_voltage_kv = old_circuit.voltage_kv
    voltage_override = (
        old_voltage_kv if project_details.project_type == "reconductoring" else None
    )

    # Calculate new configuration losses (line only). Reconductoring keeps the old
    # voltage class (towers unchanged); rebuild and greenfield use the new
    # configuration's own voltage class (new structures).
    new_losses_mwh_per_year, new_lifetime_losses_mwh = calculate_configuration_losses(
        project_details.construction_type,
        project_details.ac_dc,
        project_details.capacity_mw,
        project_details.conductor_type,
        project_details.converter_type,
        project_details.line_utilization_percent,
        project_details.project_lifetime,
        voltage_kv_override=voltage_override,
    )
    # New config total (line + converter) for cost written to batch and breakdown
    new_loss_data = get_total_energy_losses()
    new_line_mwh = new_loss_data["losses_mwh_per_year"]
    new_converter_mwh = new_loss_data.get("total_converter_losses_mwh", 0)
    new_total_mwh = new_loss_data["total_losses_mwh_per_year"]

    # Calculate counterfactual baseline losses (old conductor at new capacity).
    # For reconductoring, hold voltage at the old value for a fair apples-to-apples
    # comparison (towers unchanged). For rebuild, both configurations already use
    # the new voltage class, so no override is needed.
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
        voltage_kv_override=voltage_override,
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
        direct_loss_reduction_mwh * project_details.value_of_load
    )
    direct_lifetime_benefit = calculate_nominal_growing_series(
        direct_annual_benefit,
        project_details.benefit_price_escalation_real,
        project_details.project_lifetime,
    )

    # METHOD 2: Counterfactual Comparison - Compare old vs new conductor at new capacity
    counterfactual_loss_reduction_mwh = (
        counterfactual_baseline_losses_mwh_per_year - new_losses_mwh_per_year
    )
    counterfactual_annual_benefit = (
        counterfactual_loss_reduction_mwh * project_details.value_of_load
    )
    counterfactual_lifetime_benefit = calculate_nominal_growing_series(
        counterfactual_annual_benefit,
        project_details.benefit_price_escalation_real,
        project_details.project_lifetime,
    )

    # METHOD 3: Normalized (Per MWh) Comparison
    # Apply the difference in loss percentages to the new delivered energy
    normalized_loss_reduction_mwh = (
        from_percent(baseline_loss_percent - new_loss_percent) * new_delivered_mwh
    )
    normalized_annual_benefit = (
        normalized_loss_reduction_mwh * project_details.value_of_load
    )
    normalized_lifetime_benefit = calculate_nominal_growing_series(
        normalized_annual_benefit,
        project_details.benefit_price_escalation_real,
        project_details.project_lifetime,
    )

    # Line losses start at first year of operation (COD); kept for display only —
    # calculate_growing_annuity_pv derives the delay discount from delay/construction years
    start_year = calculate_cod_year(
        project_details.delay_years, project_details.construction_years
    )

    # Calculate NPVs for all three methods
    direct_npv = calculate_growing_annuity_pv(
        direct_annual_benefit,
        project_details.benefit_price_escalation_real,
        project_details.wacc_real,
        project_details.project_lifetime,
        delay_years=project_details.delay_years,
        construction_years=project_details.construction_years,
    )
    counterfactual_npv = calculate_growing_annuity_pv(
        counterfactual_annual_benefit,
        project_details.benefit_price_escalation_real,
        project_details.wacc_real,
        project_details.project_lifetime,
        delay_years=project_details.delay_years,
        construction_years=project_details.construction_years,
    )
    normalized_npv = calculate_growing_annuity_pv(
        normalized_annual_benefit,
        project_details.benefit_price_escalation_real,
        project_details.wacc_real,
        project_details.project_lifetime,
        delay_years=project_details.delay_years,
        construction_years=project_details.construction_years,
    )

    # Print results
    logger.info("=" * 70)
    logger.info("LINE LOSS COST RESULTS")
    logger.info("=" * 70)
    logger.info("")

    logger.info("LOSS COMPARISON:")
    logger.info("-" * 70)
    logger.info(f"Baseline (Old Config): {baseline_losses_mwh_per_year:,.2f} MWh/year")
    logger.info(f"  Capacity: {old_capacity_mw} MW | Loss Rate: {baseline_loss_percent:.2f}%")
    logger.info("")
    logger.info(f"New Configuration: {new_losses_mwh_per_year:,.2f} MWh/year")
    logger.info(
        f"  Capacity: {project_details.capacity_mw} MW | Loss Rate: {new_loss_percent:.2f}%"
    )
    logger.info("")
    logger.info(
        f"Counterfactual (Old Conductor @ New Capacity): {counterfactual_baseline_losses_mwh_per_year:,.2f} MWh/year"
    )
    logger.info("")

    logger.info("=" * 70)
    logger.info("METHOD 1: DIRECT COMPARISON")
    logger.info("=" * 70)
    logger.info("Compares: Baseline losses @ old capacity vs. New losses @ new capacity")
    logger.info("")
    logger.info("NOMINAL VALUES:")
    logger.info(f"  Loss Reduction: {direct_loss_reduction_mwh:,.2f} MWh/year")
    logger.info(f"  Annual Benefit: ${direct_annual_benefit:,.2f}/year")
    logger.info(f"  Lifetime Benefit: ${direct_lifetime_benefit:,.2f}")
    logger.info("")
    logger.info("DISCOUNTED VALUES (NPV):")
    logger.info(f"  Discount Rate: {to_percent(project_details.wacc_real):.1f}% (real WACC)")
    logger.info(f"  Start Year: {start_year:.1f} years")
    logger.info(f"  Net Present Value: ${direct_npv:,.2f}")
    logger.info("")

    logger.info("=" * 70)
    logger.info("METHOD 2: COUNTERFACTUAL COMPARISON")
    logger.info("=" * 70)
    logger.info("Compares: Old conductor @ new capacity vs. New conductor @ new capacity")
    logger.info("")
    logger.info("NOMINAL VALUES:")
    logger.info(f"  Loss Reduction: {counterfactual_loss_reduction_mwh:,.2f} MWh/year")
    logger.info(f"  Annual Benefit: ${counterfactual_annual_benefit:,.2f}/year")
    logger.info(f"  Lifetime Benefit: ${counterfactual_lifetime_benefit:,.2f}")
    logger.info("")
    logger.info("DISCOUNTED VALUES (NPV):")
    logger.info(f"  Discount Rate: {to_percent(project_details.wacc_real):.1f}% (real WACC)")
    logger.info(f"  Start Year: {start_year:.1f} years")
    logger.info(f"  Net Present Value: ${counterfactual_npv:,.2f}")
    logger.info("")

    logger.info("=" * 70)
    logger.info("METHOD 3: NORMALIZED (PER MWH) COMPARISON")
    logger.info("=" * 70)
    logger.info("Compares: Loss percentages weighted by delivered energy")
    logger.info("")
    logger.info("NOMINAL VALUES:")
    logger.info(f"  Loss Reduction: {normalized_loss_reduction_mwh:,.2f} MWh/year")
    logger.info(f"  Annual Benefit: ${normalized_annual_benefit:,.2f}/year")
    logger.info(f"  Lifetime Benefit: ${normalized_lifetime_benefit:,.2f}")
    logger.info("")
    logger.info("DISCOUNTED VALUES (NPV):")
    logger.info(f"  Discount Rate: {to_percent(project_details.wacc_real):.1f}% (real WACC)")
    logger.info(f"  Start Year: {start_year:.1f} years")
    logger.info(f"  Net Present Value: ${normalized_npv:,.2f}")
    logger.info("")

    logger.info("=" * 70)

    # ========================================================================
    # CSV OUTPUT - Write results to batch summary and detail CSV
    # ========================================================================
    # Use NEW configuration's total losses (line + converter for DC) for BCR

    csv_manager = SmartOutputManager()
    price = project_details.value_of_load

    g_benefit = project_details.benefit_price_escalation_real

    new_line_annual_cost = new_line_mwh * price
    new_converter_annual_cost = new_converter_mwh * price
    new_total_annual_cost = new_total_mwh * price
    new_lifetime_nominal_cost = calculate_nominal_growing_series(
        new_total_annual_cost, g_benefit, project_details.project_lifetime
    )
    new_line_pv = calculate_growing_annuity_pv(
        new_line_annual_cost,
        g_benefit,
        project_details.wacc_real,
        project_details.project_lifetime,
        delay_years=project_details.delay_years,
        construction_years=project_details.construction_years,
    )
    new_converter_pv = calculate_growing_annuity_pv(
        new_converter_annual_cost,
        g_benefit,
        project_details.wacc_real,
        project_details.project_lifetime,
        delay_years=project_details.delay_years,
        construction_years=project_details.construction_years,
    )
    new_pv_loss_cost = calculate_growing_annuity_pv(
        new_total_annual_cost,
        g_benefit,
        project_details.wacc_real,
        project_details.project_lifetime,
        delay_years=project_details.delay_years,
        construction_years=project_details.construction_years,
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
        "line_nominal_total": calculate_nominal_growing_series(
            new_line_annual_cost, g_benefit, project_details.project_lifetime
        ),
        "converter_nominal_total": calculate_nominal_growing_series(
            new_converter_annual_cost, g_benefit, project_details.project_lifetime
        ),
    }

    csv_manager.add_line_loss_costs(results)
    csv_manager.write_batch_summary()
