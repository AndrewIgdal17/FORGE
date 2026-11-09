# Date: 2025-10-21
# Description: Framework for Open Reproducible Grid Economics (FORGE) - Main Script
#              Orchestrates all individual cost calculation modules

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib
import json
import logging
import os
import sys
import time
from datetime import datetime
from typing import Any

from forge.contract import calculator_info, canonical_dumps, is_whole_number
from forge.errors import InvalidInputs, CalculationError
from forge.scripts.io.csv_output_manager import BATCH_SUMMARY_FIELDS
from forge.scripts.utils.run_context import (
    RunState,
    get_run_context,
    reset_run_state,
    set_run_state,
)

logger = logging.getLogger(__name__)

_PRELOAD_MODULES = [
    "forge.scripts.utils.weighted_miles",
    "forge.scripts.calc.build_costs",
    "forge.scripts.calc.row_costs",
    "forge.scripts.calc.environmental_mitigation",
    "forge.scripts.calc.revenue",
    "forge.scripts.calc.insurance_costs",
    "forge.scripts.calc.delay_costs",
    "forge.scripts.calc.wildfire_costs",
    "forge.scripts.calc.outage_costs",
    "forge.scripts.calc.congestion_reduction",
    "forge.scripts.calc.energy_losses",
    "forge.scripts.calc.oandm",
    "forge.scripts.calc.emissions",
    "forge.scripts.calc.avoided_emissions",
    "forge.scripts.calc.line_loss_costs",
    "forge.scripts.io.taxonomy_adapters",
    "forge.scripts.calc.bcr_calculator",
]
for _mod_name in _PRELOAD_MODULES:
    importlib.import_module(_mod_name)

def build_csv_equivalent(
    json_results: dict,
    bcr_results: dict | None,
    bcr_data: dict | None,
) -> dict:
    """Build a flat CSV-equivalent dict using current CSV schema."""
    technical = json_results.get("technical_parameters", {}) or {}
    base_fields = {
        "project_name": technical.get("project_name", ""),
        "scenario_id": json_results.get("scenario_id", ""),
        "timestamp": json_results.get("timestamp", ""),
        "capacity_mw": technical.get("capacity_mw", 0) or 0,
        "line_length_miles": technical.get("line_length_miles", 0) or 0,
        "construction_type": technical.get("construction_type", ""),
        "ac_dc": technical.get("ac_dc", ""),
        "social_discount_rate": technical.get("social_discount_rate", 0) or 0,
    }

    merged = {**base_fields}
    if bcr_data is not None:
        merged.update(
            bcr_data.model_dump() if hasattr(bcr_data, "model_dump") else bcr_data
        )
    if bcr_results:
        merged.update(bcr_results)

    return {field: merged.get(field, 0) for field in BATCH_SUMMARY_FIELDS}


def build_summary_from_csv_equivalent(csv_equivalent: dict) -> dict:
    """Create a minimal summary aligned with CSV/BCR totals and appendix categories."""
    return {
        # Pipeline groupings (cost/benefit category subtotals for the summary dict)
        "total_capital_pv": csv_equivalent.get("capital_costs_pv", 0),
        "total_operational_pv": csv_equivalent.get("operational_costs_pv", 0),
        "total_energy_emissions_pv": csv_equivalent.get("energy_emissions_costs_pv", 0),
        "total_risk_pv": csv_equivalent.get("risk_costs_pv", 0),
        "total_delay_pv": csv_equivalent.get("delay_costs_pv", 0),
        "total_costs_pv": csv_equivalent.get("total_costs_pv", 0),
        "total_benefits_pv": csv_equivalent.get("total_benefits_pv", 0),
        # Appendix-aligned cost categories (C_hard + C_soft + C_risk + C_emissions)
        "reporting_category_hard_pv": csv_equivalent.get("hard_costs_pv", 0),
        "reporting_category_soft_pv": csv_equivalent.get("soft_costs_pv", 0),
        "reporting_category_risk_pv": csv_equivalent.get("risk_costs_pv", 0),
        "reporting_category_emissions_pv": csv_equivalent.get("emissions_costs_pv", 0),
        "displacement_avoided_benefit_pv": csv_equivalent.get("displacement_avoided_benefit_pv", 0),
        # Appendix-aligned benefit categories (B_remedial + B_enabling)
        "benefits_remedial_pv": csv_equivalent.get("benefits_remedial_pv", 0),
        "benefits_enabling_pv": csv_equivalent.get("benefits_enabling_pv", 0),
    }


