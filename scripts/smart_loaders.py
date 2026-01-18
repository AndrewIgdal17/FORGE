# Author: Claude Code
# Date: 2025-11-10
# Description: Smart loader wrapper that automatically chooses yaml_loaders or json_loaders
#              based on environment variable. This allows calculation scripts to work
#              with both YAML and JSON input without modification.

import os
from typing import Any, Dict

# Check environment variable to determine which loader to use
_input_mode = os.environ.get('CTCC_INPUT_MODE', 'yaml').lower()

if _input_mode == 'json':
    # Use JSON loaders
    from json_loaders import *  # noqa: F401, F403
else:
    # Use YAML loaders (default)
    from yaml_loaders import *  # noqa: F401, F403


def get_input_mode() -> str:
    """
    Get the current input mode.

    Returns:
        "json" or "yaml"
    """
    return _input_mode


def get_project_data_raw() -> Dict[str, Any]:
    """
    Get raw project technical details data.
    Works in both YAML and JSON input modes.
    
    Returns:
        Dictionary with 'project' and 'timeline' keys
        
    Raises:
        FileNotFoundError: When project technical details file is not found
        ValueError: When file is empty or invalid
    """
    input_mode = get_input_mode()
    if input_mode == "json":
        from json_loaders import _data_source
        return _data_source.get_data("01_project_technical_details")
    else:
        # YAML mode
        import yaml
        from path_config import YAMLS_DIR
        with open(YAMLS_DIR / "01_project_technical_details.yaml", "r") as file:
            data = yaml.safe_load(file)
            if not data:
                raise ValueError("Project technical details YAML file is empty or invalid")
            return data


def get_financing_data_raw() -> Dict[str, Any]:
    """
    Get raw financing data.
    Works in both YAML and JSON input modes.
    
    Returns:
        Dictionary with financing data structure
        
    Raises:
        FileNotFoundError: When financing file is not found
        ValueError: When file is empty or invalid
    """
    input_mode = get_input_mode()
    if input_mode == "json":
        from json_loaders import _data_source
        return _data_source.get_data("03_financing")
    else:
        # YAML mode
        import yaml
        from path_config import YAMLS_DIR
        with open(YAMLS_DIR / "03_financing.yaml", "r") as file:
            data = yaml.safe_load(file)
            if not data:
                raise ValueError("Financing YAML file is empty or invalid")
            return data


def get_physical_data_raw() -> Dict[str, Any]:
    """
    Get raw physical project details data.
    Works in both YAML and JSON input modes.
    
    Returns:
        Dictionary with 'terrain' key containing terrain_miles
        
    Raises:
        FileNotFoundError: When physical details file is not found
        ValueError: When file is empty or invalid
    """
    input_mode = get_input_mode()
    if input_mode == "json":
        from json_loaders import _data_source
        return _data_source.get_data("02_project_physical_details")
    else:
        # YAML mode
        import yaml
        from path_config import YAMLS_DIR
        with open(YAMLS_DIR / "02_project_physical_details.yaml", "r") as file:
            data = yaml.safe_load(file)
            if not data:
                raise ValueError("Physical details YAML file is empty or invalid")
            return data
