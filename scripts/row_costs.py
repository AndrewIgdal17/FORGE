# Author: Andrew Igdal
# Date: 2025-10-20
# Description: This script calculates the right-of-way costs for a transmission line.
#              It computes acquisition, holding, and rental costs for transmission line ROW
#              across different zones and terrain types, then calculates present values.

# Standard library imports
import yaml

# Local utility imports
from yaml_loaders import (
    load_project_technical_details,
    load_physical_details,
    load_row_widths,
    load_row_details,
    load_financing_details,
)
from financial_utils import calculate_present_value


def calculate_zone_costs(row_width_feet):
    """Calculate ROW costs for each zone where the transmission line passes."""
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


def main():
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

    # Define timing parameters
    rent_start_year = delay_year + 1
    rent_total_years = project_lifetime + construction_years

    if reconductoring:
        total_holding_cost = 0
        acquisition_cost = 0
        total_rent_cost = yearly_rent_cost * (project_lifetime + construction_years)
        total_nominal_cost = total_holding_cost + acquisition_cost + total_rent_cost

        # present values
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
        # Calculate present values of all costs
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
    print("=" * 60)
    print("RIGHT-OF-WAY COST CALCULATION RESULTS")
    print("=" * 60)
    print(f"Project Category: {category}")
    print(f"Total Miles: {total_miles:.2f}")
    print(f"Row Width: {row_width_feet:.1f} feet")
    print(f"Total Acres: {total_acres:.2f}")
    print()

    print("NOMINAL VALUES (undiscounted):")
    print(f"  Holding Cost: ${total_holding_cost:,.2f}")
    print(f"  Acquisition Cost: ${acquisition_cost:,.2f}")
    print(f"  Rent Cost: ${total_rent_cost:,.2f}")
    print()
    print(f"TOTAL NOMINAL ROW Cost: ${total_nominal_cost:,.2f}")
    print()

    print(
        f"PRESENT VALUES (discounted to base year (2025) using real WACC ({wacc_real:.2%})):"
    )
    print(f"  Holding Cost PV: ${total_holding_cost_pv:,.2f}")
    print(f"  Acquisition Cost PV: ${total_acquisition_cost_pv:,.2f}")
    print(f"  Rent Cost PV: ${total_rent_cost_pv:,.2f}")
    print()

    total_pv_cost = (
        total_holding_cost_pv + total_acquisition_cost_pv + total_rent_cost_pv
    )
    print(f"TOTAL PRESENT VALUE ROW COST: ${total_pv_cost:,.2f}")
    print("=" * 60)


if __name__ == "__main__":
    main()
