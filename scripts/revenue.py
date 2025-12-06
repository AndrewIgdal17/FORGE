# Author: Andrew Igdal
# Date: 2025-11-XX
# Description: Calculate rate-based revenue requirement (utility perspective).
#              Revenue = Capital Costs PV × Allowed Return Rate, calculated annually
#              over project lifetime and discounted to present value.

# Standard library imports
import yaml
import sys
import os
import csv

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from csv_output_manager import CTCCOutputManager

# Local utility imports
from yaml_loaders import load_financing_details
from financial_utils import calculate_present_value
from path_config import YAMLS_DIR, OUTPUTS_DIR


def load_rate_based_revenue_parameters():
    """
    Load rate-based revenue parameters from financing YAML.
    
    Returns:
        tuple: (enabled, allowed_return_rate)
    """
    with open(YAMLS_DIR / "03_financing.yaml", "r") as file:
        financing_data = yaml.load(file, Loader=yaml.FullLoader)
    
    revenue_config = financing_data.get("financial", {}).get("revenue", {})
    rate_based_config = revenue_config.get("rate_based", {})
    
    enabled = rate_based_config.get("enabled", False)
    allowed_return_rate = rate_based_config.get("allowed_return_rate", 0.10)
    
    return enabled, allowed_return_rate


def load_project_technical_details():
    """
    Load project technical details for timeline information.
    
    Returns:
        tuple: (delay_years, construction_years, project_lifetime)
    """
    with open(YAMLS_DIR / "01_project_technical_details.yaml", "r") as file:
        project_details = yaml.load(file, Loader=yaml.FullLoader)
    
    delay_years = project_details["timeline"]["delay_years"]
    construction_years = project_details["timeline"]["construction_years"]
    project_lifetime = project_details["timeline"]["project_lifetime"]
    
    return delay_years, construction_years, project_lifetime


def get_capital_costs_pv():
    """
    Get capital costs PV from batch_summary.csv for the current scenario.
    
    Capital costs = build_cost_pv + row_cost_pv + env_mitigation_pv
    
    Returns:
        float: Capital costs PV, or 0 if not found
    """
    batch_summary_path = OUTPUTS_DIR / "batch_summary.csv"
    
    if not os.path.exists(batch_summary_path):
        return 0
    
    # Get current scenario_id from environment variable
    scenario_id = os.environ.get("CTCC_SCENARIO_ID")
    
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
            print(f"⚠️  Warning: Error reading capital costs from batch_summary.csv: {e}")
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
            print(f"⚠️  Warning: scenario_id '{scenario_id}' not found in batch_summary.csv")
            return 0
    except (ValueError, KeyError, IOError) as e:
        print(f"⚠️  Warning: Error reading capital costs from batch_summary.csv: {e}")
        return 0


def main():
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
    inflation_rate, base_year, wacc_nominal, wacc_real = load_financing_details()
    
    # Get capital costs PV from batch_summary.csv
    capital_costs_pv = get_capital_costs_pv()
    
    if capital_costs_pv == 0:
        print("⚠️  Warning: Capital costs PV is zero. Revenue will be zero.")
        print("   Make sure build_costs.py, row_costs.py, and environmental_mitigation.py")
        print("   have run before revenue.py")
    
    # Calculate annual revenue requirement
    # Rate Base = Capital Costs PV
    # Annual Revenue = Rate Base × Allowed Return Rate
    annual_revenue = capital_costs_pv * allowed_return_rate
    
    total_revenue_nominal = annual_revenue * project_lifetime
    
    # Calculate present value (revenue starts after construction)
    revenue_pv = calculate_present_value(
        annual_revenue,
        wacc_real,
        project_lifetime,
        start_year=delay_years + construction_years + 1
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
        f"PRESENT VALUE (discounted to base year ({base_year}) using real WACC ({wacc_real:.2%})):"
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

