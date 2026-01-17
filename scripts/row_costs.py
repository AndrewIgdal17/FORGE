# Author: Andrew Igdal
# Date: 2025-10-20
# Description: This script calculates the right-of-way costs for a transmission line.
#              It computes acquisition, holding, and rental costs for transmission line ROW
#              across different zones and terrain types, then calculates present values.

from __future__ import annotations

# Standard library imports
import yaml
import sys
import os
from typing import Tuple

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from smart_output import CTCCOutputManager

# Local utility imports
from smart_loaders import (
    load_project_technical_details,
    load_physical_details,
    load_row_widths,
    load_row_details,
    load_financing_details,
    load_cost_timing_patterns,
    load_afudc_config,
    get_financing_data_raw,
)
from financial_utils import (
    calculate_present_value,
    calculate_afudc_rate,
    calculate_afudc_capitalized_cost,
    validate_discount_rate,
)
from path_config import YAMLS_DIR


def calculate_zone_costs(row_width_feet: float) -> Tuple[float, float, float, float]:
    """
    Calculate right-of-way (ROW) costs aggregated across all zones.

    This function calculates ROW costs by iterating through all zones defined in the
    ROW details YAML file. For each zone where the transmission line passes (miles > 0),
    it calculates the zone area in acres and multiplies by zone-specific cost rates
    for acquisition, annual rent, and annual holding costs.

    Zones represent different geographic or regulatory areas (e.g., urban, rural, protected)
    that may have different ROW cost structures. The function aggregates costs across
    all zones to get total project ROW costs.

    Args:
        row_width_feet: Width of the right-of-way in feet (used to calculate zone area)

    Returns:
        tuple: A 4-element tuple containing:
            - yearly_holding_cost: Total annual holding cost across all zones ($/yr)
            - acquisition_cost: Total one-time acquisition cost across all zones ($)
            - yearly_rent_cost: Total annual rental cost across all zones ($/yr)
            - total_acres: Total ROW area in acres across all zones

    Note:
        Zone area is calculated as: (miles * 5280 * row_width_feet) / 43560
        Only zones with miles > 0 are included in the calculation.
    """
    row_details = load_row_details()
    yearly_holding_cost = acquisition_cost = yearly_rent_cost = 0

    for zone_details in row_details["right_of_way"].values():
        if zone_details["miles"] > 0:
            zone_acres = (zone_details["miles"] * 5280 * row_width_feet) / 43560
            acquisition_cost += zone_acres * zone_details["acquisition_cost"]
            yearly_rent_cost += zone_acres * zone_details["rent_cost"]
            yearly_holding_cost += zone_acres * zone_details["hold_cost"]

    total_acres = sum(
        (zd["miles"] * 5280 * row_width_feet) / 43560
        for zd in row_details["right_of_way"].values()
        if zd["miles"] > 0
    )
    return yearly_holding_cost, acquisition_cost, yearly_rent_cost, total_acres


