#!/usr/bin/env python3
"""
One-at-a-Time (OAT) Parameter Sweep Analysis for CTCC

This script performs one-at-a-time sensitivity analysis by:
- Reading PRCC results from sensitivity analysis to identify top parameters
- For each BCR metric, selecting top N parameters by absolute PRCC
- Sweeping each parameter through multiplier values (holding others at baseline)
- Generating plots showing BCR response curves

Usage:
    python oat_analysis.py --scenario "S1_Rural_Overhead_AC_460MW_Advanced_Conductor" --n_values 20 --top_n 6
"""

import argparse
import os
import sys
import shutil
import subprocess
import yaml
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import time
import uuid
from datetime import datetime
from pathlib import Path

# Import functions from sensitivity_analysis.py
# We'll need to import these or define them locally
# For now, we'll define what we need or import from sensitivity_analysis

# Try to import from sensitivity_analysis, fallback to local definitions
try:
    from sensitivity_analysis import (
        PARAM_DEFINITIONS,
        load_baseline_yamls,
        apply_sample_to_yamls,
        store_baseline_values,
        save_yamls_to_temp,
        remove_baseline_markers,
        calculate_bcr_fallback,
        read_results_by_scenario_id,
        get_nested_value,
    )
    from scripts.sensitivity_utils import (
        BCR_COLUMNS,
        run_ctcc_with_temp_yamls as _run_ctcc_with_temp_yamls_utils,
        deep_copy_yamls,
    )
except ImportError:
    # If import fails, we'll need to define these locally
    print("Error: Could not import from sensitivity_analysis.py")
    print("Make sure sensitivity_analysis.py is in the same directory")
    sys.exit(1)


# ============================================================================
# PRCC RESULTS LOADING
# ============================================================================


def load_prcc_results(sensitivity_results_dir):
    """
    Load PRCC results from sensitivity analysis output directory.

    Args:
        sensitivity_results_dir: Path to sensitivity analysis results directory

    Returns:
        DataFrame with PRCC values (index=parameters, columns=BCR metrics)
    """
    prcc_path = Path(sensitivity_results_dir) / "prcc_values.csv"

    if not prcc_path.exists():
        raise FileNotFoundError(
            f"PRCC results not found at {prcc_path}. "
            "Please run sensitivity analysis first to generate PRCC values."
        )

    prcc_df = pd.read_csv(prcc_path, index_col=0)
    return prcc_df


def get_top_parameters_per_bcr(prcc_df, top_n=6):
    """
    Get top N parameters for each BCR metric by absolute PRCC value.

    Args:
        prcc_df: DataFrame with PRCC values (index=parameters, columns=BCR metrics)
        top_n: Number of top parameters to select per BCR

    Returns:
        Dictionary: {bcr_metric: [list of top parameter names]}
    """
    top_params_per_bcr = {}

    for bcr_col in prcc_df.columns:
        # Get absolute PRCC values and sort
        abs_prcc = prcc_df[bcr_col].abs()
        top_params = abs_prcc.nlargest(top_n).index.tolist()
        top_params_per_bcr[bcr_col] = top_params

    return top_params_per_bcr


# ============================================================================
# PARAMETER SWEEP
# ============================================================================


def generate_parameter_values(param_name, param_def, n_values=20):
    """
    Generate parameter values for a parameter based on its range and type.

    Args:
        param_name: Name of the parameter
        param_def: Parameter definition from PARAM_DEFINITIONS
        n_values: Number of values to generate

    Returns:
        List of parameter values (multipliers for _mult parameters, direct values otherwise)
    """
    if param_name not in PARAM_DEFINITIONS:
        raise ValueError(f"Parameter {param_name} not found in PARAM_DEFINITIONS")

    if "range" not in param_def:
        raise ValueError(f"Parameter {param_name} does not have a range defined")

    min_val, max_val = param_def["range"]

    if min_val >= max_val:
        raise ValueError(
            f"Invalid range for parameter {param_name}: min ({min_val}) >= max ({max_val})"
        )

    # Check if this is a multiplier parameter
    is_multiplier = param_name.endswith("_mult")

    # Get parameter type (default to "linear" if not specified)
    param_type = param_def.get("type", "linear")

    # Generate values based on type
    if param_type == "integer":
        # Generate integer values
        values = np.linspace(min_val, max_val, n_values)
        # Convert to integers and ensure uniqueness
        int_values = np.unique(np.round(values).astype(int))
        # If we lost values due to rounding, try to get closer to n_values
        if len(int_values) < n_values:
            # Generate more values and take unique integers
            values = np.linspace(min_val, max_val, n_values * 2)
            int_values = np.unique(np.round(values).astype(int))
            # Take first n_values or all if fewer
            if len(int_values) > n_values:
                # Select evenly spaced indices
                indices = np.linspace(0, len(int_values) - 1, n_values, dtype=int)
                int_values = int_values[indices]
        parameter_values = int_values.tolist()
    elif param_type == "log":
        # Generate log-spaced values
        if min_val <= 0:
            raise ValueError(
                f"Log parameter {param_name} must have positive range, got ({min_val}, {max_val})"
            )
        parameter_values = np.logspace(
            np.log10(min_val), np.log10(max_val), n_values
        ).tolist()
    else:  # linear (default)
        # Generate linearly spaced values
        parameter_values = np.linspace(min_val, max_val, n_values).tolist()

    return parameter_values


