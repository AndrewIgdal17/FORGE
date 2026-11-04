# Date: 2025-10-28
# Description: This script calculates environmental mitigation costs for a transmission line.
#              It computes base construction/restoration costs and wetland/habitat credit purchases
#              across different construction types and terrain types.

from __future__ import annotations

import logging

# Standard library imports
import yaml
from typing import Any

from forge.scripts.utils.smart_output import SmartOutputManager

# Local utility imports
from forge.scripts.utils.smart_loaders import (
    load_project_technical_details,
    load_row_widths,
    load_environmental_mitigation,
    load_financing_details,
)
from forge.scripts.utils.financial_utils import (
    calculate_present_value,
    calculate_afudc_rate,
    calculate_afudc_capitalized_cost,
    validate_discount_rate,
    calculate_construction_start_year,
)
from forge.scripts.utils.run_context import get_run_context, add_derived

logger = logging.getLogger(__name__)


HABITAT_CLASSES = (
    "forested",
    "scrubbed_flat",
    "desert_barren",
    "rolling_hills",
    "mountain",
)


def disturbance_multiplier(project_type: str, rebuild_multiplier: float) -> float:
    from forge.errors import InvalidInputs

    if project_type == "reconductoring":
        return 0.0
    if project_type == "rebuild":
        return float(rebuild_multiplier)
    if project_type == "greenfield":
        return 1.0
    raise InvalidInputs(f"project_type '{project_type}' is not allowed.")


def calculate_environmental_mitigation_costs(
    em_yaml: dict[str, Any],
    category: str,
    acres_by_terrain: dict[str, float],
    protected_area_acres: dict[str, float],
    project_type: str = "greenfield",
) -> dict[str, float]:
    from forge.scripts.utils.calculation_utils import normalize_construction_type_for_yaml

    config = em_yaml["environmental_mitigation"]
    uplift = float(config["mitigation_uplift_factor"])
    mu_wet = float(config["wetland_compensation_ratio"])
    mu_hab = float(config["habitat_compensation_ratio"])
    mu_d = disturbance_multiplier(
        project_type, float(config["disturbance_multiplier_rebuild"])
    )
    yaml_ct = normalize_construction_type_for_yaml(
        category.split("/")[0], context="environmental"
    )
    base_table = config["base_mitigation_cost_per_acre"].get(yaml_ct, {})
    base_cost = 0.0
    total_base_acres = 0.0
    for terrain, acres in acres_by_terrain.items():
        if acres is None or acres <= 0:
            continue
        total_base_acres += float(acres)
        base_cost += float(base_table.get(terrain, 0.0)) * uplift * float(acres)
    base_cost *= mu_d
    wetland_acres = float(acres_by_terrain.get("wetland") or 0.0)
    wetland_impacted = mu_d * mu_wet * uplift * wetland_acres
    wetlands_credits = float(config["wetland_credit_cost_per_acre"]) * wetland_impacted
    prices = config["habitat_credit_cost_per_credit"]
    habitat_credits = 0.0
    habitat_credit_count = 0.0
    for terrain in HABITAT_CLASSES:
        gap = float(protected_area_acres.get(terrain) or 0.0)
        count = mu_d * uplift * mu_hab * gap
        habitat_credit_count += count
        habitat_credits += float(prices[terrain]) * count
    total_credits = wetlands_credits + habitat_credits
    return {
        "base_cost": base_cost,
        "wetlands_credits": wetlands_credits,
        "habitat_credits": habitat_credits,
        "habitat_credit_count": habitat_credit_count,
        "total_credits": total_credits,
        "total": base_cost + total_credits,
        "uplift_factor_applied": uplift,
        "total_base_acres": total_base_acres,
        "total_effective_acres": total_base_acres * uplift,
        "wetland_impacted_acres": wetland_impacted,
    }

