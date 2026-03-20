# Author: Dane McFarlane
# Date: 2025-11-10
# Description: Loader wrapper for the calculator. Calculator uses YAML input only;
#              this module re-exports yaml_loaders and provides get_*_raw from YAMLS_DIR.

import yaml
from typing import Any, Dict

from path_config import YAMLS_DIR
from yaml_loaders import *  # noqa: F401, F403


def get_input_mode() -> str:
    """Current input mode; calculator is YAML-in only."""
    return "yaml"


def get_project_data_raw() -> Dict[str, Any]:
    """
    Get raw project technical details from YAML.

    Returns:
        Dictionary with 'project' and 'timeline' keys
    """
    with open(YAMLS_DIR / "01_project_technical_details.yaml", "r") as file:
        data = yaml.safe_load(file)
        if not data:
            raise ValueError("Project technical details YAML file is empty or invalid")
        return data


def get_financing_data_raw() -> Dict[str, Any]:
    """
    Get raw financing data from YAML.

    Returns:
        Dictionary with financing data structure
    """
    with open(YAMLS_DIR / "03_financing.yaml", "r") as file:
        data = yaml.safe_load(file)
        if not data:
            raise ValueError("Financing YAML file is empty or invalid")
        return data


def get_physical_data_raw() -> Dict[str, Any]:
    """
    Get raw physical project details from YAML.

    Returns:
        Dictionary with 'terrain' key containing terrain_miles
    """
    with open(YAMLS_DIR / "02_project_physical_details.yaml", "r") as file:
        data = yaml.safe_load(file)
        if not data:
            raise ValueError("Physical details YAML file is empty or invalid")
        return data


def load_terrain_miles() -> Dict[str, float]:
    """
    Load terrain miles dictionary from physical details.
    Reads from YAML files under YAMLS_DIR.
    
    Returns:
        Dictionary mapping terrain types to miles (e.g., {"forested": 10.5, "urban": 2.3})
    
    Raises:
        KeyError: If terrain structure is missing or invalid
    """
    try:
        physical_details = get_physical_data_raw()
        if "terrain" not in physical_details:
            raise KeyError("Missing 'terrain' key in physical details")
        if "terrain_miles" not in physical_details["terrain"]:
            raise KeyError(
                "Missing 'terrain_miles' key in terrain section of physical details"
            )
        terrain_miles = physical_details["terrain"]["terrain_miles"]
        return terrain_miles
    except KeyError as e:
        raise KeyError(f"Missing required key in physical details: {e}")
