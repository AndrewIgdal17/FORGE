# Author: Andrew Igdal
# Date: 2025-11-XX
# Description: Calculate rate-based revenue requirement (utility perspective).
#              Revenue = Capital Costs PV × Allowed Return Rate, calculated annually
#              over project lifetime and discounted to present value.

from __future__ import annotations

# Standard library imports
import yaml
import sys
import os
import csv
from typing import Tuple, Dict, Any

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from smart_output import CTCCOutputManager

# Local utility imports
from smart_loaders import (
    load_financing_details,
    load_project_technical_details as load_project_technical_details_centralized,
    get_financing_data_raw,
)
from financial_utils import calculate_present_value, calculate_cod_year
from path_config import OUTPUTS_DIR


def load_rate_based_revenue_parameters() -> Tuple[bool, float]:
    """
    Load rate-based revenue parameters from financing data.
    Supports both YAML and JSON input modes.

    Returns:
        tuple: (enabled, allowed_return_rate)
    """
    try:
        financing_data = get_financing_data_raw()
        if not financing_data:
            raise ValueError("Financing data is empty or invalid")
        revenue_config = financing_data.get("financial", {}).get("revenue", {})
        rate_based_config = revenue_config.get("rate_based", {})

        enabled = rate_based_config.get("enabled", False)
        allowed_return_rate = rate_based_config.get("allowed_return_rate", 0.10)

        return enabled, allowed_return_rate
    except FileNotFoundError:
        raise FileNotFoundError(
            f"Financing data not found"
        )
    except yaml.YAMLError as e:
        raise ValueError(f"Error parsing financing data: {e}")


def load_project_technical_details() -> Tuple[float, int, int]:
    """
    Load project technical details for timeline information using centralized loader.

    Returns:
        tuple: (delay_years, construction_years, project_lifetime)
    """
    from yaml_loaders import ProjectTechnicalDetails
    project_details: ProjectTechnicalDetails = load_project_technical_details_centralized()
    return project_details.delay_years, project_details.construction_years, project_details.project_lifetime


def get_capital_costs_pv() -> float:
    """
    Get capital costs PV from batch_summary.csv (CSV mode) or JSON output files (JSON mode).

    Capital costs = build_cost_pv + row_cost_pv + env_mitigation_pv

    Returns:
        float: Capital costs PV, or 0 if not found
    """
    # Check output mode
    output_mode = os.environ.get("CTCC_OUTPUT_MODE", "csv").lower()
    scenario_id = os.environ.get("CTCC_SCENARIO_ID")
    
    if output_mode == "json" and scenario_id:
        # JSON mode: Read from individual JSON output files
        try:
            import json as json_lib
            build_pv = 0
            row_pv = 0
            env_pv = 0
            
            # Read build costs
            build_json_path = OUTPUTS_DIR / f"json_output_{scenario_id}_build_costs.json"
            if build_json_path.exists():
                with open(build_json_path, "r") as f:
                    build_data = json_lib.load(f)
                    build_pv = float(build_data.get("costs", {}).get("build", {}).get("total_pv", 0) or 0)
            
            # Read ROW costs
            row_json_path = OUTPUTS_DIR / f"json_output_{scenario_id}_row_costs.json"
            if row_json_path.exists():
                with open(row_json_path, "r") as f:
                    row_data = json_lib.load(f)
                    row_pv = float(row_data.get("costs", {}).get("row", {}).get("total_pv", 0) or 0)
            
            # Read environmental mitigation costs
            env_json_path = OUTPUTS_DIR / f"json_output_{scenario_id}_environmental_mitigation.json"
            if env_json_path.exists():
                with open(env_json_path, "r") as f:
                    env_data = json_lib.load(f)
                    env_pv = float(env_data.get("costs", {}).get("environmental", {}).get("total_pv", 0) or 0)
            
            total = build_pv + row_pv + env_pv
            if total > 0:
                return total
        except Exception as e:
            print(f"⚠️  Warning: Error reading capital costs from JSON files: {e}")
            import traceback
            traceback.print_exc()
    
    # CSV mode: Read from batch_summary.csv
    batch_summary_path = OUTPUTS_DIR / "batch_summary.csv"

    if not os.path.exists(batch_summary_path):
        return 0

    if not scenario_id:
        print("⚠️  Warning: CTCC_SCENARIO_ID not set. Cannot filter by scenario_id.")
        print("   Falling back to last row (may be incorrect if multiple runs exist).")
        # Fallback to last row if scenario_id is not available
        try:
            with open(batch_summary_path, "r") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                if rows:
                    latest_row = rows[-1]
                    build_pv = float(latest_row.get("build_cost_pv", 0) or 0)
                    row_pv = float(latest_row.get("row_cost_pv", 0) or 0)
                    env_pv = float(latest_row.get("env_mitigation_pv", 0) or 0)
                    return build_pv + row_pv + env_pv
        except (ValueError, KeyError, IOError) as e:
            print(
                f"⚠️  Warning: Error reading capital costs from batch_summary.csv: {e}"
            )
        return 0

    try:
        with open(batch_summary_path, "r", newline="") as f:
            reader = csv.DictReader(f)
            # Find row matching current scenario_id
            for row in reader:
                if row.get("scenario_id") == scenario_id:
                    build_pv = float(row.get("build_cost_pv", 0) or 0)
                    row_pv = float(row.get("row_cost_pv", 0) or 0)
                    env_pv = float(row.get("env_mitigation_pv", 0) or 0)
                    return build_pv + row_pv + env_pv

            # If scenario_id not found, warn and return 0
            print(
                f"⚠️  Warning: scenario_id '{scenario_id}' not found in batch_summary.csv"
            )
            return 0
    except (ValueError, KeyError, IOError) as e:
        print(f"⚠️  Warning: Error reading capital costs from batch_summary.csv: {e}")
        return 0


