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
from bcr_calculator import calculate_and_display_bcr
from csv_output_manager import CTCCOutputManager as CSVOutputManager


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
        result = subprocess.run(
            [sys.executable, script_name], capture_output=True, text=True, cwd="scripts"
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

    # Load and merge each file
    for json_file in json_files:
        aggregator.load_from_file(json_file)
        # Clean up the intermediate file
        try:
            os.unlink(json_file)
        except Exception:
            pass

    return aggregator


def write_final_json_output(aggregator, bcr_results: dict, scenario_id: str, output_dir: str = "outputs"):
    """
    Write the final aggregated JSON output file.

    Args:
        aggregator: JSONOutputManager with aggregated results
        bcr_results: BCR calculation results
        scenario_id: The scenario ID
        output_dir: Directory to write the output file
    """
    # Add BCR results if available
    if bcr_results:
        aggregator.add_bcr_metrics(bcr_results)

    # Calculate summary
    aggregator.calculate_summary()

    # Get the final results
    results = aggregator.get_json_results()

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
        help="Skip risk cost calculations (wildfire and outage costs)",
    )
    parser.add_argument(
        "--simple",
        action="store_true",
        help="Simple output mode: only show BCR analysis (suppress intermediate outputs)",
    )
    parser.add_argument(
        "--no_wf_liability",
        action="store_true",
        help="Skip wildfire liability insurance calculation",
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
    args = parser.parse_args()

    # Set environment variable for insurance_costs.py to check
    if args.no_wf_liability:
        os.environ["CTCC_NO_WF_LIABILITY"] = "1"

    if not args.simple:
        print("=" * 80)
        print("COMPREHENSIVE TRANSMISSION COST CALCULATOR (CTCC)")
        print("=" * 80)
        if args.norisk:
            print("⚠️  Risk costs disabled (--norisk flag set)")
            print("   Skipping: wildfire_costs.py, outage_costs.py")
            print("=" * 80)
        if args.no_wf_liability:
            print(
                "⚠️  Wildfire liability insurance disabled (--no_wf_liability flag set)"
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
        scripts = [
            "weighted_miles.py",
            "build_costs.py",
            "insurance_costs.py",
            "row_costs.py",
            "environmental_mitigation.py",
            "delay_costs.py",
            "revenue.py",
        ]

        # Add risk cost scripts only if --norisk flag is not set
        if not args.norisk:
            scripts.extend(["wildfire_costs.py", "outage_costs.py"])

        # Add remaining scripts
        remaining_scripts = [
            "congestion_curtailment_reduction.py",
            "energy_losses.py",
            "oandm.py",
        ]

        # Conditionally add emissions and line_loss_costs based on flags
        if not args.no_emissions:
            remaining_scripts.append("emissions.py")
        if not args.no_linelosses:
            remaining_scripts.append("line_loss_costs.py")

        scripts.extend(remaining_scripts)
        # Add more scripts as you create them

    successful_runs = 0
    total_runs = len(scripts)
    failed_scripts = []

    for script in scripts:
        if not args.simple:
            print(f"\n🔄 Running {script}...")
        if run_script(script, quiet=args.simple):
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

        bcr_results = None
        try:
            bcr_results = calculate_and_display_bcr(
                scenario_id,
                output_dir="outputs",
                no_emissions=args.no_emissions,
                no_linelosses=args.no_linelosses,
                capital_only=args.capital_only,
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
                # In simple mode, still show errors
                print(f"⚠️  BCR calculation failed: {e}")

        # Handle output based on mode
        if output_mode == "json":
            # JSON output mode: aggregate results and write final JSON
            try:
                aggregator = aggregate_json_outputs(scenario_id, output_dir="outputs")
                output_file = write_final_json_output(
                    aggregator, bcr_results, scenario_id, output_dir="outputs"
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


if __name__ == "__main__":
    main()
