# Date: 2025-10-27
# Descriptions: This script calculates transmission line losses

from __future__ import annotations

import logging

# Local utility imports
from forge.scripts.utils.smart_loaders import (
    load_project_technical_details,
    load_physical_details,
    load_circuit_and_resistance_details,
    get_project_data_raw,
)
from forge.scripts.utils.calculation_utils import (
    calculate_phase_current,
    full_load_adjusted,
    calculate_line_losses,
    calculate_converter_losses,
    to_percent,
)
from forge.scripts.utils.run_context import get_run_context

logger = logging.getLogger(__name__)


def get_total_energy_losses() -> dict:
    """
    Calculate total energy losses for the current project configuration.
    
    For reconductoring projects, automatically uses old configuration's voltage
    since physical towers (and thus voltage clearances) remain unchanged.
    
    Returns:
        dict with keys:
        - losses_mwh_per_year: Line losses in MWh per year
        - lifetime_losses_mwh: Lifetime line losses in MWh
        - losses_mw_per_mile: Line losses per mile in MW
        - resistance_per_mile: Resistance per mile in ohms
        - line_loss_per_mile_percent: Line loss percentage per mile
        - total_line_loss_mw: Total line loss in MW
        - total_line_loss_percent: Total line loss percentage
        - total_converter_losses_mw: Converter losses in MW
        - total_converter_losses_mwh: Converter losses in MWh per year
        - converter_loss_percent: Converter loss percentage
        - total_losses_mwh_per_year: Combined line + converter losses in MWh per year
        - total_lifetime_losses_mwh: Combined line + converter lifetime losses in MWh
        - project_lifetime: Project lifetime in years
        - voltage_kv: Voltage used in calculations (kV)
        - conductors_per_phase: Number of conductors per phase
        - number_of_phases: Number of phases
        - number_of_circuits_poles: Number of circuits/poles
        - phase_current: Phase current in Amps
        - full_load_adj: Full load adjustment factor
        - line_length: Line length in miles
    """
    project_details = load_project_technical_details()

    # Construct new category for resistance lookup
    from forge.scripts.utils.calculation_utils import build_category_string
    ctx = get_run_context()
    if ctx is None:
        raise RuntimeError(
            f"{__name__} requires a RunContext. Run via forge.py or set up "
            "RunContext in your test fixture."
        )
    new_category = ctx.category_string
    number_of_converters = ctx.number_of_converters

    line_length = load_physical_details()

    # For reconductoring: use old voltage (towers unchanged), but new resistance (new conductors)
    if project_details.project_type == "reconductoring":
        # Build old category to get old voltage (towers unchanged)
        project_data = get_project_data_raw()
        if "project" not in project_data:
            raise KeyError("Missing 'project' key in project technical details")
        project = project_data["project"]
        old_capacity = project["old_capacity_mw"]
        old_conductor = project["old_conductor_type"]
        old_ac_dc = project["old_ac_dc"]
        from forge.scripts.utils.calculation_utils import get_converter_type
        old_converter = get_converter_type(old_ac_dc, project_details.converter_type)
        
        old_category = build_category_string(
            project_details.construction_type, old_ac_dc, old_capacity, old_conductor, old_converter
        )
        old_circuit = load_circuit_and_resistance_details(old_category)
        voltage_kv = old_circuit.voltage_kv
        # Still use NEW config's resistance values (new conductors)
        new_circuit = load_circuit_and_resistance_details(new_category)
        conductors_per_phase = new_circuit.conductors_per_phase
        number_of_phases = new_circuit.number_of_phases
        number_of_circuits_poles = new_circuit.number_of_circuits_poles
        AC_75_resistance = new_circuit.AC_75_resistance
        DC_20_resistance = new_circuit.DC_20_resistance
        alpha_20 = new_circuit.alpha_20
    else:
        # Greenfield: use new config's voltage
        circuit = load_circuit_and_resistance_details(new_category)
        voltage_kv = circuit.voltage_kv
        conductors_per_phase = circuit.conductors_per_phase
        number_of_phases = circuit.number_of_phases
        number_of_circuits_poles = circuit.number_of_circuits_poles
        AC_75_resistance = circuit.AC_75_resistance
        DC_20_resistance = circuit.DC_20_resistance
        alpha_20 = circuit.alpha_20

    # Convert capacity_mw to numeric (handle both int and string with MW suffix)
    if isinstance(project_details.capacity_mw, str):
        capacity_mw_numeric = int(project_details.capacity_mw.replace("MW", ""))
    else:
        capacity_mw_numeric = int(project_details.capacity_mw)

    # Calculate phase current and full load adjustment
    phase_current = calculate_phase_current(
        project_details.capacity_mw, voltage_kv, number_of_phases, number_of_circuits_poles, project_details.ac_dc
    )
    full_load_adj = full_load_adjusted(project_details.line_utilization)

    # Calculate line losses (includes percentage calculations)
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
        AC_75_resistance,
        DC_20_resistance,
        alpha_20,
        project_details.ac_dc,
        number_of_circuits_poles,
        conductors_per_phase,
        number_of_phases,
        line_length,
        project_details.project_lifetime,
        capacity_mw_numeric,
        project_details.line_utilization,
        voltage_kv,
        project_details.construction_type,
    )

    # Calculate converter losses (includes percentage calculation)
    (
        total_converter_losses_mw,
        total_converter_losses_mwh,
        converter_loss_percent,
    ) = calculate_converter_losses(
        number_of_converters,
        project_details.converter_type,
        project_details.line_utilization,
        capacity_mw_numeric,
        project_details.ac_dc,
        project_details.converter_loss_percentage,
    )

    # Total energy losses is the sum of line and converter losses
    total_losses_mwh_per_year = losses_mwh_per_year + total_converter_losses_mwh
    project_lifetime = project_details.project_lifetime
    # Appendix $E_{\text{totalloss,lifetime}}$: line lifetime + converter annual × lifetime
    total_lifetime_losses_mwh = lifetime_losses_mwh + (
        total_converter_losses_mwh * project_lifetime
    )

    return {
        "losses_mwh_per_year": losses_mwh_per_year,
        "lifetime_losses_mwh": lifetime_losses_mwh,
        "losses_mw_per_mile": losses_mw_per_mile,
        "resistance_per_mile": resistance_per_mile,
        "line_loss_per_mile_percent": line_loss_per_mile_percent,
        "total_line_loss_mw": total_line_loss_mw,
        "total_line_loss_percent": total_line_loss_percent,
        "total_converter_losses_mw": total_converter_losses_mw,
        "total_converter_losses_mwh": total_converter_losses_mwh,
        "converter_loss_percent": converter_loss_percent,
        "total_losses_mwh_per_year": total_losses_mwh_per_year,
        "total_lifetime_losses_mwh": total_lifetime_losses_mwh,
        "project_lifetime": project_lifetime,
        "voltage_kv": voltage_kv,
        "conductors_per_phase": conductors_per_phase,
        "number_of_phases": number_of_phases,
        "number_of_circuits_poles": number_of_circuits_poles,
        "phase_current": phase_current,
        "full_load_adj": full_load_adj,
        "line_length": line_length,
    }

