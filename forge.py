# Date: 2025-10-21
# Description: Framework for Open Reproducible Grid Economics (FORGE) - Main Script
#              Orchestrates all individual cost calculation modules

from __future__ import annotations

import importlib
import shutil
import subprocess
import sys
import os
import argparse
import glob
import json
import tempfile
import threading
import time as _time
import traceback
from pathlib import Path
from typing import Any
from datetime import datetime

import yaml

# Add scripts directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "scripts"))
from csv_output_manager import BATCH_SUMMARY_FIELDS
from run_context import (
    set_output_manager, get_output_manager, clear_output_manager,
    RunContext, set_run_context, get_run_context, clear_run_context,
    add_derived,
)

_PRELOAD_MODULES = [
    "weighted_miles", "build_costs", "row_costs", "environmental_mitigation",
    "revenue", "insurance_costs", "delay_costs", "wildfire_costs",
    "outage_costs", "congestion_curtailment_reduction", "energy_losses",
    "oandm", "emissions", "facilitated_emissions", "displacement_delay_cost",
    "line_loss_costs", "taxonomy_adapters", "bcr_calculator",
]
for _mod_name in _PRELOAD_MODULES:
    importlib.import_module(_mod_name)

_FORGE_ROOT = Path(__file__).resolve().parent
_calculation_lock = threading.Lock()


def _set_yamls_dir(new_path: Path) -> None:
    """Patch YAMLS_DIR across path_config and all modules that cached it at import time."""
    os.environ["FORGE_YAMLS_DIR"] = str(new_path)
    import path_config
    path_config.YAMLS_DIR = new_path
    for mod in sys.modules.values():
        if mod and hasattr(mod, "YAMLS_DIR") and mod is not path_config:
            mod.YAMLS_DIR = new_path


def run_script(script_name: str, quiet: bool = False) -> bool:
    """
    Run a Python script and capture its output.

    Args:
        script_name (str): Name of the script to run
        quiet (bool): If True, suppress output messages

    Returns:
        bool: True if successful, False if error
    """
    try:
        # Pass environment variables explicitly to ensure subprocess scripts can access them
        env = os.environ.copy()
        result = subprocess.run(
            [sys.executable, script_name],
            capture_output=True,
            text=True,
            cwd="scripts",
            env=env,
        )
        if result.returncode == 0:
            if not quiet:
                print(f"✅ {script_name} completed successfully")
                print(result.stdout)
            return True
        else:
            if not quiet:
                print(f"❌ {script_name} failed with error:")
                print(result.stderr)
            return False
    except Exception as e:
        if not quiet:
            print(f"❌ Error running {script_name}: {e}")
        return False


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
        # Facilitated emissions + displacement (reporting)
        "fac_emissions_project_pv": csv_equivalent.get("fac_emissions_project_pv", 0),
        "displacement_avoided_cost_pv": csv_equivalent.get("displacement_avoided_cost_pv", 0),
        # Appendix-aligned benefit categories (B_remedial + B_enabling)
        "benefits_remedial_pv": csv_equivalent.get("benefits_remedial_pv", 0),
        "benefits_enabling_pv": csv_equivalent.get("benefits_enabling_pv", 0),
    }


def aggregate_json_outputs(scenario_id: str, output_dir: str = "outputs") -> dict:
    """
    Aggregate all JSON output files from individual calculation scripts.

    Args:
        scenario_id: The scenario ID to match output files
        output_dir: Directory containing the output files

    Returns:
        Aggregated results dictionary
    """
    from json_output_manager import JSONOutputManager

    # Create a new manager to aggregate results
    aggregator = JSONOutputManager(scenario_id=scenario_id)

    # Find all JSON output files for this scenario
    pattern = os.path.join(output_dir, f"json_output_{scenario_id}_*.json")
    json_files = glob.glob(pattern)

    # Debug: Log what files we found
    print(f"DEBUG: Looking for JSON files matching: {pattern}", file=sys.stderr)
    print(
        f"DEBUG: Found {len(json_files)} JSON files: {[os.path.basename(f) for f in json_files]}",
        file=sys.stderr,
    )

    # Load and merge each file
    for json_file in json_files:
        print(
            f"DEBUG: Loading JSON file: {os.path.basename(json_file)}", file=sys.stderr
        )
        aggregator.load_from_file(json_file)
        # Clean up the intermediate file
        try:
            os.unlink(json_file)
        except Exception:
            pass

    return aggregator


