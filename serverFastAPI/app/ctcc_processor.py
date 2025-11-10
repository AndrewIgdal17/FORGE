"""
CTCC calculation processor for FastAPI.
Orchestrates all CTCC calculation scripts with JSON input/output support.
Uses parallel JSON-specific loaders and output managers (json_loaders.py, json_output_manager.py).
"""

import sys
import os
import subprocess
from pathlib import Path
from typing import Any, Dict
from datetime import datetime

# Add CTCC scripts directory to path
CTCC_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(CTCC_ROOT / "scripts"))


def run_ctcc_calculation(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run complete CTCC calculations based on input payload.

    Args:
        payload: Dictionary containing:
            - input_mode: "json" or "yaml"
            - output_mode: "json" or "csv"
            - combined_data: Full configuration JSON (if input_mode="json")
            - scenario_id: Optional scenario identifier

    Returns:
        Dictionary containing calculation results or error information
    """
    try:
        # Extract parameters
        input_mode = payload.get("input_mode", "json")
        output_mode = payload.get("output_mode", "json")
        scenario_id = payload.get("scenario_id") or datetime.now().strftime("%Y%m%d_%H%M%S")

        # Route to appropriate implementation based on modes
        if input_mode == "json" and output_mode == "json":
            # JSON input → JSON output (full API mode)
            return run_json_to_json(payload, scenario_id)

        elif input_mode == "yaml" and output_mode == "csv":
            # YAML input → CSV output (traditional mode via API)
            return run_yaml_to_csv(scenario_id)

        else:
            # Mixed modes - use subprocess approach for now
            return run_via_subprocess(scenario_id, input_mode, output_mode)

    except Exception as e:
        # Return error information
        return {
            "success": False,
            "scenario_id": payload.get("scenario_id", "unknown"),
            "timestamp": datetime.now().isoformat(),
            "input_mode": payload.get("input_mode", "json"),
            "output_mode": payload.get("output_mode", "json"),
            "csv_files": None,
            "results": None,
            "error": str(e)
        }


def run_json_to_json(payload: Dict[str, Any], scenario_id: str) -> Dict[str, Any]:
    """
    Run calculations with JSON input and JSON output.
    Uses json_loaders.py and json_output_manager.py.
    """
    import json
    import tempfile

    # Import JSON-specific modules
    from json_loaders import set_json_data
    from json_output_manager import JSONOutputManager

    combined_data = payload.get("combined_data")
    if not combined_data:
        raise ValueError("combined_data required when input_mode='json'")

    # Write JSON data to temporary file for subprocess access
    # This allows subprocesses to load the data via environment variable pointing to the file
    temp_json_file = None
    try:
        # Create temporary file with JSON data
        temp_json_file = tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.json',
            prefix=f'ctcc_data_{scenario_id}_',
            delete=False
        )
        json.dump(combined_data, temp_json_file)
        temp_json_file.close()

        # Set JSON data source for parent process (in case we need it)
        set_json_data(combined_data)

        # Initialize JSON output manager
        output_manager = JSONOutputManager(scenario_id=scenario_id)

        # Run all calculation scripts via subprocess
        # This ensures they use json_loaders under the hood
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
        ]

        # Set environment variable for scenario ID and JSON data file path
        env = os.environ.copy()
        env['CTCC_SCENARIO_ID'] = scenario_id
        env['CTCC_INPUT_MODE'] = 'json'  # Signal to scripts to use json_loaders
        env['CTCC_OUTPUT_MODE'] = 'json'  # Signal to scripts to use json_output_manager
        env['CTCC_JSON_DATA_FILE'] = temp_json_file.name  # Path to JSON data for subprocesses

        successful_runs = 0
        errors = []

        # Use python3 from venv if available, otherwise use sys.executable
        python_exe = sys.executable
        venv_python = CTCC_ROOT / "venv" / "bin" / "python3"
        if venv_python.exists():
            python_exe = str(venv_python)

        for script in scripts:
            try:
                result = subprocess.run(
                    [python_exe, script],
                    capture_output=True,
                    text=True,
                    cwd=str(CTCC_ROOT / "scripts"),
                    env=env,
                    timeout=120  # 2 minute timeout per script
                )

                if result.returncode == 0:
                    successful_runs += 1
                else:
                    errors.append(f"{script}: {result.stderr[:200]}")

            except subprocess.TimeoutExpired:
                errors.append(f"{script}: Timeout after 120 seconds")
            except Exception as e:
                errors.append(f"{script}: {str(e)}")

        # Aggregate JSON output files from subprocesses
        import glob
        json_pattern = str(CTCC_ROOT / "outputs" / f"json_output_{scenario_id}_*.json")
        json_files = glob.glob(json_pattern)
        for json_file in json_files:
            try:
                output_manager.load_from_file(json_file)
            except Exception as e:
                errors.append(f"Loading {os.path.basename(json_file)}: {str(e)}")

        # Calculate BCR metrics
        try:
            from bcr_calculator import calculate_and_display_bcr
            bcr_results = calculate_and_display_bcr(scenario_id, output_dir=str(CTCC_ROOT / "outputs"))
            if bcr_results:
                output_manager.add_bcr_metrics(bcr_results)
        except Exception as e:
            errors.append(f"BCR calculation: {str(e)}")

        # Get results from output manager
        results = output_manager.get_json_results()

        return {
            "success": len(errors) == 0,
            "scenario_id": scenario_id,
            "timestamp": output_manager.timestamp,
            "input_mode": "json",
            "output_mode": "json",
            "csv_files": None,
            "results": results,
            "error": "; ".join(errors) if errors else None,
            "scripts_run": successful_runs,
            "total_scripts": len(scripts)
        }

    finally:
        # Clean up temporary JSON files
        if temp_json_file and os.path.exists(temp_json_file.name):
            try:
                os.unlink(temp_json_file.name)
            except Exception:
                pass  # Ignore cleanup errors

        # Clean up JSON output files
        import glob
        json_pattern = str(CTCC_ROOT / "outputs" / f"json_output_{scenario_id}_*.json")
        for json_file in glob.glob(json_pattern):
            try:
                os.unlink(json_file)
            except Exception:
                pass  # Ignore cleanup errors


def run_yaml_to_csv(scenario_id: str) -> Dict[str, Any]:
    """
    Run calculations with YAML input and CSV output.
    Uses original yaml_loaders.py and csv_output_manager.py via subprocess.
    """
    # Run ctcc.py as subprocess with the scenario ID
    env = os.environ.copy()
    env['CTCC_SCENARIO_ID'] = scenario_id

    try:
        result = subprocess.run(
            [sys.executable, "ctcc.py"],
            capture_output=True,
            text=True,
            cwd=str(CTCC_ROOT),
            env=env,
            timeout=600  # 10 minute timeout for full run
        )

        if result.returncode == 0:
            # Parse output to get list of generated CSV files
            csv_files = [
                "batch_summary.csv",
                "build_costs.csv",
                "row_costs.csv",
                "environmental_mitigation.csv",
                "delay_costs.csv",
                "insurance_costs.csv",
                "wildfire_costs.csv",
                "outage_costs.csv",
                "congestion_curtailment.csv",
                "emissions_costs.csv",
                "line_loss_costs.csv",
                "oandm_costs.csv",
            ]

            return {
                "success": True,
                "scenario_id": scenario_id,
                "timestamp": datetime.now().isoformat(),
                "input_mode": "yaml",
                "output_mode": "csv",
                "csv_files": csv_files,
                "results": None,
                "error": None,
                "output_dir": str(CTCC_ROOT / "outputs")
            }
        else:
            return {
                "success": False,
                "scenario_id": scenario_id,
                "timestamp": datetime.now().isoformat(),
                "input_mode": "yaml",
                "output_mode": "csv",
                "csv_files": None,
                "results": None,
                "error": result.stderr[:500]
            }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "scenario_id": scenario_id,
            "timestamp": datetime.now().isoformat(),
            "input_mode": "yaml",
            "output_mode": "csv",
            "csv_files": None,
            "results": None,
            "error": "Calculation timeout after 10 minutes"
        }


def run_via_subprocess(scenario_id: str, input_mode: str, output_mode: str) -> Dict[str, Any]:
    """
    Run calculations for mixed modes via subprocess.
    This is a fallback for mode combinations not yet optimized.
    """
    env = os.environ.copy()
    env['CTCC_SCENARIO_ID'] = scenario_id
    env['CTCC_INPUT_MODE'] = input_mode
    env['CTCC_OUTPUT_MODE'] = output_mode

    try:
        result = subprocess.run(
            [sys.executable, "ctcc.py"],
            capture_output=True,
            text=True,
            cwd=str(CTCC_ROOT),
            env=env,
            timeout=600
        )

        return {
            "success": result.returncode == 0,
            "scenario_id": scenario_id,
            "timestamp": datetime.now().isoformat(),
            "input_mode": input_mode,
            "output_mode": output_mode,
            "csv_files": None if output_mode == "json" else ["batch_summary.csv"],
            "results": None if output_mode == "csv" else {},
            "error": result.stderr[:500] if result.returncode != 0 else None
        }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "scenario_id": scenario_id,
            "timestamp": datetime.now().isoformat(),
            "input_mode": input_mode,
            "output_mode": output_mode,
            "csv_files": None,
            "results": None,
            "error": "Calculation timeout"
        }