def main() -> None:
    """Main function to calculate and display ROW costs."""
    # Load project specifications and timeline
    (
        construction_type,
        ac_dc,
        capacity_mw,
        conductor_type,
        converter_type,
        line_utilization,
        reconductoring,
        delay_year,
        construction_years,
        project_lifetime,
        converter_loss_percentage,
    ) = load_project_technical_details()

    # Construct category identifier
    category = (
        f"{construction_type}/{ac_dc}/{capacity_mw}MW/{conductor_type}/{converter_type}"
    )

    # Load row width for this project category
    row_width_feet = load_row_widths(category)

    # Load physical details (total miles)
    total_miles = load_physical_details()

    # Calculate costs for each zone
    yearly_holding_cost, acquisition_cost, yearly_rent_cost, total_acres = (
        calculate_zone_costs(row_width_feet)
    )

    # Load financing parameters
    inflation_rate, base_year, wacc_nominal, wacc_real = load_financing_details()

    # Load AFUDC configuration and timing patterns
    timing_patterns = load_cost_timing_patterns()["cost_timing_patterns"]
    apply_afudc, delay_active = load_afudc_config()

    # Load full financing data for AFUDC rate calculation
    financing_yaml = get_financing_data_raw()
    afudc_rate, afudc_source = calculate_afudc_rate(financing_yaml)

    # Define timing parameters
    rent_start_year = delay_year + 1
    rent_total_years = project_lifetime + construction_years

    if reconductoring:
        total_holding_cost = 0
        acquisition_cost = 0
        total_rent_cost = yearly_rent_cost * (project_lifetime + construction_years)
        total_nominal_cost = total_holding_cost + acquisition_cost + total_rent_cost

        # ===== REGULATORY PERSPECTIVE: AFUDC Capitalization =====
        # No acquisition or holding costs for reconductoring
        # Rent is not AFUDC-eligible (operational expense)
        acquisition_capitalized = 0
        acquisition_afudc = 0

        # ===== SOCIETAL PERSPECTIVE: Present Values =====
        total_holding_cost_pv = 0
        total_acquisition_cost_pv = 0
        total_rent_cost_pv = calculate_present_value(
            yearly_rent_cost, wacc_real, int(rent_total_years), int(rent_start_year)
        )

    else:
        # Calculate total nominal costs over project lifetime
        total_holding_cost = yearly_holding_cost * delay_year
        total_rent_cost = yearly_rent_cost * (project_lifetime + construction_years)
        total_nominal_cost = total_holding_cost + acquisition_cost + total_rent_cost

        # ===== REGULATORY PERSPECTIVE: AFUDC Capitalization =====
        if apply_afudc:
            # Acquisition costs: AFUDC-eligible (capitalized to plant cost)
            acquisition_capitalized, acquisition_afudc = (
                calculate_afudc_capitalized_cost(
                    acquisition_cost,
                    timing_patterns["row_acquisition"],
                    delay_year,
                    construction_years,
                    afudc_rate,
                    delay_active,
                )
            )
            # Holding costs: NOT AFUDC-eligible (operating expense, not CWIP)
            # Rent costs: NOT AFUDC-eligible (operational period expense)
        else:
            acquisition_capitalized = acquisition_cost
            acquisition_afudc = 0

        # ===== SOCIETAL PERSPECTIVE: Present Values =====
        # Validate wacc_real before direct use to prevent division by zero
        validate_discount_rate(wacc_real, "wacc_real")

        # Holding costs: incurred annually during delay period
        total_holding_cost_pv = calculate_present_value(
            yearly_holding_cost, wacc_real, int(delay_year)
        )

        # Acquisition costs: one-time payment at end of delay period
        total_acquisition_cost_pv = acquisition_cost / (1 + wacc_real) ** delay_year

        # Rent costs: incurred annually during operation period
        total_rent_cost_pv = calculate_present_value(
            yearly_rent_cost, wacc_real, int(rent_total_years), int(rent_start_year)
        )

    # Display results
    print("=" * 80)
    print("RIGHT-OF-WAY COST CALCULATION RESULTS")
    print("=" * 80)
    print(f"Project Category: {category}")
    print(f"Total Miles: {total_miles:.2f}")
    print(f"Row Width: {row_width_feet:.1f} feet")
    print(f"Total Acres: {total_acres:.2f}")
    print()

    print("[NOMINAL VALUES]")
    print(f"  Holding Cost: ${total_holding_cost:,.2f}")
    print(f"    (Annual: ${yearly_holding_cost:,.2f} over {delay_year} year(s))")
    print(f"  Acquisition Cost: ${acquisition_cost:,.2f}")
    print(f"  Rent Cost: ${total_rent_cost:,.2f}")
    print(f"    (Annual: ${yearly_rent_cost:,.2f} over {rent_total_years} year(s))")
    print(f"  ---")
    print(f"  TOTAL NOMINAL ROW COST: ${total_nominal_cost:,.2f}")
    print()

    if apply_afudc and not reconductoring:
        print("[REGULATORY PERSPECTIVE - AFUDC Capitalization]")
        print(f"  AFUDC Rate: {afudc_rate:.2%} ({afudc_source})")
        print(f"  Delay Period Active Work: {'Yes' if delay_active else 'No'}")
        print()
        print(f"  Acquisition Cost Capitalized: ${acquisition_capitalized:,.2f}")
        print(f"    AFUDC on Acquisition: ${acquisition_afudc:,.2f}")
        print(f"  Holding Cost: ${total_holding_cost:,.2f}")
        print(f"    (NOT AFUDC-eligible - operating expense)")
        print(f"  Rent Cost: ${total_rent_cost:,.2f}")
        print(f"    (NOT AFUDC-eligible - operational period)")
        print(f"  ---")
        print(
            f"  TOTAL (Acquisition capitalized + holding + rent): ${acquisition_capitalized + total_holding_cost + total_rent_cost:,.2f}"
        )
        print()

    print("[SOCIETAL PERSPECTIVE - Present Value]")
    print(f"  Discount Rate: {wacc_real:.2%} (real WACC)")
    print(f"  Base Year: {base_year}")
    print()
    print(f"  Holding Cost PV: ${total_holding_cost_pv:,.2f}")
    print(f"  Acquisition Cost PV: ${total_acquisition_cost_pv:,.2f}")
    print(f"  Rent Cost PV: ${total_rent_cost_pv:,.2f}")
    print(f"  ---")

    total_pv_cost = (
        total_holding_cost_pv + total_acquisition_cost_pv + total_rent_cost_pv
    )
    print(f"  TOTAL PRESENT VALUE ROW COST: ${total_pv_cost:,.2f}")
    print("=" * 80)

    # ========================================================================
    # CSV OUTPUT - Write results to batch summary and detail CSV
    # ========================================================================

    # Initialize CSV output manager
    csv_manager = CTCCOutputManager()

    # Prepare results dictionary
    results = {
        "total_nominal": total_nominal_cost,
        "total_afudc": (
            acquisition_capitalized + total_holding_cost + total_rent_cost
            if (apply_afudc and not reconductoring)
            else 0
        ),
        "total_pv": total_pv_cost,
        "acquisition_nominal": acquisition_cost,
        "holding_nominal": total_holding_cost,
        "rent_nominal": total_rent_cost,
    }

    # Write to CSV
    csv_manager.add_row_costs(results)
    csv_manager.write_batch_summary()


if __name__ == "__main__":
    main()