_TRAJECTORY_ARRAY_KEYS = {
    ("costs", "emissions"): ["emissions_comp_annual_values"],
    ("benefits", "facilitated_emissions"): [
        "fac_emissions_withline_annual_values",
        "fac_emissions_noline_annual_values",
        "displacement_annual_values",
    ],
}


def _hoist_trajectory_arrays(results: dict) -> None:
    """Copy year-by-year annual-value arrays up to the top level of `results`.

    emissions.py and facilitated_emissions.py nest their results under
    costs["emissions"] / benefits["facilitated_emissions"]. The (future) BCR
    trajectory module consumes these arrays directly off the top-level results
    dict (docs/design/2026-07-10__bcr-trajectory-spec.md), so hoist them here
    rather than duplicating the year-by-year loops elsewhere.
    """
    for (category, module_key), array_keys in _TRAJECTORY_ARRAY_KEYS.items():
        module_results = results.get(category, {}).get(module_key, {})
        for array_key in array_keys:
            if array_key in module_results:
                results[array_key] = module_results[array_key]


def write_final_json_output(
    aggregator,
    bcr_results: dict | None,
    scenario_id: str,
    output_dir: str = "outputs",
    csv_equivalent: dict | None = None,
    summary_override: dict | None = None,
    taxonomy_results_json: list | None = None,
):
    """
    Write the final aggregated JSON output file.

    Args:
        aggregator: JSONOutputManager with aggregated results
        bcr_results: BCR calculation results
        scenario_id: The scenario ID
        output_dir: Directory to write the output file
        csv_equivalent: Flat dict aligned with CSV schema
        summary_override: Summary aligned with CSV/BCR totals
    """
    # Add BCR results if available
    if bcr_results:
        aggregator.add_bcr_metrics(bcr_results)

    # Calculate summary
    aggregator.calculate_summary()

    # Get the final results
    results = aggregator.get_json_results()
    _hoist_trajectory_arrays(results)
    if csv_equivalent is not None:
        results["csv_equivalent"] = csv_equivalent
    if summary_override is not None:
        results["summary"] = summary_override
    if taxonomy_results_json is not None:
        results["taxonomy_results"] = taxonomy_results_json

    _ctx = get_run_context()
    if _ctx is not None and _ctx.derived_parameters:
        results["derived_parameters"] = _ctx.derived_parameters

    # Write to final output file
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
    """Build the ordered list of calculator module filenames to run."""
    if capital_only:
        return [
            "weighted_miles.py",
            "build_costs.py",
            "row_costs.py",
            "environmental_mitigation.py",
        ]
    scripts = [
        "weighted_miles.py",
        "build_costs.py",
        "row_costs.py",
        "environmental_mitigation.py",
        "revenue.py",
    ]
    if not no_insurance:
        scripts.append("insurance_costs.py")
    if not no_delay_costs:
        scripts.append("delay_costs.py")
    if not no_wildfire:
        scripts.append("wildfire_costs.py")
    if not no_outages:
        scripts.append("outage_costs.py")
    scripts.append("congestion_curtailment_reduction.py")
    scripts.append("energy_losses.py")
    if not no_oandm:
        scripts.append("oandm.py")
    if not no_emissions:
        scripts.append("emissions.py")
        scripts.append("facilitated_emissions.py")
        scripts.append("displacement_delay_cost.py")
    if not no_linelosses:
        scripts.append("line_loss_costs.py")
    return scripts


