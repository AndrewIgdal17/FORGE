# Date: 2025-10-27
# Description: This calculates the build costs for a transmission line project. Then adjusts it to terrian adjustment
# via the weighted_miles.py script

from __future__ import annotations

import logging

# Standard library imports
import math
from dataclasses import dataclass
from typing import Dict, Tuple

from forge.scripts.utils.smart_output import SmartOutputManager

# Local utility imports
from forge.scripts.utils.smart_loaders import (
    load_project_technical_details,
    load_physical_details,
    load_contingencies,
    load_financing_details,
)
from forge.scripts.utils.financial_utils import capitalize_yearly_spending
from forge.scripts.utils.streams import add, pv, undiscounted, weighted
from forge.scripts.utils.weighted_miles import calculate_weighted_miles
from forge.scripts.utils.inputs import section
from forge.scripts.utils.run_context import get_run_context

logger = logging.getLogger(__name__)


@dataclass
class BuildCosts:
    """Terrain-adjusted build cost results (appendix Eq 2, $C_{adj,*}$).

    Component fields (`conductor_cost`, `structure_cost`, `converter_cost`)
    hold ungated terrain-adjusted values. Binary selectors $\\xi_{structure}$
    and $\\xi_{DC}$ are applied to `total_cost` and to the `_with_contingencies`
    fields (including `total_cost_with_contingencies`).
    """
    total_cost: float
    total_cost_with_contingencies: float
    conductor_cost: float
    structure_cost: float
    converter_cost: float
    conductor_cost_with_contingencies: float
    structure_cost_with_contingencies: float
    converter_cost_with_contingencies: float
    weighted_miles: float
    average_terrain_multiplier: float

def load_costs(
    category: str,
    number_of_converters: int,
    contingencies: Dict[str, float],
    project_type: str,
    overrides: Dict[str, float] | None = None,
) -> BuildCosts:
    """
    Load the costs for the comprehensive transmission cost calculator.

    Args:
        category: Project category identifier
        number_of_converters: Number of converters needed
        contingencies: Dictionary of contingency percentages
        project_type: "greenfield" | "reconductoring" | "rebuild"

    Returns:
        BuildCosts with terrain-adjusted component costs (appendix Eq 2) and
        selector-gated totals / `_with_contingencies` fields.
    """
    try:
        data = section("10_project_category_build_costs")
        if not data:
            raise ValueError("Build costs YAML file is empty or invalid")
        if "project_categories_build_costs" not in data:
            raise KeyError(
                "Missing 'project_categories_build_costs' key in build costs YAML file"
            )
        costs = data["project_categories_build_costs"]
        if category not in costs:
            raise KeyError(f"Category '{category}' not found in build costs YAML")
        required_keys = [
            "variable_conductor_cost_per_mile",
            "fixed_conductor_cost",
            "variable_structure_cost_per_mile",
            "fixed_converter_cost",
        ]
        for key in required_keys:
            if key not in costs[category]:
                raise KeyError(
                    f"Missing '{key}' key for category '{category}' in build costs YAML"
                )
    except KeyError as e:
        raise KeyError(f"Missing required key in build costs YAML: {e}")

    weighted_miles, average_terrain_multiplier = calculate_weighted_miles()

    ov = overrides or {}
    variable_conductor_cost_per_mile = ov.get(
        "variable_conductor_cost_per_mile",
        costs[category]["variable_conductor_cost_per_mile"],
    )
    fixed_conductor_cost = ov.get(
        "fixed_conductor_cost",
        costs[category]["fixed_conductor_cost"],
    )
    variable_structure_cost_per_mile = ov.get(
        "variable_structure_cost_per_mile",
        costs[category]["variable_structure_cost_per_mile"],
    )
    fixed_converter_cost = ov.get(
        "fixed_converter_cost",
        costs[category]["fixed_converter_cost"],
    )

    conductor_cost = (
        variable_conductor_cost_per_mile * weighted_miles
    ) + fixed_conductor_cost
    structure_cost = variable_structure_cost_per_mile * weighted_miles
    converter_cost = fixed_converter_cost * number_of_converters

    # Explicit binary selectors matching appendix (ξ_structure, ξ_DC)
    xi_structure = 0.0 if project_type == "reconductoring" else 1.0
    xi_dc = 1.0 if number_of_converters > 0 else 0.0

    total_cost = (
        conductor_cost
        + xi_structure * structure_cost
        + xi_structure * xi_dc * converter_cost
    )

    conductor_cost_with_contingencies = conductor_cost * (
        1 + contingencies["conductor_contingency"]
    )
    structure_cost_with_contingencies = (
        xi_structure
        * structure_cost
        * (1 + contingencies["structure_contingency"])
    )
    converter_cost_with_contingencies = (
        xi_structure
        * xi_dc
        * converter_cost
        * (1 + contingencies["converter_contingency"])
    )

    total_cost_with_contingencies = (
        conductor_cost_with_contingencies
        + structure_cost_with_contingencies
        + converter_cost_with_contingencies
    )

    soft_cost_multiplier = data["soft_cost_multiplier"]
    conductor_cost_with_contingencies *= (1 + soft_cost_multiplier)
    structure_cost_with_contingencies *= (1 + soft_cost_multiplier)
    converter_cost_with_contingencies *= (1 + soft_cost_multiplier)
    total_cost_with_contingencies = (
        conductor_cost_with_contingencies
        + structure_cost_with_contingencies
        + converter_cost_with_contingencies
    )

    return BuildCosts(
        total_cost=total_cost,
        total_cost_with_contingencies=total_cost_with_contingencies,
        conductor_cost=conductor_cost,
        structure_cost=structure_cost,
        converter_cost=converter_cost,
        conductor_cost_with_contingencies=conductor_cost_with_contingencies,
        structure_cost_with_contingencies=structure_cost_with_contingencies,
        converter_cost_with_contingencies=converter_cost_with_contingencies,
        weighted_miles=weighted_miles,
        average_terrain_multiplier=average_terrain_multiplier,
    )


