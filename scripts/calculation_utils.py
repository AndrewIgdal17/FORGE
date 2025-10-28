# Author: Andrew Igdal
# Date: 2025-01-XX
# Description: Shared calculation utility functions for transmission line calculations.

import math


def calculate_phase_current(
    capacity_mw, voltage_kv, number_of_phases, number_of_circuits_poles, ac_dc
):
    """
    Calculate phase current based on AC or DC transmission type.

    Args:
        capacity_mw: Line capacity in MW (string or int)
        voltage_kv: Voltage in kV
        number_of_phases: Number of phases
        number_of_circuits_poles: Number of circuits/poles per line
        ac_dc: "AC" or "DC" string

    Returns:
        float: Phase current in Amps
    """
    if isinstance(capacity_mw, str):
        capacity_mw = int(capacity_mw.replace("MW", ""))
    numerator = capacity_mw * 1000

    if ac_dc == "AC":
        denominator = (
            0.95 * voltage_kv * math.sqrt(number_of_phases) * number_of_circuits_poles
        )
    else:
        denominator = (
            voltage_kv * math.sqrt(number_of_phases) * number_of_circuits_poles
        )

    return numerator / denominator


def full_load_adjusted(line_utilization_percent):
    """
    Calculate full load adjustment based on line utilization.

    Args:
        line_utilization_percent: Line utilization as a percentage (0-100)

    Returns:
        float: Full load adjustment factor
    """
    return (line_utilization_percent + line_utilization_percent**2) / 2


def calculate_line_losses(
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
):
    """
    Calculate line losses for transmission lines.

    Args:
        phase_current: Phase current in Amps
        full_load_adj: Full load adjustment factor
        AC_75_resistance: AC resistance at 75°C (ohms/mile)
        DC_20_resistance: DC resistance at 20°C (ohms/mile)
        ac_dc: "AC" or "DC" string
        number_of_circuits_poles: Number of circuits/poles
        conductors_per_phase: Number of conductors per phase
        number_of_phases: Number of phases
        line_length: Line length in miles
        project_lifetime: Project lifetime in years
        capacity_mw_numeric: Capacity in MW as numeric value
        line_utilization_percent: Line utilization as decimal (0-1)

    Returns:
        tuple: (losses_mwh_per_year, lifetime_losses_mwh, losses_mw_per_mile,
                resistance_per_mile, line_loss_per_mile_percent, total_line_loss_mw,
                total_line_loss_percent)
    """
    number_of_conductors = (
        conductors_per_phase * number_of_phases * number_of_circuits_poles
    )
    resistance_per_mile = AC_75_resistance if ac_dc == "AC" else DC_20_resistance

    losses_mw_per_mile = (
        ((phase_current / conductors_per_phase) ** 2)
        * number_of_conductors
        * resistance_per_mile
        * (full_load_adj / 1000000)
    )

    total_line_loss_mw = losses_mw_per_mile * line_length

    line_loss_per_mile_percent = (
        losses_mw_per_mile / (capacity_mw_numeric * line_utilization_percent)
    ) * 100
    total_line_loss_percent = (
        total_line_loss_mw / (capacity_mw_numeric * line_utilization_percent)
    ) * 100

    losses_mwh_per_year = total_line_loss_mw * 8760
    lifetime_losses_mwh = losses_mwh_per_year * project_lifetime

    return (
        losses_mwh_per_year,
        lifetime_losses_mwh,
        losses_mw_per_mile,
        resistance_per_mile,
        line_loss_per_mile_percent,
        total_line_loss_mw,
        total_line_loss_percent,
    )


def calculate_converter_losses(
    number_of_converters,
    converter_type,
    line_utilization_percent,
    capacity_mw_numeric,
    ac_dc,
):
    """
    Calculate converter losses based on number of converters.

    Args:
        number_of_converters: Number of converters
        converter_type: Converter type (LCC or VSC)
        line_utilization_percent: Line utilization as decimal (0-1)
        capacity_mw_numeric: Capacity in MW as numeric value
        ac_dc: "AC" or "DC" string

    Returns:
        tuple: (total_converter_losses_mw, total_converter_losses_mwh, converter_loss_percent)
    """
    if ac_dc == "DC":
        converter_loss_percentage = 0.0075 if "LCC" in converter_type else 0.01
        converter_losses_mw = (
            converter_loss_percentage * line_utilization_percent * capacity_mw_numeric
        )
        total_converter_losses_mw = converter_losses_mw * number_of_converters
        converter_loss_percent = (
            total_converter_losses_mw / (capacity_mw_numeric * line_utilization_percent)
        ) * 100
        total_converter_losses_mwh = total_converter_losses_mw * 8760
    else:
        total_converter_losses_mw = 0
        total_converter_losses_mwh = 0
        converter_loss_percent = 0

    return total_converter_losses_mw, total_converter_losses_mwh, converter_loss_percent