def run_calculation(
    combined_data: dict[str, Any],
    scenario_id: str,
    *,
    no_emissions: bool = False,
    no_linelosses: bool = False,
    no_insurance: bool = False,
    no_delay_costs: bool = False,
    no_wildfire: bool = False,
    no_outages: bool = False,
    no_oandm: bool = False,
    capital_only: bool = False,
    quiet: bool = True,
) -> dict[str, Any]:
    """Run the full FORGE calculation pipeline in-process.

    Accepts a Python dict of inputs, returns a Python dict of results.
    Thread-safe via _calculation_lock (env vars are process-global).
    """
    with _calculation_lock:
        import path_config
        saved_yamls_dir = path_config.YAMLS_DIR
        saved_env = {
            k: os.environ.get(k)
            for k in ("FORGE_YAMLS_DIR", "FORGE_SCENARIO_ID", "FORGE_OUTPUT_MODE")
        }
        temp_yaml_dir = None
        try:
            temp_yaml_dir = tempfile.mkdtemp(prefix=f"forge_yaml_{scenario_id}_")
            for key, value in combined_data.items():
                yaml_path = os.path.join(temp_yaml_dir, f"{key}.yaml")
                with open(yaml_path, "w") as f:
                    yaml.dump(value, f, default_flow_style=False, sort_keys=False)

            _set_yamls_dir(Path(temp_yaml_dir))
            os.environ["FORGE_SCENARIO_ID"] = scenario_id
            os.environ["FORGE_OUTPUT_MODE"] = "json"

            from json_output_manager import JSONOutputManager
            aggregator = JSONOutputManager(scenario_id=scenario_id)
            set_output_manager(aggregator)

            # Populate RunContext: load shared data once for the entire run
            from smart_loaders import get_physical_data_raw
            from yaml_loaders import (
                load_project_technical_details, load_financing_details,
                load_contingencies, load_row_widths,
            )
            from calculation_utils import build_category_string
            from weighted_miles import calculate_weighted_miles as _calc_wm

            _project_details = load_project_technical_details()
            _financing = load_financing_details()
            _contingencies = load_contingencies()
            _physical_raw = get_physical_data_raw()
            _terrain_miles = _physical_raw["terrain"]["terrain_miles"]
            _terrain_multipliers = _physical_raw["terrain"]["terrain_multipliers"]
            _total_miles = sum(v for v in _terrain_miles.values() if v is not None)
            _category_string = build_category_string(project_details=_project_details)
            _row_width_feet = load_row_widths(_category_string)
            _weighted_miles, _avg_terrain_mult = _calc_wm()

            from financial_utils import (
                calculate_afudc_rate as _calc_afudc,
                calculate_cod_year as _calc_cod,
                calculate_construction_start_year as _calc_cstart,
            )
            from smart_loaders import get_financing_data_raw
            _afudc_rate, _afudc_source = _calc_afudc(get_financing_data_raw())
            _cod_year = _calc_cod(_project_details.delay_years, _project_details.construction_years)
            _construction_start_year = _calc_cstart(_project_details.delay_years)

            set_run_context(RunContext(
                project_details=_project_details,
                terrain_miles=_terrain_miles,
                terrain_multipliers=_terrain_multipliers,
                total_miles=_total_miles,
                financing=_financing,
                contingencies=_contingencies,
                category_string=_category_string,
                row_width_feet=_row_width_feet,
                weighted_miles=_weighted_miles,
                average_terrain_multiplier=_avg_terrain_mult,
            ))

            _fin_raw = get_financing_data_raw()
            add_derived({
                "category_string": _category_string,
                "row_width_feet": _row_width_feet,
                "weighted_miles": _weighted_miles,
                "average_terrain_multiplier": _avg_terrain_mult,
                "total_miles": _total_miles,
                "terrain_miles": _terrain_miles,
                "terrain_multipliers": _terrain_multipliers,
                "wacc_real": _financing.wacc_real,
                "wacc_nominal": _financing.wacc_nominal,
                "inflation_rate": _financing.inflation_rate,
                "social_discount_rate": _fin_raw["financial"].get("social_discount_rate", 0),
                "afudc_rate": _afudc_rate,
                "afudc_source": _afudc_source,
                "cod_year": _cod_year,
                "construction_start_year": _construction_start_year,
                "contingencies": _contingencies,
            })

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

            module_timings: list[tuple[str, float]] = []
            failed_scripts: list[str] = []

            saved_stdout = sys.stdout
            if quiet:
                sys.stdout = open(os.devnull, "w")
            try:
                for script in scripts:
                    stem = script.replace(".py", "")
                    try:
                        mod = importlib.import_module(stem)
                        t0 = _time.perf_counter()
                        mod.main()
                        module_timings.append((stem, (_time.perf_counter() - t0) * 1000))
                    except Exception:
                        failed_scripts.append(script)
                        if not quiet:
                            traceback.print_exc()
            finally:
                if quiet:
                    sys.stdout.close()
                    sys.stdout = saved_stdout

            json_results = aggregator.get_json_results()
            bcr_results = None
            csv_equivalent = None
            summary_override = None
            taxonomy_results_json = None
            try:
                from taxonomy_adapters import (
                    adapt_all_results,
                    taxonomy_results_to_json_list,
                )
                from bcr_calculator import compute_all_bcrs

                t0 = _time.perf_counter()
                taxonomy_results = adapt_all_results(json_results)
                taxonomy_results_json = taxonomy_results_to_json_list(taxonomy_results)
                bcr_results = compute_all_bcrs(taxonomy_results)
                csv_equivalent = build_csv_equivalent(
                    json_results, bcr_results, bcr_results
                )
                summary_override = build_summary_from_csv_equivalent(csv_equivalent)
                module_timings.append(("taxonomy+bcr", (_time.perf_counter() - t0) * 1000))
            except Exception:
                if not quiet:
                    traceback.print_exc()

            if module_timings:
                print("\n--- Module Timings ---", file=sys.stderr)
                for name, ms in sorted(module_timings, key=lambda x: -x[1]):
                    print(f"  {ms:7.1f} ms  {name}", file=sys.stderr)
                total_time = sum(ms for _, ms in module_timings)
                print(f"  {'─' * 20}", file=sys.stderr)
                print(f"  {total_time:7.1f} ms  TOTAL", file=sys.stderr)

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

            if results.get("bcr"):
                from bcr_trajectory import compute_trajectory
                results["trajectory"] = compute_trajectory(results, combined_data)

            _ctx = get_run_context()
            if _ctx is not None and _ctx.derived_parameters:
                results["derived_parameters"] = _ctx.derived_parameters

            if failed_scripts:
                results["_warnings"] = [f"Module failed: {s}" for s in failed_scripts]
                results["_partial"] = True

            return results

        finally:
            clear_run_context()
            clear_output_manager()
            if temp_yaml_dir and os.path.exists(temp_yaml_dir):
                shutil.rmtree(temp_yaml_dir, ignore_errors=True)
            _set_yamls_dir(saved_yamls_dir)
            for k, v in saved_env.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v