def print_results(
    voltage_kv: float,
    conductors_per_phase: int,
    number_of_phases: int,
    number_of_circuits_poles: int,
    line_utilization_percent: float,
    line_length: float,
    phase_current: float,
    resistance_per_mile: float,
    full_load_adj: float,
    losses_mw_per_mile: float,
    line_loss_per_mile_percent: float,
    total_line_loss_mw: float,
    total_line_loss_percent: float,
    total_converter_losses_mw: float,
    converter_loss_percent: float,
    total_converter_losses_mwh: float,
    losses_mwh_per_year: float,
    total_lifetime_losses_mwh: float,
) -> None:
    """Print organized results in sections."""
    # System Configuration
    logger.info("=" * 60)
    logger.info("SYSTEM CONFIGURATION")
    logger.info("=" * 60)
    logger.info(f"Voltage: {voltage_kv} kV")
    logger.info(f"Conductors per phase/pole: {conductors_per_phase}")
    logger.info(f"Number of phases: {number_of_phases}")
    logger.info(f"Number of circuits/poles: {number_of_circuits_poles}")
    logger.info(f"Line utilization: {to_percent(line_utilization_percent):.1f}%")
    logger.info(f"Line length: {line_length:.2f} miles")
    logger.info(f"Phase current: {phase_current:,.2f} Amps")
    logger.info(f"Resistance: {resistance_per_mile} ohms/mile")
    logger.info(f"Full load adjustment: {full_load_adj:.4f}")
    logger.info("")

    # Line Loss Results
    logger.info("=" * 60)
    logger.info("LINE LOSS RESULTS")
    logger.info("=" * 60)
    logger.info(f"Line loss: {losses_mw_per_mile:.6f} MW/mile")
    logger.info(f"Line loss per mile: {line_loss_per_mile_percent:.4f}%")
    logger.info(f"Total line loss: {total_line_loss_mw:.4f} MW")
    logger.info(f"Total line loss %: {total_line_loss_percent:.4f}%")
    logger.info(f"Line losses MWh/yr: {losses_mwh_per_year:,.2f}")
    logger.info("")

    # Converter Loss Results
    logger.info("=" * 60)
    logger.info("CONVERTER LOSS RESULTS")
    logger.info("=" * 60)
    logger.info(f"Converter loss: {total_converter_losses_mw:.6f} MW")
    logger.info(f"Converter loss: {converter_loss_percent:.4f}%")
    logger.info(f"Converter loss MWh/yr: {total_converter_losses_mwh:,.2f}")
    logger.info("")

    # Summary
    logger.info("=" * 60)
    logger.info("SUMMARY")
    logger.info("=" * 60)
    logger.info(
        f"Total losses MWh/yr: {losses_mwh_per_year + total_converter_losses_mwh:,.2f}"
    )
    logger.info(
        f"Total Lifetime losses MWh: {total_lifetime_losses_mwh:,.2f}"
    )

