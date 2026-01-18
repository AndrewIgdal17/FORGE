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
        # Pass environment variables explicitly to ensure subprocess scripts can access them
        env = os.environ.copy()
        result = subprocess.run(
            [sys.executable, script_name], capture_output=True, text=True, cwd="scripts", env=env
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


def write_final_json_output(
    aggregator, bcr_results: dict, scenario_id: str, output_dir: str = "outputs"
):
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

    # Load YAML config for Primary BCR (YAML overrides command-line flags)
    try:
        from scripts.yaml_loaders import load_primary_bcr_config

        yaml_config = load_primary_bcr_config()

        # YAML overrides command-line flags
        if yaml_config:
            # Convert YAML enabled flags to ctcc.py flags (invert logic)
            # Operational
            if not yaml_config.get("operational", {}).get("oandm", True):
                args.no_oandm = True
            if not yaml_config.get("operational", {}).get("insurance", True):
                args.no_insurance = True
            if not yaml_config.get("operational", {}).get("delay_costs", True):
                args.no_delay_costs = True

            # Risk
            if not yaml_config.get("risk", {}).get("wildfire", True):
                args.no_wildfire = True
            if not yaml_config.get("risk", {}).get("outages", True):
                args.no_outages = True

            # Energy
            if not yaml_config.get("energy", {}).get("line_losses", True):
                args.no_linelosses = True
            if not yaml_config.get("energy", {}).get("emissions", True):
                args.no_emissions = True

            # Benefits
            if not yaml_config.get("benefits", {}).get("congestion", True):
                args.no_congestion = True
            if not yaml_config.get("benefits", {}).get("curtailment", True):
                args.no_curtailment = True
    except (FileNotFoundError, ImportError):
        # YAML doesn't exist or can't be loaded - use command-line flags only
        pass
    except Exception as e:
        # Any other error loading YAML config - use command-line flags only
        if not args.simple:
            print(f"Warning: Could not load Primary BCR config from YAML: {e}")
            print("  Using command-line flags only.")

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
            if not args.simple:
                print()
                print("CALCULATING BENEFIT-COST RATIOS...")
                print("=" * 80)
            try:
                bcr_results = calculate_and_display_bcr(
                    scenario_id,
                    output_dir="outputs",
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
            except Exception as e:
                import traceback
                if not args.simple:
                    print(f"⚠️  BCR calculation failed: {e}")
                    print(f"   Scenario ID: {scenario_id}")
                    print("   Full error traceback:")
                    traceback.print_exc()
                    print("   This does not affect the validity of the cost calculations above.")
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
                try:
                    # Extract data from aggregator in format BCR calculator expects
                    aggregator.calculate_summary()  # Ensure summary is calculated
                    json_results = aggregator.get_json_results()
                    
                    # Convert JSON structure to flat dict for BCR calculator
                    bcr_data = {}
                    # Extract benefits
                    congestion_curtailment = json_results.get("benefits", {}).get("congestion_curtailment", {})
                    bcr_data["congestion_benefit_pv"] = congestion_curtailment.get("congestion_benefit_pv", 0) or 0
                    bcr_data["curtailment_benefit_pv"] = congestion_curtailment.get("curtailment_benefit_pv", 0) or 0
                    bcr_data["congestion_benefit_nominal"] = congestion_curtailment.get("congestion_benefit_nominal", 0) or 0
                    bcr_data["curtailment_benefit_nominal"] = congestion_curtailment.get("curtailment_benefit_nominal", 0) or 0
                    bcr_data["congestion_benefit_haircut_pv"] = congestion_curtailment.get("congestion_benefit_haircut_pv", 0) or 0
                    bcr_data["curtailment_benefit_haircut_pv"] = congestion_curtailment.get("curtailment_benefit_haircut_pv", 0) or 0
                    
                    revenue = json_results.get("benefits", {}).get("revenue", {})
                    bcr_data["revenue_pv"] = revenue.get("revenue_pv", 0) or 0
                    bcr_data["revenue_nominal"] = revenue.get("revenue_nominal", 0) or 0
                    
                    # Extract costs from summary
                    summary = json_results.get("summary", {})
                    bcr_data["build_cost_pv"] = json_results.get("costs", {}).get("build", {}).get("total_pv", 0) or 0
                    bcr_data["row_cost_pv"] = json_results.get("costs", {}).get("row", {}).get("total_pv", 0) or 0
                    bcr_data["env_mitigation_pv"] = json_results.get("costs", {}).get("environmental", {}).get("total_pv", 0) or 0
                    bcr_data["capital_costs_pv"] = summary.get("total_capital_pv", 0) or 0
                    bcr_data["oandm_pv"] = json_results.get("costs", {}).get("oandm", {}).get("total_pv", 0) or 0
                    bcr_data["insurance_pv"] = json_results.get("costs", {}).get("insurance", {}).get("pv_total", 0) or 0
                    bcr_data["operational_costs_pv"] = summary.get("total_operational_pv", 0) or 0
                    bcr_data["line_loss_cost_pv"] = json_results.get("costs", {}).get("line_loss", {}).get("total_pv", 0) or 0
                    bcr_data["emissions_cost_pv"] = json_results.get("costs", {}).get("emissions", {}).get("total_pv", 0) or 0
                    bcr_data["energy_emissions_costs_pv"] = summary.get("total_operational_pv", 0) or 0  # Approximate
                    bcr_data["wildfire_pv"] = json_results.get("costs", {}).get("wildfire", {}).get("pv_cost", 0) or 0
                    bcr_data["outage_pv"] = json_results.get("costs", {}).get("outage", {}).get("pv_cost", 0) or 0
                    bcr_data["risk_costs_pv"] = summary.get("total_risk_pv", 0) or 0
                    bcr_data["delay_cost_pv"] = json_results.get("costs", {}).get("delay", {}).get("total_pv", 0) or 0
                    bcr_data["delay_cost_nominal"] = json_results.get("costs", {}).get("delay", {}).get("total_nominal", 0) or 0
                    # Extract congestion/curtailment delay costs from congestion_curtailment benefits section
                    congestion_curtailment = json_results.get("benefits", {}).get("congestion_curtailment", {})
                    bcr_data["congestion_delay_cost_pv"] = congestion_curtailment.get("congestion_delay_cost_pv", 0) or 0
                    bcr_data["congestion_delay_cost_nominal"] = congestion_curtailment.get("congestion_delay_cost_nominal", 0) or 0
                    bcr_data["curtailment_delay_cost_pv"] = congestion_curtailment.get("curtailment_delay_cost_pv", 0) or 0
                    bcr_data["curtailment_delay_cost_nominal"] = congestion_curtailment.get("curtailment_delay_cost_nominal", 0) or 0
                    bcr_data["residual_congestion_pv"] = congestion_curtailment.get("residual_congestion_pv", 0) or 0
                    bcr_data["residual_congestion_nominal"] = congestion_curtailment.get("residual_congestion_nominal", 0) or 0
                    bcr_data["total_costs_pv"] = summary.get("grand_total_cost_pv", 0) or 0
                    
                    # Calculate BCR using the helper functions
                    from bcr_calculator import calculate_benefits, calculate_costs, calculate_bcr_metrics
                    benefits = calculate_benefits(bcr_data)
                    costs = calculate_costs(bcr_data)
                    bcr_metrics = calculate_bcr_metrics(
                        benefits, costs,
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
                    bcr_results = {**benefits, **costs, **bcr_metrics}
                except Exception as e:
                    import traceback
                    if not args.simple:
                        print(f"⚠️  BCR calculation failed: {e}")
                        traceback.print_exc()
                    bcr_results = None
                
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
                # Calculate grand totals (capital AFUDC, grand total AFUDC, etc.)
                csv_manager.calculate_grand_totals()
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