def main() -> None:
    """
    Main function to calculate and display rate-based revenue requirement.
    """
    # Check if rate-based revenue is enabled
    enabled, allowed_return_rate = load_rate_based_revenue_parameters()

    if not enabled:
        print("=" * 60)
        print("RATE-BASED REVENUE CALCULATION SKIPPED")
        print("(revenue.rate_based.enabled = false in financing.yaml)")
        print("=" * 60)
        # Still write zeros to CSV for consistency
        csv_manager = CTCCOutputManager()
        results = {
            "revenue_nominal": 0,
            "revenue_pv": 0,
            "annual_revenue": 0,
            "rate_base_pv": 0,
            "allowed_return_rate": 0,
        }
        csv_manager.add_revenue(results)
        csv_manager.write_batch_summary()
        return

    # Load project details
    delay_years, construction_years, project_lifetime = load_project_technical_details()

    # Load financing details
    financing = load_financing_details()

    # Get capital costs PV from batch_summary.csv
    capital_costs_pv = get_capital_costs_pv()

    if capital_costs_pv == 0:
        print("⚠️  Warning: Capital costs PV is zero. Revenue will be zero.")
        print(
            "   Make sure build_costs.py, row_costs.py, and environmental_mitigation.py"
        )
        print("   have run before revenue.py")

    # Calculate annual revenue requirement
    # Rate Base = Capital Costs PV
    # Annual Revenue = Rate Base × Allowed Return Rate
    annual_revenue = capital_costs_pv * allowed_return_rate

    total_revenue_nominal = annual_revenue * project_lifetime

    # Calculate present value (revenue starts after construction)
    revenue_pv = calculate_present_value(
        annual_revenue,
        financing.wacc_real,
        project_lifetime,
        start_year=calculate_cod_year(delay_years, construction_years),
    )

    print("=" * 60)
    print("RATE-BASED REVENUE REQUIREMENT CALCULATION")
    print("=" * 60)
    print(f"Rate Base (Capital Costs PV): ${capital_costs_pv:,.2f}")
    print(f"Allowed Return Rate: {allowed_return_rate:.2%}")
    print(f"Annual Revenue Requirement: ${annual_revenue:,.2f}")
    print(f"Total Revenue (Nominal): ${total_revenue_nominal:,.2f}")
    print()
    print(
        f"PRESENT VALUE (discounted to base year ({financing.base_year}) using real WACC ({financing.wacc_real:.2%})):"
    )
    print(f"TOTAL PRESENT VALUE REVENUE: ${revenue_pv:,.2f}")
    print("=" * 60)

    # CSV Output
    csv_manager = CTCCOutputManager()
    results = {
        "revenue_nominal": total_revenue_nominal,
        "revenue_pv": revenue_pv,
        "annual_revenue": annual_revenue,
        "rate_base_pv": capital_costs_pv,
        "allowed_return_rate": allowed_return_rate,
    }
    csv_manager.add_revenue(results)
    csv_manager.write_batch_summary()


if __name__ == "__main__":
    main()
