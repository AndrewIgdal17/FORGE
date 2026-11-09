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
    capitalize_yearly_spending,
    validate_discount_rate,
)
from forge.scripts.utils.streams import pv, undiscounted, weighted
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
    from forge.errors import InvalidInputs

    yaml_ct = normalize_construction_type_for_yaml(
        category.split("/")[0], context="environmental"
    )
    base_table = config["base_mitigation_cost_per_acre"].get(yaml_ct, {})
    base_cost = 0.0
    total_base_acres = 0.0
    for terrain, acres in acres_by_terrain.items():
        if acres is None or acres == 0:
            continue
        if acres < 0:
            raise InvalidInputs(
                f"Negative acreage for terrain class '{terrain}'."
            )
        if terrain not in base_table or base_table[terrain] is None:
            raise InvalidInputs(
                f"No base mitigation cost per acre for construction type "
                f"'{yaml_ct}' and terrain class '{terrain}'."
            )
        total_base_acres += float(acres)
        base_cost += float(base_table[terrain]) * uplift * float(acres)
    base_cost *= mu_d
    wetland_acres = float(acres_by_terrain.get("wetland") or 0.0)
    wetland_impacted = mu_d * mu_wet * uplift * wetland_acres
    wetlands_credits = float(config["wetland_credit_cost_per_acre"]) * wetland_impacted
    prices = config["habitat_credit_cost_per_credit"]
    habitat_credits = 0.0
    habitat_credit_count = 0.0
    for terrain in HABITAT_CLASSES:
        gap = float(protected_area_acres.get(terrain) or 0.0)
        if gap > 0 and (terrain not in prices or prices[terrain] is None):
            raise InvalidInputs(
                f"No habitat credit price for habitat class '{terrain}'."
            )
        if terrain not in prices or prices[terrain] is None:
            continue
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

    # On-site mitigation and credits share one MISO-weighted stream, with no
    # escalation. Capitalization uses that same yearly stream.
    financing = load_financing_details()
    validate_discount_rate(financing.wacc_real, "wacc_real")

    base_stream = weighted(
        results["base_cost"], ctx.spending_weights, ctx.t_start, ctx.horizon
    )
    credits_stream = weighted(
        results["total_credits"], ctx.spending_weights, ctx.t_start, ctx.horizon
    )
    mitigation_stream = weighted(
        results["base_cost"] + results["total_credits"],
        ctx.spending_weights,
        ctx.t_start,
        ctx.horizon,
    )
    total_afudc = capitalize_yearly_spending(
        mitigation_stream, ctx.t_cod, ctx.afudc_rate, ctx.apply_afudc
    )
    r_social = ctx.social_discount_rate
    r_wacc = financing.wacc_real
    base_cost_pv = pv(base_stream, r_social)
    credits_pv = pv(credits_stream, r_social)
    total_pv = pv(mitigation_stream, r_social)
    total_pv_wacc = pv(mitigation_stream, r_wacc)
    base_cost_nominal = undiscounted(base_stream)
    credits_nominal = undiscounted(credits_stream)
    total_nominal = undiscounted(mitigation_stream)
    afudc_amount = total_afudc - total_nominal if ctx.apply_afudc else 0.0

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
    logger.info(f"  Base Mitigation/Restoration: ${base_cost_nominal:,.2f}")
    logger.info(f"  Wetland Credits: ${results['wetlands_credits']:,.2f}")
    logger.info(f"  Habitat Credits: ${results['habitat_credits']:,.2f}")
    logger.info(f"  Total Credit Costs: ${credits_nominal:,.2f}")
    logger.info(f"  ---")
    logger.info(f"  TOTAL NOMINAL COST: ${total_nominal:,.2f}")
    logger.info("")

    if ctx.apply_afudc:
        logger.info("[REGULATORY PERSPECTIVE - AFUDC Capitalization]")
        logger.info(f"  AFUDC Rate: {ctx.afudc_rate:.2%} ({ctx.afudc_source})")
        logger.info("")
        logger.info(f"  TOTAL CAPITALIZED COST (at COD): ${total_afudc:,.2f}")
        logger.info(f"  Total AFUDC Amount: ${afudc_amount:,.2f}")
        logger.info("")

    logger.info("[SOCIETAL PERSPECTIVE - Present Value]")
    logger.info(f"  Social Discount Rate: {r_social:.2%}")
    logger.info(f"  Real WACC: {r_wacc:.2%}")
    logger.info(f"  Base Year: {financing.base_year}")
    logger.info("")
    logger.info(f"  Base Mitigation/Restoration PV: ${base_cost_pv:,.2f}")
    logger.info(f"  Total Credit Costs PV: ${credits_pv:,.2f}")
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
        "streams": {"env_mitigation": mitigation_stream},
        "total_nominal": total_nominal,
        "total_afudc": total_afudc,
        "total_pv": total_pv,
        "total_pv_wacc": total_pv_wacc,
        "base_cost_nominal": base_cost_nominal,
        "base_cost_pv": base_cost_pv,
        "credits_nominal": credits_nominal,
        "credits_pv": credits_pv,
    }

    # Write to CSV
    csv_manager.add_environmental_mitigation(csv_results)
    csv_manager.write_batch_summary()
