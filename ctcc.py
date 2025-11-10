# Author: Andrew Igdal
# Date: 2025-10-21
# Description: Comprehensive Transmission Cost Calculator (CTCC) - Main Script
#              Orchestrates all individual cost calculation modules

import subprocess
import sys
import os
from datetime import datetime

# Add scripts directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "scripts"))
from bcr_calculator import calculate_and_display_bcr
from csv_output_manager import CTCCOutputManager


def run_script(script_name):
    """
    Run a Python script and capture its output.

    Args:
        script_name (str): Name of the script to run

    Returns:
        bool: True if successful, False if error
    """
    try:
        result = subprocess.run(
            [sys.executable, script_name], capture_output=True, text=True, cwd="scripts"
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


def main():
    """
    Main function to run all cost calculation scripts.
    """
    print("=" * 80)
    print("COMPREHENSIVE TRANSMISSION COST CALCULATOR (CTCC)")
    print("=" * 80)

    # Generate a single scenario_id for this entire run
    scenario_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    os.environ["CTCC_SCENARIO_ID"] = scenario_id
    print(f"\n📋 Scenario ID: {scenario_id}\n")

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

    for script in scripts:

        print(f"\n🔄 Running {script}...")
        if run_script(script):
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
                # Update batch_summary.csv with BCR metrics
                csv_manager = CTCCOutputManager(
                    output_dir="outputs", scenario_id=scenario_id
                )
                csv_manager.add_bcr_metrics(bcr_results)
                csv_manager.write_batch_summary()
                print("✅ BCR metrics added to batch_summary.csv")
            else:
                print("⚠️  BCR calculation completed but no results returned")
                print(f"   Scenario ID: {scenario_id}")
                print(
                    "   This may indicate missing required columns in batch_summary.csv"
                )

        except Exception as e:
            import traceback

            print(f"⚠️  BCR calculation failed: {e}")
            print(f"   Scenario ID: {scenario_id}")
            print("   Full error traceback:")
            traceback.print_exc()
            print(
                "   This does not affect the validity of the cost calculations above."
            )
    else:
        print("⚠️  Some calculations failed. Check the output above.")


if __name__ == "__main__":
    main()
