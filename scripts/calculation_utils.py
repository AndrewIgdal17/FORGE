# Author: Andrew Igdal
# Date: 2025-01-XX
# Description: Shared calculation utility functions for transmission line calculations.

from __future__ import annotations

import math
from typing import Union, Tuple, Optional, Any
from constants import (
    HOURS_PER_YEAR,
    LCC_CONVERTER_LOSS,
    VSC_CONVERTER_LOSS,
    AC_POWER_FACTOR,
    TRANSMISSION_TYPE_AC,
    TRANSMISSION_TYPE_DC,
    CONVERTER_TYPE_NA,
)


def to_percent(decimal: float) -> float:
    """
    Convert decimal (0-1) to percentage (0-100).

    Args:
        decimal: Decimal value between 0 and 1

    Returns:
        float: Percentage value between 0 and 100
    """
    return decimal * 100


def from_percent(percentage: float) -> float:
    """
    Convert percentage (0-100) to decimal (0-1).

    Args:
        percentage: Percentage value between 0 and 100

    Returns:
        float: Decimal value between 0 and 1
    """
    return percentage / 100


def normalize_capacity_mw(capacity_mw: Union[int, str]) -> int:
    """
    Normalize capacity_mw to always return an integer.

    Handles:
    - int: Returns as-is
    - str with "MW" suffix: Strips "MW" and converts to int
    - str numeric: Converts to int

    Args:
        capacity_mw: Capacity value (int or str)

    Returns:
        int: Normalized capacity in MW

    Raises:
        ValueError: If value cannot be converted to int
    """
    if isinstance(capacity_mw, int):
        return capacity_mw
    if isinstance(capacity_mw, str):
        # Strip "MW" suffix if present (case-insensitive)
        cleaned = capacity_mw.upper().replace("MW", "").strip()
        if not cleaned:  # Empty string after cleaning
            raise ValueError(f"Cannot convert empty capacity_mw to int: {capacity_mw}")
        return int(cleaned)
    raise ValueError(f"Cannot convert capacity_mw to int: {capacity_mw}")


def calculate_phase_current(
    capacity_mw: Union[int, str],
    voltage_kv: float,
    number_of_phases: int,
    number_of_circuits_poles: int,
    ac_dc: str,
) -> float:
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

    if ac_dc == TRANSMISSION_TYPE_AC:
        denominator = (
            AC_POWER_FACTOR
            * voltage_kv
            * math.sqrt(number_of_phases)
            * number_of_circuits_poles
        )
    else:
        denominator = (
            voltage_kv * math.sqrt(number_of_phases) * number_of_circuits_poles
        )

    return numerator / denominator


def full_load_adjusted(line_utilization_percent: float) -> float:
    """
    Calculate full load adjustment based on line utilization.

    Args:
        line_utilization_percent: Line utilization as a percentage (0-100)

    Returns:
        float: Full load adjustment factor
    """
    return (line_utilization_percent + line_utilization_percent**2) / 2


def calculate_line_losses(
    phase_current: float,
    full_load_adj: float,
    AC_75_resistance: float,
    DC_20_resistance: float,
    ac_dc: str,
    number_of_circuits_poles: int,
    conductors_per_phase: int,
    number_of_phases: int,
    line_length: float,
    project_lifetime: int,
    capacity_mw_numeric: int,
    line_utilization_percent: float,
) -> Tuple[float, float, float, float, float, float, float]:
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
    resistance_per_mile = (
        AC_75_resistance if ac_dc == TRANSMISSION_TYPE_AC else DC_20_resistance
    )

    losses_mw_per_mile = (
        ((phase_current / conductors_per_phase) ** 2)
        * number_of_conductors
        * resistance_per_mile
        * (full_load_adj / 1000000)
    )

    total_line_loss_mw = losses_mw_per_mile * line_length

    line_loss_per_mile_percent = to_percent(
        losses_mw_per_mile / (capacity_mw_numeric * line_utilization_percent)
    )
    total_line_loss_percent = to_percent(
        total_line_loss_mw / (capacity_mw_numeric * line_utilization_percent)
    )

    losses_mwh_per_year = total_line_loss_mw * HOURS_PER_YEAR
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
    number_of_converters: int,
    converter_type: str,
    line_utilization_percent: float,
    capacity_mw_numeric: int,
    ac_dc: str,
    converter_loss_percentage: float | None = None,
) -> Tuple[float, float, float]:
    """
    Calculate converter losses based on number of converters.

    Args:
        number_of_converters: Number of converters
        converter_type: Converter type (LCC or VSC)
        line_utilization_percent: Line utilization as decimal (0-1)
        capacity_mw_numeric: Capacity in MW as numeric value
        ac_dc: "AC" or "DC" string
        converter_loss_percentage: Optional converter loss percentage. If None, defaults to
            LCC_CONVERTER_LOSS for LCC converters or VSC_CONVERTER_LOSS for VSC converters.

    Returns:
        tuple: (total_converter_losses_mw, total_converter_losses_mwh, converter_loss_percent)
    """
    if ac_dc == TRANSMISSION_TYPE_DC:
        if converter_loss_percentage is None:
            converter_loss_percentage = (
                LCC_CONVERTER_LOSS if "LCC" in converter_type else VSC_CONVERTER_LOSS
            )
        converter_losses_mw = (
            converter_loss_percentage * line_utilization_percent * capacity_mw_numeric
        )
        total_converter_losses_mw = converter_losses_mw * number_of_converters
        converter_loss_percent = to_percent(
            total_converter_losses_mw / (capacity_mw_numeric * line_utilization_percent)
        )
        total_converter_losses_mwh = total_converter_losses_mw * HOURS_PER_YEAR
    else:
        total_converter_losses_mw = 0
        total_converter_losses_mwh = 0
        converter_loss_percent = 0

    return total_converter_losses_mw, total_converter_losses_mwh, converter_loss_percent


