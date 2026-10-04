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
from forge.scripts.utils.financial_utils import calculate_present_value

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

    total_delay_cost = total_yearly_delay_cost * delay_year

    from forge.scripts.utils.run_context import add_derived
    add_derived({"total_annual_delay_cost": total_yearly_delay_cost})

    financing = load_financing_details()

    total_delay_cost_pv = calculate_present_value(
        total_yearly_delay_cost,
        financing.wacc_real,
        delay_year,
    )

    logger.info("=" * 60)
    logger.info("DELAY COST CALCULATION RESULTS")
    logger.info("=" * 60)
    logger.info(f"Delay year: {delay_year}")
    logger.info(f"Total yearly delay cost: ${total_yearly_delay_cost:,.2f}")
    logger.info(f"Total delay cost: ${total_delay_cost:,.2f}")

    logger.info("")
    logger.info(
        f"PRESENT VALUES (discounted to base year ({financing.base_year}) using real WACC ({financing.wacc_real:.2%})):"
    )

    logger.info(f"TOTAL PRESENT VALUE DELAY COST: ${total_delay_cost_pv:,.2f}")
    logger.info("=" * 60)

    # ========================================================================
    # CSV OUTPUT - Write results to batch summary and detail CSV
    # ========================================================================

    csv_manager = SmartOutputManager()

    results = {
        "total_nominal": total_delay_cost,
        "total_afudc": 0,
        "total_pv": total_delay_cost_pv,
    }

    csv_manager.add_delay_costs(results)
    csv_manager.write_batch_summary()
