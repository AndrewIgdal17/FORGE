# Author: Andrew Igdal
# Date: 2025-10-20
# Description: This script calculates the right-of-way costs for a transmission line.
#              ROW agreement type (permanent easement, lease/license, fee simple, federal/hybrid)
#              determines which cost terms apply; acquisition and annual ROW payment are
#              mutually exclusive unless the regime is federal_hybrid. Holding cost is an
#              option fee during delay; cost of capital on acquisition during delay is in AFUDC.

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
    calculate_growing_annuity_pv,
    calculate_nominal_growing_series,
    calculate_afudc_rate,
    calculate_afudc_capitalized_cost,
    validate_discount_rate,
)
from path_config import YAMLS_DIR


def calculate_zone_costs(row_width_feet: float) -> Tuple[float, float, float, float]:
    """
    Calculate right-of-way (ROW) costs aggregated across all zones.

    For each zone where the transmission line passes (miles > 0), computes zone
    area in acres and multiplies by zone-specific rates for acquisition,
    option fee (hold_cost), and annual ROW payment (rent_cost). The caller
    applies the ROW agreement type to zero out terms that do not apply.

    Args:
        row_width_feet: Width of the right-of-way in feet (used to calculate zone area)

    Returns:
        tuple: (yearly_holding_cost, acquisition_cost, yearly_rent_cost, total_acres)
        - yearly_holding_cost: Total annual option-fee cost across zones ($/yr)
        - acquisition_cost: Total one-time acquisition cost across zones ($)
        - yearly_rent_cost: Total annual ROW payment across zones ($/yr)
        - total_acres: Total ROW area in acres across all zones

    Note:
        Zone area = (miles * 5280 * row_width_feet) / 43560. Only zones with miles > 0.
    """
    from calculation_utils import miles_to_acres

    row_details = load_row_details()
    yearly_holding_cost = acquisition_cost = yearly_rent_cost = 0

    for zone_details in row_details["right_of_way"].values():
        if zone_details["miles"] > 0:
            zone_acres = miles_to_acres(zone_details["miles"], row_width_feet)
            acquisition_cost += zone_acres * zone_details["acquisition_cost"]
            yearly_rent_cost += zone_acres * zone_details["rent_cost"]
            yearly_holding_cost += zone_acres * zone_details["hold_cost"]

    total_acres = sum(
        miles_to_acres(zd["miles"], row_width_feet)
        for zd in row_details["right_of_way"].values()
        if zd["miles"] > 0
    )
    return yearly_holding_cost, acquisition_cost, yearly_rent_cost, total_acres


