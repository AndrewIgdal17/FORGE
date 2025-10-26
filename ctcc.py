# Author: Andrew Igdal
# Date: 2025-10-21
# Description: Comprehensive Transmission Cost Calculator (CTCC) - Main Script
#              Orchestrates all individual cost calculation modules

import subprocess
import sys
import os


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

    # List of scripts to run in order
    scripts = [
        "weighted_miles.py",
        "row_costs.py",
        "delay_costs.py",
        "congestion_curtailment_reduction.py",
        "energy_losses.py",
        "emissions.py",
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
    else:
        print("⚠️  Some calculations failed. Check the output above.")


if __name__ == "__main__":
    main()
