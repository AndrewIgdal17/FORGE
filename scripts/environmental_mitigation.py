# Author: Andrew Igdal
# Date: 2025-10-28
# Description: This script calculates environmental mitigation costs for a transmission line.
#              It computes base construction/restoration costs and wetland/habitat credit purchases
#              across different construction types and terrain types.

from __future__ import annotations

# Standard library imports
import yaml
import sys
import os
from typing import Dict, Any

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from smart_output import CTCCOutputManager

# Local utility imports
from smart_loaders import (
    load_project_technical_details,
    load_physical_details,
    load_row_widths,
    load_environmental_mitigation,
    load_financing_details,
    load_cost_timing_patterns,
    load_afudc_config,
    get_physical_data_raw,
    get_financing_data_raw,
)
from financial_utils import (
    calculate_present_value,
    calculate_afudc_rate,
    calculate_afudc_capitalized_cost,
    validate_discount_rate,
)
from path_config import YAMLS_DIR


def calculate_environmental_mitigation_costs(
    em_yaml: Dict[str, Any],
    category: str,
    terrain_miles_dict: Dict[str, float],
    row_width_feet: float,
    reconductoring: bool = False,
) -> Dict[str, float]:
    """
    Calculate environmental mitigation costs including base mitigation
    and wetland/habitat credit purchases.

    Args:
        em_yaml: Loaded environmental mitigation YAML data
        category: Project category identifier
        terrain_miles_dict: Dictionary of terrain type to miles
        row_width_feet: ROW width in feet
        reconductoring: If True, sets wetland and habitat credits to zero
                       (reconductoring projects use existing ROW and don't create
                       new permanent environmental impacts requiring credits)

    Returns:
        dict: Contains base_cost, wetlands_credits, habitat_credits,
              total, uplift_factor_applied, total_acres, effective_acres
    """
    mitigation_config = em_yaml["environmental_mitigation"]
    base_costs = mitigation_config["base_mitigation_cost_per_acre"]
    credits = mitigation_config.get("credit_cost_per_acre", {})
    ratios = mitigation_config.get("credit_ratios", {})
    uplift_factor = mitigation_config.get("mitigation_uplift_factor", 1.0)

    # Determine construction type from category
    construction_type = category.split("/")[0]  # e.g., "overhead", "underground"

    # Map construction_type to YAML keys
    construction_type_map = {
        "overhead": "overhead",
        "underground": "underground_direct_buried",  # default to direct_buried
        "subsea": "subsea",
    }
    yaml_construction_type = construction_type_map.get(construction_type, "overhead")

    # Calculate base acreage by terrain (before uplift)
    total_base_acres = 0.0
    base_cost = 0.0
    acres_by_terrain = {}

    for terrain, miles in terrain_miles_dict.items():
        if miles > 0:
            # Calculate acres: miles × 5280 ft/mile × row_width_feet / 43560 ft²/acre
            terrain_acres = (miles * 5280 * row_width_feet) / 43560
            acres_by_terrain[terrain] = terrain_acres
            total_base_acres += terrain_acres

            # Apply uplift for effective acres
            effective_acres = terrain_acres * uplift_factor

            # Get cost per acre for this construction type and terrain
            cost_per_acre = base_costs.get(yaml_construction_type, {}).get(terrain, 0.0)
            base_cost += cost_per_acre * effective_acres

    # Calculate total effective acres (with uplift)
    total_effective_acres = total_base_acres * uplift_factor

    # Identify impacted acres for credits (use effective acres with uplift)
    wetland_impacted_acres = acres_by_terrain.get("wetland", 0.0) * uplift_factor

    # Habitat credits: sum relevant natural terrains (conservative approach)
    habitat_terrains = ["forested", "scrubbed_flat", "desert_barren", "rolling_hills"]
    habitat_impacted_acres = (
        sum(acres_by_terrain.get(t, 0.0) for t in habitat_terrains) * uplift_factor
    )

    # Calculate wetland credits (using "other" subtype as default)
    wetland_cost_per_acre = credits.get("wetlands", {}).get("other", 0.0)
    wetland_ratio = ratios.get("wetlands", {}).get("other", 1.0)
    wetlands_credits = wetland_cost_per_acre * wetland_ratio * wetland_impacted_acres

    # Calculate habitat credits (using "default" subtype)
    habitat_cost_per_acre = credits.get("habitat", {}).get("default", 0.0)
    habitat_ratio = ratios.get("habitat", {}).get("default", 1.0)
    habitat_credits = habitat_cost_per_acre * habitat_ratio * habitat_impacted_acres

    # For reconductoring projects, set credits to zero since they use existing ROW
    # and don't create new permanent environmental impacts requiring mitigation credits
    if reconductoring:
        wetlands_credits = 0.0
        habitat_credits = 0.0

    return {
        "base_cost": base_cost,
        "wetlands_credits": wetlands_credits,
        "habitat_credits": habitat_credits,
        "total_credits": wetlands_credits + habitat_credits,
        "total": base_cost + wetlands_credits + habitat_credits,
        "uplift_factor_applied": uplift_factor,
        "total_base_acres": total_base_acres,
        "total_effective_acres": total_effective_acres,
        "wetland_impacted_acres": wetland_impacted_acres,
        "habitat_impacted_acres": habitat_impacted_acres,
    }


