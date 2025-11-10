#!/usr/bin/env python3
"""
LHS Sensitivity Analysis for Comprehensive Transmission Cost Calculator (CTCC)

This script performs Latin Hypercube Sampling (LHS) to systematically vary
parameters and analyze their impact on project economics (BCR, costs, benefits).

Usage:
    python sensitivity_analysis.py --scenario "1.1_rural_overhead" --n_samples 300 --seed 42
"""

import argparse
import os
import sys
import shutil
import subprocess
import yaml
import numpy as np
import pandas as pd
from scipy.stats import qmc
from scipy.stats import spearmanr
from scipy import stats
import matplotlib.pyplot as plt
import time
from datetime import datetime
from pathlib import Path


# ============================================================================
# PARAMETER DEFINITIONS
# ============================================================================

PARAM_DEFINITIONS = {
    # Core Economic/Technical (10)
    "real_wacc_mult": {
        "type": "linear",
        "range": (0.7, 1.4),
        "yaml_file": "03_financing.yaml",
        "yaml_path": [
            "financial",
            "wacc_nominal",
        ],  # Will calculate real WACC from nominal
        "description": "Real WACC multiplier",
    },
    "delay_years": {
        "type": "integer",
        "range": (0, 20),
        "yaml_file": "01_project_technical_details.yaml",
        "yaml_path": ["timeline", "delay_years"],
        "description": "Permitting/regulatory delay (years)",
    },
    "construction_years": {
        "type": "linear",
        "range": (0.5, 3.0),
        "yaml_file": "01_project_technical_details.yaml",
        "yaml_path": ["timeline", "construction_years"],
        "description": "Construction duration (years)",
    },
    "line_utilization_mult": {
        "type": "linear",
        "range": (0.8, 1.1),
        "yaml_file": "01_project_technical_details.yaml",
        "yaml_path": ["project", "line_utilization"],
        "description": "Line utilization multiplier",
    },
    "wildfire_ignition_rate_mult": {
        "type": "log",
        "range": (0.3, 3.0),
        "yaml_file": "06_wildfire_costs.yaml",
        "yaml_path": ["wildfire", "ignition_rates_by_terrain"],
        "description": "Wildfire ignition rate multiplier (all terrains)",
    },
    "congestion_price_mult": {
        "type": "linear",
        "range": (0.7, 1.5),
        "yaml_file": "17_congestion_reductions.yaml",
        "yaml_path": [
            "greenfield_congestion_reductions",
            "costs",
            "average_congestion_price",
        ],
        "description": "Congestion price multiplier",
    },
    "electricity_price_mult": {
        "type": "linear",
        "range": (0.7, 1.5),
        "yaml_file": "01_project_technical_details.yaml",
        "yaml_path": ["project", "baseline_electricity_price_per_mwh"],
        "description": "Electricity price multiplier",
    },
    "environmental_mitigation_cost_mult": {
        "type": "linear",
        "range": (0.7, 1.5),
        "yaml_file": "09_environmental_mitigation.yaml",
        "yaml_path": ["environmental_mitigation", "base_mitigation_cost_per_acre"],
        "description": "Environmental mitigation cost multiplier (all construction types and terrains)",
    },
    "project_lifetime": {
        "type": "integer",
        "range": (40, 60),
        "yaml_file": "01_project_technical_details.yaml",
        "yaml_path": ["timeline", "project_lifetime"],
        "description": "Project lifetime (years)",
    },
    "social_discount_rate_mult": {
        "type": "linear",
        "range": (0.7, 1.4),
        "yaml_file": "03_financing.yaml",
        "yaml_path": ["financial", "social_discount_rate"],
        "description": "Social discount rate multiplier",
    },
    "wacc_nominal_mult": {
        "type": "linear",
        "range": (0.7, 1.4),
        "yaml_file": "03_financing.yaml",
        "yaml_path": ["financial", "wacc_nominal"],
        "description": "WACC nominal multiplier",
    },
    # ROW Cost Zones (5) - using zone_1 through zone_5 as representative
    "row_cost_mult_forested": {
        "type": "linear",
        "range": (0.7, 1.5),
        "yaml_file": "11_project_row_details.yaml",
        "yaml_path": ["right_of_way", "zone_1"],  # zone_1 represents forested
        "description": "ROW cost multiplier (forested/zone_1)",
    },
    "row_cost_mult_scrubbed_flat": {
        "type": "linear",
        "range": (0.7, 1.5),
        "yaml_file": "11_project_row_details.yaml",
        "yaml_path": ["right_of_way", "zone_2"],  # zone_2 represents scrubbed flat
        "description": "ROW cost multiplier (scrubbed flat/zone_2)",
    },
    "row_cost_mult_wetland": {
        "type": "linear",
        "range": (0.7, 1.5),
        "yaml_file": "11_project_row_details.yaml",
        "yaml_path": ["right_of_way", "zone_3"],  # zone_3 represents wetland
        "description": "ROW cost multiplier (wetland/zone_3)",
    },
    "row_cost_mult_farmland": {
        "type": "linear",
        "range": (0.7, 1.5),
        "yaml_file": "11_project_row_details.yaml",
        "yaml_path": ["right_of_way", "zone_4"],  # zone_4 represents farmland
        "description": "ROW cost multiplier (farmland/zone_4)",
    },
    "row_cost_mult_rolling_hills": {
        "type": "linear",
        "range": (0.7, 1.5),
        "yaml_file": "11_project_row_details.yaml",
        "yaml_path": ["right_of_way", "zone_5"],  # zone_5 represents rolling hills
        "description": "ROW cost multiplier (rolling hills/zone_5)",
    },
    # Operational/Risk (5)
    "outage_rate_mult": {
        "type": "linear",
        "range": (0.5, 2.0),
        "yaml_file": "07_outage_costs.yaml",
        "yaml_path": ["outage", "outage_rates"],
        "description": "Outage rate multiplier (all construction types and terrains)",
    },
    "veg_om_per_mile_mult": {
        "type": "linear",
        "range": (0.6, 1.6),
        "yaml_file": "12_project_om_vegetation_management.yaml",
        "yaml_path": ["vegetation_management_om_costs"],
        "description": "Vegetation O&M cost multiplier (all construction types and terrains)",
    },
    "labor_cost_mult": {
        "type": "linear",
        "range": (0.8, 1.3),
        "yaml_file": "10_project_category_build_costs.yaml",
        "yaml_path": ["project_categories_build_costs"],
        "description": "Labor cost multiplier (affects structure costs via build costs)",
    },
    "materials_cost_mult": {
        "type": "linear",
        "range": (0.8, 1.3),
        "yaml_file": "10_project_category_build_costs.yaml",
        "yaml_path": ["project_categories_build_costs"],
        "description": "Materials cost multiplier (affects conductor costs via build costs)",
    },
    "outage_growth_rate_mult": {
        "type": "linear",
        "range": (0.5, 2.0),
        "yaml_file": "07_outage_costs.yaml",
        "yaml_path": ["outage", "risk_growth_rate"],
        "description": "Outage risk growth rate multiplier",
    },
}