_TRAJECTORY_ARRAY_KEYS = {
    ("costs", "emissions"): ["emissions_comp_annual_values"],
    ("benefits", "avoided_emissions"): ["avoided_emissions_annual_values"],
}


def _hoist_trajectory_arrays(results: dict) -> None:
    """Copy year-by-year annual-value arrays up to the top level of `results`.

    emissions.py and avoided_emissions.py nest their results under
    costs["emissions"] / benefits["avoided_emissions"]. The BCR trajectory
    module consumes these arrays directly off the top-level results dict.
    """
    for (category, module_key), array_keys in _TRAJECTORY_ARRAY_KEYS.items():
        module_results = results.get(category, {}).get(module_key, {})
        for array_key in array_keys:
            if array_key in module_results:
                results[array_key] = module_results[array_key]


def write_final_json_output(
    results: dict,
    scenario_id: str,
    output_dir: str = "outputs",
) -> str:
    """Write a results dict to a JSON file."""
    output_file = os.path.join(output_dir, f"forge_results_{scenario_id}.json")
    os.makedirs(output_dir, exist_ok=True)
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
    return output_file


def _build_scripts_list(
    *,
    no_emissions: bool = False,
    no_linelosses: bool = False,
    no_insurance: bool = False,
    no_delay_costs: bool = False,
    no_wildfire: bool = False,
    no_outages: bool = False,
    no_oandm: bool = False,
    capital_only: bool = False,
) -> list[str]:
    """Build the ordered list of calculator module dotted paths to run."""
    if capital_only:
        return [
            "forge.scripts.utils.weighted_miles",
            "forge.scripts.calc.build_costs",
            "forge.scripts.calc.row_costs",
            "forge.scripts.calc.environmental_mitigation",
        ]
    scripts = [
        "forge.scripts.utils.weighted_miles",
        "forge.scripts.calc.build_costs",
        "forge.scripts.calc.row_costs",
        "forge.scripts.calc.environmental_mitigation",
        "forge.scripts.calc.revenue",
    ]
    if not no_insurance:
        scripts.append("forge.scripts.calc.insurance_costs")
    if not no_delay_costs:
        scripts.append("forge.scripts.calc.delay_costs")
    if not no_wildfire:
        scripts.append("forge.scripts.calc.wildfire_costs")
    if not no_outages:
        scripts.append("forge.scripts.calc.outage_costs")
    scripts.append("forge.scripts.calc.congestion_reduction")
    scripts.append("forge.scripts.calc.energy_losses")
    if not no_oandm:
        scripts.append("forge.scripts.calc.oandm")
    if not no_emissions:
        scripts.append("forge.scripts.calc.emissions")
        scripts.append("forge.scripts.calc.avoided_emissions")
    if not no_linelosses:
        scripts.append("forge.scripts.calc.line_loss_costs")
    return scripts


def _baseline_delay_years(inputs: dict, project_details: Any) -> Any:
    """Read the on-time delay, defaulting to 0 when the input is absent."""
    section = inputs.get("01_project_technical_details", {})
    timeline = section.get("timeline", {}) if isinstance(section, dict) else {}
    if isinstance(timeline, dict) and "baseline_delay_years" in timeline:
        return timeline["baseline_delay_years"]
    if hasattr(project_details, "baseline_delay_years"):
        return project_details.baseline_delay_years
    return 0


def _require_whole_year(name: str, value: Any) -> int:
    if not is_whole_number(value):
        raise InvalidInputs(f"{name} {value} is not a whole number")
    return int(value)