def main() -> None:
    """Main function to calculate and display environmental mitigation costs."""
    # Load project specifications
    project_details = load_project_technical_details()

    # Construct category identifier
    ctx = get_run_context()
    if ctx is None:
        raise RuntimeError(
            f"{__name__} requires a RunContext. Run via forge.py or set up "
            "RunContext in your test fixture."
        )
    category = ctx.category_string

    # Load ROW width for this project category
    row_width_feet = load_row_widths(category)

    # Load terrain details
    from forge.scripts.utils.smart_loaders import load_terrain_miles
    terrain_miles = load_terrain_miles()

    # Load environmental mitigation parameters
    em_yaml = load_environmental_mitigation()

    from forge.scripts.utils.calculation_utils import miles_to_acres
    from forge.scripts.io.yaml_loaders import load_protected_area_acres

    acres_by_terrain = {
        terrain: miles_to_acres(miles, row_width_feet)
        for terrain, miles in terrain_miles.items()
        if miles
    }
    results = calculate_environmental_mitigation_costs(
        em_yaml,
        category,
        acres_by_terrain,
        load_protected_area_acres(),
        project_type=project_details.project_type,
    )

    _terrain_acres = {t: miles_to_acres(m, row_width_feet) for t, m in terrain_miles.items() if m > 0}
    _uplift = results["uplift_factor_applied"]
    _eff_acres = {t: a * _uplift for t, a in _terrain_acres.items()}
    add_derived({
        "terrain_acres": _terrain_acres,
        "effective_acres_per_terrain": _eff_acres,
        "total_effective_acres": results["total_effective_acres"],
        "wetland_impacted_acres": results["wetland_impacted_acres"],
        "habitat_credit_count": results["habitat_credit_count"],
    })

    # Load financing parameters for discounting
    financing = load_financing_details()

    # Load AFUDC configuration and timing patterns
    from forge.scripts.utils.financial_utils import load_afudc_setup
    afudc_setup = load_afudc_setup()

    # ===== REGULATORY PERSPECTIVE: AFUDC Capitalization =====
    if afudc_setup.apply_afudc:
        # Base mitigation costs
        base_cap, base_afudc = calculate_afudc_capitalized_cost(
            results["base_cost"],
            afudc_setup.timing_patterns["environmental_mitigation_base"],
            project_details.delay_years,
            project_details.construction_years,
            afudc_setup.afudc_rate,
            afudc_setup.delay_active,
            spending_profiles=afudc_setup.spending_profiles,
        )

        # Credit costs (wetlands + habitat combined)
        credits_cap, credits_afudc = calculate_afudc_capitalized_cost(
            results["total_credits"],
            afudc_setup.timing_patterns["environmental_mitigation_credits"],
            project_details.delay_years,
            project_details.construction_years,
            afudc_setup.afudc_rate,
            afudc_setup.delay_active,
            spending_profiles=afudc_setup.spending_profiles,
        )

        total_capitalized = base_cap + credits_cap
        total_afudc = base_afudc + credits_afudc

    # ===== SOCIETAL PERSPECTIVE: Present Value Discounting =====
    # Validate wacc_real before direct use to prevent division by zero
    validate_discount_rate(financing.wacc_real, "wacc_real")

    construction_start_year = calculate_construction_start_year(project_details.delay_years)
    annual_total_credits = results["total_credits"] / project_details.construction_years
    annual_wetlands = results["wetlands_credits"] / project_details.construction_years
    annual_habitat = results["habitat_credits"] / project_details.construction_years
    total_credits_pv = calculate_present_value(
        annual_total_credits, financing.wacc_real, project_details.construction_years, construction_start_year
    )
    wetlands_credits_pv = calculate_present_value(
        annual_wetlands, financing.wacc_real, project_details.construction_years, construction_start_year
    )
    habitat_credits_pv = calculate_present_value(
        annual_habitat, financing.wacc_real, project_details.construction_years, construction_start_year
    )

    # Base mitigation: spread evenly over construction period
    # Annual cost during construction years
    annual_base_cost = results["base_cost"] / project_details.construction_years
    base_cost_pv = calculate_present_value(
        annual_base_cost, financing.wacc_real, project_details.construction_years, construction_start_year
    )

    # Total PV
    total_pv = base_cost_pv + total_credits_pv

    # Display results
    logger.info("=" * 80)
    logger.info("ENVIRONMENTAL MITIGATION COST CALCULATION RESULTS")
    logger.info("=" * 80)
    logger.info(f"Project Category: {category}")
    logger.info(f"ROW Width: {row_width_feet:.1f} feet")
    logger.info(f"Uplift Factor (TCE): {results['uplift_factor_applied']:.2f}x")
    logger.info("")

    logger.info("ACREAGE SUMMARY:")
    logger.info(f"  Base ROW Acres: {results['total_base_acres']:,.2f}")
    logger.info(f"  Effective Acres (with uplift): {results['total_effective_acres']:,.2f}")
    logger.info(f"  Wetland Impacted Acres: {results['wetland_impacted_acres']:,.2f}")
    logger.info(f"  Habitat Credit Count: {results['habitat_credit_count']:,.2f}")
    logger.info("")

    logger.info("[NOMINAL VALUES]")
    logger.info(f"  Base Mitigation/Restoration: ${results['base_cost']:,.2f}")
    logger.info(f"  Wetland Credits: ${results['wetlands_credits']:,.2f}")
    logger.info(f"  Habitat Credits: ${results['habitat_credits']:,.2f}")
    logger.info(f"  Total Credit Costs: ${results['total_credits']:,.2f}")
    logger.info(f"  ---")
    logger.info(f"  TOTAL NOMINAL COST: ${results['total']:,.2f}")
    logger.info("")

    if afudc_setup.apply_afudc:
        logger.info("[REGULATORY PERSPECTIVE - AFUDC Capitalization]")
        logger.info(f"  AFUDC Rate: {afudc_setup.afudc_rate:.2%} ({afudc_setup.afudc_source})")
        logger.info(f"  Delay Period Active Work: {'Yes' if afudc_setup.delay_active else 'No'}")
        logger.info("")
        logger.info(f"  Base Mitigation Capitalized: ${base_cap:,.2f}")
        logger.info(f"    AFUDC on Base: ${base_afudc:,.2f}")
        logger.info(f"  Credits Capitalized: ${credits_cap:,.2f}")
        logger.info(f"    AFUDC on Credits: ${credits_afudc:,.2f}")
        logger.info(f"  ---")
        logger.info(f"  TOTAL CAPITALIZED COST (at COD): ${total_capitalized:,.2f}")
        logger.info(f"  Total AFUDC Amount: ${total_afudc:,.2f}")
        logger.info("")

    logger.info("[SOCIETAL PERSPECTIVE - Present Value]")
    logger.info(f"  Discount Rate: {financing.wacc_real:.2%} (real WACC)")
    logger.info(f"  Base Year: {financing.base_year}")
    logger.info("")
    logger.info(f"  Base Mitigation/Restoration PV: ${base_cost_pv:,.2f}")
    logger.info(f"    (Spread over {project_details.construction_years} year(s))")
    logger.info(f"  Wetland Credits PV: ${wetlands_credits_pv:,.2f}")
    logger.info(f"  Habitat Credits PV: ${habitat_credits_pv:,.2f}")
    logger.info(f"  Total Credit Costs PV: ${total_credits_pv:,.2f}")
    logger.info(f"    (Payments start at year {construction_start_year:.1f})")
    logger.info(f"  ---")
    logger.info(f"  TOTAL PRESENT VALUE: ${total_pv:,.2f}")
    logger.info("=" * 80)

    # ========================================================================
    # CSV OUTPUT - Write results to batch summary and detail CSV
    # ========================================================================

    # Initialize CSV output manager
    csv_manager = SmartOutputManager()

    # Prepare results dictionary
    csv_results = {
        "total_nominal": results["total"],
        "total_afudc": total_capitalized if afudc_setup.apply_afudc else 0,
        "total_pv": total_pv,
        "base_cost_nominal": results["base_cost"],
        "base_cost_pv": base_cost_pv,
        "credits_nominal": results["total_credits"],
        "credits_pv": total_credits_pv,
    }

    # Write to CSV
    csv_manager.add_environmental_mitigation(csv_results)
    csv_manager.write_batch_summary()