def run_single_parameter_sweep(
    param_name, parameter_values, base_dir, baseline_yamls, baselines
):
    """
    Run parameter sweep for a single parameter.

    Args:
        param_name: Name of the parameter to sweep
        parameter_values: List of parameter values to test (multipliers or direct values)
        base_dir: Base directory of the project (Path or str)
        baseline_yamls: Dictionary of baseline YAML files
        baselines: Dictionary of baseline values for multiplier parameters

    Returns:
        List of dictionaries with results: [{parameter_value, bcr_system, bcr_capital, ...}, ...]
    """
    results = []
    base_dir = Path(base_dir)  # Ensure it's a Path object

    for param_value in parameter_values:
        # Create sample dictionary with only this parameter varied
        sample_dict = {param_name: param_value}

        # Create temporary YAML directory with unique name per parameter value
        # Format value appropriately for directory name
        if isinstance(param_value, float):
            value_str = f"{param_value:.3f}"
        else:
            value_str = str(param_value)
        temp_yaml_dir = base_dir / f"yamls_oat_{param_name}_{value_str}"
        if temp_yaml_dir.exists():
            shutil.rmtree(temp_yaml_dir)
        temp_yaml_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Copy baseline YAMLs
            yaml_files_copy = deep_copy_yamls(baseline_yamls)

            # Apply parameter value
            apply_sample_to_yamls(
                yaml_files_copy, sample_dict, PARAM_DEFINITIONS, baselines
            )

            # Save to temp directory
            save_yamls_to_temp(yaml_files_copy, temp_yaml_dir)

            # Run CTCC with unique scenario ID
            scenario_id = f"oat_{param_name}_{value_str}_{uuid.uuid4().hex[:8]}"
            result_dict, error = run_ctcc_with_temp_yamls(
                str(temp_yaml_dir), str(base_dir), scenario_id
            )

            if result_dict and error is None:
                # Extract BCR values
                # Check if BCR columns exist, use fallback if needed
                missing_bcr = [col for col in BCR_COLUMNS if col not in result_dict]
                if missing_bcr:
                    fallback_bcr = calculate_bcr_fallback(result_dict)
                    if fallback_bcr:
                        result_dict.update(fallback_bcr)

                result_row = {
                    "parameter_name": param_name,
                    "parameter_value": param_value,
                }

                for bcr_col in BCR_COLUMNS:
                    result_row[bcr_col] = result_dict.get(bcr_col, None)

                results.append(result_row)
            else:
                # Log error but continue
                value_str = (
                    f"{param_value:.3f}"
                    if isinstance(param_value, float)
                    else str(param_value)
                )
                print(
                    f"  Warning: CTCC failed for {param_name} at value {value_str}: {error}"
                )

        except Exception as e:
            value_str = (
                f"{param_value:.3f}"
                if isinstance(param_value, float)
                else str(param_value)
            )
            print(f"  Error processing {param_name} at value {value_str}: {str(e)}")
        finally:
            # Clean up temp directory
            if temp_yaml_dir.exists():
                shutil.rmtree(temp_yaml_dir)

    return results


# run_ctcc_with_temp_yamls is now imported from scripts.sensitivity_utils
# Create a wrapper that matches the original function signature for oat_analysis
def run_ctcc_with_temp_yamls(temp_yaml_dir, base_dir, scenario_id):
    """
    Wrapper for run_ctcc_with_temp_yamls that provides the function signature
    expected by oat_analysis.py.
    """
    return _run_ctcc_with_temp_yamls_utils(
        temp_yaml_dir,
        base_dir,
        scenario_id,
        ctcc_args=["--simple"],
        use_env_dict=False,
        read_results_by_scenario_id_func=read_results_by_scenario_id,
        calculate_bcr_fallback_func=calculate_bcr_fallback,
    )


# ============================================================================
# PLOTTING
# ============================================================================