# ============================================================================
# LHS SAMPLING
# ============================================================================


def generate_lhs_samples(n_samples, param_definitions, seed=42):
    """
    Generate Latin Hypercube samples for all parameters.

    Args:
        n_samples: Number of samples to generate
        param_definitions: Dictionary of parameter definitions
        seed: Random seed for reproducibility

    Returns:
        DataFrame with N samples × d parameters (values in [0,1])
    """
    n_params = len(param_definitions)
    param_names = list(param_definitions.keys())

    # Generate LHS samples in [0,1]
    sampler = qmc.LatinHypercube(d=n_params, seed=seed)
    samples = sampler.random(n=n_samples)

    # Create DataFrame
    df = pd.DataFrame(samples, columns=param_names)
    return df


def map_samples_to_ranges(samples_df, param_definitions):
    """
    Map LHS samples from [0,1] to actual parameter ranges.

    Args:
        samples_df: DataFrame with samples in [0,1]
        param_definitions: Dictionary of parameter definitions

    Returns:
        DataFrame with actual parameter values
    """
    mapped_df = samples_df.copy()

    for param_name, param_def in param_definitions.items():
        sample_values = mapped_df[param_name].values
        min_val, max_val = param_def["range"]

        if param_def["type"] == "linear":
            # Linear mapping: [0,1] -> [min_val, max_val]
            mapped_values = min_val + sample_values * (max_val - min_val)
        elif param_def["type"] == "log":
            # Log scale: sample uniformly in log space
            log_min = np.log10(min_val)
            log_max = np.log10(max_val)
            log_values = log_min + sample_values * (log_max - log_min)
            mapped_values = 10**log_values
        elif param_def["type"] == "integer":
            # Integer: round after linear mapping
            mapped_values = min_val + sample_values * (max_val - min_val)
            mapped_values = np.round(mapped_values).astype(int)
        else:
            raise ValueError(f"Unknown parameter type: {param_def['type']}")

        mapped_df[param_name] = mapped_values

    return mapped_df


