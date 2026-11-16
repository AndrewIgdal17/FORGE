# Date: 2025-10-27
# Descriptions: This script calculates transmission line losses

from __future__ import annotations

import logging
from dataclasses import dataclass

# Local utility imports
from forge.errors import InvalidInputs
from forge.scripts.utils.smart_loaders import (
    load_project_technical_details,
    load_physical_details,
    load_circuit_and_resistance_details,
    get_project_data_raw,
)
from forge.scripts.utils.calculation_utils import (
    build_category_string,
    calculate_phase_current,
    full_load_adjusted,
    calculate_line_losses,
    calculate_converter_losses,
    get_converter_type,
    to_percent,
)
from forge.scripts.utils.run_context import get_run_context

logger = logging.getLogger(__name__)

_PROJECT_PREFIX = "01_project_technical_details.project."


@dataclass(frozen=True)
class ReplacedConfiguration:
    ac_dc: str
    capacity_mw: int
    conductor_type: str
    converter_type: str
    number_of_converters: int


def load_replaced_configuration() -> ReplacedConfiguration | None:
    """Old line configuration for reconductoring or rebuild; None for greenfield."""
    details = load_project_technical_details()
    if details.project_type == "greenfield":
        return None
    project = get_project_data_raw()["project"]
    missing: list[str] = []
    old_capacity_mw = project.get("old_capacity_mw")
    old_conductor_type = project.get("old_conductor_type")
    old_ac_dc = project.get("old_ac_dc")
    if old_capacity_mw is None:
        missing.append("old_capacity_mw")
    if old_conductor_type is None:
        missing.append("old_conductor_type")
    if old_ac_dc is None:
        missing.append("old_ac_dc")
    old_converter_type = project.get("old_converter_type")
    if old_ac_dc == "DC" and old_converter_type is None:
        missing.append("old_converter_type")
    if missing:
        path = _PROJECT_PREFIX + missing[0]
        raise InvalidInputs(f"{path} is required.")
    assert old_ac_dc is not None
    assert old_capacity_mw is not None
    assert old_conductor_type is not None
    if old_ac_dc == "DC":
        conv_type = get_converter_type("DC", old_converter_type)
        ctx = get_run_context()
        if ctx is None:
            raise RuntimeError(
                f"{__name__} requires a RunContext. Run via forge.py or set up "
                "RunContext in your test fixture."
            )
        num_converters = ctx.number_of_converters
    else:
        conv_type = "NA"
        num_converters = 0
    return ReplacedConfiguration(
        ac_dc=old_ac_dc,
        capacity_mw=int(old_capacity_mw),
        conductor_type=old_conductor_type,
        converter_type=conv_type,
        number_of_converters=num_converters,
    )


def configuration_losses(
    construction_type: str,
    ac_dc: str,
    capacity_mw: int,
    conductor_type: str,
    converter_type: str,
    number_of_converters: int,
    line_utilization: float,
    converter_loss_percentage: float | None,
    project_lifetime: int,
) -> tuple[float, float]:
    """Annual line and converter MWh at this category's voltage (no overrides)."""
    category = build_category_string(
        construction_type, ac_dc, capacity_mw, conductor_type, converter_type
    )
    line_length = load_physical_details()
    circuit = load_circuit_and_resistance_details(category)
    voltage_kv = circuit.voltage_kv
    capacity_mw_str = f"{capacity_mw}MW"
    phase_current = calculate_phase_current(
        capacity_mw_str,
        voltage_kv,
        circuit.number_of_phases,
        circuit.number_of_circuits_poles,
        ac_dc,
    )
    full_load_adj = full_load_adjusted(line_utilization)
    losses_mwh_per_year, *_rest = calculate_line_losses(
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
        line_utilization,
        voltage_kv,
        construction_type,
    )
    _conv_mw, converter_mwh, _conv_pct = calculate_converter_losses(
        number_of_converters,
        converter_type,
        line_utilization,
        capacity_mw,
        ac_dc,
        converter_loss_percentage,
    )
    return losses_mwh_per_year, converter_mwh


def net_energy_losses() -> dict:
    """Net annual MWh (new minus old) for reconductoring and rebuild projects."""
    details = load_project_technical_details()
    new_data = get_total_energy_losses()
    line_mwh_new = new_data["losses_mwh_per_year"]
    converter_mwh_new = new_data["total_converter_losses_mwh"]
    ctx = get_run_context()
    if ctx is None:
        raise RuntimeError(
            f"{__name__} requires a RunContext. Run via forge.py or set up "
            "RunContext in your test fixture."
        )
    replaced = load_replaced_configuration()
    new_dc = details.ac_dc == "DC" and ctx.number_of_converters > 0
    if replaced is None:
        return {
            "replaced": False,
            "line_mwh_new": line_mwh_new,
            "line_mwh_old": 0.0,
            "line_mwh": line_mwh_new,
            "converter_mwh_new": converter_mwh_new,
            "converter_mwh_old": 0.0,
            "converter_mwh": converter_mwh_new,
            "total_mwh": line_mwh_new + converter_mwh_new,
            "converters_apply": new_dc,
        }
    line_mwh_old, converter_mwh_old = configuration_losses(
        details.construction_type,
        replaced.ac_dc,
        replaced.capacity_mw,
        replaced.conductor_type,
        replaced.converter_type,
        replaced.number_of_converters,
        details.line_utilization,
        details.converter_loss_percentage,
        details.project_lifetime,
    )
    line_mwh = line_mwh_new - line_mwh_old
    converter_mwh = converter_mwh_new - converter_mwh_old
    old_dc = replaced.ac_dc == "DC" and replaced.number_of_converters > 0
    return {
        "replaced": True,
        "line_mwh_new": line_mwh_new,
        "line_mwh_old": line_mwh_old,
        "line_mwh": line_mwh,
        "converter_mwh_new": converter_mwh_new,
        "converter_mwh_old": converter_mwh_old,
        "converter_mwh": converter_mwh,
        "total_mwh": line_mwh + converter_mwh,
        "converters_apply": new_dc or old_dc,
    }


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
        replaced = load_replaced_configuration()
        if replaced is None:
            raise RuntimeError("reconductoring project missing replaced configuration")
        old_category = build_category_string(
            project_details.construction_type,
            replaced.ac_dc,
            replaced.capacity_mw,
            replaced.conductor_type,
            replaced.converter_type,
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
