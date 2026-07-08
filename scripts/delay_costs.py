# Author: Andrew Igdal
# Date: 2025-10-21
# Description: This script calculates the delay costs for a transmission line.
#              It computes the delay costs for a transmission line over the delay period.

from __future__ import annotations

# Standard library imports
import yaml
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from smart_output import CTCCOutputManager

# Local utility imports
from smart_loaders import (
    load_delay_costs,
    load_financing_details,
    load_project_technical_details as load_project_technical_details_centralized,
)
from financial_utils import calculate_present_value


def load_project_technical_details() -> float:
    """
    Load delay years from project technical details using centralized loader.

    This wrapper extracts only the delay_years value from the centralized loader,
    as this is the only field needed for delay cost calculations.

    Returns:
        float: Number of years of project delay before construction begins
    """
    from yaml_loaders import ProjectTechnicalDetails
    project_details: ProjectTechnicalDetails = load_project_technical_details_centralized()
    return project_details.delay_years


def main() -> None:
    """Main function to calculate and display delay costs."""
    delay_cost_df = load_delay_costs()
    delay_year = load_project_technical_details()

    # Single annual cost field (replaces prior 8-category decomposition)
    if "annual_base_delay_cost" in delay_cost_df:
        total_yearly_delay_cost = delay_cost_df["annual_base_delay_cost"]
    elif "annual_delay_costs" in delay_cost_df:
        # Runner scripts provide an 8-category annual_delay_costs dict;
        # YAML default provides a single annual_base_delay_cost scalar. Both paths are active.
        total_yearly_delay_cost = sum(delay_cost_df["annual_delay_costs"].values())
    else:
        total_yearly_delay_cost = 0.0

    total_delay_cost = total_yearly_delay_cost * delay_year

    from run_context import add_derived
    add_derived({"total_annual_delay_cost": total_yearly_delay_cost})

    financing = load_financing_details()

    total_delay_cost_pv = calculate_present_value(
        total_yearly_delay_cost,
        financing.wacc_real,
        delay_year,
    )

    print("=" * 60)
    print("DELAY COST CALCULATION RESULTS")
    print("=" * 60)
    print(f"Delay year: {delay_year}")
    print(f"Total yearly delay cost: ${total_yearly_delay_cost:,.2f}")
    print(f"Total delay cost: ${total_delay_cost:,.2f}")

    print()
    print(
        f"PRESENT VALUES (discounted to base year ({financing.base_year}) using real WACC ({financing.wacc_real:.2%})):"
    )

    print(f"TOTAL PRESENT VALUE DELAY COST: ${total_delay_cost_pv:,.2f}")
    print("=" * 60)

    # ========================================================================
    # CSV OUTPUT - Write results to batch summary and detail CSV
    # ========================================================================

    csv_manager = CTCCOutputManager()

    results = {
        "total_nominal": total_delay_cost,
        "total_afudc": 0,
        "total_pv": total_delay_cost_pv,
    }

    csv_manager.add_delay_costs(results)
    csv_manager.write_batch_summary()


if __name__ == "__main__":
    main()