def main() -> None:
    """Main function to calculate and display environmental mitigation costs."""
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
        converter_loss_percentage,
    ) = load_project_technical_details()

    # Construct category identifier
    category = (
        f"{construction_type}/{ac_dc}/{capacity_mw}MW/{conductor_type}/{converter_type}"
    )

    # Load ROW width for this project category
    row_width_feet = load_row_widths(category)

    # Load terrain details
    try:
        physical_details = get_physical_data_raw()
        if "terrain" not in physical_details:
            raise KeyError("Missing 'terrain' key in physical details")
        if "terrain_miles" not in physical_details["terrain"]:
            raise KeyError(
                "Missing 'terrain_miles' key in terrain section of physical details"
            )
        terrain_miles = physical_details["terrain"]["terrain_miles"]
    except KeyError as e:
        raise KeyError(f"Missing required key in physical details: {e}")

    # Load environmental mitigation parameters
    em_yaml = load_environmental_mitigation()

    # Calculate environmental mitigation costs (nominal)
    results = calculate_environmental_mitigation_costs(
        em_yaml, category, terrain_miles, row_width_feet, reconductoring
    )

    # Load financing parameters for discounting
    inflation_rate, base_year, wacc_nominal, wacc_real = load_financing_details()

    # Load AFUDC configuration and timing patterns
    timing_patterns = load_cost_timing_patterns()["cost_timing_patterns"]
    apply_afudc, delay_active = load_afudc_config()

    # Load full financing data for AFUDC rate calculation
    financing_yaml = get_financing_data_raw()
    afudc_rate, afudc_source = calculate_afudc_rate(financing_yaml)

    # ===== REGULATORY PERSPECTIVE: AFUDC Capitalization =====
    if apply_afudc:
        # Base mitigation costs
        base_cap, base_afudc = calculate_afudc_capitalized_cost(
            results["base_cost"],
            timing_patterns["environmental_mitigation_base"],
            delay_year,
            construction_years,
            afudc_rate,
            delay_active,
        )

        # Credit costs (wetlands + habitat combined)
        credits_cap, credits_afudc = calculate_afudc_capitalized_cost(
            results["total_credits"],
            timing_patterns["environmental_mitigation_credits"],
            delay_year,
            construction_years,
            afudc_rate,
            delay_active,
        )

        total_capitalized = base_cap + credits_cap
        total_afudc = base_afudc + credits_afudc

    # ===== SOCIETAL PERSPECTIVE: Present Value Discounting =====
    # Validate wacc_real before direct use to prevent division by zero
    validate_discount_rate(wacc_real, "wacc_real")

    # Credit purchases: occur upfront at start of construction (end of delay period)
    # Discount as one-time payment at delay_year + 1
    credit_start_year = delay_year + 1
    total_credits_pv = results["total_credits"] / (1 + wacc_real) ** credit_start_year
    wetlands_credits_pv = (
        results["wetlands_credits"] / (1 + wacc_real) ** credit_start_year
    )
    habitat_credits_pv = (
        results["habitat_credits"] / (1 + wacc_real) ** credit_start_year
    )

    # Base mitigation: spread evenly over construction period
    # Annual cost during construction years
    if construction_years > 0:
        annual_base_cost = results["base_cost"] / construction_years
        base_cost_pv = calculate_present_value(
            annual_base_cost, wacc_real, construction_years, credit_start_year
        )
    else:
        # If construction_years is 0, treat as one-time cost at credit_start_year
        base_cost_pv = results["base_cost"] / (1 + wacc_real) ** credit_start_year

    # Total PV
    total_pv = base_cost_pv + total_credits_pv

    # Display results
    print("=" * 80)
    print("ENVIRONMENTAL MITIGATION COST CALCULATION RESULTS")
    print("=" * 80)
    print(f"Project Category: {category}")
    print(f"ROW Width: {row_width_feet:.1f} feet")
    print(f"Uplift Factor (TCE): {results['uplift_factor_applied']:.2f}x")
    print()

    print("ACREAGE SUMMARY:")
    print(f"  Base ROW Acres: {results['total_base_acres']:,.2f}")
    print(f"  Effective Acres (with uplift): {results['total_effective_acres']:,.2f}")
    print(f"  Wetland Impacted Acres: {results['wetland_impacted_acres']:,.2f}")
    print(f"  Habitat Impacted Acres: {results['habitat_impacted_acres']:,.2f}")
    print()

    print("[NOMINAL VALUES]")
    print(f"  Base Mitigation/Restoration: ${results['base_cost']:,.2f}")
    print(f"  Wetland Credits: ${results['wetlands_credits']:,.2f}")
    print(f"  Habitat Credits: ${results['habitat_credits']:,.2f}")
    print(f"  Total Credit Costs: ${results['total_credits']:,.2f}")
    print(f"  ---")
    print(f"  TOTAL NOMINAL COST: ${results['total']:,.2f}")
    print()

    if apply_afudc:
        print("[REGULATORY PERSPECTIVE - AFUDC Capitalization]")
        print(f"  AFUDC Rate: {afudc_rate:.2%} ({afudc_source})")
        print(f"  Delay Period Active Work: {'Yes' if delay_active else 'No'}")
        print()
        print(f"  Base Mitigation Capitalized: ${base_cap:,.2f}")
        print(f"    AFUDC on Base: ${base_afudc:,.2f}")
        print(f"  Credits Capitalized: ${credits_cap:,.2f}")
        print(f"    AFUDC on Credits: ${credits_afudc:,.2f}")
        print(f"  ---")
        print(f"  TOTAL CAPITALIZED COST (at COD): ${total_capitalized:,.2f}")
        print(f"  Total AFUDC Amount: ${total_afudc:,.2f}")
        print()

    print("[SOCIETAL PERSPECTIVE - Present Value]")
    print(f"  Discount Rate: {wacc_real:.2%} (real WACC)")
    print(f"  Base Year: {base_year}")
    print()
    print(f"  Base Mitigation/Restoration PV: ${base_cost_pv:,.2f}")
    print(f"    (Spread over {construction_years} year(s))")
    print(f"  Wetland Credits PV: ${wetlands_credits_pv:,.2f}")
    print(f"  Habitat Credits PV: ${habitat_credits_pv:,.2f}")
    print(f"  Total Credit Costs PV: ${total_credits_pv:,.2f}")
    print(f"    (Payments start at year {credit_start_year})")
    print(f"  ---")
    print(f"  TOTAL PRESENT VALUE: ${total_pv:,.2f}")
    print("=" * 80)

    # ========================================================================
    # CSV OUTPUT - Write results to batch summary and detail CSV
    # ========================================================================

    # Initialize CSV output manager
    csv_manager = CTCCOutputManager()

    # Prepare results dictionary
    csv_results = {
        "total_nominal": results["total"],
        "total_afudc": total_capitalized if apply_afudc else 0,
        "total_pv": total_pv,
        "base_cost_nominal": results["base_cost"],
        "credits_nominal": results["total_credits"],
        "credits_pv": total_credits_pv,
    }

    # Write to CSV
    csv_manager.add_environmental_mitigation(csv_results)
    csv_manager.write_batch_summary()


if __name__ == "__main__":
    main()