# ============================================================================
# YAML MANIPULATION
# ============================================================================


def load_baseline_yamls(yaml_dir):
    """Load all baseline YAML files."""
    yaml_files = {}
    yaml_path = Path(yaml_dir)

    for yaml_file in yaml_path.glob("*.yaml"):
        with open(yaml_file, "r") as f:
            yaml_files[yaml_file.name] = yaml.load(f, Loader=yaml.FullLoader)

    return yaml_files


def apply_multiplier_to_nested_dict(data, path, multiplier, is_baseline=False):
    """
    Apply multiplier to a nested dictionary value.

    Args:
        data: Nested dictionary
        path: List of keys to traverse (e.g., ['project', 'line_utilization'])
        multiplier: Multiplier to apply
        is_baseline: If True, store baseline value first (for nested dicts like wildfire rates)
    """
    current = data
    for key in path[:-1]:
        if key not in current:
            current[key] = {}
        current = current[key]

    final_key = path[-1]

    # Handle special cases
    if isinstance(current.get(final_key), dict):
        # If it's a dictionary (like ignition_rates_by_terrain), multiply all values
        for subkey in current[final_key]:
            if isinstance(current[final_key][subkey], (int, float)):
                if is_baseline:
                    # Store baseline on first call
                    if f"_baseline_{subkey}" not in current[final_key]:
                        current[final_key][f"_baseline_{subkey}"] = current[final_key][
                            subkey
                        ]
                    base_val = current[final_key][f"_baseline_{subkey}"]
                else:
                    base_val = current[final_key].get(
                        f"_baseline_{subkey}", current[final_key][subkey]
                    )
                current[final_key][subkey] = base_val * multiplier
    elif isinstance(current.get(final_key), list):
        # If it's a list (like outage_rates.overhead), multiply all values
        for item in current[final_key]:
            if isinstance(item, dict):
                for subkey in item:
                    if isinstance(item[subkey], (int, float)):
                        if is_baseline:
                            item[f"_baseline_{subkey}"] = item[subkey]
                        base_val = item.get(f"_baseline_{subkey}", item[subkey])
                        item[subkey] = base_val * multiplier
    else:
        # Simple value
        if is_baseline:
            if f"_baseline_{final_key}" not in current:
                current[f"_baseline_{final_key}"] = current.get(final_key, 0)
            base_val = current[f"_baseline_{final_key}"]
        else:
            base_val = current.get(f"_baseline_{final_key}", current.get(final_key, 0))
        current[final_key] = base_val * multiplier


def get_nested_value(data, path):
    """Get value from nested dictionary using path."""
    current = data
    for key in path:
        if key in current:
            current = current[key]
        else:
            return None
    return current


