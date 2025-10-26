# Author: Andrew Igdal
# Date: 2025-10-27
# Descriptions: This script calculates transmission line losses


import yaml
import math


def load_project_technical_details():
    """
    Load project technical details and construct category identifier.

    The category identifier follows the format:
    "construction_type/AC_or_DC/capacity_MW/conductor_type/converter_type"

    Returns:
        tuple: (category, delay_year, construction_years, project_lifetime, reconductoring)
    """
    with open("../yamls/01_project_technical_details.yaml", "r") as file:
        project_details = yaml.load(file, Loader=yaml.FullLoader)

    # Extract project specifications
    construction_type = project_details["project"]["construction_type"]
    ac_dc = project_details["project"]["ac_dc"]
    capacity_mw = f"{project_details['project']['capacity_mw']}MW"
    conductor_type = project_details["project"]["conductor_type"]

    if ac_dc == "AC":
        converter_type = "NA"
    else:
        converter_type = project_details["project"]["converter_type"]

    reconductoring = project_details["project"]["reconductoring"]

    line_utilization_percent = project_details["project"]["line_utilization"]

    number_of_converters = project_details["project"]["number_of_converters"]

    # Construct category identifier for row width lookup
    category = (
        f"{construction_type}/{ac_dc}/{capacity_mw}/{conductor_type}/{converter_type}"
    )

    # Extract timeline information
    delay_year = project_details["timeline"]["delay_years"]
    construction_years = project_details["timeline"]["construction_years"]
    project_lifetime = project_details["timeline"]["project_lifetime"]

    return (
        category,
        delay_year,
        construction_years,
        project_lifetime,
        reconductoring,
        line_utilization_percent,
        ac_dc,
        capacity_mw,
        number_of_converters,
        converter_type,
    )


def load_physical_details():
    """
    Load physical project details and calculate total miles.

    Returns:
        float: Total miles of transmission line across all terrain types
    """
    with open("../yamls/02_project_physical_details.yaml", "r") as file:
        physical_details = yaml.load(file, Loader=yaml.FullLoader)

    # Sum miles across all terrain types to get total line length
    line_length = sum(physical_details["terrain"]["terrain_miles"].values())
    return line_length


def load_circuit_and_resistance_details(category):
    """
    Load circuit and resistance details and construct category identifier.

    The category identifier follows the format:
    "construction_type/AC_or_DC/capacity_MW/conductor_type/converter_type"
    category: (category)
    Returns:
        tuple: (voltage_kv, conductors_per_phase, number_of_phases, number_of_circuits_poles, AC_75_resistance, DC_20_resistance)
    """
    with open(
        "../yamls/21_project_category_circuit_and_resistance_detail.yaml", "r"
    ) as file:
        circuit_and_resistance_details = yaml.load(file, Loader=yaml.FullLoader)[
            "project_categories_circuit_and_resistance_details"
        ]

    # Extract circuit and resistance details
    voltage_kv = circuit_and_resistance_details[category]["voltage_kv"]
    conductors_per_phase = circuit_and_resistance_details[category][
        "conductors_per_phase"
    ]
    number_of_phases = circuit_and_resistance_details[category]["number_of_phases"]
    number_of_circuits_poles = circuit_and_resistance_details[category][
        "number_of_circuits_poles"
    ]
    AC_75_resistance = circuit_and_resistance_details[category]["AC_75_resistance"]
    DC_20_resistance = circuit_and_resistance_details[category]["DC_20_resistance"]

    return (
        voltage_kv,
        conductors_per_phase,
        number_of_phases,
        number_of_circuits_poles,
        AC_75_resistance,
        DC_20_resistance,
    )


def calculate_phase_current(
    capacity_mw, voltage_kv, number_of_phases, number_of_circuits_poles, ac_dc
):
    """
    Calculate phase current based on AC or DC transmission type.

    Args:
        capacity_mw: Line capacity in MW
        voltage_kv: Voltage in kV
        number_of_phases: Number of phases
        number_of_circuits_poles: Number of circuits/poles per line
        ac_dc: "AC" or "DC" string

    Returns:
        Phase current in Amps
    """

    # need to drop the text MW from capacity_MW so its just a int
    capacity_mw = int(capacity_mw.replace("MW", ""))
    numerator = capacity_mw * 1000

    if ac_dc == "AC":
        # Equation (4): AC phase current
        denominator = (
            0.95 * voltage_kv * math.sqrt(number_of_phases) * number_of_circuits_poles
        )
    else:
        # Equation (5): DC phase current
        denominator = (
            voltage_kv * math.sqrt(number_of_phases) * number_of_circuits_poles
        )

    phase_current = numerator / denominator

    return phase_current


def full_load_adjusted(line_utilization_percent):
    """
    Calculate full load adjustment based on line utilization.

    Args:
        line_utilization_percent: Line utilization as a percentage (0-100)

    Returns:
        Full load adjustment factor
    """
    # Equation (6): Full load adjustment
    full_load_adj = (line_utilization_percent + line_utilization_percent**2) / 2

    return full_load_adj


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

    # Get number of conductors
    number_of_conductors = (
        conductors_per_phase * number_of_phases * number_of_circuits_poles
    )

    # calculate resistance per mile
    if ac_dc == "AC":
        resistance_per_mile = AC_75_resistance
    else:
        resistance_per_mile = DC_20_resistance

    # losses I^2 * R adjusted by load factor
    losses_mw_per_mile = (
        ((phase_current / conductors_per_phase) ** 2)
        * number_of_conductors
        * resistance_per_mile
        * (full_load_adj / 1000000)
    )  # Convert to MW

    # losses along the length of the line
    total_line_loss_mw = losses_mw_per_mile * line_length

    # Calculate loss percentages
    line_loss_per_mile_percent = (
        losses_mw_per_mile / (capacity_mw_numeric * line_utilization_percent)
    ) * 100
    total_line_loss_percent = (
        total_line_loss_mw / (capacity_mw_numeric * line_utilization_percent)
    ) * 100

    # losses mwh/yr 8760 hours/year
    losses_mwh_per_year = total_line_loss_mw * 8760

    # lifetime losses mwh
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
        capacity_mw_numeric: Capacity in MW as numeric value
    """
    if ac_dc == "DC":
        # Get converter resistance
        if "LCC" in converter_type:
            converter_loss_percentage = 0.0075
        else:
            converter_loss_percentage = 0.01

        converter_losses_mw = (
            converter_loss_percentage * line_utilization_percent * capacity_mw_numeric
        )

        total_converter_losses_mw = converter_losses_mw * number_of_converters

        # Calculate converter loss percentage
        converter_loss_percent = (
            total_converter_losses_mw / (capacity_mw_numeric * line_utilization_percent)
        ) * 100

        total_converter_losses_mwh = total_converter_losses_mw * 8760
    else:
        total_converter_losses_mw = 0
        total_converter_losses_mwh = 0
        converter_loss_percent = 0

    return total_converter_losses_mw, total_converter_losses_mwh, converter_loss_percent


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
        category,
        delay_year,
        construction_years,
        project_lifetime,
        reconductoring,
        line_utilization_percent,
        ac_dc,
        capacity_mw,
        number_of_converters,
        converter_type,
    ) = load_project_technical_details()
    line_length = load_physical_details()
    (
        voltage_kv,
        conductors_per_phase,
        number_of_phases,
        number_of_circuits_poles,
        AC_75_resistance,
        DC_20_resistance,
    ) = load_circuit_and_resistance_details(category)
    # Convert capacity_mw to numeric early
    capacity_mw_numeric = int(capacity_mw.replace("MW", ""))

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
