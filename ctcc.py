# Author: Andrew Igdal
# Date: 2025-10-21
# Description: Comprehensive Transmission Cost Calculator (CTCC) - Main Script
#              Orchestrates all individual cost calculation modules

from __future__ import annotations

import subprocess
import sys
import os
import argparse
import glob
import json
from datetime import datetime

# Add scripts directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "scripts"))
from bcr_calculator import calculate_and_display_bcr, BCRConfig, BCRInputData
from csv_output_manager import (
    CTCCOutputManager as CSVOutputManager,
    BATCH_SUMMARY_FIELDS,
)


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


def build_bcr_data_from_json(json_results: dict) -> BCRInputData:
    """Build a flat dict for BCR calculations from JSON results."""
    costs = json_results.get("costs", {}) or {}
    benefits = json_results.get("benefits", {}) or {}

    congestion = benefits.get("congestion_curtailment", {}) or {}
    revenue = benefits.get("revenue", {}) or {}

    build = costs.get("build", {}) or {}
    row = costs.get("row", {}) or {}
    environmental = costs.get("environmental", {}) or {}
    oandm = costs.get("oandm", {}) or {}
    insurance = costs.get("insurance", {}) or {}
    wildfire = costs.get("wildfire", {}) or {}
    outage = costs.get("outage", {}) or {}
    wildfire_liability = costs.get("wildfire_liability", {}) or {}
    delay = costs.get("delay", {}) or {}
    emissions = costs.get("emissions", {}) or {}
    line_loss = costs.get("line_loss", {}) or {}

    flat_dict = {
        # Benefits (PV + nominal)
        "congestion_benefit_pv": congestion.get("congestion_benefit_pv", 0) or 0,
        "curtailment_benefit_pv": congestion.get("curtailment_benefit_pv", 0) or 0,
        "congestion_benefit_nominal": congestion.get("congestion_benefit_nominal", 0)
        or 0,
        "curtailment_benefit_nominal": congestion.get("curtailment_benefit_nominal", 0)
        or 0,
        "congestion_benefit_haircut_pv": congestion.get(
            "congestion_benefit_haircut_pv", 0
        )
        or 0,
        "curtailment_benefit_haircut_pv": congestion.get(
            "curtailment_benefit_haircut_pv", 0
        )
        or 0,
        "delivered_benefit_pv": congestion.get("delivered_benefit_pv", 0) or 0,
        "delivered_benefit_nominal": congestion.get("delivered_benefit_nominal", 0)
        or 0,
        "revenue_pv": revenue.get("revenue_pv", 0) or 0,
        "revenue_nominal": revenue.get("revenue_nominal", 0) or 0,
        # Capital costs (PV + nominal); ROW = capital only (acquisition + holding)
        "build_cost_pv": build.get("total_pv", 0) or 0,
        "build_cost_nominal": build.get("total_nominal", 0) or 0,
        "row_cost_pv": row.get("total_pv", 0) or 0,
        "row_cost_nominal": row.get("total_nominal", 0) or 0,
        "row_capital_pv": row.get("row_capital_pv", 0) or row.get("total_pv", 0) or 0,
        "row_capital_nominal": row.get("row_capital_nominal", 0)
        or row.get("total_nominal", 0)
        or 0,
        "row_rent_pv": row.get("row_rent_pv", 0) or 0,
        "row_rent_nominal": row.get("row_rent_nominal", 0) or 0,
        "env_mitigation_pv": environmental.get("total_pv", 0) or 0,
        "env_mitigation_nominal": environmental.get("total_nominal", 0) or 0,
        # Operational costs (PV + nominal)
        "oandm_pv": oandm.get("total_pv", 0) or 0,
        "oandm_nominal": oandm.get("total_nominal", 0) or 0,
        "insurance_pv": insurance.get("pv_total", 0) or 0,
        "insurance_nominal": insurance.get("nominal_lifetime_cost", 0) or 0,
        # Energy & emissions costs (PV + nominal)
        "energy_losses_pv": line_loss.get("total_pv", 0) or 0,
        "energy_losses_nominal": line_loss.get("total_nominal", 0) or 0,
        "conductor_loss_pv": line_loss.get("line_cost_pv", 0) or 0,
        "converter_loss_pv": line_loss.get("converter_cost_pv", 0) or 0,
        "emissions_cost_pv": emissions.get("total_pv", 0) or 0,
        "emissions_cost_nominal": emissions.get("total_nominal", 0) or 0,
        # Risk costs (PV + nominal)
        "wildfire_pv": wildfire.get("pv_cost", 0) or 0,
        "wildfire_nominal": wildfire.get("nominal_total", 0) or 0,
        "outage_pv": outage.get("pv_cost", 0) or 0,
        "outage_nominal": outage.get("nominal_total", 0) or 0,
        "wildfire_liability_pv": wildfire_liability.get("pv_total", 0) or 0,
        "wildfire_liability_nominal": wildfire_liability.get("nominal_lifetime_cost", 0)
        or 0,
        "wildfire_liability_insurance_pv": wildfire_liability.get("pv_total", 0) or 0,
        # Delay costs (PV + nominal)
        "delay_cost_pv": delay.get("total_pv", 0) or 0,
        "delay_cost_nominal": delay.get("total_nominal", 0) or 0,
        "congestion_delay_cost_pv": congestion.get("congestion_delay_cost_pv", 0) or 0,
        "congestion_delay_cost_nominal": congestion.get(
            "congestion_delay_cost_nominal", 0
        )
        or 0,
        "curtailment_delay_cost_pv": congestion.get("curtailment_delay_cost_pv", 0)
        or 0,
        "curtailment_delay_cost_nominal": congestion.get(
            "curtailment_delay_cost_nominal", 0
        )
        or 0,
        "residual_exceedance_pv": congestion.get("residual_exceedance_pv", 0) or 0,
        "residual_exceedance_nominal": congestion.get("residual_exceedance_nominal", 0)
        or 0,
    }
    return BCRInputData.model_validate(flat_dict)


