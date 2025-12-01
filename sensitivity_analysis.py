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
import seaborn as sns
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
    "congestion_flow_factor_mult": {
        "type": "linear",
        "range": (0.5, 1.2),
        "yaml_file": "17_congestion_reductions.yaml",
        "yaml_path": [
            "greenfield_congestion_reductions",
            "constraints",
            "flow_factor",
        ],
        "description": "Flow factor multiplier (affects effective capacity relief)",
    },
    "congestion_binding_hours_mult": {
        "type": "linear",
        "range": (0.5, 2.0),
        "yaml_file": "17_congestion_reductions.yaml",
        "yaml_path": [
            "greenfield_congestion_reductions",
            "constraints",
            "binding_hours",
        ],
        "description": "Binding hours multiplier (hours per year line is binding)",
    },
    "congestion_average_exceedance_mult": {
        "type": "linear",
        "range": (0.5, 2.0),
        "yaml_file": "17_congestion_reductions.yaml",
        "yaml_path": [
            "greenfield_congestion_reductions",
            "constraints",
            "average_exceedance",
        ],
        "description": "Average exceedance multiplier (MW exceedance during binding hours)",
    },
    "congestion_near_binding_hours_mult": {
        "type": "linear",
        "range": (0.5, 2.0),
        "yaml_file": "17_congestion_reductions.yaml",
        "yaml_path": [
            "greenfield_congestion_reductions",
            "constraints",
            "near_binding_hours",
        ],
        "description": "Near binding hours multiplier",
    },
    "congestion_near_binding_relief_factor_mult": {
        "type": "linear",
        "range": (0.5, 1.5),
        "yaml_file": "17_congestion_reductions.yaml",
        "yaml_path": [
            "greenfield_congestion_reductions",
            "constraints",
            "near_binding_relief_factor",
        ],
        "description": "Near binding relief factor multiplier [0,1]",
    },
    "congestion_saturation_factor_mult": {
        "type": "linear",
        "range": (0.5, 2.0),
        "yaml_file": "17_congestion_reductions.yaml",
        "yaml_path": [
            "greenfield_congestion_reductions",
            "constraints",
            "saturation_factor",
        ],
        "description": "Saturation factor multiplier (affects congestion benefit haircut)",
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
    "inflation_rate_mult": {
        "type": "linear",
        "range": (0.7, 1.4),
        "yaml_file": "03_financing.yaml",
        "yaml_path": ["financial", "inflation_rate"],
        "description": "Inflation rate multiplier",
    },
    # ROW Cost Multipliers (3) - apply to all zones 1-15
    "row_acquisition_cost_mult": {
        "type": "linear",
        "range": (0.7, 1.5),
        "yaml_file": "11_project_row_details.yaml",
        "yaml_path": ["right_of_way"],
        "target_fields": [
            "acquisition_cost"
        ],  # Only multiply acquisition_cost across all zones
        "description": "ROW acquisition cost multiplier (all zones)",
    },
    "row_rent_cost_mult": {
        "type": "linear",
        "range": (0.7, 1.5),
        "yaml_file": "11_project_row_details.yaml",
        "yaml_path": ["right_of_way"],
        "target_fields": ["rent_cost"],  # Only multiply rent_cost across all zones
        "description": "ROW rent cost multiplier (all zones)",
    },
    "row_hold_cost_mult": {
        "type": "linear",
        "range": (0.7, 1.5),
        "yaml_file": "11_project_row_details.yaml",
        "yaml_path": ["right_of_way"],
        "target_fields": ["hold_cost"],  # Only multiply hold_cost across all zones
        "description": "ROW hold cost multiplier (all zones)",
    },
    # Terrain Multipliers (9) - from 02_project_physical_details.yaml
    "terrain_mult_forested": {
        "type": "linear",
        "range": (0.7, 1.5),
        "yaml_file": "02_project_physical_details.yaml",
        "yaml_path": ["terrain", "terrain_multipliers", "forested"],
        "description": "Terrain multiplier (forested)",
    },
    "terrain_mult_scrubbed_flat": {
        "type": "linear",
        "range": (0.7, 1.5),
        "yaml_file": "02_project_physical_details.yaml",
        "yaml_path": ["terrain", "terrain_multipliers", "scrubbed_flat"],
        "description": "Terrain multiplier (scrubbed flat)",
    },
    "terrain_mult_wetland": {
        "type": "linear",
        "range": (0.7, 1.5),
        "yaml_file": "02_project_physical_details.yaml",
        "yaml_path": ["terrain", "terrain_multipliers", "wetland"],
        "description": "Terrain multiplier (wetland)",
    },
    "terrain_mult_farmland": {
        "type": "linear",
        "range": (0.7, 1.5),
        "yaml_file": "02_project_physical_details.yaml",
        "yaml_path": ["terrain", "terrain_multipliers", "farmland"],
        "description": "Terrain multiplier (farmland)",
    },
    "terrain_mult_desert_barren": {
        "type": "linear",
        "range": (0.7, 1.5),
        "yaml_file": "02_project_physical_details.yaml",
        "yaml_path": ["terrain", "terrain_multipliers", "desert_barren"],
        "description": "Terrain multiplier (desert barren)",
    },
    "terrain_mult_urban": {
        "type": "linear",
        "range": (0.7, 1.5),
        "yaml_file": "02_project_physical_details.yaml",
        "yaml_path": ["terrain", "terrain_multipliers", "urban"],
        "description": "Terrain multiplier (urban)",
    },
    "terrain_mult_rolling_hills": {
        "type": "linear",
        "range": (0.7, 1.5),
        "yaml_file": "02_project_physical_details.yaml",
        "yaml_path": ["terrain", "terrain_multipliers", "rolling_hills"],
        "description": "Terrain multiplier (rolling hills)",
    },
    "terrain_mult_mountain": {
        "type": "linear",
        "range": (0.7, 1.5),
        "yaml_file": "02_project_physical_details.yaml",
        "yaml_path": ["terrain", "terrain_multipliers", "mountain"],
        "description": "Terrain multiplier (mountain)",
    },
    "terrain_mult_subsea": {
        "type": "linear",
        "range": (0.7, 1.5),
        "yaml_file": "02_project_physical_details.yaml",
        "yaml_path": ["terrain", "terrain_multipliers", "subsea"],
        "description": "Terrain multiplier (subsea)",
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


def create_baseline_sample(param_definitions, yaml_files):
    """
    Create a baseline sample dictionary with all parameters at their baseline values.

    Args:
        param_definitions: Dictionary of parameter definitions
        yaml_files: Dictionary of loaded YAML data

    Returns:
        Dictionary with parameter_name: baseline_value pairs
    """
    baseline_sample = {}

    for param_name, param_def in param_definitions.items():
        # Check if this is a multiplier parameter
        is_multiplier = param_name.endswith("_mult")

        if is_multiplier:
            # For multipliers, baseline value is always 1.0
            baseline_sample[param_name] = 1.0
        else:
            # For non-multiplier parameters, read baseline value from YAML
            yaml_file_name = param_def["yaml_file"]
            if yaml_file_name in yaml_files:
                baseline_value = get_nested_value(
                    yaml_files[yaml_file_name], param_def["yaml_path"]
                )
                if baseline_value is not None:
                    baseline_sample[param_name] = baseline_value
                else:
                    # If value not found, use midpoint of range as fallback
                    min_val, max_val = param_def["range"]
                    if param_def["type"] == "integer":
                        baseline_sample[param_name] = int((min_val + max_val) / 2)
                    else:
                        baseline_sample[param_name] = (min_val + max_val) / 2
            else:
                # If YAML file not found, use midpoint of range as fallback
                min_val, max_val = param_def["range"]
                if param_def["type"] == "integer":
                    baseline_sample[param_name] = int((min_val + max_val) / 2)
                else:
                    baseline_sample[param_name] = (min_val + max_val) / 2

    return baseline_sample


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
                # Check if target_fields is specified (for field-specific multipliers)
                target_fields = param_def.get("target_fields")

                if target_fields:
                    # Store only the target fields for each zone/key
                    baseline_dict = {}
                    for zone_key, zone_dict in current_value.items():
                        if isinstance(zone_dict, dict):
                            baseline_dict[zone_key] = {}
                            for field_name in target_fields:
                                if field_name in zone_dict and isinstance(
                                    zone_dict[field_name], (int, float)
                                ):
                                    baseline_dict[zone_key][field_name] = zone_dict[
                                        field_name
                                    ]
                    baselines[param_name] = baseline_dict
                else:
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
                    # Check if target_fields is specified (for field-specific multiplication)
                    target_fields = param_def.get("target_fields")

                    if target_fields:
                        # Field-specific multiplication: only multiply specified fields
                        # Get target dict
                        current = yaml_files[yaml_file_name]
                        for key in param_def["yaml_path"]:
                            if key in current:
                                current = current[key]
                            else:
                                current = None
                                break

                        if current is not None:
                            # Iterate through all zones/keys in the dict
                            for zone_key, zone_dict in current.items():
                                if isinstance(zone_dict, dict):
                                    # For each target field, multiply if it exists
                                    for field_name in target_fields:
                                        if field_name in zone_dict and isinstance(
                                            zone_dict[field_name], (int, float)
                                        ):
                                            # Get baseline value for this field
                                            baseline_field_value = baseline_value.get(
                                                zone_key, {}
                                            ).get(field_name)
                                            if baseline_field_value is not None:
                                                zone_dict[field_name] = (
                                                    baseline_field_value * param_value
                                                )
                    else:
                        # For nested dicts, multiply all values recursively (original behavior)
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


def calculate_bcr_fallback(data):
    """
    Fallback BCR calculation when BCR columns are missing from batch_summary.csv.
    Uses the same logic as bcr_calculator.py but works directly with data dict.

    Args:
        data: Dictionary with scenario data from batch_summary.csv

    Returns:
        Dictionary with BCR metrics, or None if calculation fails
    """
    try:
        # Calculate benefits (present value)
        congestion_benefit_pv = data.get("congestion_benefit_pv", 0) or 0
        curtailment_benefit_pv = data.get("curtailment_benefit_pv", 0) or 0
        line_loss_pv = data.get("line_loss_cost_pv", 0) or 0

        # For reconductoring, line losses are negative (benefit)
        line_loss_benefit_pv = abs(line_loss_pv) if line_loss_pv < 0 else 0
        total_benefits_pv = (
            congestion_benefit_pv + curtailment_benefit_pv + line_loss_benefit_pv
        )

        # Haircut benefits (conservative)
        congestion_benefit_haircut = data.get("congestion_benefit_haircut_pv", 0) or 0
        curtailment_benefit_haircut = data.get("curtailment_benefit_haircut_pv", 0) or 0
        total_benefits_haircut_pv = (
            congestion_benefit_haircut
            + curtailment_benefit_haircut
            + line_loss_benefit_pv
        )

        # Calculate costs (present value)
        build_cost_pv = data.get("build_cost_pv", 0) or 0
        row_cost_pv = data.get("row_cost_pv", 0) or 0
        env_mitigation_pv = data.get("env_mitigation_pv", 0) or 0
        capital_costs_pv = build_cost_pv + row_cost_pv + env_mitigation_pv

        # Operational costs (PV) - O&M and operational insurance only
        oandm_pv = data.get("oandm_pv", 0) or 0
        insurance_pv = data.get("insurance_pv", 0) or 0
        operational_costs_pv = oandm_pv + insurance_pv

        # Energy & Emissions costs (PV) - Line losses and emissions
        emissions_pv = data.get("emissions_cost_pv", 0) or 0
        line_loss_cost_pv = max(0, line_loss_pv)  # Only count as cost if positive
        energy_emissions_costs_pv = line_loss_cost_pv + emissions_pv

        # Risk costs (PV) - Wildfire, outage, and wildfire liability insurance
        wildfire_pv = data.get("wildfire_pv", 0) or 0
        outage_pv = data.get("outage_pv", 0) or 0
        wildfire_liability_pv = data.get("wildfire_liability_pv", 0) or 0
        risk_costs_pv = wildfire_pv + outage_pv + wildfire_liability_pv

        delay_cost_pv = data.get("delay_cost_pv", 0) or 0
        congestion_delay_pv = data.get("congestion_delay_cost_pv", 0) or 0
        curtailment_delay_pv = data.get("curtailment_delay_cost_pv", 0) or 0
        residual_congestion_pv = data.get("residual_congestion_pv", 0) or 0
        delay_costs_pv = (
            delay_cost_pv
            + congestion_delay_pv
            + curtailment_delay_pv
            + residual_congestion_pv
        )

        total_costs_pv = (
            capital_costs_pv
            + operational_costs_pv
            + energy_emissions_costs_pv
            + risk_costs_pv
            + delay_costs_pv
        )
        total_costs_excluding_risk_pv = total_costs_pv - risk_costs_pv
        total_costs_excluding_emissions_pv = total_costs_pv - energy_emissions_costs_pv
        total_costs_excluding_emissions_and_risk_pv = (
            total_costs_pv - energy_emissions_costs_pv - risk_costs_pv
        )

        # Calculate BCR metrics
        # Use conservative (haircut) benefits for all BCR calculations
        if total_costs_pv > 0:
            bcr_system = total_benefits_haircut_pv / total_costs_pv
        else:
            bcr_system = 0

        if capital_costs_pv > 0:
            bcr_capital = total_benefits_haircut_pv / capital_costs_pv
        else:
            bcr_capital = 0

        if capital_costs_pv + delay_costs_pv > 0:
            bcr_capital_and_delay = total_benefits_haircut_pv / (
                capital_costs_pv + delay_costs_pv
            )
        else:
            bcr_capital_and_delay = 0

        if total_costs_excluding_risk_pv > 0:
            bcr_excluding_risk = (
                total_benefits_haircut_pv / total_costs_excluding_risk_pv
            )
        else:
            bcr_excluding_risk = 0

        if total_costs_excluding_emissions_pv > 0:
            bcr_excluding_emissions = (
                total_benefits_haircut_pv / total_costs_excluding_emissions_pv
            )
        else:
            bcr_excluding_emissions = 0

        if total_costs_excluding_emissions_and_risk_pv > 0:
            bcr_excluding_emissions_and_risk = (
                total_benefits_haircut_pv / total_costs_excluding_emissions_and_risk_pv
            )
        else:
            bcr_excluding_emissions_and_risk = 0

        return {
            "bcr_system": bcr_system,
            "bcr_capital": bcr_capital,
            "bcr_capital_and_delay": bcr_capital_and_delay,
            "bcr_excluding_risk": bcr_excluding_risk,
            "bcr_excluding_emissions": bcr_excluding_emissions,
            "bcr_excluding_emissions_and_risk": bcr_excluding_emissions_and_risk,
        }
    except Exception as e:
        # If calculation fails, return None
        return None


def read_results_by_scenario_id(batch_summary_path, scenario_id):
    """
    Read results from batch_summary.csv by matching scenario_id.

    Args:
        batch_summary_path: Path to batch_summary.csv
        scenario_id: Scenario ID to search for

    Returns:
        Dictionary of results if found, None otherwise
    """
    if not batch_summary_path.exists():
        return None

    try:
        df = pd.read_csv(batch_summary_path)
        if len(df) == 0:
            return None

        # Find row with matching scenario_id
        matching_rows = df[df["scenario_id"] == scenario_id]
        if len(matching_rows) > 0:
            return matching_rows.iloc[-1].to_dict()  # Take last if multiple matches
        else:
            return None
    except Exception as e:
        return None


def run_ctcc_with_temp_yamls(temp_yaml_dir, base_dir, scenario_id):
    """
    Run CTCC with temporary YAML directory.

    Args:
        temp_yaml_dir: Path to temporary YAML directory
        base_dir: Base directory of the project
        scenario_id: Unique scenario ID for this sample

    Returns:
        Tuple of (result_dict, error_message)
    """
    yamls_dir = base_dir / "yamls"
    yamls_backup = base_dir / "yamls_backup"

    try:
        # Backup original yamls directory if it exists
        if yamls_dir.exists():
            if yamls_backup.exists():
                shutil.rmtree(yamls_backup)
            shutil.move(str(yamls_dir), str(yamls_backup))

        # Move temp to main yamls location
        shutil.move(str(temp_yaml_dir), str(yamls_dir))

        # Set environment variable for scenario ID
        env = os.environ.copy()
        env["CTCC_SCENARIO_ID"] = scenario_id

        # Run CTCC
        result = subprocess.run(
            [sys.executable, "ctcc.py"],
            cwd=base_dir,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout per run
            env=env,
        )

        # Check for errors
        if result.returncode != 0:
            error_msg = f"CTCC failed with return code {result.returncode}"
            if result.stderr:
                error_msg += f"\nStderr: {result.stderr[-500:]}"
            if result.stdout:
                error_msg += f"\nStdout (last 500 chars): {result.stdout[-500:]}"
            return None, error_msg

        # Extract actual scenario_id from CTCC output (it prints it)
        actual_scenario_id = scenario_id
        if result.stdout:
            for line in result.stdout.split("\n"):
                if "Scenario ID:" in line:
                    parts = line.split("Scenario ID:")
                    if len(parts) > 1:
                        actual_scenario_id = parts[1].strip()
                        break

        # Check for BCR calculation issues in stdout
        bcr_warning_detected = False
        if result.stdout:
            if (
                "BCR calculation failed" in result.stdout
                or "no results returned" in result.stdout
            ):
                bcr_warning_detected = True

        # Extract results from batch_summary.csv by scenario_id
        batch_summary_path = Path(base_dir) / "outputs" / "batch_summary.csv"
        results = read_results_by_scenario_id(batch_summary_path, actual_scenario_id)

        if results is None:
            # Fallback: try to read the last row (in case scenario_id format changed)
            if batch_summary_path.exists():
                df = pd.read_csv(batch_summary_path)
                if len(df) > 0:
                    # Try to find a row with scenario_id that contains our sample index
                    sample_idx_str = (
                        scenario_id.split("_")[1] if "_" in scenario_id else None
                    )
                    if sample_idx_str:
                        matching = df[
                            df["scenario_id"]
                            .astype(str)
                            .str.contains(sample_idx_str, na=False)
                        ]
                        if len(matching) > 0:
                            results = matching.iloc[-1].to_dict()
                            actual_scenario_id = results.get(
                                "scenario_id", actual_scenario_id
                            )

                    # Last resort: use the last row
                    if results is None:
                        results = df.iloc[-1].to_dict()
                        actual_scenario_id = results.get(
                            "scenario_id", actual_scenario_id
                        )

            if results is None:
                return (
                    None,
                    f"Results not found for scenario_id: {scenario_id} (tried: {actual_scenario_id})",
                )

        # Check if BCR columns are missing or empty/NaN and attempt fallback calculation
        bcr_columns = [
            "bcr_system",
            "bcr_capital",
            "bcr_capital_and_delay",
            "bcr_excluding_risk",
            "bcr_excluding_emissions",
            "bcr_excluding_emissions_and_risk",
        ]
        # Check for missing columns OR empty/NaN values
        missing_bcr = []
        for col in bcr_columns:
            if col not in results:
                missing_bcr.append(col)
            else:
                # Check if value is empty, None, NaN, or empty string
                val = results.get(col)
                # Use pandas.isna for proper NaN/None/empty checking
                is_empty = (
                    val is None
                    or pd.isna(val)
                    or val == ""
                    or (isinstance(val, str) and val.strip() == "")
                )
                if is_empty:
                    missing_bcr.append(col)

        if missing_bcr:
            # Attempt fallback BCR calculation
            fallback_bcr = calculate_bcr_fallback(results)
            if fallback_bcr:
                # Add fallback BCR metrics to results
                results.update(fallback_bcr)
            else:
                error_info = f"BCR columns missing or empty: {missing_bcr}. "
                if bcr_warning_detected:
                    error_info += "CTCC stdout indicates BCR calculation issue. "
                error_info += "Fallback BCR calculation also failed."
                return results, error_info

        return results, None

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
# SAMPLE PROCESSING FUNCTION
# ============================================================================


def process_single_sample(args_tuple):
    """
    Process a single sample.

    Args:
        args_tuple: Tuple containing:
            - sample_idx: Index of the sample
            - sample_dict: Dictionary of parameter values
            - base_dir: Base directory path (as string)
            - baseline_yamls: Dictionary of baseline YAML data
            - param_definitions: Parameter definitions
            - baselines: Baseline values for multipliers

    Returns:
        Tuple of (sample_id, result_dict, error_message)
        If successful: (sample_id, result_dict, None)
        If failed: (sample_id, None, error_message)
    """
    (
        sample_idx,
        sample_dict,
        base_dir_str,
        baseline_yamls,
        param_definitions,
        baselines,
    ) = args_tuple

    base_dir = Path(base_dir_str)
    sample_id = f"sample_{sample_idx + 1:04d}"
    # Generate unique scenario_id for this sample
    scenario_id = f"sample_{sample_idx}_{int(time.time() * 1000000)}"

    try:
        # Create unique temporary YAML directory for this sample
        temp_yaml_dir = base_dir / f"yamls_temp_sample_{sample_idx}"
        if temp_yaml_dir.exists():
            shutil.rmtree(temp_yaml_dir)

        # Deep copy baseline YAMLs
        yaml_files_copy = {}
        for yaml_name, yaml_data in baseline_yamls.items():
            yaml_files_copy[yaml_name] = yaml.load(
                yaml.dump(yaml_data), Loader=yaml.FullLoader
            )  # Deep copy

        # Apply sample to YAMLs
        apply_sample_to_yamls(
            yaml_files_copy, sample_dict, param_definitions, baselines
        )

        # Save to temp directory
        save_yamls_to_temp(yaml_files_copy, temp_yaml_dir)

        # Run CTCC
        result_dict, error = run_ctcc_with_temp_yamls(
            temp_yaml_dir, base_dir, scenario_id
        )

        # Cleanup temp YAML directory
        if temp_yaml_dir.exists():
            shutil.rmtree(temp_yaml_dir)

        if result_dict:
            # Combine inputs and outputs
            combined = {**sample_dict, **result_dict}
            combined["sample_id"] = sample_id
            return (sample_id, combined, None)
        else:
            return (sample_id, None, error)

    except Exception as e:
        # Cleanup on error
        temp_yaml_dir = base_dir / f"yamls_temp_sample_{sample_idx}"
        if temp_yaml_dir.exists():
            shutil.rmtree(temp_yaml_dir)
        return (sample_id, None, str(e))


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


def generate_scatter_plots(results_df, top_params, bcr_col, output_path):
    """Generate scatter plots for top N parameters vs a specific BCR metric.

    Args:
        results_df: DataFrame with all results
        top_params: List of top parameter names to include
        bcr_col: BCR column name to plot against
        output_path: Path to save the plot
    """
    n_params = len(top_params)
    n_cols = 3
    n_rows = (n_params + n_cols - 1) // n_cols

    fig, axes = plt.subplots(n_rows, n_cols, figsize=(15, 5 * n_rows))
    axes = axes.flatten() if n_params > 1 else [axes]

    for idx, param in enumerate(top_params):
        ax = axes[idx]
        ax.scatter(results_df[param], results_df[bcr_col], alpha=0.5, s=20)
        ax.set_xlabel(param, fontsize=9)
        ax.set_ylabel(bcr_col, fontsize=9)
        ax.grid(alpha=0.3)
        ax.set_title(f"{param} vs {bcr_col}", fontsize=10)

    # Hide unused subplots
    for idx in range(n_params, len(axes)):
        axes[idx].set_visible(False)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()


def generate_prcc_heatmap(prcc_all, output_path, top_n=20):
    """
    Generate heatmap showing PRCC values across all BCR metrics.

    Args:
        prcc_all: DataFrame with PRCC values (index=parameters, columns=BCR metrics)
        output_path: Path to save the plot
        top_n: Number of top parameters to show (by average absolute PRCC)
    """
    # Calculate average absolute PRCC across all metrics to rank parameters
    prcc_all_copy = prcc_all.copy()
    prcc_all_copy["avg_abs_prcc"] = prcc_all_copy.abs().mean(axis=1)

    # Select top N parameters
    top_params = prcc_all_copy.nlargest(top_n, "avg_abs_prcc").index.tolist()
    heatmap_data = prcc_all_copy.loc[top_params].drop("avg_abs_prcc", axis=1)

    # Create figure
    fig, ax = plt.subplots(
        figsize=(max(8, len(heatmap_data.columns) * 2), max(10, len(top_params) * 0.4))
    )

    # Create heatmap with custom colormap
    # Use diverging colormap: red (negative) -> white (zero) -> blue (positive)
    sns.heatmap(
        heatmap_data,
        annot=True,  # Show PRCC values in cells
        fmt=".2f",  # Format to 2 decimal places
        cmap="RdBu_r",  # Red-Blue reversed (red=negative, blue=positive)
        center=0,  # Center colormap at zero
        vmin=-1,  # Min value
        vmax=1,  # Max value
        cbar_kws={"label": "PRCC"},
        linewidths=0.5,
        linecolor="gray",
        ax=ax,
    )

    ax.set_title(
        "PRCC Heatmap: Parameter Sensitivity Across BCR Metrics",
        fontsize=12,
        fontweight="bold",
        pad=20,
    )
    ax.set_xlabel("BCR Metric", fontsize=10)
    ax.set_ylabel("Parameter", fontsize=10)
    ax.set_yticklabels(ax.get_yticklabels(), rotation=0, fontsize=8)
    ax.set_xticklabels(ax.get_xticklabels(), rotation=45, ha="right", fontsize=9)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()


def generate_parallel_coordinates_plot(
    results_df, top_params, bcr_col, output_path, n_samples_to_plot=300
):
    """
    Generate parallel coordinates plot showing parameter combinations and BCR outcomes.

    Args:
        results_df: DataFrame with all results
        top_params: List of top parameter names to include
        bcr_col: BCR column name to use for coloring
        output_path: Path to save the plot
        n_samples_to_plot: Number of samples to plot (for readability, default all)
    """
    # Select top parameters + BCR
    plot_cols = top_params + [bcr_col]

    # Subset data
    plot_data = results_df[plot_cols].copy()

    # Limit number of samples if too many (for readability)
    if len(plot_data) > n_samples_to_plot:
        plot_data = plot_data.sample(n=n_samples_to_plot, random_state=42)

    # Normalize all columns to [0, 1] for parallel coordinates
    normalized_data = plot_data.copy()
    for col in plot_cols:
        col_min = normalized_data[col].min()
        col_max = normalized_data[col].max()
        if col_max > col_min:
            normalized_data[col] = (normalized_data[col] - col_min) / (
                col_max - col_min
            )
        else:
            normalized_data[col] = 0.5  # Constant value

    # Create figure
    fig, ax = plt.subplots(figsize=(max(12, len(plot_cols) * 1.5), 8))

    # Color by BCR value
    bcr_values = plot_data[bcr_col].values
    bcr_normalized = normalized_data[bcr_col].values

    # Use a colormap (green for high BCR, red for low BCR)
    cmap = plt.cm.get_cmap("RdYlGn")  # Red-Yellow-Green
    colors = cmap(bcr_normalized)

    # Plot parallel coordinates manually for better control
    n_samples = len(normalized_data)
    n_axes = len(plot_cols)

    # Create positions for axes
    positions = np.linspace(0, 1, n_axes)

    # Plot lines
    for idx in range(n_samples):
        values = normalized_data.iloc[idx].values
        ax.plot(positions, values, alpha=0.3, color=colors[idx], linewidth=0.5)

    # Set axis labels and positions
    ax.set_xticks(positions)
    ax.set_xticklabels(plot_cols, rotation=45, ha="right", fontsize=9)
    ax.set_ylabel("Normalized Value", fontsize=10)
    ax.set_title(
        f"Parallel Coordinates: Parameter Combinations → {bcr_col}",
        fontsize=12,
        fontweight="bold",
        pad=20,
    )
    ax.grid(True, alpha=0.3, axis="y")

    # Add colorbar
    sm = plt.cm.ScalarMappable(
        cmap=cmap, norm=plt.Normalize(vmin=bcr_values.min(), vmax=bcr_values.max())
    )
    sm.set_array([])
    cbar = plt.colorbar(sm, ax=ax, pad=0.02)
    cbar.set_label(bcr_col, fontsize=10, rotation=270, labelpad=15)

    # Add min/max labels on right side of each axis
    for i, col in enumerate(plot_cols):
        col_min = plot_data[col].min()
        col_max = plot_data[col].max()
        ax.text(
            positions[i],
            -0.05,
            f"{col_min:.2f}",
            ha="center",
            va="top",
            fontsize=7,
            transform=ax.get_xaxis_transform(),
        )
        ax.text(
            positions[i],
            1.05,
            f"{col_max:.2f}",
            ha="center",
            va="bottom",
            fontsize=7,
            transform=ax.get_xaxis_transform(),
        )

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

    # Create baseline sample and prepend it to samples
    print("Creating baseline sample...")
    baseline_sample = create_baseline_sample(PARAM_DEFINITIONS, baseline_yamls)
    baseline_df = pd.DataFrame([baseline_sample])
    samples_mapped = pd.concat([baseline_df, samples_mapped], ignore_index=True)
    total_runs = args.n_samples + 1
    print(f"Including baseline run as sample_0001 (total runs: {total_runs})")
    print()

    # Save LHS samples (includes baseline as first row)
    samples_path = output_dir / "lhs_samples.csv"
    samples_mapped.to_csv(samples_path, index=False)
    print(f"Saved samples (1 baseline + {args.n_samples} LHS) to {samples_path}")
    print()

    # Step 3: Run CTCC for each sample
    print(
        f"Running CTCC for each sample (1 baseline + {args.n_samples} LHS samples)..."
    )
    print("-" * 80)

    results_list = []
    failed_samples = []
    start_time = time.time()

    # Process samples sequentially
    for sample_idx in range(total_runs):
        sample_dict = samples_mapped.iloc[sample_idx].to_dict()
        sample_id = f"sample_{sample_idx + 1:04d}"
        scenario_id = f"sample_{sample_idx}_{int(time.time() * 1000000)}"

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
            result_dict, error = run_ctcc_with_temp_yamls(
                temp_yaml_dir, base_dir, scenario_id
            )

            if result_dict:
                # Combine inputs and outputs
                combined = {**sample_dict, **result_dict}
                combined["sample_id"] = sample_id
                results_list.append(combined)

                # Progress update
                if (sample_idx + 1) % 10 == 0:
                    elapsed = time.time() - start_time
                    avg_time = elapsed / (sample_idx + 1)
                    remaining = (total_runs - sample_idx - 1) * avg_time

                    bcr = result_dict.get("bcr_system", "N/A")
                    bcr_str = (
                        f"{bcr:.4f}" if isinstance(bcr, (int, float)) else str(bcr)
                    )
                    sample_type = "baseline" if sample_idx == 0 else "LHS"
                    print(
                        f"[{sample_idx + 1}/{total_runs}] {sample_id} complete ({sample_type}). "
                        f"BCR_system: {bcr_str}. "
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
                print(f"[{sample_idx + 1}/{total_runs}] {sample_id} FAILED: {error}")

        except Exception as e:
            failed_samples.append((sample_id, str(e)))
            print(f"[{sample_idx + 1}/{total_runs}] {sample_id} ERROR: {e}")

    print()
    print("=" * 80)
    print(f"Completed: {len(results_list)}/{total_runs} successful")
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
        # Sort results by sample_id for consistency
        results_list_sorted = sorted(results_list, key=lambda x: x.get("sample_id", ""))
        results_df = pd.DataFrame(results_list_sorted)
        results_path = output_dir / "results.csv"
        results_df.to_csv(results_path, index=False)
        print(f"Saved results to {results_path}")
        print()

        # Step 5: Calculate PRCC and generate plots for all BCR metrics
        bcr_columns = [
            "bcr_system",
            "bcr_capital",
            "bcr_capital_and_delay",
            "bcr_excluding_risk",
            "bcr_excluding_emissions",
            "bcr_excluding_emissions_and_risk",
        ]
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

            # Generate PRCC heatmap
            print("Generating PRCC heatmap...")
            heatmap_path = output_dir / "prcc_heatmap.png"
            generate_prcc_heatmap(prcc_all, heatmap_path, top_n=25)
            print(f"  Saved PRCC heatmap: {heatmap_path}")
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

            # Generate scatter plots for each BCR metric
            print("Generating scatter plots...")
            for bcr_col in available_bcr_columns:
                prcc_values = prcc_all[bcr_col]
                top_6_params = prcc_values.abs().nlargest(6).index.tolist()
                scatter_path = output_dir / f"scatter_top6_{bcr_col}.png"
                generate_scatter_plots(results_df, top_6_params, bcr_col, scatter_path)
                print(f"  Saved scatter plots: {scatter_path}")
            print()

            # Generate parallel coordinates plot using bcr_system (most important one)
            if "bcr_system" in available_bcr_columns:
                print("Generating parallel coordinates plot...")
                prcc_values_system = prcc_all["bcr_system"]
                top_8_params = prcc_values_system.abs().nlargest(8).index.tolist()
                parallel_path = output_dir / "parallel_coordinates_bcr_system.png"
                generate_parallel_coordinates_plot(
                    results_df, top_8_params, "bcr_system", parallel_path
                )
                print(f"  Saved parallel coordinates plot: {parallel_path}")
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
                f.write(
                    f"Total runs: {total_runs} (1 baseline + {args.n_samples} LHS samples)\n"
                )
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