def set_nested_value(data, path, value):
    """Set value in nested dictionary using path."""
    current = data
    for key in path[:-1]:
        if key not in current:
            current[key] = {}
        current = current[key]
    current[path[-1]] = value


def store_baseline_values(yaml_files, param_definitions):
    """
    Store baseline values for all multiplier parameters.
    This should be called once before applying any samples.
    """
    baselines = {}

    for param_name, param_def in param_definitions.items():
        if not param_name.endswith("_mult"):
            continue

        yaml_file_name = param_def["yaml_file"]
        if yaml_file_name not in yaml_files:
            continue

        current_value = get_nested_value(
            yaml_files[yaml_file_name], param_def["yaml_path"]
        )

        if current_value is not None:
            if isinstance(current_value, dict):
                # For nested dicts, store the entire structure
                baselines[param_name] = yaml.load(
                    yaml.dump(current_value), Loader=yaml.FullLoader
                )  # Deep copy
            else:
                baselines[param_name] = current_value

    return baselines


def apply_sample_to_yamls(yaml_files, sample_dict, param_definitions, baselines):
    """
    Apply a sample's parameter values to YAML files.

    Args:
        yaml_files: Dictionary of loaded YAML data
        sample_dict: Dictionary of parameter: value for this sample
        param_definitions: Parameter definitions
        baselines: Dictionary of baseline values for multiplier parameters
    """

    # Apply values
    for param_name, param_value in sample_dict.items():
        if param_name not in param_definitions:
            continue

        param_def = param_definitions[param_name]
        yaml_file_name = param_def["yaml_file"]

        if yaml_file_name not in yaml_files:
            print(f"Warning: YAML file {yaml_file_name} not found")
            continue

        # Check if this is a multiplier parameter or direct value
        is_multiplier = param_name.endswith("_mult")

        if is_multiplier:
            # Apply multiplier to baseline value(s)
            if param_name in baselines:
                baseline_value = baselines[param_name]

                if isinstance(baseline_value, dict):
                    # For nested dicts, multiply all values recursively
                    def multiply_nested_dict(base_dict, mult, target_dict):
                        """Multiply all numeric values in nested dict structure."""
                        for key, value in base_dict.items():
                            if isinstance(value, dict):
                                if key not in target_dict:
                                    target_dict[key] = {}
                                multiply_nested_dict(value, mult, target_dict[key])
                            elif isinstance(value, (int, float)):
                                target_dict[key] = value * mult

                    # Get target dict
                    current = yaml_files[yaml_file_name]
                    for key in param_def["yaml_path"]:
                        if key in current:
                            current = current[key]
                        else:
                            current = None
                            break

                    if current is not None:
                        multiply_nested_dict(baseline_value, param_value, current)
                else:
                    # Simple numeric value
                    new_value = baseline_value * param_value
                    set_nested_value(
                        yaml_files[yaml_file_name], param_def["yaml_path"], new_value
                    )
            else:
                print(f"Warning: Baseline not found for {param_name}")
        else:
            # Direct value replacement (e.g., delay_years, project_lifetime)
            set_nested_value(
                yaml_files[yaml_file_name], param_def["yaml_path"], param_value
            )


def save_yamls_to_temp(yaml_files, temp_dir):
    """Save modified YAML files to temporary directory."""
    temp_path = Path(temp_dir)
    temp_path.mkdir(parents=True, exist_ok=True)

    for yaml_file_name, yaml_data in yaml_files.items():
        # Clean up baseline markers before saving
        cleaned_data = remove_baseline_markers(yaml_data)

        output_path = temp_path / yaml_file_name
        with open(output_path, "w") as f:
            yaml.dump(cleaned_data, f, default_flow_style=False, sort_keys=False)


