# Author: Andrew Igdal
# Date: 2025-10-27
# Descriptions: This script calculates transmission line losses


# Local utility imports
from yaml_loaders import (
    load_project_technical_details,
    load_physical_details,
    load_circuit_and_resistance_details,
)
from calculation_utils import (
    calculate_phase_current,
    full_load_adjusted,
    calculate_line_losses,
    calculate_converter_losses,
)


def print_results(
    voltage_kv,
    conductors_per_phase,
    number_of_phases,
    number_of_circuits_poles,
    line_utilization_percent,
    line_length,
    phase_current,
    resistance_per_mile,
    full_load_adj,
    losses_mw_per_mile,
    line_loss_per_mile_percent,
    total_line_loss_mw,
    total_line_loss_percent,
    total_converter_losses_mw,
    converter_loss_percent,
    total_converter_losses_mwh,
    losses_mwh_per_year,
    lifetime_losses_mwh,
    project_lifetime,
):
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


def main():
    (
        construction_type,
        ac_dc,
        capacity_mw,
        conductor_type,
        converter_type,
        line_utilization_percent,
        reconductoring,
        delay_year,
        construction_years,
        project_lifetime,
        converter_loss_percentage,
    ) = load_project_technical_details()

    # Construct category locally
    category = (
        f"{construction_type}/{ac_dc}/{capacity_mw}MW/{conductor_type}/{converter_type}"
    )

    # Get number of converters if DC
    if ac_dc == "DC":
        import yaml

        with open("../yamls/01_project_technical_details.yaml", "r") as file:
            pd = yaml.load(file, Loader=yaml.FullLoader)
        number_of_converters = pd["project"]["number_of_converters"]
    else:
        number_of_converters = 0

    line_length = load_physical_details()
    (
        voltage_kv,
        conductors_per_phase,
        number_of_phases,
        number_of_circuits_poles,
        AC_75_resistance,
        DC_20_resistance,
    ) = load_circuit_and_resistance_details(category)
    # Convert capacity_mw to numeric early (handle both int and string with MW suffix)
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

    # Print all results in organized sections
    print_results(
        voltage_kv,
        conductors_per_phase,
        number_of_phases,
        number_of_circuits_poles,
        line_utilization_percent,
        line_length,
        phase_current,
        resistance_per_mile,
        full_load_adj,
        losses_mw_per_mile,
        line_loss_per_mile_percent,
        total_line_loss_mw,
        total_line_loss_percent,
        total_converter_losses_mw,
        converter_loss_percent,
        total_converter_losses_mwh,
        losses_mwh_per_year,
        lifetime_losses_mwh,
        project_lifetime,
    )


if __name__ == "__main__":
    main()