def main() -> None:
    """
    Main function to calculate and display build costs.
    """
    project_details = load_project_technical_details()

    # Construct category identifier
    ctx = get_run_context()
    if ctx is None:
        raise RuntimeError(
            f"{__name__} requires a RunContext. Run via forge.py or set up "
            "RunContext in your test fixture."
        )
    category = ctx.category_string
    number_of_converters = ctx.number_of_converters

    total_miles = load_physical_details()
    contingencies = load_contingencies()
    financing = load_financing_details()

    # Load user overrides from the build costs YAML (if present)
    build_cost_overrides = None
    try:
        bc_data = section("10_project_category_build_costs") or {}
        raw_ov = bc_data.get("overrides")
        if raw_ov and isinstance(raw_ov, dict):
            build_cost_overrides = {k: v for k, v in raw_ov.items() if v is not None}
            if not build_cost_overrides:
                build_cost_overrides = None
    except Exception:
        pass

    costs = load_costs(
        category, number_of_converters, contingencies,
        project_details.project_type, overrides=build_cost_overrides,
    )

    from forge.scripts.utils.run_context import set_build_costs, add_derived
    set_build_costs(costs)
    add_derived({
        "conductor_cost": costs.conductor_cost,
        "structure_cost": costs.structure_cost,
        "converter_cost": costs.converter_cost,
        "conductor_cost_with_contingencies": costs.conductor_cost_with_contingencies,
        "structure_cost_with_contingencies": costs.structure_cost_with_contingencies,
        "converter_cost_with_contingencies": costs.converter_cost_with_contingencies,
        "total_build_cost_with_contingencies": costs.total_cost_with_contingencies,
    })

    # Per-year real escalation on the MISO weights. The BuildCosts object stays
    # in base-year prices; insurance and O&M read that capital base.
    g_construction = financing.construction_escalation_real
    bases = {
        "conductor": costs.conductor_cost_with_contingencies,
        "structure": costs.structure_cost_with_contingencies,
        "converter": costs.converter_cost_with_contingencies,
    }
    build_streams = {
        f"build_{name}": weighted(
            base,
            ctx.spending_weights,
            ctx.t_start,
            ctx.horizon,
            escalation=g_construction,
        )
        for name, base in bases.items()
    }
    summed = add(
        build_streams["build_conductor"],
        build_streams["build_structure"],
        build_streams["build_converter"],
    )
    capitalized_cost_with_contingencies = capitalize_yearly_spending(
        summed,
        ctx.t_cod,
        ctx.afudc_rate,
        ctx.apply_afudc,
    )
    total_nominal = undiscounted(summed)
    afudc_amount = (
        capitalized_cost_with_contingencies - total_nominal
        if ctx.apply_afudc
        else 0.0
    )
    r_social = ctx.social_discount_rate
    r_wacc = financing.wacc_real
    component_pv = {
        name: pv(build_streams[f"build_{name}"], r_social) for name in bases
    }
    component_pv_wacc = {
        name: pv(build_streams[f"build_{name}"], r_wacc) for name in bases
    }
    component_nominal = {
        name: undiscounted(build_streams[f"build_{name}"]) for name in bases
    }
    total_pv = pv(summed, r_social)
    total_pv_wacc = pv(summed, r_wacc)

    # Format and display results
    logger.info("=" * 80)
    logger.info("TRANSMISSION LINE BUILD COSTS ANALYSIS")
    logger.info("=" * 80)
    logger.info("")
    logger.info("Project Metrics:")
    logger.info(f"  Total Miles:              {total_miles:,.2f} miles")
    logger.info(f"  Weighted Miles:           {costs.weighted_miles:,.2f} miles")
    logger.info(f"  Terrain Multiplier:       {costs.average_terrain_multiplier:.2f}")
    logger.info("")

    logger.info("[NOMINAL VALUES]")
    logger.info("Base Build Costs:")
    logger.info(f"  Conductor Costs:          ${costs.conductor_cost:,.2f}")
    logger.info(f"  Structure Costs:          ${costs.structure_cost:,.2f}")
    logger.info(f"  Converter Costs:          ${costs.converter_cost:,.2f}")
    logger.info("  " + "-" * 52)
    logger.info(f"  Total Base Cost:          ${costs.total_cost:,.2f}")
    logger.info("")
    logger.info("Costs with Contingencies:")
    logger.info(f"  Conductor Costs:          ${costs.conductor_cost_with_contingencies:,.2f}")
    logger.info(f"  Structure Costs:          ${costs.structure_cost_with_contingencies:,.2f}")
    logger.info(f"  Converter Costs:          ${costs.converter_cost_with_contingencies:,.2f}")
    logger.info("  " + "-" * 52)
    logger.info(f"  TOTAL UNDISCOUNTED COST:  ${total_nominal:,.2f}")
    logger.info(
        f"\n  Construction escalation (real): {g_construction:.2%} on each calendar year"
    )
    logger.info("")

    if ctx.apply_afudc:
        logger.info("[REGULATORY PERSPECTIVE - AFUDC Capitalization]")
        logger.info(f"  AFUDC Rate: {ctx.afudc_rate:.2%} ({ctx.afudc_source})")
        logger.info("")
        logger.info(
            f"  TOTAL CAPITALIZED COST (at COD): ${capitalized_cost_with_contingencies:,.2f}"
        )
        logger.info(f"  Total AFUDC Amount: ${afudc_amount:,.2f}")
        logger.info(
            f"    (Build costs incurred during {project_details.construction_years} year construction)"
        )
        logger.info("")

    logger.info("[SOCIETAL PERSPECTIVE - Present Value]")
    logger.info(f"  Social Discount Rate: {r_social:.2%}")
    logger.info(f"  Real WACC: {r_wacc:.2%}")
    logger.info(f"  Base Year: {financing.base_year}")
    logger.info("")
    logger.info("Build costs incurred during construction period:")
    logger.info(
        f"  Construction Period: Year {ctx.t_start} to Year {ctx.t_end}"
    )
    logger.info(f"  Build Cost PV (social): ${total_pv:,.2f}")
    logger.info(f"  Build Cost PV (WACC): ${total_pv_wacc:,.2f}")
    logger.info("=" * 80)

    # ========================================================================
    # CSV OUTPUT - Write results to batch summary and detail CSV
    # ========================================================================

    # Initialize CSV output manager
    csv_manager = SmartOutputManager()

    # Prepare results dictionary
    results = {
        "conductor_base_cost": bases["conductor"],
        "structure_base_cost": bases["structure"],
        "converter_base_cost": bases["converter"],
        "streams": build_streams,
        "total_nominal": total_nominal,
        "total_afudc": capitalized_cost_with_contingencies,
        "total_pv": total_pv,
        "total_pv_wacc": total_pv_wacc,
        "conductor_nominal": component_nominal["conductor"],
        "structure_nominal": component_nominal["structure"],
        "converter_nominal": component_nominal["converter"],
        "conductor_pv": component_pv["conductor"],
        "structure_pv": component_pv["structure"],
        "converter_pv": component_pv["converter"],
        "conductor_pv_wacc": component_pv_wacc["conductor"],
        "structure_pv_wacc": component_pv_wacc["structure"],
        "converter_pv_wacc": component_pv_wacc["converter"],
        "conductor_afudc": 0,  # Component-level AFUDC not calculated separately
        "structure_afudc": 0,
        "converter_afudc": 0,
    }

    # Write to CSV
    csv_manager.add_build_costs(results)
    csv_manager.write_batch_summary()
