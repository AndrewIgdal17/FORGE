# Author: Andrew Igdal
# Date: 2025-10-21
# Description: Comprehensive Transmission Cost Calculator (CTCC) - Main Script
#              Orchestrates all individual cost calculation modules

import subprocess
import sys
import os
import argparse
from datetime import datetime

# Add scripts directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "scripts"))
from bcr_calculator import calculate_and_display_bcr
from smart_output import CTCCOutputManager


<<<<<<< HEAD
def run_script(script_name, env=None):
=======
def run_script(script_name, quiet=False):
>>>>>>> master
    """
    Run a Python script and capture its output.

    Args:
        script_name (str): Name of the script to run
<<<<<<< HEAD
        env (dict): Optional environment variables to pass to the script
=======
        quiet (bool): If True, suppress output messages
>>>>>>> master

    Returns:
        bool: True if successful, False if error
    """
    try:
        result = subprocess.run(
            [sys.executable, script_name],
            capture_output=True,
            text=True,
            cwd="scripts",
            env=env
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


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='CTCC - Comprehensive Transmission Cost Calculator',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Default mode (YAML → CSV)
  python ctcc.py

  # JSON input → CSV output
  python ctcc.py --json

  # JSON input → JSON output
  python ctcc.py --json --json-out

  # With custom scenario ID
  python ctcc.py --json --json-out --id my_scenario

  # Short flags
  python ctcc.py -j -o      # JSON → JSON
  python ctcc.py -j         # JSON → CSV
        """
    )

    parser.add_argument(
        '-j', '--json',
        action='store_true',
        help='Use JSON input mode (default: YAML)'
    )

    parser.add_argument(
        '-o', '--json-out',
        action='store_true',
        help='Use JSON output mode (default: CSV)'
    )

    parser.add_argument(
        '--id', '--scenario-id',
        dest='scenario_id',
        type=str,
        help='Custom scenario identifier (default: auto-generated timestamp)'
    )

    parser.add_argument(
        '--json-file',
        dest='json_file',
        type=str,
        help='Path to combined JSON data file (required when using --json flag)'
    )

    return parser.parse_args()


def main():
    """
    Main function to run all cost calculation scripts.
    """
    # Parse command line arguments
    args = parse_arguments()

    # Determine modes from command-line flags
    input_mode = 'json' if args.json else 'yaml'
    output_mode = 'json' if args.json_out else 'csv'

    print("=" * 80)
    print("COMPREHENSIVE TRANSMISSION COST CALCULATOR (CTCC)")
    print("=" * 80)
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
            print("⚠️  Wildfire liability insurance disabled (--no_wf_liability flag set)")
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
            print("   Running only: weighted_miles.py, build_costs.py, row_costs.py, environmental_mitigation.py")
            print("=" * 80)

    print(f"\n🔧 Input Mode: {input_mode.upper()}")
    print(f"🔧 Output Mode: {output_mode.upper()}")

    # Generate a single scenario_id for this entire run
    scenario_id = args.scenario_id
    if not scenario_id:
        scenario_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    print(f"📋 Scenario ID: {scenario_id}\n")

    # If JSON input mode, determine JSON data file path
    combined_json_file = None
    if input_mode == 'json':
        if args.json_file:
            # Use provided JSON file path
            from pathlib import Path
            combined_json_file = Path(args.json_file)
            if not combined_json_file.exists():
                print(f"❌ Error: JSON file not found: {combined_json_file}")
                return
            print(f"📄 Using JSON file: {combined_json_file}\n")
        else:
            # No JSON file provided, convert from YAML
            print("🔄 Converting YAML files to combined JSON...")
            try:
                from pathlib import Path
                script_dir = Path(__file__).parent
                yamls_dir = script_dir / "yamls"
                combined_json_file = script_dir / "combined_data.json"

                # Run yaml_to_json.py
                result = subprocess.run(
                    [sys.executable, "yaml_to_json.py", str(yamls_dir), str(combined_json_file)],
                    capture_output=True,
                    text=True,
                    cwd=str(script_dir)
                )

                if result.returncode == 0:
                    print(f"✅ YAML to JSON conversion successful")
                    print(result.stdout)
                else:
                    print(f"❌ YAML to JSON conversion failed:")
                    print(result.stderr)
                    return
            except Exception as e:
                print(f"❌ Error during YAML to JSON conversion: {e}")
                return

            print("-" * 80)
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

    # Prepare environment variables for subprocess scripts
    # Note: Subprocesses still use environment variables for configuration
    env = os.environ.copy()
    env['CTCC_SCENARIO_ID'] = scenario_id
    env['CTCC_INPUT_MODE'] = input_mode
    env['CTCC_OUTPUT_MODE'] = output_mode
    if input_mode == 'json' and combined_json_file:
        # Convert to absolute path since subprocesses run in scripts/ directory
        json_file_path = str(combined_json_file.absolute())
        env['CTCC_JSON_DATA_FILE'] = json_file_path
        # Also set for parent process (for aggregation and BCR calculation)
        os.environ['CTCC_JSON_DATA_FILE'] = json_file_path

    for script in scripts:
        print(f"\n🔄 Running {script}...")
        if run_script(script, env=env):
    for script in scripts:
        if not args.simple:
            print(f"\n🔄 Running {script}...")
        if run_script(script, quiet=args.simple):
            successful_runs += 1
        if not args.simple:
            print("-" * 60)

    if not args.simple:
        print(
            f"\n📊 SUMMARY: {successful_runs}/{total_runs} scripts completed successfully"
        )

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

        try:
            bcr_results = calculate_and_display_bcr(scenario_id, output_dir="outputs")

            if bcr_results:
                # Update batch_summary with BCR metrics
                # SmartOutputManager will choose CSV or JSON based on CTCC_OUTPUT_MODE
                output_manager = CTCCOutputManager()
                output_manager.add_bcr_metrics(bcr_results)
                output_manager.write_batch_summary()

                if output_mode == 'csv':
                    print("✅ BCR metrics added to batch_summary.csv")
                else:
                    print("✅ BCR metrics added to output")
            else:
                print("⚠️  BCR calculation completed but no results returned")

        except Exception as e:
            print(f"⚠️  BCR calculation failed: {e}")
            print("This does not affect the validity of the cost calculations above.")

        # If JSON output mode, aggregate and save final JSON results
        if output_mode == 'json':
            print("\n" + "=" * 80)
            print("AGGREGATING JSON OUTPUT...")
            print("=" * 80)

            try:
                from pathlib import Path
                import glob
                import json
                from json_output_manager import JSONOutputManager

                # Initialize JSON output manager
                json_manager = JSONOutputManager(scenario_id=scenario_id)

                # Aggregate JSON output files from subprocesses
                outputs_dir = Path("outputs")
                json_pattern = str(outputs_dir / f"json_output_{scenario_id}_*.json")
                json_files = glob.glob(json_pattern)

                print(f"Found {len(json_files)} JSON output files to aggregate")

                for json_file in json_files:
                    try:
                        json_manager.load_from_file(json_file)
                        print(f"  ✅ Loaded: {Path(json_file).name}")
                    except Exception as e:
                        print(f"  ⚠️  Failed to load {Path(json_file).name}: {str(e)}")

                # Add BCR metrics if available
                if bcr_results:
                    json_manager.add_bcr_metrics(bcr_results)

                # Get aggregated results
                results = json_manager.get_json_results()

                # Save final combined JSON output
                final_json_path = outputs_dir / f"ctcc_results_{scenario_id}.json"
                with open(final_json_path, 'w') as f:
                    json.dump(results, f, indent=2)

                print(f"\n✅ Final JSON output saved to: {final_json_path}")
                print(f"📊 Output size: {final_json_path.stat().st_size / 1024:.1f} KB")

                # Clean up individual subprocess JSON files
                for json_file in json_files:
                    try:
                        Path(json_file).unlink()
                        print(f"  🗑️  Cleaned up: {Path(json_file).name}")
                    except Exception:
                        pass  # Ignore cleanup errors

            except Exception as e:
                print(f"⚠️  JSON aggregation failed: {e}")
                import traceback
                traceback.print_exc()
            bcr_results = calculate_and_display_bcr(
                scenario_id,
                output_dir="outputs",
                no_emissions=args.no_emissions,
                no_linelosses=args.no_linelosses,
                capital_only=args.capital_only,
            )

            if bcr_results:
                # Update batch_summary.csv with BCR metrics
                csv_manager = CTCCOutputManager(
                    output_dir="outputs", scenario_id=scenario_id
                )
                csv_manager.add_bcr_metrics(bcr_results)
                csv_manager.write_batch_summary()
                if not args.simple:
                    print("✅ BCR metrics added to batch_summary.csv")
            else:
                if not args.simple:
                    print("⚠️  BCR calculation completed but no results returned")
                    print(f"   Scenario ID: {scenario_id}")
                    print(
                        "   This may indicate missing required columns in batch_summary.csv"
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
    else:
        if not args.simple:
            print("⚠️  Some calculations failed. Check the output above.")
        else:
            # In simple mode, show error even if quiet
            print("⚠️  Some calculations failed. BCR analysis may be incomplete.")


if __name__ == "__main__":
    main()