def _bootstrap_run_context() -> "RunContext":
    """Load input sections once and populate the shared RunContext.

    Called by _run_once() after RunState is set. Returns the populated
    RunContext; also calls set_run_context() and add_derived() as side effects.
    """
    from forge.scripts.utils.run_context import RunContext, add_derived, set_run_context
    from forge.scripts.utils.smart_loaders import get_physical_data_raw
    from forge.scripts.io.yaml_loaders import (
        load_project_technical_details, load_financing_details,
        load_contingencies, load_row_widths,
    )
    from forge.scripts.utils.calculation_utils import build_category_string
    from forge.scripts.utils.weighted_miles import calculate_weighted_miles as _calc_wm
    from forge.scripts.utils.financial_utils import (
        calculate_afudc_rate,
        get_construction_spending_weights,
    )
    from forge.scripts.utils.smart_loaders import get_financing_data_raw

    project_details = load_project_technical_details()
    capacity_mw = getattr(project_details, "capacity_mw", None)
    if capacity_mw is None or capacity_mw == 0:
        raise InvalidInputs(
            f"capacity_mw is required and must be > 0 (got {capacity_mw}). "
            "Set a valid line capacity in MW."
        )
    from forge.contract import missing_protected_area_acres
    from forge.scripts.utils.run_context import get_run_state

    inputs = get_run_state().inputs
    missing = missing_protected_area_acres(inputs)
    if missing:
        raise InvalidInputs(
            "protected_area_acres are required. Missing: " + ", ".join(missing)
        )
    delay_years = _require_whole_year("delay_years", project_details.delay_years)
    if not is_whole_number(project_details.construction_years):
        raise InvalidInputs(
            f"construction_years {project_details.construction_years} is not a whole number"
        )
    if project_details.construction_years < 1:
        raise InvalidInputs(
            f"construction_years must be >= 1 (got {project_details.construction_years})."
        )
    construction_years = int(project_details.construction_years)
    project_lifetime = _require_whole_year(
        "project_lifetime", getattr(project_details, "project_lifetime", None)
    )
    baseline_delay = _require_whole_year(
        "baseline_delay_years", _baseline_delay_years(inputs, project_details)
    )
    if baseline_delay > delay_years:
        raise InvalidInputs(
            f"baseline_delay_years ({baseline_delay}) must not exceed delay_years ({delay_years})."
        )
    if project_details.construction_type == "Subsea":
        raise InvalidInputs("construction_type 'Subsea' is not allowed.")
    t_start = delay_years + 1
    t_end = delay_years + construction_years
    t_cod = t_end + 1
    horizon = t_cod + project_lifetime - 1
    spending_weights = get_construction_spending_weights(
        construction_years,
        inputs["19_cost_timing_patterns"]["construction_spending_profiles"],
    )
    financing = load_financing_details()
    contingencies = load_contingencies()
    physical_raw = get_physical_data_raw()
    terrain_miles = physical_raw["terrain"]["terrain_miles"]
    terrain_multipliers = physical_raw["terrain"]["terrain_multipliers"]
    total_miles = sum(v for v in terrain_miles.values() if v is not None)
    category_string = build_category_string(project_details=project_details)
    row_width_feet = load_row_widths(category_string)
    weighted_miles, avg_terrain_mult = _calc_wm()

    fin_raw = get_financing_data_raw()
    afudc_rate, afudc_source = calculate_afudc_rate(fin_raw)
    afudc_cfg = fin_raw.get("financial", {}).get("afudc", {})
    apply_afudc = True
    if isinstance(afudc_cfg, dict) and "apply_afudc" in afudc_cfg:
        apply_afudc = bool(afudc_cfg["apply_afudc"])
    social_discount_rate = getattr(financing, "social_discount_rate", None)
    if social_discount_rate is None:
        social_discount_rate = fin_raw["financial"].get("social_discount_rate", 0)
    construction_escalation_real = getattr(
        financing, "construction_escalation_real", None
    )

    ctx = RunContext(
        project_details=project_details,
        terrain_miles=terrain_miles,
        terrain_multipliers=terrain_multipliers,
        total_miles=total_miles,
        financing=financing,
        contingencies=contingencies,
        category_string=category_string,
        row_width_feet=row_width_feet,
        weighted_miles=weighted_miles,
        average_terrain_multiplier=avg_terrain_mult,
        number_of_converters=project_details.number_of_converters,
        social_discount_rate=social_discount_rate,
        afudc_rate=afudc_rate,
        afudc_source=afudc_source,
        cod_year=t_cod,
        construction_start_year=t_start,
        horizon=horizon,
        t_start=t_start,
        t_end=t_end,
        t_cod=t_cod,
        spending_weights=spending_weights,
        apply_afudc=apply_afudc,
    )
    set_run_context(ctx)

    add_derived({
        "category_string": category_string,
        "row_width_feet": row_width_feet,
        "weighted_miles": weighted_miles,
        "average_terrain_multiplier": avg_terrain_mult,
        "total_miles": total_miles,
        "terrain_miles": terrain_miles,
        "terrain_multipliers": terrain_multipliers,
        "wacc_real": financing.wacc_real,
        "wacc_nominal": financing.wacc_nominal,
        "inflation_rate": financing.inflation_rate,
        "social_discount_rate": social_discount_rate,
        "construction_escalation_real": construction_escalation_real,
        "construction_spending_weights": spending_weights,
        "t_cod": t_cod,
        "horizon": horizon,
        "afudc_rate": afudc_rate,
        "afudc_source": afudc_source,
        "cod_year": t_cod,
        "construction_start_year": t_start,
        "contingencies": contingencies,
    })

    return ctx


