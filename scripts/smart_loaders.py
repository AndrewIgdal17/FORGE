# Author: Claude Code
# Date: 2025-11-10
# Description: Smart loader wrapper that automatically chooses yaml_loaders or json_loaders
#              based on environment variable. This allows calculation scripts to work
#              with both YAML and JSON input without modification.

import os
from typing import Any

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