def generate_oat_plots(
    results_df, bcr_metric, top_params, prcc_values, output_path, baseline_yamls
):
    """
    Generate OAT plots for a BCR metric.

    Args:
        results_df: DataFrame with results (columns: parameter_name, parameter_value, bcr_*)
        bcr_metric: Name of the BCR metric to plot
        top_params: List of top parameter names (up to 6)
        prcc_values: Series of PRCC values for this BCR metric
        output_path: Path to save the plot
        baseline_yamls: Dictionary of baseline YAML files
    """
    n_params = len(top_params)
    if n_params == 0:
        return

    # Create figure with 6 subplots (2 rows, 3 columns)
    fig, axes = plt.subplots(2, 3, figsize=(18, 12))
    axes = axes.flatten()

    for idx, param_name in enumerate(top_params):
        if idx >= 6:
            break

        ax = axes[idx]

        # Filter results for this parameter
        param_results = results_df[results_df["parameter_name"] == param_name].copy()
        param_results = param_results.sort_values("parameter_value")

        if len(param_results) > 0:
            # Plot BCR vs parameter value
            ax.plot(
                param_results["parameter_value"],
                param_results[bcr_metric],
                "b-",
                linewidth=2,
                label=bcr_metric,
            )

            # Add baseline reference line
            # For multipliers: baseline is 1.0
            # For direct values: get actual baseline from YAML files
            is_multiplier = param_name.endswith("_mult")
            if is_multiplier:
                baseline_value = 1.0
            else:
                # For direct values, read actual baseline value from YAML files
                baseline_value = None
                if param_name in PARAM_DEFINITIONS:
                    param_def = PARAM_DEFINITIONS[param_name]
                    yaml_file_name = param_def.get("yaml_file")
                    if yaml_file_name and yaml_file_name in baseline_yamls:
                        baseline_value = get_nested_value(
                            baseline_yamls[yaml_file_name],
                            param_def.get("yaml_path", []),
                        )

                    # Fallback to midpoint of range if value not found
                    if baseline_value is None and "range" in param_def:
                        min_val, max_val = param_def["range"]
                        baseline_value = (min_val + max_val) / 2

            if baseline_value is not None:
                ax.axvline(
                    x=baseline_value,
                    color="r",
                    linestyle="--",
                    linewidth=1,
                    alpha=0.7,
                    label="Baseline",
                )

            # Get PRCC value for this parameter
            prcc_val = prcc_values.get(param_name, 0)
            prcc_sign = "+" if prcc_val >= 0 else ""

            # Set title with parameter name and PRCC
            param_desc = PARAM_DEFINITIONS.get(param_name, {}).get(
                "description", param_name
            )
            ax.set_title(
                f"{param_desc}\nPRCC: {prcc_sign}{prcc_val:.3f}",
                fontsize=10,
                fontweight="bold",
            )

            # Set x-axis label based on parameter type
            if is_multiplier:
                ax.set_xlabel("Multiplier Value", fontsize=9)
            else:
                ax.set_xlabel("Parameter Value", fontsize=9)
            ax.set_ylabel(f"{bcr_metric}", fontsize=9)
            ax.grid(True, alpha=0.3)
            ax.legend(fontsize=8)

    # Hide unused subplots
    for idx in range(n_params, 6):
        axes[idx].axis("off")

    # Main title
    fig.suptitle(
        f"One-at-a-Time Analysis: {bcr_metric}",
        fontsize=14,
        fontweight="bold",
        y=0.995,
    )

    plt.tight_layout(rect=[0, 0, 1, 0.98])
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()


# ============================================================================
# MAIN WORKFLOW
# ============================================================================


