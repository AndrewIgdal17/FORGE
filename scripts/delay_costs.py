# Author: Andrew Igdal
# Date: 2025-10-21
# Description: This script calculates the delay costs for a transmission line.
#              It computes the delay costs for a transmission line over the delay period.

# Standard library imports
import yaml
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from csv_output_manager import CTCCOutputManager

# Local utility imports
from yaml_loaders import load_delay_costs, load_financing_details
from financial_utils import calculate_present_value


def load_project_technical_details():
    """
    Load project technical details and construct category identifier.
    """
    with open("../yamls/01_project_technical_details.yaml", "r") as file:
        project_details = yaml.load(file, Loader=yaml.FullLoader)
    delay_year = project_details["timeline"]["delay_years"]
    return delay_year


def main():
    """

    Main function to calculate and display delay costs.
    """
    delay_cost_df = load_delay_costs()
    delay_year = load_project_technical_details()

    legal = delay_cost_df["annual_delay_costs"]["legal"]
    admin = delay_cost_df["annual_delay_costs"]["admin"]
    labor = delay_cost_df["annual_delay_costs"]["labor"]
    material_and_equipment = delay_cost_df["annual_delay_costs"][
        "material_and_equipment"
    ]
    regulatory = delay_cost_df["annual_delay_costs"]["regulatory"]
    public_relations = delay_cost_df["annual_delay_costs"]["public_relations"]
    project_management = delay_cost_df["annual_delay_costs"]["project_management"]
    miscellaneous = delay_cost_df["annual_delay_costs"]["miscellaneous"]

    total_yearly_delay_cost = (
        legal
        + admin
        + labor
        + material_and_equipment
        + regulatory
        + public_relations
        + project_management
        + miscellaneous
    )
    total_delay_cost = total_yearly_delay_cost * delay_year

    inflation_rate, base_year, wacc_nominal, wacc_real = load_financing_details()

    total_delay_cost_pv = calculate_present_value(
        total_yearly_delay_cost,
        wacc_real,
        int(
            round(delay_year)
        ),  # Move rounding to the actual function, outside of main to prevent headaches
    )

    print("=" * 60)
    print("DELAY COST CALCULATION RESULTS")
    print("=" * 60)
    print(f"Delay year: {delay_year}")
    print(f"Total yearly delay cost: ${total_yearly_delay_cost:,.2f}")
    print(f"Total delay cost: ${total_delay_cost:,.2f}")

    print()
    print(
        f"PRESENT VALUES (discounted to base year (2025) using real WACC ({wacc_real:.2%})):"
    )

    print(f"TOTAL PRESENT VALUE DELAY COST: ${total_delay_cost_pv:,.2f}")
    print("=" * 60)

    # ========================================================================
    # CSV OUTPUT - Write results to batch summary and detail CSV
    # ========================================================================
    
    # Initialize CSV output manager
    csv_manager = CTCCOutputManager()
    
    # Prepare results dictionary
    results = {
        "total_nominal": total_delay_cost,
        "total_afudc": 0,  # Delay costs are not AFUDC-eligible
        "total_pv": total_delay_cost_pv,
    }
    
    # Write to CSV
    csv_manager.add_delay_costs(results)
    csv_manager.write_batch_summary()


if __name__ == "__main__":
    main()