def miles_to_acres(miles: float, row_width_feet: float) -> float:
    """Convert miles of ROW to acres.

    Args:
        miles: Length in miles
        row_width_feet: Width of right-of-way in feet

    Returns:
        Area in acres
    """
    from constants import FEET_PER_MILE, SQUARE_FEET_PER_ACRE

    return (miles * FEET_PER_MILE * row_width_feet) / SQUARE_FEET_PER_ACRE


def build_category_string(
    construction_type: Optional[str] = None,
    ac_dc: Optional[str] = None,
    capacity_mw: Optional[Union[int, str]] = None,
    conductor_type: Optional[str] = None,
    converter_type: Optional[str] = None,
    project_details: Optional[Any] = None,
) -> str:
    """
    Build project category string for YAML/JSON lookups.

    Category format: "{construction_type}/{ac_dc}/{capacity_mw}MW/{conductor_type}/{converter_type}"

    Args:
        construction_type: Construction type (Overhead, Underground, Subsea)
        ac_dc: "AC" or "DC"
        capacity_mw: Capacity in MW (int or str, with/without "MW" suffix)
        conductor_type: Conductor type
        converter_type: Converter type (or "NA" for AC)
        project_details: Optional ProjectTechnicalDetails-like object with attributes:
            construction_type, ac_dc, capacity_mw, conductor_type, converter_type
            If provided, individual parameters are ignored.

    Returns:
        Formatted category string

    Examples:
        >>> build_category_string("Overhead", "AC", 500, "ACSR", "NA")
        "Overhead/AC/500MW/ACSR/NA"

        >>> build_category_string(project_details=project_details)
        "Overhead/AC/500MW/ACSR/NA"
    """
    # If project_details is provided, extract attributes from it
    if project_details is not None:
        construction_type = project_details.construction_type
        ac_dc = project_details.ac_dc
        capacity_mw = project_details.capacity_mw
        conductor_type = project_details.conductor_type
        converter_type = project_details.converter_type

    # Validate required parameters
    if (
        construction_type is None
        or ac_dc is None
        or capacity_mw is None
        or conductor_type is None
        or converter_type is None
    ):
        raise ValueError(
            "build_category_string requires construction_type, ac_dc, capacity_mw, "
            "conductor_type, and converter_type (either as parameters or via project_details)"
        )

    # Normalize capacity_mw to int
    capacity_mw_normalized = normalize_capacity_mw(capacity_mw)

    # Build and return category string
    return f"{construction_type}/{ac_dc}/{capacity_mw_normalized}MW/{conductor_type}/{converter_type}"


def get_converter_type(ac_dc: str, converter_type: str) -> str:
    """
    Get converter type, returning "NA" for AC projects.

    Args:
        ac_dc: "AC" or "DC"
        converter_type: Converter type (for DC projects) or any value (ignored for AC)

    Returns:
        "NA" if ac_dc == "AC", otherwise returns converter_type

    Examples:
        >>> get_converter_type("AC", "LCC")
        "NA"
        >>> get_converter_type("DC", "LCC")
        "LCC"
    """
    return CONVERTER_TYPE_NA if ac_dc == TRANSMISSION_TYPE_AC else converter_type


def normalize_construction_type_for_yaml(
    construction_type: str, context: str = "default"
) -> str:
    """
    Normalize construction type string to YAML key format.

    Handles various input formats:
    - "Overhead" -> "overhead"
    - "Underground" -> "underground" (or "underground_direct_buried" for environmental)
    - "Underground direct-buried" -> "underground" (or "underground_direct_buried" for environmental)
    - "Subsea" -> "subsea"

    Args:
        construction_type: Construction type string (case-insensitive)
        context: Context for mapping ("default", "environmental")
                 - "default": Maps underground variants to "underground"
                 - "environmental": Maps "Underground" to "underground_direct_buried"

    Returns:
        str: Normalized YAML key (lowercase, standardized)
    """
    construction_type_lower = construction_type.lower()

    if "subsea" in construction_type_lower:
        return "subsea"
    elif "underground" in construction_type_lower:
        if context == "environmental":
            return "underground_direct_buried"
        else:
            return "underground"
    else:
        return "overhead"  # Default