def _run_once(
    combined_data: dict[str, Any],
    scenario_id: str = "",
    *,
    no_emissions: bool = False,
    no_linelosses: bool = False,
    no_insurance: bool = False,
    no_delay_costs: bool = False,
    no_wildfire: bool = False,
    no_outages: bool = False,
    no_oandm: bool = False,
    capital_only: bool = False,
    trajectory: bool = True,
) -> dict[str, Any]:
    """Run the pipeline once. ``trajectory=False`` skips the year-by-year rows."""
    from forge.scripts.io.json_output_manager import JSONOutputManager

    inputs = copy.deepcopy(combined_data)
    state = RunState(
        inputs=inputs,
        scenario_id=scenario_id or datetime.now().strftime("%Y%m%d_%H%M%S_%f"),
    )
    token = set_run_state(state)
    try:
        aggregator = JSONOutputManager(scenario_id=state.scenario_id)
        state.aggregator = aggregator

        _bootstrap_run_context()

        scripts = _build_scripts_list(
            no_emissions=no_emissions,
            no_linelosses=no_linelosses,
            no_insurance=no_insurance,
            no_delay_costs=no_delay_costs,
            no_wildfire=no_wildfire,
            no_outages=no_outages,
            no_oandm=no_oandm,
            capital_only=capital_only,
        )

        module_timings: dict[str, float] = {}
        for script in scripts:
            started = time.perf_counter()
            try:
                mod = importlib.import_module(script)
                mod.main()
            except InvalidInputs:
                raise
            except Exception as exc:
                raise CalculationError(script, exc) from exc
            module_timings[script] = time.perf_counter() - started

        json_results = aggregator.get_json_results()
        bcr_results = None
        csv_equivalent = None
        summary_override = None
        taxonomy_results_json = None
        try:
            from forge.scripts.io.taxonomy_adapters import (
                adapt_all_results,
                taxonomy_results_to_json_list,
            )
            from forge.scripts.calc.bcr_calculator import compute_all_bcrs

            taxonomy_results = adapt_all_results(json_results)
            taxonomy_results_json = taxonomy_results_to_json_list(taxonomy_results)
            bcr_results = compute_all_bcrs(taxonomy_results)
            csv_equivalent = build_csv_equivalent(json_results, bcr_results, bcr_results)
            summary_override = build_summary_from_csv_equivalent(csv_equivalent)
        except InvalidInputs:
            raise
        except Exception as exc:
            raise CalculationError("taxonomy+bcr", exc) from exc

        if bcr_results:
            aggregator.add_bcr_metrics(bcr_results)
        aggregator.calculate_summary()
        results = aggregator.get_json_results()
        _hoist_trajectory_arrays(results)
        if csv_equivalent is not None:
            results["csv_equivalent"] = csv_equivalent
        if summary_override is not None:
            results["summary"] = summary_override
        if taxonomy_results_json is not None:
            results["taxonomy_results"] = taxonomy_results_json

        if trajectory and results.get("bcr"):
            try:
                from forge.scripts.calc.bcr_trajectory import compute_trajectory
                results["trajectory"] = compute_trajectory(results, inputs)
            except InvalidInputs:
                raise
            except Exception as exc:
                raise CalculationError("bcr_trajectory", exc) from exc

        ctx = get_run_context()
        if ctx is not None and ctx.derived_parameters:
            results["derived_parameters"] = ctx.derived_parameters

        provenance = calculator_info()
        provenance["inputs_id"] = "sha256:" + hashlib.sha256(
            canonical_dumps(combined_data).encode("utf-8")
        ).hexdigest()
        results["provenance"] = provenance
        logger.debug("Module timings: %s", module_timings)

        return results
    finally:
        reset_run_state(token)


