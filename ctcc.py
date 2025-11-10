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
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'scripts'))
from bcr_calculator import calculate_and_display_bcr
from smart_output import CTCCOutputManager


def run_script(script_name, env=None):
    """
    Run a Python script and capture its output.

    Args:
        script_name (str): Name of the script to run
        env (dict): Optional environment variables to pass to the script

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
            print(f"✅ {script_name} completed successfully")
            print(result.stdout)
            return True
        else:
            print(f"❌ {script_name} failed with error:")
            print(result.stderr)
            return False
    except Exception as e:
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

    return parser.parse_args()


def main():
    """
    Main function to run all cost calculation scripts.
    """
    # Parse command line arguments
    args = parse_arguments()

    # Determine modes from arguments or environment variables
    # Command-line flags take precedence over environment variables
    if args.json:
        input_mode = 'json'
    else:
        input_mode = os.environ.get('CTCC_INPUT_MODE', 'yaml').lower()

    if args.json_out:
        output_mode = 'json'
    else:
        output_mode = os.environ.get('CTCC_OUTPUT_MODE', 'csv').lower()

    print("=" * 80)
    print("COMPREHENSIVE TRANSMISSION COST CALCULATOR (CTCC)")
    print("=" * 80)

    print(f"\n🔧 Input Mode: {input_mode.upper()}")
    print(f"🔧 Output Mode: {output_mode.upper()}")

    # Generate a single scenario_id for this entire run
    scenario_id = args.scenario_id or os.environ.get('CTCC_SCENARIO_ID')
    if not scenario_id:
        scenario_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        os.environ['CTCC_SCENARIO_ID'] = scenario_id

    print(f"📋 Scenario ID: {scenario_id}\n")

    # If JSON input mode, convert YAML to JSON first
    if input_mode == 'json':
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
                # Set environment variable for JSON data file location
                os.environ['CTCC_JSON_DATA_FILE'] = str(combined_json_file)
            else:
                print(f"❌ YAML to JSON conversion failed:")
                print(result.stderr)
                return
        except Exception as e:
            print(f"❌ Error during YAML to JSON conversion: {e}")
            return

        print("-" * 80)

    # List of scripts to run in order
    scripts = [
        "weighted_miles.py",
        "build_costs.py",
        "insurance_costs.py",
        "row_costs.py",
        "environmental_mitigation.py",
        "delay_costs.py",
        "wildfire_costs.py",
        "outage_costs.py",
        "congestion_curtailment_reduction.py",
        "energy_losses.py",
        "emissions.py",
        "line_loss_costs.py",
        "oandm.py",
        # Add more scripts as you create them
    ]

    successful_runs = 0
    total_runs = len(scripts)

    # Prepare environment variables for subprocess scripts
    env = os.environ.copy()
    env['CTCC_SCENARIO_ID'] = scenario_id
    env['CTCC_INPUT_MODE'] = input_mode
    env['CTCC_OUTPUT_MODE'] = output_mode  # Pass through the output mode to scripts
    if input_mode == 'json' and 'CTCC_JSON_DATA_FILE' in os.environ:
        env['CTCC_JSON_DATA_FILE'] = os.environ['CTCC_JSON_DATA_FILE']

    for script in scripts:
        print(f"\n🔄 Running {script}...")
        if run_script(script, env=env):
            successful_runs += 1
        print("-" * 60)

    print(
        f"\n📊 SUMMARY: {successful_runs}/{total_runs} scripts completed successfully"
    )

    if successful_runs == total_runs:
        print("🎉 All calculations completed successfully!")
        
        # Calculate and display BCR metrics
        print("\n" + "=" * 80)
        print("CALCULATING BENEFIT-COST RATIOS...")
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
    else:
        print("⚠️  Some calculations failed. Check the output above.")


if __name__ == "__main__":
    main()
