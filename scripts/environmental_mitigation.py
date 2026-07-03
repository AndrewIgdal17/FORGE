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
from calculation_utils import normalize_construction_type_for_yaml
from financial_utils import (
    calculate_present_value,
    calculate_afudc_rate,
    calculate_afudc_capitalized_cost,
    validate_discount_rate,
    calculate_construction_start_year,
)
from path_config import YAMLS_DIR


def calculate_environmental_mitigation_costs(
    em_yaml: Dict[str, Any],
    category: str,
    terrain_miles_dict: Dict[str, float],
    row_width_feet: float,
    reconductoring: bool = False,
    subsea_capex: float = 0.0,
) -> Dict[str, float]:
    """
    Calculate environmental mitigation costs including base mitigation,
    wetland/habitat credit purchases, and marine environmental mitigation.

    Args:
        em_yaml: Loaded environmental mitigation YAML data
        category: Project category identifier
        terrain_miles_dict: Dictionary of terrain type to miles
        row_width_feet: ROW width in feet
        reconductoring: If True, sets wetland and habitat credits to zero
                       (reconductoring projects use existing ROW and don't create
                       new permanent environmental impacts requiring credits)
        subsea_capex: Subsea line construction CAPEX (conductor + structure),
                     used for marine environmental mitigation (% of CAPEX)

    Returns:
        dict: Contains base_cost, wetlands_credits, habitat_credits, marine_cost,
              total, uplift_factor_applied, total_acres, effective_acres
    """
    mitigation_config = em_yaml["environmental_mitigation"]
    base_costs = mitigation_config["base_mitigation_cost_per_acre"]
    uplift_factor = mitigation_config.get("mitigation_uplift_factor", 1.0)
    mitigation_ratio = mitigation_config.get("mitigation_ratio", 2.0)

    # Determine construction type from category
    construction_type = category.split("/")[0]  # e.g., "overhead", "underground"

    # Map construction_type to YAML keys
    yaml_construction_type = normalize_construction_type_for_yaml(construction_type, context="environmental")

    # Calculate base acreage by terrain (before uplift)
    total_base_acres = 0.0
    base_cost = 0.0
    acres_by_terrain = {}

    for terrain, miles in terrain_miles_dict.items():
        if miles > 0:
            # Calculate acres using utility function
            from calculation_utils import miles_to_acres
            terrain_acres = miles_to_acres(miles, row_width_feet)
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
    wetland_impacted_acres = acres_by_terrain.get("wetland", 0.0) * uplift_factor * mitigation_ratio

    # Habitat credits: sum relevant natural terrains (conservative approach)
    habitat_terrains = [
        "forested",
        "scrubbed_flat",
        "desert_barren",
        "rolling_hills",
        "mountain",
    ]
    habitat_impacted_acres = (
        sum(acres_by_terrain.get(t, 0.0) for t in habitat_terrains) * uplift_factor * mitigation_ratio
    )

    # Calculate wetland credits
    wetland_cost_per_acre = mitigation_config.get("wetland_credit_cost_per_acre", 25000)
    wetlands_credits = wetland_cost_per_acre * wetland_impacted_acres

    # Calculate habitat credits: per-terrain cost
    habitat_costs = mitigation_config.get("habitat_credit_cost_per_acre", {})
    habitat_credits = 0.0
    for terrain in habitat_terrains:
        terrain_acres = acres_by_terrain.get(terrain, 0.0)
        if terrain_acres > 0:
            effective_acres = terrain_acres * uplift_factor * mitigation_ratio
            cost_per_acre = habitat_costs.get(terrain, 30000)
            habitat_credits += cost_per_acre * effective_acres

    # For reconductoring projects, set credits to zero since they use existing ROW
    # and don't create new permanent environmental impacts requiring mitigation credits
    if reconductoring:
        wetlands_credits = 0.0
        habitat_credits = 0.0

    # Marine environmental mitigation (subsea only, % of CAPEX)
    marine_env_mitigation_pct_capex = mitigation_config.get("marine_env_mitigation_pct_capex", 0.0)
    if yaml_construction_type == "subsea":
        marine_cost = marine_env_mitigation_pct_capex * subsea_capex
    else:
        marine_cost = 0.0

    return {
        "base_cost": base_cost,
        "wetlands_credits": wetlands_credits,
        "habitat_credits": habitat_credits,
        "total_credits": wetlands_credits + habitat_credits,
        "marine_cost": marine_cost,
        "total": base_cost + wetlands_credits + habitat_credits + marine_cost,
        "uplift_factor_applied": uplift_factor,
        "total_base_acres": total_base_acres,
        "total_effective_acres": total_effective_acres,
        "wetland_impacted_acres": wetland_impacted_acres,
        "habitat_impacted_acres": habitat_impacted_acres,
        "mitigation_ratio": mitigation_ratio,
    }


