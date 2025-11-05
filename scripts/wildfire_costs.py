# Author: Andrew Igdal
# Date: 2025-10-29
# Description: This script calculates expected wildfire costs using probabilistic risk approach.
#              Based on ignition rates by terrain/construction type, event severity, and
#              present value of growing annuity over project lifetime.

# Standard library imports
import yaml
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from csv_output_manager import CTCCOutputManager

# Local utility imports
from yaml_loaders import (
    load_project_technical_details,
    load_physical_details,
    load_financing_details,
    load_wildfire_costs,
)


def get_discount_rate(wildfire_yaml, financing_yaml):
    """
    Get discount rate based on configuration source.

    Args:
        wildfire_yaml: Loaded wildfire YAML data
        financing_yaml: Loaded financing YAML data

    Returns:
        tuple: (discount_rate, source_description)
    """
    source = wildfire_yaml["wildfire"]["discount_rate_source"]

    if source == "social":
        rate = financing_yaml["financial"]["social_discount_rate"]
        desc = "social discount rate"
    elif source == "wacc_real":
        wacc_nominal = financing_yaml["financial"]["wacc_nominal"]
        inflation = financing_yaml["financial"]["inflation_rate"]
        rate = (1 + wacc_nominal) / (1 + inflation) - 1
        desc = "real WACC"
    elif source == "custom":
        rate = wildfire_yaml["wildfire"]["discount_rate_custom"]
        desc = "custom rate"
    else:
        raise ValueError(f"Unknown discount_rate_source: {source}")

    return rate, desc


def calculate_wildfire_costs(
    wildfire_yaml, construction_type, terrain_miles, project_lifetime, discount_rate
):
    """
    Calculate expected wildfire costs using segment-based ignition rates.

    Args:
        wildfire_yaml: Loaded wildfire YAML data
        construction_type: Construction type (overhead, underground, etc.)
        terrain_miles: Dictionary of terrain type to miles
        project_lifetime: Project lifetime in years
        discount_rate: Discount rate for PV calculation

    Returns:
        dict: Contains lambda_total, EAL, lambda_by_terrain, nominal_cost, pv_cost
    """
    cfg = wildfire_yaml["wildfire"]
    severity = cfg["severity_per_event"]
    growth_rate = cfg["risk_growth_rate"]
    ignition_rates_by_terrain = cfg["ignition_rates_by_terrain"]
    ignition_rate_multiplier = cfg["ignition_rate_multiplier"]

    # Map construction type to YAML keys
    ct_map = {
        "overhead": "overhead",
        "underground": "underground",
        "subsea": "subsea",
    }
    yaml_ct = ct_map.get(construction_type.lower(), "overhead")

    # Get construction type multiplier
    construction_multiplier = ignition_rate_multiplier.get(yaml_ct, 1.0)

    # Step 1 & 2: Calculate segment-specific and total event rates
    # Using multiplicative model: effective_rate = base_rate × construction_multiplier
    lambda_by_terrain = {}
    lambda_total = 0.0

    for terrain, miles in terrain_miles.items():
        if miles > 0:
            base_rate = ignition_rates_by_terrain.get(terrain, 0.0)
            f_i_t = base_rate * construction_multiplier  # Effective ignition rate
            lambda_segment = miles * f_i_t  # events/year for this terrain
            lambda_by_terrain[terrain] = {
                "miles": miles,
                "base_rate": base_rate,
                "construction_multiplier": construction_multiplier,
                "rate_per_mile": f_i_t,
                "events_per_year": lambda_segment,
            }
            lambda_total += lambda_segment

    # Step 3: Calculate Expected Annual Loss (EAL)
    EAL = lambda_total * severity

    # Calculate nominal total cost (sum of growing annual costs)
    # Sum of geometric series: EAL * sum((1+g)^t for t=0 to N-1)
    if abs(growth_rate) < 1e-9:  # No growth
        nominal_total = EAL * project_lifetime
    else:
        nominal_total = EAL * ((1 + growth_rate) ** project_lifetime - 1) / growth_rate

    # Step 4: Present value with growing annuity
    g = growth_rate
    d = discount_rate
    N = project_lifetime

    if abs(d - g) < 1e-9:  # Edge case: d = g
        pv_cost = EAL * N
    else:
        pv_cost = EAL * ((1 - ((1 + g) / (1 + d)) ** N) / (d - g))

    return {
        "lambda_total": lambda_total,
        "EAL": EAL,
        "lambda_by_terrain": lambda_by_terrain,
        "severity": severity,
        "growth_rate": growth_rate,
        "nominal_total": nominal_total,
        "pv_cost": pv_cost,
    }