def remove_baseline_markers(data):
    """Recursively remove baseline marker keys from dictionary."""
    if isinstance(data, dict):
        cleaned = {}
        for key, value in data.items():
            if not key.startswith("_baseline_"):
                cleaned[key] = remove_baseline_markers(value)
        return cleaned
    elif isinstance(data, list):
        return [remove_baseline_markers(item) for item in data]
    else:
        return data


# ============================================================================
# CTCC RUNNER
# ============================================================================


def run_ctcc_with_temp_yamls(temp_yaml_dir, base_dir):
    """
    Run CTCC with temporary YAML directory.

    Strategy: Temporarily rename yamls/ to yamls_backup/ and yamls_temp/ to yamls/
    Then restore after running.
    """
    yamls_dir = Path(base_dir) / "yamls"
    yamls_backup = Path(base_dir) / "yamls_backup"
    yamls_temp = Path(temp_yaml_dir)

    # Backup original yamls directory
    if yamls_dir.exists():
        if yamls_backup.exists():
            shutil.rmtree(yamls_backup)
        shutil.move(str(yamls_dir), str(yamls_backup))

    # Move temp to yamls
    shutil.move(str(yamls_temp), str(yamls_dir))

    try:
        # Run CTCC
        result = subprocess.run(
            [sys.executable, "ctcc.py"],
            cwd=base_dir,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout per run
        )

        # Extract results from batch_summary.csv
        batch_summary_path = Path(base_dir) / "outputs" / "batch_summary.csv"
        if batch_summary_path.exists():
            df = pd.read_csv(batch_summary_path)
            if len(df) > 0:
                results = df.iloc[-1].to_dict()
                return results, None
            else:
                return None, "batch_summary.csv is empty"
        else:
            return None, "batch_summary.csv not found"

    except subprocess.TimeoutExpired:
        return None, "CTCC run timed out"
    except Exception as e:
        return None, str(e)
    finally:
        # Restore original yamls directory
        if yamls_dir.exists():
            shutil.rmtree(yamls_dir)
        if yamls_backup.exists():
            shutil.move(str(yamls_backup), str(yamls_dir))


# ============================================================================
# SENSITIVITY ANALYSIS
# ============================================================================


def calculate_prcc(inputs_df, outputs_series):
    """
    Calculate Partial Rank Correlation Coefficients (PRCC).

    Args:
        inputs_df: DataFrame of input parameters (N samples × d parameters)
        outputs_series: Series of output values (N samples)

    Returns:
        Series of PRCC values for each parameter
    """
    # Rank transform inputs and output
    inputs_ranked = inputs_df.rank()
    output_ranked = outputs_series.rank()

    prcc_values = {}

    for param in inputs_df.columns:
        # Calculate partial correlation: corr(X, Y | all other X)
        other_params = [p for p in inputs_df.columns if p != param]

        if len(other_params) > 0:
            # Partial correlation via residuals
            X_param = inputs_ranked[param].values
            X_others = inputs_ranked[other_params].values
            Y = output_ranked.values

            # Residuals of param on others
            try:
                from sklearn.linear_model import LinearRegression

                reg_param = LinearRegression().fit(X_others, X_param)
                residuals_param = X_param - reg_param.predict(X_others)

                # Residuals of output on others
                reg_output = LinearRegression().fit(X_others, Y)
                residuals_output = Y - reg_output.predict(X_others)

                # Correlation of residuals = partial correlation
                prcc, _ = spearmanr(residuals_param, residuals_output)
                prcc_values[param] = prcc
            except ImportError:
                # Fallback: use simple rank correlation
                prcc, _ = spearmanr(X_param, Y)
                prcc_values[param] = prcc
        else:
            # Only one parameter
            prcc, _ = spearmanr(inputs_ranked[param], output_ranked)
            prcc_values[param] = prcc

    return pd.Series(prcc_values)


# ============================================================================
# PLOTTING
# ============================================================================


