# Date: 2025-10-21
# Description: This script calculates the delay costs for a transmission line.
#              It computes the delay costs for a transmission line over the delay period.

from __future__ import annotations

import logging

# Standard library imports
import yaml

from forge.scripts.utils.smart_output import SmartOutputManager

# Local utility imports
from forge.scripts.utils.smart_loaders import (
    load_delay_costs,
    load_financing_details,
    load_project_technical_details as load_project_technical_details_centralized,
)
from forge.scripts.utils.financial_utils import validate_discount_rate
from forge.scripts.utils.run_context import add_derived, get_run_context
from forge.scripts.utils.streams import level, pv, undiscounted

logger = logging.getLogger(__name__)


def load_project_technical_details() -> float:
    """
    Load delay years from project technical details using centralized loader.

    This wrapper extracts only the delay_years value from the centralized loader,
    as this is the only field needed for delay cost calculations.

    Returns:
        float: Number of years of project delay before construction begins
    """
    from forge.scripts.io.yaml_loaders import ProjectTechnicalDetails
    project_details: ProjectTechnicalDetails = load_project_technical_details_centralized()
    return project_details.delay_years

def main() -> None:
    """Main function to calculate and display delay costs."""
    delay_cost_df = load_delay_costs()
    delay_year = load_project_technical_details()

    total_yearly_delay_cost = delay_cost_df["annual_base_delay_cost"]

    ctx = get_run_context()
    if ctx is None:
        raise RuntimeError(
            f"{__name__} requires a RunContext. Run via forge.py or set up "
            "RunContext in your test fixture."
        )
    delay_years = int(delay_year)
    base_delay_stream = level(total_yearly_delay_cost, 1, delay_years, ctx.horizon)
    total_delay_cost = undiscounted(base_delay_stream)

    add_derived({"total_annual_delay_cost": total_yearly_delay_cost})

    financing = load_financing_details()
    validate_discount_rate(financing.wacc_real, "wacc_real")
    r_social = ctx.social_discount_rate
    r_wacc = financing.wacc_real
    total_delay_cost_pv = pv(base_delay_stream, r_social)
    total_delay_cost_pv_wacc = pv(base_delay_stream, r_wacc)

    logger.info("=" * 60)
    logger.info("DELAY COST CALCULATION RESULTS")
    logger.info("=" * 60)
    logger.info(f"Delay year: {delay_year}")
    logger.info(f"Total yearly delay cost: ${total_yearly_delay_cost:,.2f}")
    logger.info(f"Total delay cost: ${total_delay_cost:,.2f}")

    logger.info("")
    logger.info(
        f"PRESENT VALUES (discounted to base year ({financing.base_year}); "
        f"social {r_social:.2%}, real WACC {r_wacc:.2%}):"
    )

    logger.info(f"TOTAL PRESENT VALUE DELAY COST (social): ${total_delay_cost_pv:,.2f}")
    logger.info(f"TOTAL PRESENT VALUE DELAY COST (WACC): ${total_delay_cost_pv_wacc:,.2f}")
    logger.info("=" * 60)

    # ========================================================================
    # CSV OUTPUT - Write results to batch summary and detail CSV
    # ========================================================================

    csv_manager = SmartOutputManager()

    results = {
        "streams": {"base_delay": base_delay_stream},
        "total_nominal": total_delay_cost,
        "total_afudc": 0,
        "total_pv": total_delay_cost_pv,
        "total_pv_wacc": total_delay_cost_pv_wacc,
    }

    csv_manager.add_delay_costs(results)
    csv_manager.write_batch_summary()
