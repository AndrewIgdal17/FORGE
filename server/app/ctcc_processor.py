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


def merge_user_data_with_template(user_data: Dict[str, Any], template: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge simplified user input data with the full CTCC template structure.
    
    Args:
        user_data: Simplified data from web interface
        template: Full CTCC template with all required sections
        
    Returns:
        Merged data ready for CTCC processing
    """
    # Start with the full template
    merged = template.copy()
    
    # Extract common mappings from user data
    if "scenario" in user_data:
        scenario = user_data["scenario"]
        if "scenario_name" in scenario:
            merged["01_project_technical_details"]["project"]["name"] = scenario["scenario_name"]
    
    if "project" in user_data:
        project = user_data["project"]
        
        # Map project details to 01_project_technical_details
        project_tech = merged["01_project_technical_details"]["project"]
        if "project_name" in project:
            project_tech["name"] = project["project_name"]
        if "line_miles" in project:
            # Update terrain miles in 02_project_physical_details to match total line miles
            total_miles = project["line_miles"]
            terrain = merged["02_project_physical_details"]["terrain"]["terrain_miles"]
            # Simple approach: distribute evenly across existing terrain types
            if total_miles:
                existing_total = sum(terrain.values())
                if existing_total > 0:
                    scale_factor = total_miles / existing_total
                    for terrain_type in terrain:
                        terrain[terrain_type] = terrain[terrain_type] * scale_factor
        if "voltage_kv" in project:
            # Map to appropriate voltage category in build costs
            voltage = project["voltage_kv"]
            if voltage >= 500:
                merged["10_project_category_build_costs"]["category"] = "Above_500kV"
            elif voltage >= 345:
                merged["10_project_category_build_costs"]["category"] = "300_to_500kV"
            elif voltage >= 138:
                merged["10_project_category_build_costs"]["category"] = "138_to_300kV"
            else:
                merged["10_project_category_build_costs"]["category"] = "Below_138kV"
        if "capacity_mw" in project:
            project_tech["capacity_mw"] = project["capacity_mw"]
        if "project_type" in project:
            if project["project_type"] == "reconductoring":
                project_tech["reconductoring"] = True
            else:
                project_tech["reconductoring"] = False
    
    if "project_costs" in user_data:
        costs = user_data["project_costs"]
        if "build_costs_per_mile" in costs:
            # Update build costs - simplified approach
            merged["10_project_category_build_costs"]["costs"]["structures_per_mile"] = costs["build_costs_per_mile"] * 0.6
            merged["10_project_category_build_costs"]["costs"]["conductor_per_mile"] = costs["build_costs_per_mile"] * 0.4
    
    if "financial" in user_data:
        financial = user_data["financial"]
        if "discount_rate" in financial:
            merged["01_project_technical_details"]["project"]["social_discount_rate"] = financial["discount_rate"]
            merged["03_financing"]["wacc"]["real_wacc"] = financial["discount_rate"]
        if "analysis_period_years" in financial:
            merged["01_project_technical_details"]["timeline"]["project_lifetime"] = financial["analysis_period_years"]
    
    return merged


def ensure_cli_venv() -> str:
    """
    Ensure CLI virtual environment exists and has dependencies installed.
    Returns the path to the venv Python executable.
    """
    import subprocess

    venv_dir = CTCC_ROOT / "venv"
    requirements_file = CTCC_ROOT / "requirements.txt"

    # If venv doesn't exist, create it
    if not venv_dir.exists():
        print(f"Creating CLI virtual environment at {venv_dir}")
        subprocess.run(
            [sys.executable, "-m", "venv", str(venv_dir)],
            check=True,
            cwd=str(CTCC_ROOT)
        )

    # Find the Python executable in the venv (try common names)
    possible_pythons = [
        venv_dir / "bin" / "python3",
        venv_dir / "bin" / "python",
        venv_dir / "Scripts" / "python.exe",  # Windows
        venv_dir / "Scripts" / "python3.exe"  # Windows
    ]
    
    venv_python = None
    for python_path in possible_pythons:
        if python_path.exists():
            venv_python = python_path
            break
    
    if venv_python is None:
        # If no venv python found, remove and recreate the venv
        print(f"Virtual environment at {venv_dir} appears broken, recreating...")
        import shutil
        shutil.rmtree(venv_dir)
        subprocess.run(
            [sys.executable, "-m", "venv", str(venv_dir)],
            check=True,
            cwd=str(CTCC_ROOT)
        )
        # Try again to find python
        for python_path in possible_pythons:
            if python_path.exists():
                venv_python = python_path
                break
        
        if venv_python is None:
            raise RuntimeError(f"Virtual environment creation failed: no Python executable found in {venv_dir}")

    # Test if the Python executable actually works
    try:
        subprocess.run([str(venv_python), "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        raise RuntimeError(f"Virtual environment Python executable is not working: {venv_python}")

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

        # For JSON input mode, we need to merge user input with the full template
        temp_json_file = None
        if input_mode == "json" and combined_data:
            # Check if combined_data is already in full CTCC format (has numbered keys like "01_project_technical_details")
            # The web app sends the full structure, so we should use it directly
            is_full_format = any(key.startswith(('0', '1')) and '_' in key for key in combined_data.keys())
            
            if is_full_format:
                # Already in full CTCC format - use directly
                merged_data = combined_data
            else:
                # Simplified format - merge with template
                template_file = Path(__file__).parent.parent / "json" / "final_combined.json"
                if template_file.exists():
                    with open(template_file, 'r') as f:
                        full_template = json.load(f)
                    
                    # Merge user data with template
                    merged_data = merge_user_data_with_template(combined_data, full_template)
                else:
                    # Fallback to user data if template not found
                    merged_data = combined_data
            
            temp_json_file = tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.json',
                prefix=f'ctcc_api_{scenario_id}_',
                delete=False
            )
            json.dump(merged_data, temp_json_file)
            temp_json_file.close()

        try:
            # Build command-line arguments for ctcc.py
            import subprocess

            # Ensure CLI venv exists and has dependencies
            python_exe = ensure_cli_venv()

            # Build command - ctcc.py uses environment variables for mode configuration
            cmd = [python_exe, "ctcc.py"]

            # Set up environment variables for the subprocess
            env = os.environ.copy()
            env["CTCC_INPUT_MODE"] = input_mode
            env["CTCC_OUTPUT_MODE"] = output_mode
            env["CTCC_SCENARIO_ID"] = scenario_id

            # Add JSON file path if available (use absolute path for subprocess scripts)
            if temp_json_file:
                # Convert to absolute path so subprocess scripts can find it regardless of working directory
                json_file_path = os.path.abspath(temp_json_file.name)
                env["CTCC_JSON_DATA_FILE"] = json_file_path

            # Run ctcc.py as subprocess with environment variables
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=str(CTCC_ROOT),
                env=env,
                timeout=600  # 10 minute timeout
            )

            # Log subprocess output for debugging (especially BCR config loading)
            if result.stdout:
                # Look for DEBUG messages
                for line in result.stdout.split('\n'):
                    if 'DEBUG:' in line or 'Warning:' in line:
                        print(f"[CTCC Subprocess] {line}", flush=True)
            if result.stderr:
                # Log any errors
                for line in result.stderr.split('\n'):
                    if line.strip():  # Only log non-empty lines
                        print(f"[CTCC Subprocess STDERR] {line}", flush=True)

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