def build_csv_equivalent(
    json_results: dict,
    bcr_results: dict | None,
    bcr_data: dict | BCRInputData | None,
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
    """Create a minimal summary aligned with CSV/BCR totals."""
    return {
        "total_capital_pv": csv_equivalent.get("capital_costs_pv", 0),
        "total_operational_pv": csv_equivalent.get("operational_costs_pv", 0),
        "total_energy_emissions_pv": csv_equivalent.get("energy_emissions_costs_pv", 0),
        "total_risk_pv": csv_equivalent.get("risk_costs_pv", 0),
        "total_delay_pv": csv_equivalent.get("delay_costs_pv", 0),
        "total_costs_pv": csv_equivalent.get("total_costs_pv", 0),
        "total_benefits_pv": csv_equivalent.get("total_benefits_pv", 0),
        "total_benefits_haircut_pv": csv_equivalent.get("total_benefits_haircut_pv", 0),
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


def write_final_json_output(
    aggregator,
    bcr_results: dict | None,
    scenario_id: str,
    output_dir: str = "outputs",
    csv_equivalent: dict | None = None,
    summary_override: dict | None = None,
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
    if csv_equivalent is not None:
        results["csv_equivalent"] = csv_equivalent
    if summary_override is not None:
        results["summary"] = summary_override

    # Write to final output file
    output_file = os.path.join(output_dir, f"ctcc_results_{scenario_id}.json")
    os.makedirs(output_dir, exist_ok=True)

    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)

    return output_file


def main() -> None:
    """
    Main function to run all cost calculation scripts.
    """
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Comprehensive Transmission Cost Calculator (CTCC)"
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
        "--no_wf_liability",
        action="store_true",
        help="[DEPRECATED] Skip wildfire liability insurance calculation. Use --no_wildfire instead.",
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
        help="Skip wildfire risk costs (both wildfire costs and wildfire liability insurance)",
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
        "--no_curtailment",
        action="store_true",
        help="Skip curtailment benefit calculations",
    )
    args = parser.parse_args()

    # Load Primary BCR config (from YAML or JSON based on input mode)
    # This overrides command-line flags
    bcr_config = None  # Initialize to avoid NameError if exception occurs
    source = "YAML"  # Default source name for error messages
    try:
        input_mode = os.environ.get("CTCC_INPUT_MODE", "yaml").lower()

        if input_mode == "json":
            # Use JSON loader when in JSON input mode
            from scripts.json_loaders import load_primary_bcr_config

            source = "JSON"
        else:
            # Use YAML loader (default)
            from scripts.yaml_loaders import load_primary_bcr_config

            source = "YAML"

        bcr_config = load_primary_bcr_config()
        bcr_config_dict = (
            bcr_config.model_dump() if hasattr(bcr_config, "model_dump") else bcr_config
        )

        # Debug: Log what we loaded (always log for JSON mode to help diagnose issues)
        if input_mode == "json":
            line_losses_enabled = (
                bcr_config_dict.get("energy", {}).get("line_losses", True)
                if bcr_config_dict
                else True
            )
            print(
                f"DEBUG: BCR config loaded from {source}, line_losses={line_losses_enabled}",
                file=sys.stderr,
            )
            print(
                f"DEBUG: args.no_linelosses will be set to: {not line_losses_enabled}",
                file=sys.stderr,
            )

        # BCR config overrides command-line flags
        if bcr_config_dict:
            # Convert BCR config enabled flags to ctcc.py flags (invert logic)
            # Operational
            if not bcr_config_dict.get("operational", {}).get("oandm", True):
                args.no_oandm = True
            if not bcr_config_dict.get("operational", {}).get("insurance", True):
                args.no_insurance = True
            if not bcr_config_dict.get("operational", {}).get("delay_costs", True):
                args.no_delay_costs = True

            # Risk
            if not bcr_config_dict.get("risk", {}).get("wildfire", True):
                args.no_wildfire = True
            if not bcr_config_dict.get("risk", {}).get("outages", True):
                args.no_outages = True

            # Energy
            if not bcr_config_dict.get("energy", {}).get("line_losses", True):
                args.no_linelosses = True
            if not bcr_config_dict.get("energy", {}).get("emissions", True):
                args.no_emissions = True

            # Benefits
            if not bcr_config_dict.get("benefits", {}).get("congestion", True):
                args.no_congestion = True
            if not bcr_config_dict.get("benefits", {}).get("curtailment", True):
                args.no_curtailment = True
    except (FileNotFoundError, ImportError):
        # Config file doesn't exist or can't be loaded - use command-line flags only
        pass
    except Exception as e:
        # Any other error loading config - use command-line flags only
        if not args.simple:
            print(f"Warning: Could not load Primary BCR config from {source}: {e}")
            print("  Using command-line flags only.")
            import traceback

            traceback.print_exc()

    # Create BCRConfig from args (after YAML overrides are applied)
    bcr_config = BCRConfig(
        no_emissions=args.no_emissions,
        no_linelosses=args.no_linelosses,
        capital_only=args.capital_only,
        no_wildfire=args.no_wildfire,
        no_outages=args.no_outages,
        no_oandm=args.no_oandm,
        no_insurance=args.no_insurance,
        no_delay_costs=args.no_delay_costs,
        no_congestion=args.no_congestion,
        no_curtailment=args.no_curtailment,
    )

    # Handle flag interactions and set environment variables
    # --no_wildfire replaces --no_wf_liability and sets the environment variable
    if args.no_wildfire:
        os.environ["CTCC_NO_WF_LIABILITY"] = "1"
    # Backward compatibility: --no_wf_liability also sets the environment variable
    elif args.no_wf_liability:
        os.environ["CTCC_NO_WF_LIABILITY"] = "1"

    # Set environment variables for congestion/curtailment script
    if args.no_congestion:
        os.environ["CTCC_NO_CONGESTION"] = "1"
    if args.no_curtailment:
        os.environ["CTCC_NO_CURTAILMENT"] = "1"

    # Handle --norisk deprecation: if used, set individual flags
    if args.norisk:
        args.no_wildfire = True
        args.no_outages = True

    if not args.simple:
        print("=" * 80)
        print("COMPREHENSIVE TRANSMISSION COST CALCULATOR (CTCC)")
        print("=" * 80)
        if args.norisk:
            print("⚠️  [DEPRECATED] --norisk flag is deprecated")
            print("   Use --no_wildfire --no_outages instead")
            print("   Risk costs disabled (wildfire and outage)")
            print("=" * 80)
        if args.no_wf_liability:
            print("⚠️  [DEPRECATED] --no_wf_liability flag is deprecated")
            print(
                "   Use --no_wildfire instead (skips both wildfire costs and liability)"
            )
            print("=" * 80)
        if args.no_wildfire:
            print("⚠️  Wildfire risk costs disabled (--no_wildfire flag set)")
            print("   Skipping: wildfire_costs.py, wildfire liability insurance")
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
        if args.no_curtailment:
            print("⚠️  Curtailment benefits disabled (--no_curtailment flag set)")
            print(
                "   Curtailment portion of congestion_curtailment_reduction.py will be skipped"
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
    if "CTCC_SCENARIO_ID" not in os.environ:
        scenario_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        os.environ["CTCC_SCENARIO_ID"] = scenario_id
    else:
        scenario_id = os.environ["CTCC_SCENARIO_ID"]

    if not args.simple:
        print(f"\n📋 Scenario ID: {scenario_id}\n")

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
        if not args.no_linelosses:
            scripts.append("line_loss_costs.py")

        # Add more scripts as you create them

    successful_runs = 0
    total_runs = len(scripts)
    failed_scripts = []

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
        # Debug: Log when we're about to run line_loss_costs
        if script == "line_loss_costs.py":
            print(
                f"DEBUG: About to run line_loss_costs.py, args.no_linelosses={args.no_linelosses}",
                file=sys.stderr,
            )
        if not args.simple:
            print(f"\n🔄 Running {script}...")

        # Special handling for line_loss_costs to capture detailed error output
        if script == "line_loss_costs.py":
            import subprocess

            env = os.environ.copy()
            result = subprocess.run(
                [sys.executable, script],
                capture_output=True,
                text=True,
                cwd="scripts",
                env=env,
            )
            success = result.returncode == 0
            if not success:
                print("DEBUG: line_loss_costs.py FAILED!", file=sys.stderr)
                if result.stderr:
                    print(
                        f"DEBUG: line_loss_costs.py stderr:\n{result.stderr}",
                        file=sys.stderr,
                    )
                if result.stdout:
                    print(
                        f"DEBUG: line_loss_costs.py stdout:\n{result.stdout}",
                        file=sys.stderr,
                    )
            else:
                print(f"DEBUG: line_loss_costs.py succeeded", file=sys.stderr)
                if not args.simple and result.stdout:
                    print(result.stdout)
        else:
            success = run_script(script, quiet=args.simple)

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

    # Check output mode from environment variable
    output_mode = os.environ.get("CTCC_OUTPUT_MODE", "csv").lower()

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

        # Calculate BCR for CSV mode (before JSON aggregation)
        bcr_results = None
        if output_mode == "csv":
            # CSV mode: Calculate BCR from batch_summary.csv
            try:
                bcr_results = calculate_and_display_bcr(
                    scenario_id,
                    output_dir="outputs",
                    config=bcr_config,
                )
            except Exception as e:
                import traceback

                if not args.simple:
                    print(f"⚠️  BCR calculation failed: {e}")
                    print(f"   Scenario ID: {scenario_id}")
                    print("   Full error traceback:")
                    traceback.print_exc()
                    print(
                        "   This does not affect the validity of the cost calculations above."
                    )
                else:
                    print(f"⚠️  BCR calculation failed: {e}")
                bcr_results = None

        # Handle output based on mode
        # For JSON mode, aggregate results even if some scripts failed (partial results)
        if output_mode == "json":
            # JSON output mode: aggregate results and write final JSON
            try:
                aggregator = aggregate_json_outputs(scenario_id, output_dir="outputs")

                # Calculate BCR from JSON aggregator data (not CSV)
                bcr_results = None
                csv_equivalent = None
                summary_override = None
                json_results = aggregator.get_json_results()
                bcr_data = build_bcr_data_from_json(json_results)
                try:
                    from bcr_calculator import (
                        calculate_benefits,
                        calculate_costs,
                        calculate_bcr_metrics,
                    )

                    benefits = calculate_benefits(bcr_data)
                    costs = calculate_costs(bcr_data)
                    bcr_metrics = calculate_bcr_metrics(
                        benefits,
                        costs,
                        config=bcr_config,
                    )
                    bcr_results = {**benefits, **costs, **bcr_metrics}
                    csv_equivalent = build_csv_equivalent(
                        json_results, bcr_results, bcr_data
                    )
                    summary_override = build_summary_from_csv_equivalent(csv_equivalent)
                except Exception as e:
                    import traceback

                    if not args.simple:
                        print(f"⚠️  BCR calculation failed: {e}")
                        traceback.print_exc()
                    if bcr_data is not None:
                        csv_equivalent = build_csv_equivalent(
                            json_results, None, bcr_data
                        )
                        summary_override = build_summary_from_csv_equivalent(
                            csv_equivalent
                        )
                    bcr_results = None

                output_file = write_final_json_output(
                    aggregator,
                    bcr_results,
                    scenario_id,
                    output_dir="outputs",
                    csv_equivalent=csv_equivalent,
                    summary_override=summary_override,
                )

                if not args.simple:
                    print(f"✅ JSON results written to {output_file}")
            except Exception as e:
                import traceback

                if not args.simple:
                    print(f"⚠️  JSON output aggregation failed: {e}")
                    traceback.print_exc()
                else:
                    print(f"⚠️  JSON output aggregation failed: {e}")
        else:
            # CSV output mode (default)
            if bcr_results:
                # Update batch_summary.csv with BCR metrics
                csv_manager = CSVOutputManager(
                    output_dir="outputs", scenario_id=scenario_id
                )
                csv_manager.add_bcr_metrics(bcr_results)
                csv_manager.write_batch_summary()

                if not args.simple:
                    print("✅ BCR metrics added to batch_summary.csv")
                else:
                    # In simple mode, still confirm BCR columns were written
                    print("✅ BCR metrics written to batch_summary.csv")
            else:
                # Always show this warning, even in simple mode
                print("⚠️  BCR calculation completed but no results returned")
                print(f"   Scenario ID: {scenario_id}")
                print(
                    "   This may indicate missing required columns in batch_summary.csv"
                )
                print("   BCR columns will not be available in batch_summary.csv")
    else:
        if not args.simple:
            print("⚠️  Some calculations failed. Check the output above.")
        else:
            # In simple mode, show error even if quiet
            print("⚠️  Some calculations failed. BCR analysis may be incomplete.")

    # Exit with failure so callers (e.g. batch_craft) can detect module failures
    if failed_scripts:
        sys.exit(1)


if __name__ == "__main__":
    main()