def _societal_value_pv(results: dict[str, Any], taxonomy_id: str) -> Any:
    """Societal present value, or None when that module did not run."""
    for entry in results.get("taxonomy_results") or []:
        if entry.get("taxonomy_id") == taxonomy_id:
            return entry.get("value_pv")
    return None


def _forgone_delay(cong: Any, avoid: Any) -> Any:
    """Sum of the two benefit differences. None when either difference is None."""
    if cong is None or avoid is None:
        return None
    return cong + avoid


def _on_time_metrics(results: dict[str, Any]) -> dict[str, Any]:
    bcr = results["bcr"]
    return {
        "bcr_societal": bcr["bcr_societal"],
        "net_benefit_pv": bcr["net_benefit_pv"],
        "total_costs_pv": bcr["total_costs_pv"],
        "total_benefits_pv": bcr["total_benefits_pv"],
    }


def _delay_block(
    *,
    baseline: int,
    delay_years: int,
    on_time_run: bool,
    cong: Any,
    avoid: Any,
    delta_nb: float,
    on_time: dict[str, Any],
) -> dict[str, Any]:
    return {
        "baseline_delay_years": baseline,
        "delay_years": delay_years,
        "on_time_run": on_time_run,
        "delay_cost_cong": cong,
        "delay_cost_avoid": avoid,
        "delay_cost_forgone": _forgone_delay(cong, avoid),
        "delta_nb_delay": delta_nb,
        "on_time": on_time,
    }


def _entered_delay_years(inputs: dict[str, Any]) -> tuple[int, int]:
    section = inputs.get("01_project_technical_details", {})
    timeline = section.get("timeline", {}) if isinstance(section, dict) else {}
    if not isinstance(timeline, dict):
        timeline = {}
    delay_years = _require_whole_year("delay_years", timeline["delay_years"])
    baseline = _require_whole_year(
        "baseline_delay_years", _baseline_delay_years(inputs, None)
    )
    return delay_years, baseline


def _delay_comparison(
    inputs: dict[str, Any],
    results: dict[str, Any],
    scenario_id: str,
    flags: dict[str, Any],
) -> dict[str, Any] | None:
    """Compare the run as entered with the same project at the baseline delay.

    Capital-only runs have no benefits, so the block is None. A run already at
    the baseline delay is not run again. A module that did not run contributes
    None, including when the two delays are equal.
    """
    if flags["capital_only"]:
        return None
    delay_years, baseline = _entered_delay_years(inputs)
    if delay_years == baseline:
        cong = 0.0 if _societal_value_pv(results, "congestion_benefit") is not None else None
        avoid = 0.0 if _societal_value_pv(results, "avoided_emissions_benefit") is not None else None
        return _delay_block(
            baseline=baseline,
            delay_years=delay_years,
            on_time_run=False,
            cong=cong,
            avoid=avoid,
            delta_nb=0.0,
            on_time=_on_time_metrics(results),
        )
    ot_inputs = copy.deepcopy(inputs)
    ot_inputs["01_project_technical_details"]["timeline"]["delay_years"] = baseline
    # Look up the module global at call time so a test patch of _run_once counts.
    ot = _run_once(ot_inputs, scenario_id, trajectory=False, **flags)
    entered_cong = _societal_value_pv(results, "congestion_benefit")
    on_time_cong = _societal_value_pv(ot, "congestion_benefit")
    entered_avoid = _societal_value_pv(results, "avoided_emissions_benefit")
    on_time_avoid = _societal_value_pv(ot, "avoided_emissions_benefit")
    cong = None if entered_cong is None or on_time_cong is None else on_time_cong - entered_cong
    avoid = None if entered_avoid is None or on_time_avoid is None else on_time_avoid - entered_avoid
    delta_nb = ot["bcr"]["net_benefit_pv"] - results["bcr"]["net_benefit_pv"]
    return _delay_block(
        baseline=baseline,
        delay_years=delay_years,
        on_time_run=True,
        cong=cong,
        avoid=avoid,
        delta_nb=delta_nb,
        on_time=_on_time_metrics(ot),
    )


