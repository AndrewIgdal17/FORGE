# Date: 2025-10-20
# Description: This script calculates the right-of-way costs for a transmission line.
#              ROW agreement type (permanent easement, lease/license, fee simple, federal/hybrid)
#              determines which cost terms apply via explicit xi selectors at assembly
#              (appendix §Capital ROW Eq 5, §Op ROW Rent Eq 1). Acquisition and annual
#              ROW payment are mutually exclusive unless the regime is federal_hybrid.
#              Holding is an operating expense during delay (FERC Account 567), not
#              AFUDC-eligible. Only acquisition enters rate base.

from __future__ import annotations

import logging

# Standard library imports
import yaml
from typing import Tuple

from forge.scripts.utils.smart_output import SmartOutputManager

# Local utility imports
from forge.scripts.utils.smart_loaders import (
    load_project_technical_details,
    load_physical_details,
    load_row_widths,
    load_row_details,
    load_financing_details,
    load_cost_timing_patterns,
    load_afudc_config,
    get_financing_data_raw,
)
from forge.scripts.utils.financial_utils import (
    calculate_growing_annuity_pv,
    calculate_nominal_growing_series,
    calculate_afudc_rate,
    calculate_afudc_capitalized_cost,
    validate_discount_rate,
)

logger = logging.getLogger(__name__)

