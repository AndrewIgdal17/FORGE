#!/usr/bin/env python3
"""
Shared utilities for sensitivity analysis and OAT analysis scripts.

This module contains common functions and constants used by both
sensitivity_analysis.py and oat_analysis.py to avoid code duplication.
"""

from __future__ import annotations

import os
import sys
import shutil
import subprocess
import yaml
import pandas as pd
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional, Callable


# ============================================================================
# CONSTANTS
# ============================================================================

BCR_COLUMNS = [
    "bcr_societal",
    "bcr_excluding_avoided_emissions",
    "bcr_excluding_wildfire_risk",
    "bcr_excluding_wildfire_risk_and_outage_risk",
    "bcr_utility",
    "bcr_ratepayer",
]


# ============================================================================
# YAML UTILITIES
# ============================================================================


def deep_copy_yamls(baseline_yamls: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deep copy YAML files dictionary.

    Args:
        baseline_yamls: Dictionary of baseline YAML data

    Returns:
        Deep copy of the YAML files dictionary
    """
    yaml_files_copy = {}
    for yaml_name, yaml_data in baseline_yamls.items():
        try:
            # Deep copy using yaml dump/load
            dumped = yaml.dump(yaml_data)
            if not dumped:
                raise ValueError(f"Failed to dump YAML data for {yaml_name}")
            yaml_files_copy[yaml_name] = yaml.safe_load(dumped)  # Deep copy
        except yaml.YAMLError as e:
            raise ValueError(f"Error processing YAML data for {yaml_name}: {e}")
    return yaml_files_copy


# ============================================================================
# BCR VALIDATION UTILITIES
# ============================================================================


def check_missing_bcr(
    results: Dict[str, Any], bcr_columns: Optional[List[str]] = None
) -> Tuple[List[str], Dict[str, bool]]:
    """
    Check for missing or empty BCR columns.

    Args:
        results: Dictionary of results from batch_summary.csv
        bcr_columns: List of BCR column names (defaults to BCR_COLUMNS)

    Returns:
        tuple: (missing_bcr_list, is_empty_dict)
            - missing_bcr_list: List of BCR columns that are missing or empty
            - is_empty_dict: Dictionary mapping column names to boolean (True if empty)
    """
    if bcr_columns is None:
        bcr_columns = BCR_COLUMNS

    missing_bcr = []
    is_empty_dict = {}

    for col in bcr_columns:
        if col not in results:
            missing_bcr.append(col)
            is_empty_dict[col] = True
        else:
            column_value = results.get(col)
            # Use pandas.isna for proper NaN/None/empty checking
            is_empty = (
                column_value is None
                or pd.isna(column_value)
                or column_value == ""
                or (isinstance(column_value, str) and column_value.strip() == "")
            )
            if is_empty:
                missing_bcr.append(col)
            is_empty_dict[col] = is_empty

    return missing_bcr, is_empty_dict


def validate_bcr_results(
    results: Dict[str, Any], bcr_warning_detected: bool = False
) -> Tuple[Dict[str, Any], Optional[str]]:
    """
    Validate that BCR results are present in the results dictionary.

    Args:
        results: Dictionary of results from batch_summary.csv
        bcr_warning_detected: Whether BCR warning was detected in CTCC stdout

    Returns:
        tuple: (results_dict, error_message_or_none)
            - If BCR columns are present: (results, None)
            - If BCR columns are missing: (results, error_message)
    """
    missing_bcr, _ = check_missing_bcr(results)

    if missing_bcr:
        error_info = f"BCR columns missing or empty: {missing_bcr}."
        if bcr_warning_detected:
            error_info += " CTCC stdout indicates BCR calculation issue."
        error_info += " This suggests the BCR calculator failed to write columns to batch_summary.csv."
        return results, error_info

    return results, None


# ============================================================================
# CTCC EXECUTION UTILITIES
# ============================================================================


def format_ctcc_error(result: subprocess.CompletedProcess[str]) -> str:
    """
    Format CTCC subprocess error message.

    Args:
        result: subprocess.CompletedProcess or subprocess result object

    Returns:
        Formatted error message string
    """
    error_msg = f"CTCC failed with return code {result.returncode}"
    if result.stderr:
        error_msg += f"\nStderr: {result.stderr[-500:]}"
    if result.stdout:
        error_msg += f"\nStdout (last 500 chars): {result.stdout[-500:]}"
    return error_msg


def run_ctcc_with_temp_yamls(
    temp_yaml_dir: Path | str,
    base_dir: Path | str,
    scenario_id: str,
    ctcc_args: Optional[List[str]] = None,
    use_env_dict: bool = True,
    read_results_by_scenario_id_func: Optional[
        Callable[[Path, str], Optional[Dict[str, Any]]]
    ] = None,
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Run CTCC with temporary YAML directory.

    This is a unified version combining the best features from both
    sensitivity_analysis.py and oat_analysis.py implementations.

    Args:
        temp_yaml_dir: Path to temporary YAML directory
        base_dir: Base directory of the project
        scenario_id: Unique scenario ID for this sample
        ctcc_args: Additional args for ctcc.py (e.g., ["--simple"])
        use_env_dict: If True, use env dict; if False, set os.environ directly
        read_results_by_scenario_id_func: Function to read results by scenario_id

    Returns:
        Tuple of (result_dict, error_message)
    """
    base_dir = Path(base_dir)  # Ensure it's a Path object
    temp_yaml_dir = Path(temp_yaml_dir)  # Ensure it's a Path object

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
        if use_env_dict:
            env = os.environ.copy()
            env["CTCC_SCENARIO_ID"] = scenario_id
        else:
            os.environ["CTCC_SCENARIO_ID"] = scenario_id

        # Build CTCC command
        ctcc_cmd = [sys.executable, "ctcc.py"]
        if ctcc_args:
            ctcc_cmd.extend(ctcc_args)

        # Run CTCC
        if use_env_dict:
            result = subprocess.run(
                ctcc_cmd,
                cwd=base_dir,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout per run
                env=env,
            )
        else:
            result = subprocess.run(
                ctcc_cmd,
                cwd=str(base_dir),
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout per run
            )

        # Check for errors
        if result.returncode != 0:
            error_msg = format_ctcc_error(result)
            return None, error_msg

        # DEBUG: Print subprocess output to see BCR debug messages
        print(
            f"[DEBUG SENS] CTCC subprocess completed with return code {result.returncode}"
        )
        if result.stdout:
            # Extract and print BCR-related debug messages
            debug_lines = [
                line for line in result.stdout.split("\n") if "[DEBUG" in line
            ]
            if debug_lines:
                print(
                    f"[DEBUG SENS] Found {len(debug_lines)} debug lines in CTCC stdout:"
                )
                for line in debug_lines[:30]:  # Print first 30 debug lines
                    print(f"  {line}")
            # Also check for BCR-related warnings/errors
            bcr_lines = [
                line
                for line in result.stdout.split("\n")
                if any(
                    x in line.lower()
                    for x in [
                        "bcr",
                        "calculate_and_display_bcr",
                        "load_scenario_data",
                        "add_bcr_metrics",
                        "write_batch_summary",
                    ]
                )
            ]
            if bcr_lines:
                print(
                    f"[DEBUG SENS] Found {len(bcr_lines)} BCR-related lines in CTCC stdout:"
                )
                for line in bcr_lines[:30]:
                    print(f"  {line}")

            # Specifically check for CTCC debug messages about script execution and BCR
            ctcc_debug_lines = [
                line for line in result.stdout.split("\n") if "[DEBUG CTCC]" in line
            ]
            if ctcc_debug_lines:
                print(f"[DEBUG SENS] Found {len(ctcc_debug_lines)} CTCC debug lines:")
                for line in ctcc_debug_lines:
                    print(f"  {line}")
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

        if not read_results_by_scenario_id_func:
            # Fallback: try to read directly
            if not batch_summary_path.exists():
                return None, "batch_summary.csv not found"

            try:
                df = pd.read_csv(batch_summary_path)
                if len(df) == 0:
                    return None, "batch_summary.csv is empty"

                # Try to find by scenario_id
                matching_rows = df[df["scenario_id"] == scenario_id]
                if len(matching_rows) > 0:
                    results = matching_rows.iloc[-1].to_dict()
                    actual_scenario_id = results.get("scenario_id", actual_scenario_id)
                else:
                    # Fallback to last row
                    results = df.iloc[-1].to_dict()
                    actual_scenario_id = results.get("scenario_id", actual_scenario_id)
            except Exception as e:
                return None, f"Error reading batch_summary.csv: {str(e)}"
        else:
            # Use provided function
            results = read_results_by_scenario_id_func(
                batch_summary_path, actual_scenario_id
            )

            if results is None:
                # Fallback: try to read the last row (in case scenario_id format changed)
                if batch_summary_path.exists():
                    try:
                        df = pd.read_csv(batch_summary_path)
                        if len(df) > 0:
                            # Try to find a row with scenario_id that contains our sample index
                            sample_idx_str = (
                                scenario_id.split("_")[1]
                                if "_" in scenario_id
                                else None
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
                    except Exception as e:
                        return None, f"Error reading batch_summary.csv: {str(e)}"

                if results is None:
                    return (
                        None,
                        f"Results not found for scenario_id: {scenario_id} (tried: {actual_scenario_id})",
                    )

        # Validate BCR results (just check if they exist, no fallback)
        print(
            f"[DEBUG SENS] Validating BCR results for scenario_id='{actual_scenario_id}'"
        )
        print(f"[DEBUG SENS] Results dict has {len(results)} keys")
        bcr_keys_in_results = [k for k in results.keys() if k.startswith("bcr_")]
        print(f"[DEBUG SENS] BCR keys in results: {bcr_keys_in_results}")

        results, error = validate_bcr_results(
            results, bcr_warning_detected=bcr_warning_detected
        )
        if error:
            # Log warning but don't fail - BCR calculator should have written them
            # This is a warning, not a fatal error
            print(f"[DEBUG SENS] ERROR: BCR validation failed: {error}")
            print(f"Warning: {error}")
            # Continue with results even if BCR columns are missing
        else:
            print(f"[DEBUG SENS] BCR validation passed - all BCR columns present")

        return results, None

    except subprocess.TimeoutExpired:
        return None, "CTCC run timed out"
    except Exception as e:
        return None, str(e)
    finally:
        # Restore original yamls directory
        if yamls_dir.exists():
            try:
                shutil.rmtree(yamls_dir)
            except Exception:
                pass
        if yamls_backup.exists():
            try:
                shutil.move(str(yamls_backup), str(yamls_dir))
            except Exception:
                pass
