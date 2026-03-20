"""
CTCC calculation processor for FastAPI.
Delegates to the main ctcc.py for all calculations to maintain consistency.
Server converts client JSON to YAML at the boundary; calculator is YAML-in, JSON-out.
"""

import sys
import os
import json
import subprocess
import shutil
import tempfile
import yaml
from pathlib import Path
from typing import Any, Dict
from datetime import datetime

from .models import UserMergeInput

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


def run_ctcc_calculation(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run complete CTCC calculations based on input payload.
    Server converts client JSON to YAML; calculator is YAML-in, JSON-out.
    API still accepts and returns JSON.

    Args:
        payload: Dictionary containing:
            - combined_data: Full or simplified configuration JSON (merged with template if simplified)
            - scenario_id: Optional scenario identifier
            - input_mode: Accepted for backwards compatibility but ignored; calculator always uses YAML

    Returns:
        Dictionary containing calculation results (JSON) or error information
    """
    input_mode = payload.get("input_mode", "json")
    scenario_id = payload.get("scenario_id") or datetime.now().strftime("%b %d %Y %H.%M.%S")
    combined_data = payload.get("combined_data")
    temp_yaml_dir = None

    try:
        env = os.environ.copy()
        env["CTCC_SCENARIO_ID"] = scenario_id
        env["CTCC_OUTPUT_MODE"] = "json"

        if combined_data:
            # Merge with template if simplified format
            is_full_format = any(
                key.startswith(("0", "1")) and "_" in key for key in combined_data.keys()
            )
            if is_full_format:
                merged_data = combined_data
            else:
                template_file = Path(__file__).parent.parent / "json" / "final_combined.json"
                if template_file.exists():
                    with open(template_file, "r") as f:
                        full_template = json.load(f)
                    user_input = UserMergeInput.model_validate(combined_data)
                    merged_data = merge_user_data_with_template(
                        user_input.model_dump(exclude_none=True), full_template
                    )
                else:
                    merged_data = combined_data

            # Write merged data to temp YAML dir (one file per key)
            temp_yaml_dir = tempfile.mkdtemp(prefix=f"ctcc_yaml_{scenario_id}_")
            for key, value in merged_data.items():
                yaml_path = os.path.join(temp_yaml_dir, f"{key}.yaml")
                with open(yaml_path, "w") as f:
                    yaml.dump(value, f, default_flow_style=False, sort_keys=False)
            env["CTCC_YAMLS_DIR"] = os.path.abspath(temp_yaml_dir)

        cmd = [sys.executable, "ctcc.py"]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(CTCC_ROOT),
            env=env,
            timeout=600,
        )

        if result.stdout:
            for line in result.stdout.split("\n"):
                if "DEBUG:" in line or "Warning:" in line:
                    print(f"[CTCC Subprocess] {line}", flush=True)
        if result.stderr:
            for line in result.stderr.split("\n"):
                if line.strip():
                    print(f"[CTCC Subprocess STDERR] {line}", flush=True)

        json_output_file = CTCC_ROOT / "outputs" / f"ctcc_results_{scenario_id}.json"
        if json_output_file.exists():
            with open(json_output_file, "r") as f:
                results = json.load(f)
            try:
                json_output_file.unlink()
            except Exception:
                pass
            return {
                "success": result.returncode == 0,
                "scenario_id": scenario_id,
                "timestamp": results.get("timestamp", datetime.now().isoformat()),
                "input_mode": input_mode,
                "results": results,
                "error": result.stderr[:500] if result.returncode != 0 else None,
            }
        return {
            "success": False,
            "scenario_id": scenario_id,
            "timestamp": datetime.now().isoformat(),
            "input_mode": input_mode,
            "results": None,
            "error": f"JSON output file not found. stderr: {result.stderr[:500]}",
        }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "scenario_id": scenario_id,
            "timestamp": datetime.now().isoformat(),
            "input_mode": input_mode,
            "results": None,
            "error": "Calculation timeout after 10 minutes",
        }

    except Exception as e:
        return {
            "success": False,
            "scenario_id": payload.get("scenario_id", "unknown"),
            "timestamp": datetime.now().isoformat(),
            "input_mode": payload.get("input_mode", "json"),
            "results": None,
            "error": str(e),
        }

    finally:
        if temp_yaml_dir and os.path.exists(temp_yaml_dir):
            try:
                shutil.rmtree(temp_yaml_dir)
            except Exception:
                pass