def main() -> None:
    """
    Main function to calculate and display transmission line energy losses.

    This script calculates electrical losses (I²R losses) for transmission lines, including:
    - Line losses: Resistive losses in conductors based on phase current, resistance, and line length
    - Converter losses: Losses in DC converter stations (for DC projects only)

    The calculation uses project technical details (voltage, capacity, conductor type, etc.) and
    physical details (line length, terrain) to determine:
    - Phase current based on capacity and voltage
    - Full load adjustment factor based on line utilization
    - Annual and lifetime energy losses in MWh
    - Loss percentages (per mile and total)

    Results are printed to console in organized sections showing system configuration,
    line loss results, converter loss results, and summary totals.

    Outputs:
        - Prints system configuration (voltage, conductors, phases, etc.)
        - Prints line loss results (MW, MWh/yr, percentages)
        - Prints converter loss results (for DC projects)
        - Prints summary totals (combined losses)
    """
    # Get all loss calculation results
    loss_data = get_total_energy_losses()

    from forge.scripts.utils.run_context import add_derived
    add_derived({
        "voltage_kv": loss_data["voltage_kv"],
        "phase_current": loss_data["phase_current"],
        "full_load_adj": loss_data["full_load_adj"],
        "losses_mwh_per_year": loss_data["losses_mwh_per_year"],
        "total_converter_losses_mwh": loss_data["total_converter_losses_mwh"],
        "total_losses_mwh_per_year": loss_data["total_losses_mwh_per_year"],
    })

    # Load line utilization for printing
    project_details = load_project_technical_details()

    # Print all results in organized sections
    print_results(
        loss_data["voltage_kv"],
        loss_data["conductors_per_phase"],
        loss_data["number_of_phases"],
        loss_data["number_of_circuits_poles"],
        project_details.line_utilization,
        loss_data["line_length"],
        loss_data["phase_current"],
        loss_data["resistance_per_mile"],
        loss_data["full_load_adj"],
        loss_data["losses_mw_per_mile"],
        loss_data["line_loss_per_mile_percent"],
        loss_data["total_line_loss_mw"],
        loss_data["total_line_loss_percent"],
        loss_data["total_converter_losses_mw"],
        loss_data["converter_loss_percent"],
        loss_data["total_converter_losses_mwh"],
        loss_data["losses_mwh_per_year"],
        loss_data["total_lifetime_losses_mwh"],
    )

if __name__ == "__main__":
    main()
