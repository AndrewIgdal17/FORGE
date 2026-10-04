# Date: 2025-10-27
# Description: This calculates the build costs for a transmission line project. Then adjusts it to terrian adjustment
# via the weighted_miles.py script

from __future__ import annotations

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
    get_financing_data_raw,
)
from forge.scripts.utils.financial_utils import (
    calculate_present_value,
    calculate_afudc_rate,
    calculate_afudc_capitalized_cost,
    validate_discount_rate,
    calculate_construction_start_year,
)
from forge.scripts.utils.weighted_miles import calculate_weighted_miles
from forge.scripts.utils.inputs import section
from forge.scripts.utils.run_context import get_run_context

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


def load_and_escalate_costs(
    category: str,
    number_of_converters: int,
    contingencies: dict,
    project_type: str,
    project_details,
) -> BuildCosts:
    """Load build costs with overrides and delay escalation — full pipeline equivalent.

    Use this in downstream modules' standalone fallback paths to get the same
    BuildCosts object that main() would produce. This replaces incomplete
    re-derivation fallbacks that were missing overrides/escalation/contingencies.
    """
    overrides = None
    try:
        raw = section("10_project_category_build_costs") or {}
        raw_ov = raw.get("overrides")
        if raw_ov and isinstance(raw_ov, dict):
            overrides = {k: v for k, v in raw_ov.items() if v is not None}
            if not overrides:
                overrides = None
    except KeyError:
        pass

    costs = load_costs(
        category, number_of_converters, contingencies, project_type, overrides=overrides
    )

    delay_years = getattr(project_details, "delay_years", 0) or 0
    if delay_years > 0:
        from forge.scripts.utils.smart_loaders import get_financing_data_raw as _get_financing_data_raw
        fin_raw = _get_financing_data_raw()
        escalation_rate = (
            fin_raw["financial"]["construction_cost_escalation_rate"] or 0
        )
        if escalation_rate > 0:
            factor = (1 + escalation_rate) ** delay_years
            costs = BuildCosts(
                total_cost=costs.total_cost,
                total_cost_with_contingencies=costs.total_cost_with_contingencies * factor,
                conductor_cost=costs.conductor_cost,
                structure_cost=costs.structure_cost,
                converter_cost=costs.converter_cost,
                conductor_cost_with_contingencies=costs.conductor_cost_with_contingencies * factor,
                structure_cost_with_contingencies=costs.structure_cost_with_contingencies * factor,
                converter_cost_with_contingencies=costs.converter_cost_with_contingencies * factor,
                weighted_miles=costs.weighted_miles,
                average_terrain_multiplier=costs.average_terrain_multiplier,
            )
    return costs


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

    # Escalate build cost during delay period (#27)
    financing_yaml_raw = get_financing_data_raw()
    construction_cost_escalation_rate = financing_yaml_raw["financial"][
        "construction_cost_escalation_rate"
    ]
    if project_details.delay_years > 0 and construction_cost_escalation_rate > 0:
        escalation_factor = (1 + construction_cost_escalation_rate) ** project_details.delay_years
        costs = BuildCosts(
            total_cost=costs.total_cost,
            total_cost_with_contingencies=costs.total_cost_with_contingencies * escalation_factor,
            conductor_cost=costs.conductor_cost,
            structure_cost=costs.structure_cost,
            converter_cost=costs.converter_cost,
            conductor_cost_with_contingencies=costs.conductor_cost_with_contingencies * escalation_factor,
            structure_cost_with_contingencies=costs.structure_cost_with_contingencies * escalation_factor,
            converter_cost_with_contingencies=costs.converter_cost_with_contingencies * escalation_factor,
            weighted_miles=costs.weighted_miles,
            average_terrain_multiplier=costs.average_terrain_multiplier,
        )
        # Update context with escalated values
        set_build_costs(costs)
        add_derived({
            "conductor_cost": costs.conductor_cost,
            "structure_cost": costs.structure_cost,
            "converter_cost": costs.converter_cost,
            "conductor_cost_with_contingencies": costs.conductor_cost_with_contingencies,
            "structure_cost_with_contingencies": costs.structure_cost_with_contingencies,
            "converter_cost_with_contingencies": costs.converter_cost_with_contingencies,
            "total_build_cost_with_contingencies": costs.total_cost_with_contingencies,
            "construction_cost_escalation_factor": escalation_factor,
        })

    # Load AFUDC configuration and timing patterns
    from forge.scripts.utils.financial_utils import load_afudc_setup
    afudc_setup = load_afudc_setup()

    # ===== REGULATORY PERSPECTIVE: AFUDC Capitalization =====
    if afudc_setup.apply_afudc:
        # Build costs are AFUDC-eligible and occur during construction
        (
            capitalized_cost_with_contingencies,
            afudc_amount,
        ) = calculate_afudc_capitalized_cost(
            costs.total_cost_with_contingencies,
            afudc_setup.timing_patterns["build_costs"],
            project_details.delay_years,
            project_details.construction_years,
            afudc_setup.afudc_rate,
            afudc_setup.delay_active,
            spending_profiles=afudc_setup.spending_profiles,
        )

    # ===== SOCIETAL PERSPECTIVE: Present Value Discounting =====
    # Build costs: spread evenly over construction period
    # Annual cost during construction years
    construction_start_year = calculate_construction_start_year(project_details.delay_years)
    if project_details.construction_years > 0:
        annual_build_cost = costs.total_cost_with_contingencies / project_details.construction_years
        build_cost_pv = calculate_present_value(
            annual_build_cost, financing.wacc_real, project_details.construction_years, construction_start_year
        )
    else:
        # Validate wacc_real before direct use to prevent division by zero
        validate_discount_rate(financing.wacc_real, "wacc_real")
        # If construction_years is 0, treat as one-time cost at construction_start_year
        build_cost_pv = (
            costs.total_cost_with_contingencies / (1 + financing.wacc_real) ** construction_start_year
        )

    # Format and display results
    print("=" * 80)
    print("TRANSMISSION LINE BUILD COSTS ANALYSIS")
    print("=" * 80)
    print()
    print("Project Metrics:")
    print(f"  Total Miles:              {total_miles:,.2f} miles")
    print(f"  Weighted Miles:           {costs.weighted_miles:,.2f} miles")
    print(f"  Terrain Multiplier:       {costs.average_terrain_multiplier:.2f}")
    print()

    print("[NOMINAL VALUES]")
    print("Base Build Costs:")
    print(f"  Conductor Costs:          ${costs.conductor_cost:,.2f}")
    print(f"  Structure Costs:          ${costs.structure_cost:,.2f}")
    print(f"  Converter Costs:          ${costs.converter_cost:,.2f}")
    print("  " + "-" * 52)
    print(f"  Total Base Cost:          ${costs.total_cost:,.2f}")
    print()
    print("Costs with Contingencies:")
    print(f"  Conductor Costs:          ${costs.conductor_cost_with_contingencies:,.2f}")
    print(f"  Structure Costs:          ${costs.structure_cost_with_contingencies:,.2f}")
    print(f"  Converter Costs:          ${costs.converter_cost_with_contingencies:,.2f}")
    print("  " + "-" * 52)
    print(f"  TOTAL NOMINAL COST:       ${costs.total_cost_with_contingencies:,.2f}")
    if project_details.delay_years > 0 and construction_cost_escalation_rate > 0:
        print(f"\n  Delay Escalation: {construction_cost_escalation_rate:.1%}/yr × {project_details.delay_years} yrs = {escalation_factor:.3f}× ({(escalation_factor-1)*100:.1f}% increase)")
    print()

    if afudc_setup.apply_afudc:
        print("[REGULATORY PERSPECTIVE - AFUDC Capitalization]")
        print(f"  AFUDC Rate: {afudc_setup.afudc_rate:.2%} ({afudc_setup.afudc_source})")
        print(f"  Delay Period Active Work: {'Yes' if afudc_setup.delay_active else 'No'}")
        print()
        print(
            f"  TOTAL CAPITALIZED COST (at COD): ${capitalized_cost_with_contingencies:,.2f}"
        )
        print(f"  Total AFUDC Amount: ${afudc_amount:,.2f}")
        print(
            f"    (Build costs incurred during {project_details.construction_years} year construction)"
        )
        print()

    print("[SOCIETAL PERSPECTIVE - Present Value]")
    print(f"  Discount Rate: {financing.wacc_real:.2%} (real WACC)")
    print(f"  Base Year: {financing.base_year}")
    print()
    print("Build costs incurred during construction period:")
    if project_details.construction_years > 0:
        print(
            f"  Annual Cost (over {project_details.construction_years} year(s) construction): ${annual_build_cost:,.2f}"
        )
        print(
            f"  Construction Period: Year {construction_start_year:.1f} to Year {construction_start_year + project_details.construction_years - 1:.1f}"
        )
    else:
        print(f"  One-time cost at Year {construction_start_year:.1f}")
    print(f"  Build Cost PV: ${build_cost_pv:,.2f}")
    print("=" * 80)

    # ========================================================================
    # CSV OUTPUT - Write results to batch summary and detail CSV
    # ========================================================================

    # Initialize CSV output manager
    csv_manager = SmartOutputManager()

    # Prepare results dictionary
    results = {
        "total_nominal": costs.total_cost_with_contingencies,
        "total_afudc": capitalized_cost_with_contingencies if afudc_setup.apply_afudc else 0,
        "total_pv": build_cost_pv,
        "conductor_nominal": costs.conductor_cost_with_contingencies,
        "structure_nominal": costs.structure_cost_with_contingencies,
        "converter_nominal": costs.converter_cost_with_contingencies,
        "conductor_afudc": 0,  # Component-level AFUDC not calculated separately
        "structure_afudc": 0,
        "converter_afudc": 0,
    }

    # Write to CSV
    csv_manager.add_build_costs(results)
    csv_manager.write_batch_summary()

if __name__ == "__main__":
    main()