def main():
    """Main function to calculate and display wildfire costs."""
    # Load project specifications
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

    # Load terrain details
    with open("../yamls/02_project_physical_details.yaml", "r") as file:
        physical_details = yaml.load(file, Loader=yaml.FullLoader)
    terrain_miles = physical_details["terrain"]["terrain_miles"]

    # Load wildfire parameters
    wildfire_yaml = load_wildfire_costs()

    # Load financing YAML for discount rate
    with open("../yamls/03_financing.yaml", "r") as file:
        financing_yaml = yaml.load(file, Loader=yaml.FullLoader)

    # Get discount rate
    discount_rate, discount_source = get_discount_rate(wildfire_yaml, financing_yaml)

    # Calculate wildfire costs
    results = calculate_wildfire_costs(
        wildfire_yaml, construction_type, terrain_miles, project_lifetime, discount_rate
    )

    # Display results
    print("=" * 80)
    print("EXPECTED WILDFIRE COST CALCULATION RESULTS")
    print("=" * 80)
    print(f"Project Category: {category}")
    print(f"Construction Type: {construction_type}")
    print()

    print("[WILDFIRE RISK ASSESSMENT]")
    print()
    print("IGNITION EXPOSURE BY TERRAIN:")
    for terrain, data in results["lambda_by_terrain"].items():
        print(f"  {terrain.replace('_', ' ').title():20} ({data['miles']:5.1f} mi):")
        print(
            f"    Base Rate: {data['base_rate']:.6f} events/mi/yr (overhead baseline)"
        )
        print(f"    Construction Multiplier: {data['construction_multiplier']:.2f}×")
        print(
            f"    Effective Rate: {data['rate_per_mile']:.6f} events/mi/yr ({data['base_rate']:.6f} × {data['construction_multiplier']:.2f})"
        )
        print(f"    Events/Year: {data['events_per_year']:.6f}")
        print()
    print(f"  {'-' * 76}")
    print(f"  {'Total Annual Events:':20} {results['lambda_total']:.6f} events/year")
    print()

    print("EVENT SEVERITY:")
    print(f"  Mean Loss per Event: ${results['severity']:,.0f}")
    print()

    print("EXPECTED ANNUAL LOSS:")
    print(f"  EAL = λ × S: ${results['EAL']:,.2f}/year")
    print()

    print("[NOMINAL VALUES]")
    print(f"  Project Lifetime: {project_lifetime} years")
    print(f"  Risk Growth Rate: {results['growth_rate']:.1%}/year")
    print(f"  ---")
    print(f"  TOTAL NOMINAL COST: ${results['nominal_total']:,.2f}")
    print(f"    (Sum of growing annual costs, undiscounted)")
    print()

    print("[SOCIETAL PERSPECTIVE - Present Value]")
    print(f"  Discount Rate: {discount_rate:.2%} ({discount_source})")
    print(f"  Growing Annuity Formula: Applied")
    if results["growth_rate"] > discount_rate:
        print(
            f"  ⚠️  WARNING: Risk growth rate ({results['growth_rate']:.2%}) > discount rate ({discount_rate:.2%})"
        )
        print(f"      PV grows over time - risk is escalating faster than discounting!")
    print(f"  ---")
    print(f"  TOTAL PRESENT VALUE: ${results['pv_cost']:,.2f}")
    print()
    print("NOTE: Wildfire costs are probabilistic future losses, not capital costs.")
    print("      No AFUDC applies to expected loss calculations.")
    print("=" * 80)

    # ========================================================================
    # CSV OUTPUT - Write results to batch summary and detail CSV
    # ========================================================================
    
    # Initialize CSV output manager
    csv_manager = CTCCOutputManager()
    
    # Write to CSV (results dict already has all needed values)
    csv_manager.add_wildfire_costs(results)
    csv_manager.write_batch_summary()


if __name__ == "__main__":
    main()
