# Author: Andrew Igdal
# Date: 2025-10-27
# Descriptions: This script calculates transmission line losses

from __future__ import annotations

# Local utility imports
from smart_loaders import (
    load_project_technical_details,
    load_physical_details,
    load_circuit_and_resistance_details,
    get_project_data_raw,
)
from calculation_utils import (
    calculate_phase_current,
    full_load_adjusted,
    calculate_line_losses,
    calculate_converter_losses,
)
from path_config import YAMLS_DIR


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
        - project_lifetime: Project lifetime in years
        - voltage_kv: Voltage used in calculations (kV)
        - conductors_per_phase: Number of conductors per phase
        - number_of_phases: Number of phases
        - number_of_circuits_poles: Number of circuits/poles
        - phase_current: Phase current in Amps
        - full_load_adj: Full load adjustment factor
        - line_length: Line length in miles
    """
    (
        construction_type,
        ac_dc,
        capacity_mw,
        conductor_type,
        converter_type,
        line_utilization_percent,
        reconductoring,
        uses_existing_row,
        delay_year,
        construction_years,
        project_lifetime,
        converter_loss_percentage,
    ) = load_project_technical_details()

    # Construct new category for resistance lookup
    new_category = (
        f"{construction_type}/{ac_dc}/{capacity_mw}MW/{conductor_type}/{converter_type}"
    )

    # Get number of converters if DC
    if ac_dc == "DC":
        try:
            project_details_data = get_project_data_raw()
            if "project" not in project_details_data:
                raise KeyError(
                    "Missing 'project' key in project technical details"
                )
            if "number_of_converters" not in project_details_data["project"]:
                raise KeyError(
                    "Missing 'number_of_converters' key in project section of technical details"
                )
            number_of_converters = project_details_data["project"][
                "number_of_converters"
            ]
        except KeyError as e:
            raise KeyError(
                f"Missing required key in project technical details: {e}"
            )
    else:
        number_of_converters = 0

    line_length = load_physical_details()

    # For reconductoring: use old voltage (towers unchanged), but new resistance (new conductors)
    if reconductoring:
        # Build old category to get old voltage (towers unchanged)
        project_data = get_project_data_raw()
        if "project" not in project_data:
            raise KeyError("Missing 'project' key in project technical details")
        project = project_data["project"]
        old_capacity = project["old_capacity_mw"]
        old_conductor = project["old_conductor_type"]
        old_ac_dc = project["old_ac_dc"]
        old_converter = "NA" if old_ac_dc == "AC" else converter_type
        
        old_category = f"{construction_type}/{old_ac_dc}/{old_capacity}MW/{old_conductor}/{old_converter}"
        voltage_kv, _, _, _, _, _ = load_circuit_and_resistance_details(old_category)
        # Still use NEW config's resistance values (new conductors)
        _, conductors_per_phase, number_of_phases, number_of_circuits_poles, AC_75_resistance, DC_20_resistance = load_circuit_and_resistance_details(new_category)
    else:
        # Greenfield: use new config's voltage
        voltage_kv, conductors_per_phase, number_of_phases, number_of_circuits_poles, AC_75_resistance, DC_20_resistance = load_circuit_and_resistance_details(new_category)

    # Convert capacity_mw to numeric (handle both int and string with MW suffix)
    if isinstance(capacity_mw, str):
        capacity_mw_numeric = int(capacity_mw.replace("MW", ""))
    else:
        capacity_mw_numeric = int(capacity_mw)

    # Calculate phase current and full load adjustment
    phase_current = calculate_phase_current(
        capacity_mw, voltage_kv, number_of_phases, number_of_circuits_poles, ac_dc
    )
    full_load_adj = full_load_adjusted(line_utilization_percent)

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
        ac_dc,
        number_of_circuits_poles,
        conductors_per_phase,
        number_of_phases,
        line_length,
        project_lifetime,
        capacity_mw_numeric,
        line_utilization_percent,
    )

    # Calculate converter losses (includes percentage calculation)
    (
        total_converter_losses_mw,
        total_converter_losses_mwh,
        converter_loss_percent,
    ) = calculate_converter_losses(
        number_of_converters,
        converter_type,
        line_utilization_percent,
        capacity_mw_numeric,
        ac_dc,
        converter_loss_percentage,
    )

    # Total energy losses is the sum of line and converter losses
    total_losses_mwh_per_year = losses_mwh_per_year + total_converter_losses_mwh

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
    lifetime_losses_mwh: float,
    project_lifetime: int,
) -> None:
    """Print organized results in sections."""
    # System Configuration
    print("=" * 60)
    print("SYSTEM CONFIGURATION")
    print("=" * 60)
    print(f"Voltage: {voltage_kv} kV")
    print(f"Conductors per phase/pole: {conductors_per_phase}")
    print(f"Number of phases: {number_of_phases}")
    print(f"Number of circuits/poles: {number_of_circuits_poles}")
    print(f"Line utilization: {line_utilization_percent * 100:.1f}%")
    print(f"Line length: {line_length:.2f} miles")
    print(f"Phase current: {phase_current:,.2f} Amps")
    print(f"Resistance: {resistance_per_mile} ohms/mile")
    print(f"Full load adjustment: {full_load_adj:.4f}")
    print()

    # Line Loss Results
    print("=" * 60)
    print("LINE LOSS RESULTS")
    print("=" * 60)
    print(f"Line loss: {losses_mw_per_mile:.6f} MW/mile")
    print(f"Line loss per mile: {line_loss_per_mile_percent:.4f}%")
    print(f"Total line loss: {total_line_loss_mw:.4f} MW")
    print(f"Total line loss %: {total_line_loss_percent:.4f}%")
    print(f"Line losses MWh/yr: {losses_mwh_per_year:,.2f}")
    print()

    # Converter Loss Results
    print("=" * 60)
    print("CONVERTER LOSS RESULTS")
    print("=" * 60)
    print(f"Converter loss: {total_converter_losses_mw:.6f} MW")
    print(f"Converter loss: {converter_loss_percent:.4f}%")
    print(f"Converter loss MWh/yr: {total_converter_losses_mwh:,.2f}")
    print()

    # Summary
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(
        f"Total losses MWh/yr: {losses_mwh_per_year + total_converter_losses_mwh:,.2f}"
    )
    print(
        f"Total Lifetime losses MWh: {lifetime_losses_mwh + (total_converter_losses_mwh * project_lifetime):,.2f}"
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

    # Load line utilization for printing
    (
        _,
        _,
        _,
        _,
        _,
        line_utilization_percent,
        _,
        _,
        _,
        _,
        _,
        _,
    ) = load_project_technical_details()

    # Print all results in organized sections
    print_results(
        loss_data["voltage_kv"],
        loss_data["conductors_per_phase"],
        loss_data["number_of_phases"],
        loss_data["number_of_circuits_poles"],
        line_utilization_percent,
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
        loss_data["lifetime_losses_mwh"],
        loss_data["project_lifetime"],
    )


if __name__ == "__main__":
    main()
