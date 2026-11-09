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
)
from forge.scripts.utils.financial_utils import (
    capitalize_yearly_spending,
    validate_discount_rate,
)
from forge.scripts.utils.streams import growing, level, pv, undiscounted, weighted

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
    agreement_type = (
        getattr(project_details, "row_agreement_type", None) or "permanent_easement_new"
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

    # Real annual escalation applies to operational ROW rent only. Acquisition
    # follows the MISO weights with no escalation. Holding is a level amount
    # over the delay years and is not capitalized.
    g_rent = float(_row_details["row_rent_escalation_real"])

    financing = load_financing_details()
    validate_discount_rate(financing.wacc_real, "wacc_real")

    delay_years = int(project_details.delay_years)
    annual_hold = xi_holding * yearly_holding_cost
    acq_total = xi_acquisition * acquisition_cost
    annual_rent = xi_rent * yearly_rent_cost
    # Lease rent runs from year 1 through the horizon. Every other agreement
    # type starts at construction and runs through the horizon. Growth is
    # measured from year 1 in both cases.
    if agreement_type == "lease_license_existing":
        rent_t0, rent_n = 1, ctx.horizon
    else:
        rent_t0 = ctx.t_start
        rent_n = ctx.horizon - ctx.t_start + 1

    acq_stream = weighted(acq_total, ctx.spending_weights, ctx.t_start, ctx.horizon)
    holding_stream = level(annual_hold, 1, delay_years, ctx.horizon)
    rent_stream = growing(annual_rent, g_rent, rent_t0, rent_n, ctx.horizon)
    row_streams = {
        "row_acquisition": acq_stream,
        "row_holding": holding_stream,
        "row_rent": rent_stream,
    }

    r_social = ctx.social_discount_rate
    r_wacc = financing.wacc_real
    acquisition_pv = pv(acq_stream, r_social)
    acquisition_pv_wacc = pv(acq_stream, r_wacc)
    row_holding_pv = pv(holding_stream, r_social)
    row_holding_pv_wacc = pv(holding_stream, r_wacc)
    row_rent_pv = pv(rent_stream, r_social)
    row_rent_pv_wacc = pv(rent_stream, r_wacc)
    total_pv = acquisition_pv + row_holding_pv + row_rent_pv
    total_pv_wacc = acquisition_pv_wacc + row_holding_pv_wacc + row_rent_pv_wacc

    acquisition_nominal = undiscounted(acq_stream)
    holding_nominal = undiscounted(holding_stream)
    rent_nominal = undiscounted(rent_stream)
    row_rent_nominal = rent_nominal
    total_nominal = acquisition_nominal + holding_nominal + rent_nominal
    acquisition_nominal_total = acquisition_nominal + holding_nominal

    # Only the acquisition stream is capitalized. Holding and rent stay outside
    # rate base. With AFUDC off this is the undiscounted acquisition spending.
    total_afudc = capitalize_yearly_spending(
        acq_stream,
        ctx.t_cod,
        ctx.afudc_rate,
        ctx.apply_afudc,
    )
    acquisition_afudc = total_afudc
    afudc_on_acquisition = (
        total_afudc - acquisition_nominal if ctx.apply_afudc else 0.0
    )

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
    logger.info(f"  Holding Cost (option fee): ${holding_nominal:,.2f}")
    logger.info(
        f"    (Annual: ${annual_hold:,.2f} over {delay_years} year(s))"
    )
    logger.info(f"  Acquisition Cost: ${acquisition_nominal:,.2f}")
    logger.info(f"  Annual ROW Payment: ${rent_nominal:,.2f}")
    logger.info(f"    (Annual: ${annual_rent:,.2f} over {rent_n} year(s))")
    logger.info(f"  ---")
    logger.info(f"  TOTAL NOMINAL ROW COST: ${total_nominal:,.2f}")
    logger.info("")

    if ctx.apply_afudc and acquisition_nominal != 0:
        logger.info("[REGULATORY PERSPECTIVE - AFUDC Capitalization]")
        logger.info(
            f"  AFUDC Rate: {ctx.afudc_rate:.2%} ({ctx.afudc_source})"
        )
        logger.info("")
        logger.info(f"  Acquisition Cost Capitalized: ${total_afudc:,.2f}")
        logger.info(f"    AFUDC on Acquisition: ${afudc_on_acquisition:,.2f}")
        logger.info(f"  Holding Cost (operating expense): ${holding_nominal:,.2f}")
        logger.info(f"    AFUDC on Holding: ${0.0:,.2f} (not AFUDC-eligible)")
        logger.info(f"  Annual ROW Payment: ${rent_nominal:,.2f}")
        logger.info(f"    (NOT AFUDC-eligible - operational period)")
        logger.info(f"  ---")
        logger.info(
            f"  Acquisition (at COD): ${acquisition_afudc:,.2f}"
        )
        logger.info(
            f"  TOTAL (Acquisition at COD + annual ROW payment): ${acquisition_afudc + rent_nominal:,.2f}"
        )
        logger.info("")

    logger.info("[SOCIETAL PERSPECTIVE - Present Value]")
    logger.info(f"  Social Discount Rate: {r_social:.2%}")
    logger.info(f"  Real WACC: {r_wacc:.2%}")
    logger.info(f"  Base Year: {financing.base_year}")
    logger.info("")
    logger.info(f"  Holding Cost PV: ${row_holding_pv:,.2f}")
    logger.info(f"  Acquisition Cost PV: ${acquisition_pv:,.2f}")
    logger.info(f"  Annual ROW Payment PV: ${row_rent_pv:,.2f}")
    logger.info(f"  ---")
    logger.info(f"  TOTAL PRESENT VALUE ROW COST: ${total_pv:,.2f}")
    logger.info("=" * 80)

    # ========================================================================
    # CSV OUTPUT - Write results to batch summary and detail CSV
    # ========================================================================

    csv_manager = SmartOutputManager()
    results = {
        "streams": row_streams,
        "total_nominal": total_nominal,
        "total_afudc": total_afudc,
        "total_pv": total_pv,
        "total_pv_wacc": total_pv_wacc,
        "acquisition_pv": acquisition_pv,
        "acquisition_pv_wacc": acquisition_pv_wacc,
        "acquisition_afudc": acquisition_afudc,
        "acquisition_nominal_total": acquisition_nominal_total,
        "row_holding_pv": row_holding_pv,
        "row_holding_pv_wacc": row_holding_pv_wacc,
        "row_rent_pv": row_rent_pv,
        "row_rent_pv_wacc": row_rent_pv_wacc,
        "row_rent_nominal": row_rent_nominal,
        "acquisition_nominal": acquisition_nominal,
        "holding_nominal": holding_nominal,
        "rent_nominal": rent_nominal,
        "row_rent_escalation_real": g_rent,
    }

    # Write to CSV
    csv_manager.add_row_costs(results)
    csv_manager.write_batch_summary()