def run_calculation(
    combined_data: dict[str, Any],
    scenario_id: str = "",
    *,
    no_emissions: bool = False,
    no_linelosses: bool = False,
    no_insurance: bool = False,
    no_delay_costs: bool = False,
    no_wildfire: bool = False,
    no_outages: bool = False,
    no_oandm: bool = False,
    capital_only: bool = False,
) -> dict[str, Any]:
    """Run the full FORGE calculation pipeline.

    Pure function: reads no file, writes no file, changes no process-wide state.
    Concurrent calls on different threads return the same results as sequential calls.
    """
    flags = {
        "no_emissions": no_emissions,
        "no_linelosses": no_linelosses,
        "no_insurance": no_insurance,
        "no_delay_costs": no_delay_costs,
        "no_wildfire": no_wildfire,
        "no_outages": no_outages,
        "no_oandm": no_oandm,
        "capital_only": capital_only,
    }
    results = _run_once(combined_data, scenario_id, trajectory=True, **flags)
    results["delay_comparison"] = _delay_comparison(
        combined_data, results, scenario_id, flags
    )
    return results


def main() -> None:
    """CLI entry point: load inputs and run the calculator."""
    parser = argparse.ArgumentParser(
        description="Framework for Open Reproducible Grid Economics (FORGE)"
    )
    parser.add_argument("--simple", action="store_true", help="Suppress intermediate outputs")
    parser.add_argument("--verbose", action="store_true", help="Show DEBUG-level diagnostics")
    parser.add_argument("--no_emissions", action="store_true")
    parser.add_argument("--no_linelosses", action="store_true")
    parser.add_argument("--capital_only", action="store_true")
    parser.add_argument("--no_oandm", action="store_true")
    parser.add_argument("--no_insurance", action="store_true")
    parser.add_argument("--no_delay_costs", action="store_true")
    parser.add_argument("--no_wildfire", action="store_true")
    parser.add_argument("--no_outages", action="store_true")
    args = parser.parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(message)s",
        stream=sys.stdout,
    )

    from forge.data import get_defaults_template

    if not args.simple:
        logger.info("=" * 80)
        logger.info("FRAMEWORK FOR OPEN REPRODUCIBLE GRID ECONOMICS (FORGE)")
        logger.info("=" * 80)

    combined_data = get_defaults_template()
    scenario_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")

    if not args.simple:
        logger.info(f"\n📋 Scenario ID: {scenario_id}\n")

    try:
        results = run_calculation(
            combined_data,
            scenario_id=scenario_id,
            no_emissions=args.no_emissions,
            no_linelosses=args.no_linelosses,
            no_insurance=args.no_insurance,
            no_delay_costs=args.no_delay_costs,
            no_wildfire=args.no_wildfire,
            no_outages=args.no_outages,
            no_oandm=args.no_oandm,
            capital_only=args.capital_only,
        )
    except InvalidInputs as exc:
        logger.error(f"❌ Invalid inputs: {exc}")
        sys.exit(1)
    except CalculationError as exc:
        logger.error(f"❌ {exc}")
        sys.exit(1)

    if results.get("bcr") and not args.simple:
        from forge.scripts.calc.bcr_calculator import print_bcr_summary
        print_bcr_summary(results["bcr"])

    output_file = write_final_json_output(results, scenario_id)

    if not args.simple:
        logger.info(f"✅ JSON results written to {output_file}")


if __name__ == "__main__":
    main()
