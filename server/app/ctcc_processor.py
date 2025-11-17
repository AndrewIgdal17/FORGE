"""
CTCC calculation processor for FastAPI.
Delegates to the main ctcc.py for all calculations to maintain consistency.
"""

import sys
import os
import json
import tempfile
from pathlib import Path
from typing import Any, Dict
from datetime import datetime

# Add CTCC root directory to path
CTCC_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(CTCC_ROOT))
sys.path.insert(0, str(CTCC_ROOT / "scripts"))


def ensure_cli_venv() -> str:
    """
    Ensure CLI virtual environment exists and has dependencies installed.
    Returns the path to the venv Python executable.
    """
    import subprocess

    venv_dir = CTCC_ROOT / "venv"
    venv_python = venv_dir / "bin" / "python3"
    requirements_file = CTCC_ROOT / "requirements.txt"

    # If venv doesn't exist, create it
    if not venv_dir.exists():
        print(f"Creating CLI virtual environment at {venv_dir}")
        subprocess.run(
            [sys.executable, "-m", "venv", str(venv_dir)],
            check=True,
            cwd=str(CTCC_ROOT)
        )

    # Verify venv Python exists
    if not venv_python.exists():
        raise RuntimeError(f"Virtual environment creation failed: {venv_python} not found")

    # Install/update dependencies if requirements.txt exists
    if requirements_file.exists():
        print(f"Installing/updating CLI dependencies from {requirements_file}")
        subprocess.run(
            [str(venv_python), "-m", "pip", "install", "--upgrade", "pip"],
            capture_output=True,
            cwd=str(CTCC_ROOT)
        )
        result = subprocess.run(
            [str(venv_python), "-m", "pip", "install", "-r", str(requirements_file)],
            capture_output=True,
            text=True,
            cwd=str(CTCC_ROOT)
        )
        # Only raise if pip failed AND packages are actually missing
        # Exit code 120 can be a warning, not necessarily a failure
        if result.returncode not in [0, 120]:
            raise RuntimeError(
                f"Failed to install dependencies (exit code {result.returncode}):\n"
                f"stdout: {result.stdout}\n"
                f"stderr: {result.stderr}"
            )

    return str(venv_python)


def run_ctcc_calculation(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run complete CTCC calculations based on input payload.

    This function delegates to the main ctcc.py implementation to ensure
    all updates to ctcc.py automatically benefit the API server.

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
        combined_data = payload.get("combined_data")

        # For JSON input mode, write combined_data to temp file
        temp_json_file = None
        if input_mode == "json" and combined_data:
            temp_json_file = tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.json',
                prefix=f'ctcc_api_{scenario_id}_',
                delete=False
            )
            json.dump(combined_data, temp_json_file)
            temp_json_file.close()

        try:
            # Build command-line arguments for ctcc.py
            import subprocess

            # Ensure CLI venv exists and has dependencies
            python_exe = ensure_cli_venv()

            # Build command with flags
            cmd = [python_exe, "ctcc.py"]

            # Add input mode flag
            if input_mode == "json":
                cmd.append("--json")

            # Add output mode flag
            if output_mode == "json":
                cmd.append("--json-out")

            # Add scenario ID
            cmd.extend(["--id", scenario_id])

            # Add JSON file path if available
            if temp_json_file:
                cmd.extend(["--json-file", temp_json_file.name])

            # Run ctcc.py as subprocess with command-line flags
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=str(CTCC_ROOT),
                timeout=600  # 10 minute timeout
            )

            # Parse results based on output mode
            if output_mode == "json":
                # Read the JSON output file
                json_output_file = CTCC_ROOT / "outputs" / f"ctcc_results_{scenario_id}.json"

                if json_output_file.exists():
                    with open(json_output_file, 'r') as f:
                        results = json.load(f)

                    # Clean up the output file
                    try:
                        json_output_file.unlink()
                    except Exception:
                        pass

                    return {
                        "success": result.returncode == 0,
                        "scenario_id": scenario_id,
                        "timestamp": results.get("timestamp", datetime.now().isoformat()),
                        "input_mode": input_mode,
                        "output_mode": "json",
                        "csv_files": None,
                        "results": results,
                        "error": result.stderr[:500] if result.returncode != 0 else None
                    }
                else:
                    return {
                        "success": False,
                        "scenario_id": scenario_id,
                        "timestamp": datetime.now().isoformat(),
                        "input_mode": input_mode,
                        "output_mode": "json",
                        "csv_files": None,
                        "results": None,
                        "error": f"JSON output file not found. stderr: {result.stderr[:500]}"
                    }

            else:  # CSV mode
                # Check which CSV files were created
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

                outputs_dir = CTCC_ROOT / "outputs"
                existing_csv_files = [
                    csv_file for csv_file in csv_files
                    if (outputs_dir / csv_file).exists()
                ]

                return {
                    "success": result.returncode == 0 and len(existing_csv_files) > 0,
                    "scenario_id": scenario_id,
                    "timestamp": datetime.now().isoformat(),
                    "input_mode": input_mode,
                    "output_mode": "csv",
                    "csv_files": existing_csv_files,
                    "results": None,
                    "error": result.stderr[:500] if result.returncode != 0 else None,
                    "output_dir": str(outputs_dir)
                }

        finally:
            # Clean up temporary JSON input file
            if temp_json_file and os.path.exists(temp_json_file.name):
                try:
                    os.unlink(temp_json_file.name)
                except Exception:
                    pass  # Ignore cleanup errors

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "scenario_id": scenario_id,
            "timestamp": datetime.now().isoformat(),
            "input_mode": input_mode,
            "output_mode": output_mode,
            "csv_files": None,
            "results": None,
            "error": "Calculation timeout after 10 minutes"
        }

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