def generate_tornado_plot(prcc_values, output_path, bcr_metric_name=None):
    """Generate tornado diagram showing PRCC values.

    Args:
        prcc_values: Series of PRCC values
        output_path: Path to save the plot
        bcr_metric_name: Name of the BCR metric (for title)
    """
    # Sort by absolute value
    prcc_sorted = prcc_values.reindex(
        prcc_values.abs().sort_values(ascending=False).index
    )

    fig, ax = plt.subplots(figsize=(10, max(8, len(prcc_sorted) * 0.5)))

    colors = ["red" if x < 0 else "green" for x in prcc_sorted.values]
    ax.barh(range(len(prcc_sorted)), prcc_sorted.values, color=colors)
    ax.set_yticks(range(len(prcc_sorted)))
    ax.set_yticklabels(prcc_sorted.index, fontsize=9)
    ax.set_xlabel("Partial Rank Correlation Coefficient (PRCC)", fontsize=11)

    # Use metric name in title if provided
    if bcr_metric_name:
        title = f"Tornado Diagram: Parameter Sensitivity on {bcr_metric_name}"
    else:
        title = "Tornado Diagram: Parameter Sensitivity on BCR_system"

    ax.set_title(title, fontsize=12, fontweight="bold")
    ax.axvline(x=0, color="black", linestyle="-", linewidth=0.5)
    ax.grid(axis="x", alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()


def generate_scatter_plots(results_df, top_params, output_path):
    """Generate scatter plots for top N parameters vs BCR."""
    n_params = len(top_params)
    n_cols = 3
    n_rows = (n_params + n_cols - 1) // n_cols

    fig, axes = plt.subplots(n_rows, n_cols, figsize=(15, 5 * n_rows))
    axes = axes.flatten() if n_params > 1 else [axes]

    for idx, param in enumerate(top_params):
        ax = axes[idx]
        ax.scatter(results_df[param], results_df["bcr_system"], alpha=0.5, s=20)
        ax.set_xlabel(param, fontsize=9)
        ax.set_ylabel("BCR_system", fontsize=9)
        ax.grid(alpha=0.3)
        ax.set_title(f"{param} vs BCR", fontsize=10)

    # Hide unused subplots
    for idx in range(n_params, len(axes)):
        axes[idx].set_visible(False)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()


# ============================================================================
# MAIN WORKFLOW
# ============================================================================


def main():
    parser = argparse.ArgumentParser(
        description="LHS Sensitivity Analysis for CTCC",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--scenario", required=True, help='Scenario name (e.g., "1.1_rural_overhead")'
    )
    parser.add_argument(
        "--n_samples", type=int, default=300, help="Number of LHS samples"
    )
    parser.add_argument(
        "--seed", type=int, default=42, help="Random seed for reproducibility"
    )
    parser.add_argument(
        "--output_dir", default="sensitivity_results", help="Output directory"
    )
    parser.add_argument(
        "--checkpoint_interval",
        type=int,
        default=50,
        help="Save checkpoint every N runs",
    )

    args = parser.parse_args()

    # Setup directories
    base_dir = Path(__file__).parent
    yaml_dir = base_dir / "yamls"
    output_dir = base_dir / args.output_dir / f"scenario_{args.scenario}"
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("LHS SENSITIVITY ANALYSIS FOR CTCC")
    print("=" * 80)
    print(f"Scenario: {args.scenario}")
    print(f"Samples: {args.n_samples}")
    print(f"Parameters: {len(PARAM_DEFINITIONS)}")
    print(f"Seed: {args.seed}")
    print(f"Output: {output_dir}")
    print("=" * 80)
    print()

    # Step 1: Load baseline YAMLs
    print("Loading baseline YAML files...")
    baseline_yamls = load_baseline_yamls(yaml_dir)
    print(f"Loaded {len(baseline_yamls)} YAML files")

    # Store baseline values for multiplier parameters
    print("Storing baseline values...")
    baselines = store_baseline_values(baseline_yamls, PARAM_DEFINITIONS)
    print(f"Stored baselines for {len(baselines)} multiplier parameters")
    print()

    # Step 2: Generate LHS samples
    print("Generating LHS samples...")
    samples_uniform = generate_lhs_samples(
        args.n_samples, PARAM_DEFINITIONS, seed=args.seed
    )
    samples_mapped = map_samples_to_ranges(samples_uniform, PARAM_DEFINITIONS)

    # Save LHS samples
    samples_path = output_dir / "lhs_samples.csv"
    samples_mapped.to_csv(samples_path, index=False)
    print(f"Saved LHS samples to {samples_path}")
    print()

    # Step 3: Run CTCC for each sample
    print("Running CTCC for each sample...")
    print("-" * 80)

    results_list = []
    failed_samples = []
    start_time = time.time()

    for sample_idx in range(args.n_samples):
        sample_dict = samples_mapped.iloc[sample_idx].to_dict()
        sample_id = f"sample_{sample_idx + 1:04d}"

        try:
            # Create temporary YAML directory
            temp_yaml_dir = base_dir / "yamls_temp"
            if temp_yaml_dir.exists():
                shutil.rmtree(temp_yaml_dir)

            # Copy baseline YAMLs
            yaml_files_copy = {}
            for yaml_name, yaml_data in baseline_yamls.items():
                yaml_files_copy[yaml_name] = yaml.load(
                    yaml.dump(yaml_data), Loader=yaml.FullLoader
                )  # Deep copy

            # Apply sample to YAMLs
            apply_sample_to_yamls(
                yaml_files_copy, sample_dict, PARAM_DEFINITIONS, baselines
            )

            # Save to temp directory
            save_yamls_to_temp(yaml_files_copy, temp_yaml_dir)

            # Run CTCC
            result_dict, error = run_ctcc_with_temp_yamls(temp_yaml_dir, base_dir)

            if result_dict:
                # Combine inputs and outputs
                combined = {**sample_dict, **result_dict}
                combined["sample_id"] = sample_id
                results_list.append(combined)

                # Progress update
                if (sample_idx + 1) % 10 == 0:
                    elapsed = time.time() - start_time
                    avg_time = elapsed / (sample_idx + 1)
                    remaining = (args.n_samples - sample_idx - 1) * avg_time

                    bcr = result_dict.get("bcr_system", "N/A")
                    print(
                        f"[{sample_idx + 1}/{args.n_samples}] {sample_id} complete. "
                        f"BCR_system: {bcr:.4f if isinstance(bcr, (int, float)) else bcr}. "
                        f"Est. time remaining: {remaining/60:.1f} min"
                    )

                # Checkpoint
                if (sample_idx + 1) % args.checkpoint_interval == 0:
                    checkpoint_df = pd.DataFrame(results_list)
                    checkpoint_path = output_dir / "results_checkpoint.csv"
                    checkpoint_df.to_csv(checkpoint_path, index=False)
                    print(f"  Checkpoint saved: {checkpoint_path}")
            else:
                failed_samples.append((sample_id, error))
                print(
                    f"[{sample_idx + 1}/{args.n_samples}] {sample_id} FAILED: {error}"
                )

        except Exception as e:
            failed_samples.append((sample_id, str(e)))
            print(f"[{sample_idx + 1}/{args.n_samples}] {sample_id} ERROR: {e}")

    print()
    print("=" * 80)
    print(f"Completed: {len(results_list)}/{args.n_samples} successful")
    if failed_samples:
        print(f"Failed: {len(failed_samples)} samples")
        print("Failed samples:")
        for sample_id, error in failed_samples[:10]:  # Show first 10
            print(f"  {sample_id}: {error}")
        if len(failed_samples) > 10:
            print(f"  ... and {len(failed_samples) - 10} more")
    print()

    # Step 4: Save results
    if results_list:
        results_df = pd.DataFrame(results_list)
        results_path = output_dir / "results.csv"
        results_df.to_csv(results_path, index=False)
        print(f"Saved results to {results_path}")
        print()

        # Step 5: Calculate PRCC and generate plots for all BCR metrics
        bcr_columns = ["bcr_system", "bcr_capital", "bcr_haircut", "bcr_excluding_risk"]
        available_bcr_columns = [
            col for col in bcr_columns if col in results_df.columns
        ]

        if available_bcr_columns:
            print("Calculating PRCC values for all BCR metrics...")
            inputs_df = results_df[
                [p for p in PARAM_DEFINITIONS.keys() if p in results_df.columns]
            ]

            # Calculate PRCC for each BCR metric
            prcc_all = pd.DataFrame(index=inputs_df.columns)

            for bcr_col in available_bcr_columns:
                outputs_series = results_df[bcr_col]
                prcc_values = calculate_prcc(inputs_df, outputs_series)
                prcc_all[bcr_col] = prcc_values

            # Save PRCC values (all BCRs in one file)
            prcc_path = output_dir / "prcc_values.csv"
            prcc_all.to_csv(prcc_path)
            print(f"Saved PRCC values to {prcc_path}")
            print(f"  Columns: {', '.join(available_bcr_columns)}")
            print()

            # Generate tornado plots for each BCR metric
            print("Generating tornado diagrams...")
            for bcr_col in available_bcr_columns:
                prcc_values = prcc_all[bcr_col]
                tornado_path = output_dir / f"tornado_{bcr_col}.png"
                generate_tornado_plot(
                    prcc_values, tornado_path, bcr_metric_name=bcr_col
                )
                print(f"  Saved tornado diagram: {tornado_path}")
            print()

            # Generate scatter plots using bcr_system (most important one)
            if "bcr_system" in available_bcr_columns:
                print("Generating scatter plots...")
                prcc_values_system = prcc_all["bcr_system"]
                top_6_params = prcc_values_system.abs().nlargest(6).index.tolist()
                scatter_path = output_dir / "scatter_top6.png"
                generate_scatter_plots(results_df, top_6_params, scatter_path)
                print(f"  Saved scatter plots: {scatter_path}")
                print()

            # Summary statistics for all BCR metrics
            print("Summary Statistics:")
            print("-" * 80)
            for bcr_col in available_bcr_columns:
                print(f"{bcr_col}:")
                print(f"  Mean: {results_df[bcr_col].mean():.4f}")
                print(f"  Median (P50): {results_df[bcr_col].median():.4f}")
                print(f"  P95: {results_df[bcr_col].quantile(0.95):.4f}")
                print(f"  P5: {results_df[bcr_col].quantile(0.05):.4f}")
                print()

            # Save summary
            summary_path = output_dir / "summary_stats.txt"
            with open(summary_path, "w") as f:
                f.write("LHS Sensitivity Analysis Summary\n")
                f.write("=" * 80 + "\n")
                f.write(f"Scenario: {args.scenario}\n")
                f.write(f"Samples: {args.n_samples}\n")
                f.write(f"Successful runs: {len(results_list)}\n")
                f.write(f"Failed runs: {len(failed_samples)}\n")
                f.write("\n")

                for bcr_col in available_bcr_columns:
                    f.write(f"{bcr_col} Statistics:\n")
                    f.write(f"  Mean: {results_df[bcr_col].mean():.4f}\n")
                    f.write(f"  Median (P50): {results_df[bcr_col].median():.4f}\n")
                    f.write(f"  P95: {results_df[bcr_col].quantile(0.95):.4f}\n")
                    f.write(f"  P5: {results_df[bcr_col].quantile(0.05):.4f}\n")
                    f.write(f"  Std: {results_df[bcr_col].std():.4f}\n")
                    f.write("\n")

            print(f"Saved summary to {summary_path}")
        else:
            print("Warning: No BCR columns found in results")
    else:
        print("Error: No successful runs!")
        sys.exit(1)

    print()
    print("=" * 80)
    print("✅ Sensitivity analysis complete!")
    print("=" * 80)


if __name__ == "__main__":
    main()