def main() -> None:
    """Main function to calculate and display environmental mitigation costs."""
    # Load project specifications
    project_details = load_project_technical_details()

    # Construct category identifier
    from calculation_utils import build_category_string
    category = build_category_string(project_details=project_details)

    # Load ROW width for this project category
    row_width_feet = load_row_widths(category)

    # Load terrain details
    from smart_loaders import load_terrain_miles
    terrain_miles = load_terrain_miles()

    # Load environmental mitigation parameters
    em_yaml = load_environmental_mitigation()

    # Compute subsea CAPEX for marine mitigation (subsea only)
    subsea_capex = 0.0
    if project_details.construction_type == "Subsea":
        from weighted_miles import calculate_weighted_miles
        import yaml as _yaml
        _static_yamls = YAMLS_DIR
        with open(_static_yamls / "10_project_category_build_costs.yaml", "r") as _f:
            _bc_data = _yaml.safe_load(_f)
        _build_costs = _bc_data["project_categories_build_costs"]
        _cat = category
        if _cat in _build_costs:
            _cat_data = _build_costs[_cat]
            _wm, _ = calculate_weighted_miles()
            _conductor_cost = (_cat_data.get("variable_conductor_cost_per_mile", 0) * _wm) + _cat_data.get("fixed_conductor_cost", 0)
            _structure_cost = _cat_data.get("variable_structure_cost_per_mile", 0) * _wm
            subsea_capex = _conductor_cost + _structure_cost

    # Calculate environmental mitigation costs (nominal)
    results = calculate_environmental_mitigation_costs(
        em_yaml, category, terrain_miles, row_width_feet, project_details.reconductoring,
        subsea_capex=subsea_capex,
    )

    from run_context import add_derived
    from calculation_utils import miles_to_acres
    _terrain_acres = {t: miles_to_acres(m, row_width_feet) for t, m in terrain_miles.items() if m > 0}
    _uplift = results["uplift_factor_applied"]
    _eff_acres = {t: a * _uplift for t, a in _terrain_acres.items()}
    add_derived({
        "terrain_acres": _terrain_acres,
        "effective_acres_per_terrain": _eff_acres,
        "total_effective_acres": results["total_effective_acres"],
        "wetland_impacted_acres": results["wetland_impacted_acres"],
        "habitat_impacted_acres": results["habitat_impacted_acres"],
    })

    # Load financing parameters for discounting
    financing = load_financing_details()

    # Load AFUDC configuration and timing patterns
    from financial_utils import load_afudc_setup
    afudc_setup = load_afudc_setup()

    # ===== REGULATORY PERSPECTIVE: AFUDC Capitalization =====
    if afudc_setup.apply_afudc:
        # Base mitigation costs (includes marine environmental mitigation)
        base_cap, base_afudc = calculate_afudc_capitalized_cost(
            results["base_cost"] + results["marine_cost"],
            afudc_setup.timing_patterns["environmental_mitigation_base"],
            project_details.delay_years,
            project_details.construction_years,
            afudc_setup.afudc_rate,
            afudc_setup.delay_active,
        )

        # Credit costs (wetlands + habitat combined)
        credits_cap, credits_afudc = calculate_afudc_capitalized_cost(
            results["total_credits"],
            afudc_setup.timing_patterns["environmental_mitigation_credits"],
            project_details.delay_years,
            project_details.construction_years,
            afudc_setup.afudc_rate,
            afudc_setup.delay_active,
        )

        total_capitalized = base_cap + credits_cap
        total_afudc = base_afudc + credits_afudc

    # ===== SOCIETAL PERSPECTIVE: Present Value Discounting =====
    # Validate wacc_real before direct use to prevent division by zero
    validate_discount_rate(financing.wacc_real, "wacc_real")

    # Credit purchases: occur upfront at start of construction (end of delay period)
    # Discount as one-time payment at delay_year + 1
    credit_start_year = calculate_construction_start_year(project_details.delay_years)
    total_credits_pv = results["total_credits"] / (1 + financing.wacc_real) ** credit_start_year
    wetlands_credits_pv = (
        results["wetlands_credits"] / (1 + financing.wacc_real) ** credit_start_year
    )
    habitat_credits_pv = (
        results["habitat_credits"] / (1 + financing.wacc_real) ** credit_start_year
    )

    # Base mitigation: spread evenly over construction period
    # Annual cost during construction years
    if project_details.construction_years > 0:
        annual_base_cost = (results["base_cost"] + results["marine_cost"]) / project_details.construction_years
        base_cost_pv = calculate_present_value(
            annual_base_cost, financing.wacc_real, project_details.construction_years, credit_start_year
        )
    else:
        base_cost_pv = (results["base_cost"] + results["marine_cost"]) / (1 + financing.wacc_real) ** credit_start_year

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
    print(f"  Marine Environmental Mitigation: ${results['marine_cost']:,.2f}")
    print(f"  Wetland Credits: ${results['wetlands_credits']:,.2f}")
    print(f"  Habitat Credits: ${results['habitat_credits']:,.2f}")
    print(f"  Total Credit Costs: ${results['total_credits']:,.2f}")
    print(f"  ---")
    print(f"  TOTAL NOMINAL COST: ${results['total']:,.2f}")
    print()

    if afudc_setup.apply_afudc:
        print("[REGULATORY PERSPECTIVE - AFUDC Capitalization]")
        print(f"  AFUDC Rate: {afudc_setup.afudc_rate:.2%} ({afudc_setup.afudc_source})")
        print(f"  Delay Period Active Work: {'Yes' if afudc_setup.delay_active else 'No'}")
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
    print(f"  Discount Rate: {financing.wacc_real:.2%} (real WACC)")
    print(f"  Base Year: {financing.base_year}")
    print()
    print(f"  Base Mitigation/Restoration PV: ${base_cost_pv:,.2f}")
    print(f"    (Spread over {project_details.construction_years} year(s))")
    print(f"  Wetland Credits PV: ${wetlands_credits_pv:,.2f}")
    print(f"  Habitat Credits PV: ${habitat_credits_pv:,.2f}")
    print(f"  Total Credit Costs PV: ${total_credits_pv:,.2f}")
    print(f"    (Payments start at year {credit_start_year:.1f})")
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
        "total_afudc": total_capitalized if afudc_setup.apply_afudc else 0,
        "total_pv": total_pv,
        "base_cost_nominal": results["base_cost"],
        "marine_cost_nominal": results["marine_cost"],
        "credits_nominal": results["total_credits"],
        "credits_pv": total_credits_pv,
    }

    # Write to CSV
    csv_manager.add_environmental_mitigation(csv_results)
    csv_manager.write_batch_summary()


if __name__ == "__main__":
    main()