def calculate_zone_costs(row_width_feet: float) -> Tuple[float, float, float, float]:
    """
    Calculate right-of-way (ROW) costs aggregated across all zones.

    For each zone where the transmission line passes (miles > 0), computes zone
    area in acres and multiplies by zone-specific rates for acquisition,
    option fee (hold_cost), and annual ROW payment (rent_cost). The caller
    applies explicit xi selectors when assembling totals; component costs
    here are ungated.

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
    from forge.scripts.utils.calculation_utils import miles_to_acres

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
    from forge.scripts.utils.run_context import get_run_context

    ctx = get_run_context()
    if ctx is None:
        raise RuntimeError(
            f"{__name__} requires a RunContext. Run via forge.py or set up "
            "RunContext in your test fixture."
        )
    category = ctx.category_string

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
        if (project_details.project_type in ("reconductoring", "rebuild") or project_details.uses_existing_row)
        else "permanent_easement_new"
    )
    # Explicit binary selectors (appendix §Capital ROW Eq 5, §Op ROW Rent Eq 1).
    # Component costs stay ungated; selectors apply at assembly of totals.
    xi_acquisition = 0.0 if agreement_type == "lease_license_existing" else 1.0
    xi_holding = 0.0 if agreement_type == "lease_license_existing" else 1.0
    xi_rent = 1.0 if agreement_type in ("lease_license_existing", "federal_hybrid") else 0.0

    from forge.scripts.utils.run_context import add_derived
    from forge.scripts.utils.calculation_utils import miles_to_acres
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

    # Real annual escalation applied to operational ROW rent only (default 0% real,
    # backward-compatible with pre-escalation YAMLs). Holding uses a flat product.
    g_rent = float(_row_details["row_rent_escalation_real"])

    # Load financing parameters
    financing = load_financing_details()

    # Load AFUDC configuration and timing patterns
    from forge.scripts.utils.financial_utils import load_afudc_setup

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

    # Holding: appendix §Capital ROW Eq 4 — simple product, no escalation.
    total_holding_cost = (
        xi_holding * yearly_holding_cost * project_details.delay_years
    )
    # Rent: appendix §Op ROW Rent Eq 3 — growing series gated by xi_rent.
    total_rent_cost = xi_rent * calculate_nominal_growing_series(
        yearly_rent_cost,
        g_rent,
        rent_total_years,
    )
    acquisition_cost_used = xi_acquisition * acquisition_cost
    total_nominal_cost = (
        total_holding_cost + acquisition_cost_used + total_rent_cost
    )

    # Only acquisition is AFUDC-eligible (appendix L392–393, L475–476).
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

    # Holding is a real operating expense (FERC Account 567), not AFUDC-eligible.
    holding_capitalized = total_holding_cost
    holding_afudc = 0.0

    validate_discount_rate(financing.wacc_real, "wacc_real")
    # Holding PV: constant-payment annuity over delay (growth_rate=0).
    total_holding_cost_pv = xi_holding * calculate_growing_annuity_pv(
        yearly_holding_cost,
        0.0,
        financing.wacc_real,
        int(project_details.delay_years),
        delay_years=0.0,
        construction_years=0.0,
    )
    total_acquisition_cost_pv = (
        acquisition_cost_used
        / (1 + financing.wacc_real) ** project_details.delay_years
    )
    # Lease rent starts year 1 (no delay shift); hybrid starts after delay.
    rent_delay = (
        0.0
        if agreement_type == "lease_license_existing"
        else project_details.delay_years
    )
    total_rent_cost_pv = xi_rent * calculate_growing_annuity_pv(
        yearly_rent_cost,
        g_rent,
        financing.wacc_real,
        int(rent_total_years),
        delay_years=rent_delay,
        construction_years=0.0,
    )

    # Capital = acquisition only. Holding is operating expense, not capital.
    row_capital_afudc = acquisition_capitalized
    row_capital_pv = total_acquisition_cost_pv
    row_holding_pv = total_holding_cost_pv
    row_capital_nominal = acquisition_cost_used + total_holding_cost
    row_rent_pv = total_rent_cost_pv
    row_rent_nominal = total_rent_cost
    total_afudc = row_capital_afudc
    total_pv_cost = row_capital_pv + row_holding_pv + total_rent_cost_pv

    # Display results
    logger.info("=" * 80)
    logger.info("RIGHT-OF-WAY COST CALCULATION RESULTS")
    logger.info("=" * 80)
    logger.info(f"Project Category: {category}")
    logger.info(f"ROW Agreement Type: {agreement_type}")
    logger.info(f"Total Miles: {total_miles:.2f}")
    logger.info(f"Row Width: {row_width_feet:.1f} feet")
    logger.info(f"Total Acres: {total_acres:.2f}")
    logger.info("")

    logger.info("[NOMINAL VALUES]")
    logger.info(f"  Rent Escalation Rate (g_rent): {g_rent:.2%}/year (real)")
    logger.info(f"  Holding Cost (option fee): ${total_holding_cost:,.2f}")
    logger.info(
        f"    (Annual: ${xi_holding * yearly_holding_cost:,.2f} over {project_details.delay_years} year(s))"
    )
    logger.info(f"  Acquisition Cost: ${acquisition_cost_used:,.2f}")
    logger.info(f"  Annual ROW Payment: ${total_rent_cost:,.2f}")
    logger.info(f"    (Annual: ${xi_rent * yearly_rent_cost:,.2f} over {rent_total_years} year(s))")
    logger.info(f"  ---")
    logger.info(f"  TOTAL NOMINAL ROW COST: ${total_nominal_cost:,.2f}")
    logger.info("")

    if afudc_setup.apply_afudc and acquisition_cost_used != 0:
        logger.info("[REGULATORY PERSPECTIVE - AFUDC Capitalization]")
        logger.info(
            f"  AFUDC Rate: {afudc_setup.afudc_rate:.2%} ({afudc_setup.afudc_source})"
        )
        logger.info(
            f"  Delay Period Active Work: {'Yes' if afudc_setup.delay_active else 'No'}"
        )
        logger.info("")
        logger.info(f"  Acquisition Cost Capitalized: ${acquisition_capitalized:,.2f}")
        logger.info(f"    AFUDC on Acquisition: ${acquisition_afudc:,.2f}")
        logger.info(f"  Holding Cost (operating expense): ${holding_capitalized:,.2f}")
        logger.info(f"    AFUDC on Holding: ${holding_afudc:,.2f} (not AFUDC-eligible)")
        logger.info(f"  Annual ROW Payment: ${total_rent_cost:,.2f}")
        logger.info(f"    (NOT AFUDC-eligible - operational period)")
        logger.info(f"  ---")
        logger.info(
            f"  ROW Capital (at COD): ${row_capital_afudc:,.2f}"
        )
        logger.info(
            f"  TOTAL (Capital + annual ROW payment): ${row_capital_afudc + total_rent_cost:,.2f}"
        )
        logger.info("")

    logger.info("[SOCIETAL PERSPECTIVE - Present Value]")
    logger.info(f"  Discount Rate: {financing.wacc_real:.2%} (real WACC)")
    logger.info(f"  Base Year: {financing.base_year}")
    logger.info("")
    logger.info(f"  Holding Cost PV: ${total_holding_cost_pv:,.2f}")
    logger.info(f"  Acquisition Cost PV: ${total_acquisition_cost_pv:,.2f}")
    logger.info(f"  Annual ROW Payment PV: ${total_rent_cost_pv:,.2f}")
    logger.info(f"  ---")
    logger.info(f"  TOTAL PRESENT VALUE ROW COST: ${total_pv_cost:,.2f}")
    logger.info("=" * 80)

    # ========================================================================
    # CSV OUTPUT - Write results to batch summary and detail CSV
    # ========================================================================

    csv_manager = SmartOutputManager()
    results = {
        "total_nominal": total_nominal_cost,
        "total_afudc": total_afudc,
        "total_pv": total_pv_cost,
        "row_capital_pv": row_capital_pv,
        "row_capital_afudc": row_capital_afudc,
        "row_capital_nominal": row_capital_nominal,
        "row_holding_pv": row_holding_pv,
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