def main() -> None:
    """
    Main function to run all cost calculation scripts (CLI entry point).
    """
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Framework for Open Reproducible Grid Economics (FORGE)"
    )
    parser.add_argument(
        "--norisk",
        action="store_true",
        help="[DEPRECATED] Skip risk cost calculations (wildfire and outage costs). Use --no_wildfire --no_outages instead.",
    )
    parser.add_argument(
        "--simple",
        action="store_true",
        help="Simple output mode: only show BCR analysis (suppress intermediate outputs)",
    )
    parser.add_argument(
        "--no_emissions",
        action="store_true",
        help="Skip emissions cost calculations",
    )
    parser.add_argument(
        "--no_linelosses",
        action="store_true",
        help="Skip line loss cost calculations",
    )
    parser.add_argument(
        "--capital_only",
        action="store_true",
        help="Run only capital cost scripts (build, ROW, environmental mitigation) plus prerequisites",
    )
    parser.add_argument(
        "--no_oandm",
        action="store_true",
        help="Skip O&M cost calculations",
    )
    parser.add_argument(
        "--no_insurance",
        action="store_true",
        help="Skip general insurance cost calculations",
    )
    parser.add_argument(
        "--no_delay_costs",
        action="store_true",
        help="Skip delay cost calculations",
    )
    parser.add_argument(
        "--no_wildfire",
        action="store_true",
        help="Skip wildfire risk costs (expected wildfire cost)",
    )
    parser.add_argument(
        "--no_outages",
        action="store_true",
        help="Skip outage risk costs",
    )
    parser.add_argument(
        "--no_congestion",
        action="store_true",
        help="Skip congestion benefit calculations",
    )
    parser.add_argument(
        "--subprocess",
        action="store_true",
        help="Run each calculation script as a subprocess (legacy). Default is in-process.",
    )
    args = parser.parse_args()

    # Set environment variables for congestion/curtailment script
    if args.no_congestion:
        os.environ["FORGE_NO_CONGESTION"] = "1"

    # Handle --norisk deprecation: if used, set individual flags
    if args.norisk:
        args.no_wildfire = True
        args.no_outages = True

    if not args.simple:
        print("=" * 80)
        print("FRAMEWORK FOR OPEN REPRODUCIBLE GRID ECONOMICS (FORGE)")
        print("=" * 80)
        if args.norisk:
            print("⚠️  [DEPRECATED] --norisk flag is deprecated")
            print("   Use --no_wildfire --no_outages instead")
            print("   Risk costs disabled (wildfire and outage)")
            print("=" * 80)
        if args.no_wildfire:
            print("⚠️  Wildfire risk costs disabled (--no_wildfire flag set)")
            print("   Skipping: wildfire_costs.py")
            print("=" * 80)
        if args.no_outages:
            print("⚠️  Outage risk costs disabled (--no_outages flag set)")
            print("   Skipping: outage_costs.py")
            print("=" * 80)
        if args.no_oandm:
            print("⚠️  O&M costs disabled (--no_oandm flag set)")
            print("   Skipping: oandm.py")
            print("=" * 80)
        if args.no_insurance:
            print("⚠️  Insurance costs disabled (--no_insurance flag set)")
            print("   Skipping: insurance_costs.py")
            print("=" * 80)
        if args.no_delay_costs:
            print("⚠️  Delay costs disabled (--no_delay_costs flag set)")
            print("   Skipping: delay_costs.py")
            print("=" * 80)
        if args.no_congestion:
            print("⚠️  Congestion benefits disabled (--no_congestion flag set)")
            print(
                "   Congestion portion of congestion_curtailment_reduction.py will be skipped"
            )
            print("=" * 80)
        if args.no_emissions:
            print("⚠️  Emissions costs disabled (--no_emissions flag set)")
            print("   Skipping: emissions.py")
            print("=" * 80)
        if args.no_linelosses:
            print("⚠️  Line loss costs disabled (--no_linelosses flag set)")
            print("   Skipping: line_loss_costs.py")
            print("=" * 80)
        if args.capital_only:
            print("⚠️  Capital-only mode enabled (--capital_only flag set)")
            print(
                "   Running only: weighted_miles.py, build_costs.py, row_costs.py, environmental_mitigation.py"
            )
            print("=" * 80)

    # Generate a single scenario_id for this entire run
    # Only generate if not already set (for parallel sensitivity analysis)
    # Use microseconds to ensure uniqueness even if runs happen in the same second
    if "FORGE_SCENARIO_ID" not in os.environ:
        scenario_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        os.environ["FORGE_SCENARIO_ID"] = scenario_id
    else:
        scenario_id = os.environ["FORGE_SCENARIO_ID"]

    if not args.simple:
        print(f"\n📋 Scenario ID: {scenario_id}\n")

    # Calculator is JSON-out only; always use JSON aggregator
    in_process_aggregator = None
    if not args.subprocess:
        from json_output_manager import JSONOutputManager
        in_process_aggregator = JSONOutputManager(scenario_id=scenario_id)
        set_output_manager(in_process_aggregator)

        # Populate RunContext: load shared data once for the entire run
        from smart_loaders import get_physical_data_raw
        from yaml_loaders import (
            load_project_technical_details, load_financing_details,
            load_contingencies, load_row_widths,
        )
        from calculation_utils import build_category_string
        from weighted_miles import calculate_weighted_miles as _calc_wm

        _project_details = load_project_technical_details()
        _financing = load_financing_details()
        _contingencies = load_contingencies()
        _physical_raw = get_physical_data_raw()
        _terrain_miles = _physical_raw["terrain"]["terrain_miles"]
        _terrain_multipliers = _physical_raw["terrain"]["terrain_multipliers"]
        _total_miles = sum(v for v in _terrain_miles.values() if v is not None)
        _category_string = build_category_string(project_details=_project_details)
        _row_width_feet = load_row_widths(_category_string)
        _weighted_miles, _avg_terrain_mult = _calc_wm()

        set_run_context(RunContext(
            project_details=_project_details,
            terrain_miles=_terrain_miles,
            terrain_multipliers=_terrain_multipliers,
            total_miles=_total_miles,
            financing=_financing,
            contingencies=_contingencies,
            category_string=_category_string,
            row_width_feet=_row_width_feet,
            weighted_miles=_weighted_miles,
            average_terrain_multiplier=_avg_terrain_mult,
        ))

        from financial_utils import (
            calculate_afudc_rate as _calc_afudc_cli,
            calculate_cod_year as _calc_cod_cli,
            calculate_construction_start_year as _calc_cstart_cli,
        )
        from smart_loaders import get_financing_data_raw as _get_fin_raw_cli
        _afudc_rate_cli, _afudc_source_cli = _calc_afudc_cli(_get_fin_raw_cli())
        _cod_year_cli = _calc_cod_cli(_project_details.delay_years, _project_details.construction_years)
        _cstart_cli = _calc_cstart_cli(_project_details.delay_years)

        _fin_raw_cli = _get_fin_raw_cli()
        add_derived({
            "category_string": _category_string,
            "row_width_feet": _row_width_feet,
            "weighted_miles": _weighted_miles,
            "average_terrain_multiplier": _avg_terrain_mult,
            "total_miles": _total_miles,
            "terrain_miles": _terrain_miles,
            "terrain_multipliers": _terrain_multipliers,
            "wacc_real": _financing.wacc_real,
            "wacc_nominal": _financing.wacc_nominal,
            "inflation_rate": _financing.inflation_rate,
            "social_discount_rate": _fin_raw_cli["financial"].get("social_discount_rate", 0),
            "afudc_rate": _afudc_rate_cli,
            "afudc_source": _afudc_source_cli,
            "cod_year": _cod_year_cli,
            "construction_start_year": _cstart_cli,
            "contingencies": _contingencies,
        })

    os.environ["FORGE_OUTPUT_MODE"] = "json"

    # List of scripts to run in order
    # If --capital_only is set, only run capital scripts plus prerequisites
    if args.capital_only:
        scripts = [
            "weighted_miles.py",
            "build_costs.py",
            "row_costs.py",
            "environmental_mitigation.py",
        ]
    else:
        # Always-on scripts (prerequisites and capital costs)
        scripts = [
            "weighted_miles.py",  # Always (prerequisite)
            "build_costs.py",  # Always (capital cost)
            "row_costs.py",  # Always (capital cost)
            "environmental_mitigation.py",  # Always (capital cost)
            "revenue.py",  # Always (revenue)
        ]

        # Conditionally add insurance costs
        if not args.no_insurance:
            scripts.append("insurance_costs.py")

        # Conditionally add delay costs
        if not args.no_delay_costs:
            scripts.append("delay_costs.py")

        # Conditionally add risk cost scripts
        if not args.no_wildfire:
            scripts.append("wildfire_costs.py")
        if not args.no_outages:
            scripts.append("outage_costs.py")

        # Always run congestion_curtailment_reduction.py
        # (flags control what it calculates via environment variables)
        scripts.append("congestion_curtailment_reduction.py")

        # Always run energy_losses.py (prerequisite for line_loss_costs)
        scripts.append("energy_losses.py")

        # Conditionally add O&M costs
        if not args.no_oandm:
            scripts.append("oandm.py")

        # Conditionally add emissions and line_loss_costs based on flags
        if not args.no_emissions:
            scripts.append("emissions.py")
            scripts.append("facilitated_emissions.py")
            scripts.append("displacement_delay_cost.py")
        if not args.no_linelosses:
            scripts.append("line_loss_costs.py")

        # Add more scripts as you create them

    successful_runs = 0
    total_runs = len(scripts)
    failed_scripts = []
    module_timings: list[tuple[str, float]] = []

    # Debug: Log which scripts will be run
    if not args.simple:
        print(f"DEBUG: Scripts to run ({total_runs}): {scripts}", file=sys.stderr)
        if "line_loss_costs.py" in scripts:
            print("DEBUG: line_loss_costs.py IS in the scripts list", file=sys.stderr)
        else:
            print(
                "DEBUG: line_loss_costs.py is NOT in the scripts list!", file=sys.stderr
            )

    for script in scripts:
        if not args.simple:
            print(f"\n🔄 Running {script}...")

        if args.subprocess:
            if script == "line_loss_costs.py":
                env = os.environ.copy()
                result = subprocess.run(
                    [sys.executable, script],
                    capture_output=True,
                    text=True,
                    cwd="scripts",
                    env=env,
                )
                success = result.returncode == 0
                if not success and not args.simple:
                    if result.stderr:
                        print(result.stderr, file=sys.stderr)
                    if result.stdout:
                        print(result.stdout, file=sys.stderr)
                elif success and not args.simple and result.stdout:
                    print(result.stdout)
            else:
                success = run_script(script, quiet=args.simple)
        else:
            stem = script.replace(".py", "")
            try:
                mod = importlib.import_module(stem)
                t0 = _time.perf_counter()
                mod.main()
                elapsed_ms = (_time.perf_counter() - t0) * 1000
                module_timings.append((stem, elapsed_ms))
                success = True
            except Exception as e:
                success = False
                if not args.simple:
                    print(f"❌ {script} failed with error:", file=sys.stderr)
                    traceback.print_exc()
                else:
                    print(f"❌ Error running {script}: {e}", file=sys.stderr)

        if success:
            successful_runs += 1
        else:
            failed_scripts.append(script)
        if not args.simple:
            print("-" * 60)

    if not args.simple:
        print(
            f"\n📊 SUMMARY: {successful_runs}/{total_runs} scripts completed successfully"
        )

    # Calculate and display BCR metrics (even if some scripts failed)
    if successful_runs > 0:
        if successful_runs == total_runs:
            if not args.simple:
                print("🎉 All calculations completed successfully!")

        # Calculate and display BCR metrics
        if not args.simple:
            print("\n" + "=" * 80)
            print("CALCULATING BENEFIT-COST RATIOS...")
            print("=" * 80)
        else:
            # In simple mode, just print the BCR analysis header
            print("=" * 80)

        # Aggregate JSON results and compute BCR (calculator is JSON-out only)
        bcr_results = None
        try:
            if not args.subprocess and in_process_aggregator is not None:
                aggregator = in_process_aggregator
            else:
                aggregator = aggregate_json_outputs(scenario_id, output_dir="outputs")

            csv_equivalent = None
            summary_override = None
            taxonomy_results_json = None
            json_results = aggregator.get_json_results()
            try:
                from taxonomy_adapters import (
                    adapt_all_results,
                    taxonomy_results_to_json_list,
                )
                from bcr_calculator import compute_all_bcrs, print_bcr_summary

                t0 = _time.perf_counter()
                taxonomy_results = adapt_all_results(json_results)
                taxonomy_results_json = taxonomy_results_to_json_list(taxonomy_results)
                bcr_results = compute_all_bcrs(taxonomy_results)
                csv_equivalent = build_csv_equivalent(
                    json_results, bcr_results, bcr_results
                )
                summary_override = build_summary_from_csv_equivalent(csv_equivalent)
                module_timings.append(("taxonomy+bcr", (_time.perf_counter() - t0) * 1000))

                if not args.simple:
                    print_bcr_summary(bcr_results)
            except Exception as e:
                if not args.simple:
                    print(f"⚠️  BCR calculation failed: {e}")
                    traceback.print_exc()
                bcr_results = None

            output_file = write_final_json_output(
                aggregator,
                bcr_results,
                scenario_id,
                output_dir="outputs",
                csv_equivalent=csv_equivalent,
                summary_override=summary_override,
                taxonomy_results_json=taxonomy_results_json,
            )

            if not args.simple:
                print(f"✅ JSON results written to {output_file}")
            if not args.subprocess:
                clear_run_context()
                clear_output_manager()
        except Exception as e:
            if not args.subprocess:
                clear_run_context()
                clear_output_manager()
            if not args.simple:
                print(f"⚠️  JSON output aggregation failed: {e}")
                traceback.print_exc()
            else:
                print(f"⚠️  JSON output aggregation failed: {e}")
    else:
        if not args.simple:
            print("⚠️  Some calculations failed. Check the output above.")
        else:
            # In simple mode, show error even if quiet
            print("⚠️  Some calculations failed. BCR analysis may be incomplete.")

    if module_timings:
        print("\n--- Module Timings ---", file=sys.stderr)
        for name, ms in sorted(module_timings, key=lambda x: -x[1]):
            print(f"  {ms:7.1f} ms  {name}", file=sys.stderr)
        total_time = sum(ms for _, ms in module_timings)
        print(f"  {'─' * 20}", file=sys.stderr)
        print(f"  {total_time:7.1f} ms  TOTAL", file=sys.stderr)

    if failed_scripts:
        sys.exit(1)


if __name__ == "__main__":
    main()
