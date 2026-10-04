# Date: 2025-11-10
# Description: Loader wrapper for the calculator. Calculator uses the active run's
#              input sections; this module re-exports yaml_loaders and provides get_*_raw.

from typing import Any, Dict

from forge.scripts.utils.inputs import section
from .run_context import get_run_context
from forge.scripts.io.yaml_loaders import *  # noqa: F401, F403


def get_project_data_raw() -> Dict[str, Any]:
    """
    Get raw project technical details for the active run.

    Returns:
        Dictionary with 'project' and 'timeline' keys
    """
    data = section("01_project_technical_details")
    if not data:
        raise ValueError("Project technical details YAML file is empty or invalid")
    return data


def get_financing_data_raw() -> Dict[str, Any]:
    """
    Get raw financing data for the active run.

    Returns:
        Dictionary with financing data structure
    """
    data = section("03_financing")
    if not data:
        raise ValueError("Financing YAML file is empty or invalid")
    return data


def get_physical_data_raw() -> Dict[str, Any]:
    """
    Get raw physical project details for the active run.

    Returns:
        Dictionary with 'terrain' key containing terrain_miles
    """
    data = section("02_project_physical_details")
    if not data:
        raise ValueError("Physical details YAML file is empty or invalid")
    return data


def load_terrain_miles() -> Dict[str, float]:
    """
    Load terrain miles dictionary from physical details.
    Reads the active run's physical-details section.
    
    Returns:
        Dictionary mapping terrain types to miles (e.g., {"forested": 10.5, "urban": 2.3})
    
    Raises:
        KeyError: If terrain structure is missing or invalid
    """
    ctx = get_run_context()
    if ctx is not None:
        return ctx.terrain_miles
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