def main():
    parser = argparse.ArgumentParser(
        description="One-at-a-Time (OAT) Parameter Sweep Analysis for CTCC"
    )
    parser.add_argument(
        "--scenario",
        type=str,
        required=True,
        help="Scenario ID or path to sensitivity results directory",
    )
    parser.add_argument(
        "--n_values",
        type=int,
        default=20,
        help="Number of multiplier values per parameter (default: 20)",
    )
    parser.add_argument(
        "--top_n",
        type=int,
        default=6,
        help="Number of top parameters to analyze per BCR (default: 6)",
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default=None,
        help="Output directory for results (default: oat_results/scenario_<ID>)",
    )

    args = parser.parse_args()

    # Determine base directory (where script is located)
    base_dir = Path(__file__).parent.absolute()

    # Determine sensitivity results directory
    scenario_id = args.scenario
    sensitivity_results_dir = (
        base_dir / "sensitivity_results" / f"scenario_{scenario_id}"
    )

    if not sensitivity_results_dir.exists():
        # Try as direct path
        if Path(scenario_id).exists():
            sensitivity_results_dir = Path(scenario_id)
        else:
            print(
                f"Error: Sensitivity results directory not found: {sensitivity_results_dir}"
            )
            sys.exit(1)

    # Determine output directory
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        output_dir = base_dir / "oat_results" / f"scenario_{scenario_id}"

    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("ONE-AT-A-TIME (OAT) PARAMETER SWEEP ANALYSIS")
    print("=" * 80)
    print(f"Scenario: {scenario_id}")
    print(f"Sensitivity results: {sensitivity_results_dir}")
    print(f"Output directory: {output_dir}")
    print(f"Values per parameter: {args.n_values}")
    print(f"Top parameters per BCR: {args.top_n}")
    print()

    # Load PRCC results
    print("Loading PRCC results...")
    try:
        prcc_df = load_prcc_results(sensitivity_results_dir)
        print(
            f"  Loaded PRCC results: {len(prcc_df)} parameters, {len(prcc_df.columns)} BCR metrics"
        )
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)

    # Get top parameters per BCR
    print("Identifying top parameters per BCR metric...")
    top_params_per_bcr = get_top_parameters_per_bcr(prcc_df, top_n=args.top_n)

    for bcr_metric, params in top_params_per_bcr.items():
        print(f"  {bcr_metric}: {', '.join(params)}")

    print()

    # Load baseline YAMLs
    print("Loading baseline YAML files...")
    yaml_dir = base_dir / "yamls"
    if not yaml_dir.exists():
        print(f"Error: YAML directory not found: {yaml_dir}")
        sys.exit(1)

    baseline_yamls = load_baseline_yamls(yaml_dir)
    print(f"  Loaded {len(baseline_yamls)} YAML files")

    # Store baseline values
    print("Storing baseline values...")
    baselines = store_baseline_values(baseline_yamls, PARAM_DEFINITIONS)
    print(f"  Stored baselines for {len(baselines)} multiplier parameters")
    print()

    # Collect all parameter sweeps to run
    all_sweeps = []
    for bcr_metric, top_params in top_params_per_bcr.items():
        for param_name in top_params:
            if param_name not in PARAM_DEFINITIONS:
                print(f"  Warning: Skipping {param_name} (not in PARAM_DEFINITIONS)")
                continue

            param_def = PARAM_DEFINITIONS[param_name]

            # Check if parameter has a range (required for OAT analysis)
            if "range" not in param_def:
                print(f"  Warning: Skipping {param_name} (no range defined)")
                continue

            try:
                parameter_values = generate_parameter_values(
                    param_name, param_def, n_values=args.n_values
                )
                all_sweeps.append((bcr_metric, param_name, parameter_values))
            except Exception as e:
                print(
                    f"  Warning: Skipping {param_name} (error generating values: {str(e)})"
                )
                continue

    total_runs = sum(len(param_vals) for _, _, param_vals in all_sweeps)
    print(f"Total parameter sweeps to run: {len(all_sweeps)}")
    print(f"Total CTCC runs: {total_runs}")
    print()

    # Run parameter sweeps
    print("Running parameter sweeps...")
    start_time = time.time()

    all_results = []
    completed = 0
    for bcr_metric, param_name, parameter_values in all_sweeps:
        print(f"  Sweeping {param_name} for {bcr_metric}...")
        results = run_single_parameter_sweep(
            param_name,
            parameter_values,
            base_dir,
            baseline_yamls,
            baselines,
        )
        all_results.extend(results)
        completed += len(parameter_values)
        print(f"    Completed {completed}/{total_runs} runs")

    elapsed_time = time.time() - start_time
    print(f"\nCompleted all sweeps in {elapsed_time:.1f} seconds")
    print()

    # Convert results to DataFrame
    if len(all_results) == 0:
        print("Error: No results collected. Check CTCC runs for errors.")
        sys.exit(1)

    results_df = pd.DataFrame(all_results)
    print(f"Collected {len(results_df)} result rows")

    # Save results per BCR
    print("\nSaving results...")

    for bcr_metric in prcc_df.columns:
        # Filter results for parameters relevant to this BCR
        top_params = top_params_per_bcr[bcr_metric]
        bcr_results = results_df[results_df["parameter_name"].isin(top_params)].copy()

        if len(bcr_results) > 0:
            # Save CSV
            csv_path = output_dir / f"oat_results_{bcr_metric}.csv"
            bcr_results.to_csv(csv_path, index=False)
            print(f"  Saved {csv_path} ({len(bcr_results)} rows)")

            # Generate plot
            plot_path = output_dir / f"oat_{bcr_metric}_plot1.png"
            prcc_series = prcc_df[bcr_metric]
            generate_oat_plots(
                bcr_results,
                bcr_metric,
                top_params,
                prcc_series,
                plot_path,
                baseline_yamls,
            )
            print(f"  Saved {plot_path}")

    # Save combined summary
    summary_path = output_dir / "oat_summary.csv"
    results_df.to_csv(summary_path, index=False)
    print(f"  Saved {summary_path}")

    print("\n" + "=" * 80)
    print("OAT ANALYSIS COMPLETE")
    print("=" * 80)
    print(f"Results saved to: {output_dir}")


if __name__ == "__main__":
    main()