def main() -> None:
    """Main function to calculate and display ROW costs."""
    # Load project specifications and timeline
    project_details = load_project_technical_details()

    # Construct category identifier
    from calculation_utils import build_category_string

    category = build_category_string(project_details=project_details)

    # Load row width for this project category
    row_width_feet = load_row_widths(category)

    # Load physical details (total miles)
    total_miles = load_physical_details()

    # Calculate costs for each zone (potential acquisition, holding, annual ROW payment)
    yearly_holding_cost, acquisition_cost, yearly_rent_cost, total_acres = (
        calculate_zone_costs(row_width_feet)
    )

    # ROW agreement type: drives which terms apply (mutual exclusivity)
    agreement_type = getattr(project_details, "row_agreement_type", None) or (
        "lease_license_existing"
        if (project_details.reconductoring or project_details.uses_existing_row)
        else "permanent_easement_new"
    )
    if agreement_type == "lease_license_existing":
        acquisition_cost = 0.0
        yearly_holding_cost = 0.0
    elif agreement_type in ("permanent_easement_new", "fee_simple"):
        yearly_rent_cost = 0.0
    # federal_hybrid: keep all three (acquisition, holding, annual ROW payment)

    from run_context import add_derived
    from calculation_utils import miles_to_acres
    _row_details = load_row_details()
    _zone_acres = {
        zname: miles_to_acres(zd["miles"], row_width_feet)
        for zname, zd in _row_details["right_of_way"].items()
        if zd["miles"] > 0
    }
    add_derived({
        "zone_acres": _zone_acres,
        "total_row_acres": total_acres,
        "agreement_type": agreement_type,
    })

    # Real annual escalation applied to ROW rent and holding cost (default 0% real,
    # backward-compatible with pre-escalation YAMLs).
    g_rent = float(_row_details.get("row_rent_escalation_real", 0.0))

    # Load financing parameters
    financing = load_financing_details()

    # Load AFUDC configuration and timing patterns
    from financial_utils import load_afudc_setup

    afudc_setup = load_afudc_setup()

    # Define timing for annual ROW payment (rent). Lease/license rent runs from
    # year 1 (rent_start_year == 1); other agreement types start rent at
    # calculate_construction_start_year(delay_years) == delay_years + 1, i.e.
    # once the delay period ends.
    if agreement_type == "lease_license_existing":
        rent_total_years = (
            project_details.delay_years
            + project_details.construction_years
            + project_details.project_lifetime
        )
    else:
        rent_total_years = (
            project_details.project_lifetime + project_details.construction_years
        )

    if agreement_type == "lease_license_existing":
        total_holding_cost = 0.0
        acquisition_cost_used = 0.0  # no acquisition for lease/license
        total_rent_cost = calculate_nominal_growing_series(
            yearly_rent_cost,
            g_rent,
            rent_total_years,
        )
        total_nominal_cost = (
            total_holding_cost + acquisition_cost_used + total_rent_cost
        )

        acquisition_capitalized = 0.0
        acquisition_afudc = 0.0
        holding_capitalized = 0.0
        holding_afudc = 0.0
        total_holding_cost_pv = 0.0
        total_acquisition_cost_pv = 0.0
        # rent_start_year == 1 here, so no delay/construction shift is applied;
        # the growing annuity already covers year 1 through rent_total_years.
        total_rent_cost_pv = calculate_growing_annuity_pv(
            yearly_rent_cost,
            g_rent,
            financing.wacc_real,
            int(rent_total_years),
            delay_years=0.0,
            construction_years=0.0,
        )
        # Lease/license: only rent; capital is zero
        row_capital_afudc = 0.0
        row_capital_pv = 0.0
        row_capital_nominal = 0.0
        row_rent_pv = total_rent_cost_pv
        row_rent_nominal = total_rent_cost
        total_afudc = 0.0
        total_pv_cost = total_rent_cost_pv
    else:
        total_holding_cost = calculate_nominal_growing_series(
            yearly_holding_cost,
            g_rent,
            project_details.delay_years,
        )
        total_rent_cost = calculate_nominal_growing_series(
            yearly_rent_cost,
            g_rent,
            rent_total_years,
        )
        acquisition_cost_used = acquisition_cost
        total_nominal_cost = (
            total_holding_cost + acquisition_cost_used + total_rent_cost
        )

        if afudc_setup.apply_afudc and acquisition_cost_used != 0:
            acquisition_capitalized, acquisition_afudc = (
                calculate_afudc_capitalized_cost(
                    acquisition_cost_used,
                    afudc_setup.timing_patterns["row_acquisition"],
                    project_details.delay_years,
                    project_details.construction_years,
                    afudc_setup.afudc_rate,
                    afudc_setup.delay_active,
                    spending_profiles=afudc_setup.spending_profiles,
                )
            )
        else:
            acquisition_capitalized = acquisition_cost_used
            acquisition_afudc = 0.0

        # Holding: AFUDC-eligible (option fee during delay)
        if (
            afudc_setup.apply_afudc
            and total_holding_cost > 0
        ):
            holding_capitalized, holding_afudc = calculate_afudc_capitalized_cost(
                total_holding_cost,
                afudc_setup.timing_patterns["row_holding"],
                project_details.delay_years,
                project_details.construction_years,
                afudc_setup.afudc_rate,
                afudc_setup.delay_active,
                spending_profiles=afudc_setup.spending_profiles,
            )
        else:
            holding_capitalized = total_holding_cost
            holding_afudc = 0.0

        validate_discount_rate(financing.wacc_real, "wacc_real")
        # Holding (option fee) is paid during the delay period only (years 1..delay_years).
        total_holding_cost_pv = calculate_growing_annuity_pv(
            yearly_holding_cost,
            g_rent,
            financing.wacc_real,
            int(project_details.delay_years),
            delay_years=0.0,
            construction_years=0.0,
        )
        total_acquisition_cost_pv = (
            acquisition_cost_used
            / (1 + financing.wacc_real) ** project_details.delay_years
        )
        # rent_start_year == delay_years + 1 here, so shift the growing annuity
        # by delay_years to reproduce the same payment timing.
        total_rent_cost_pv = calculate_growing_annuity_pv(
            yearly_rent_cost,
            g_rent,
            financing.wacc_real,
            int(rent_total_years),
            delay_years=project_details.delay_years,
            construction_years=0.0,
        )

        # Capital = acquisition + holding only (no rent)
        row_capital_afudc = acquisition_capitalized + holding_capitalized
        row_capital_pv = total_acquisition_cost_pv + total_holding_cost_pv
        row_capital_nominal = acquisition_cost_used + total_holding_cost
        row_rent_pv = total_rent_cost_pv
        row_rent_nominal = total_rent_cost
        total_afudc = row_capital_afudc
        total_pv_cost = row_capital_pv + total_rent_cost_pv

    # Display results
    print("=" * 80)
    print("RIGHT-OF-WAY COST CALCULATION RESULTS")
    print("=" * 80)
    print(f"Project Category: {category}")
    print(f"ROW Agreement Type: {agreement_type}")
    print(f"Total Miles: {total_miles:.2f}")
    print(f"Row Width: {row_width_feet:.1f} feet")
    print(f"Total Acres: {total_acres:.2f}")
    print()

    print("[NOMINAL VALUES]")
    print(f"  Rent Escalation Rate (g_rent): {g_rent:.2%}/year (real)")
    print(f"  Holding Cost (option fee): ${total_holding_cost:,.2f}")
    print(
        f"    (Annual: ${yearly_holding_cost:,.2f} over {project_details.delay_years} year(s))"
    )
    print(f"  Acquisition Cost: ${acquisition_cost_used:,.2f}")
    print(f"  Annual ROW Payment: ${total_rent_cost:,.2f}")
    print(f"    (Annual: ${yearly_rent_cost:,.2f} over {rent_total_years} year(s))")
    print(f"  ---")
    print(f"  TOTAL NOMINAL ROW COST: ${total_nominal_cost:,.2f}")
    print()

    if (
        afudc_setup.apply_afudc
        and agreement_type != "lease_license_existing"
        and (acquisition_cost_used != 0 or total_holding_cost != 0)
    ):
        print("[REGULATORY PERSPECTIVE - AFUDC Capitalization]")
        print(
            f"  AFUDC Rate: {afudc_setup.afudc_rate:.2%} ({afudc_setup.afudc_source})"
        )
        print(
            f"  Delay Period Active Work: {'Yes' if afudc_setup.delay_active else 'No'}"
        )
        print()
        print(f"  Acquisition Cost Capitalized: ${acquisition_capitalized:,.2f}")
        print(f"    AFUDC on Acquisition: ${acquisition_afudc:,.2f}")
        print(f"  Holding Cost Capitalized: ${holding_capitalized:,.2f}")
        print(f"    AFUDC on Holding: ${holding_afudc:,.2f}")
        print(f"  Annual ROW Payment: ${total_rent_cost:,.2f}")
        print(f"    (NOT AFUDC-eligible - operational period)")
        print(f"  ---")
        print(
            f"  ROW Capital (at COD): ${row_capital_afudc:,.2f}"
        )
        print(
            f"  TOTAL (Capital + annual ROW payment): ${row_capital_afudc + total_rent_cost:,.2f}"
        )
        print()

    print("[SOCIETAL PERSPECTIVE - Present Value]")
    print(f"  Discount Rate: {financing.wacc_real:.2%} (real WACC)")
    print(f"  Base Year: {financing.base_year}")
    print()
    print(f"  Holding Cost PV: ${total_holding_cost_pv:,.2f}")
    print(f"  Acquisition Cost PV: ${total_acquisition_cost_pv:,.2f}")
    print(f"  Annual ROW Payment PV: ${total_rent_cost_pv:,.2f}")
    print(f"  ---")
    print(f"  TOTAL PRESENT VALUE ROW COST: ${total_pv_cost:,.2f}")
    print("=" * 80)

    # ========================================================================
    # CSV OUTPUT - Write results to batch summary and detail CSV
    # ========================================================================

    csv_manager = CTCCOutputManager()
    results = {
        "total_nominal": total_nominal_cost,
        "total_afudc": total_afudc,
        "total_pv": total_pv_cost,
        "row_capital_pv": row_capital_pv,
        "row_capital_afudc": row_capital_afudc,
        "row_capital_nominal": row_capital_nominal,
        "row_rent_pv": row_rent_pv,
        "row_rent_nominal": row_rent_nominal,
        "acquisition_nominal": acquisition_cost_used,
        "holding_nominal": total_holding_cost,
        "rent_nominal": total_rent_cost,
        "row_rent_escalation_real": g_rent,
    }

    # Write to CSV
    csv_manager.add_row_costs(results)
    csv_manager.write_batch_summary()


if __name__ == "__main__":
    main()
