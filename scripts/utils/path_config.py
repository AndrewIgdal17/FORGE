# Date: 2025-01-XX
# Description: Centralized path configuration for FORGE scripts.
#              Provides absolute paths based on script location to ensure
#              scripts work when run from any directory or imported as modules.

import os
from pathlib import Path

# This file lives at scripts/utils/path_config.py
_UTILS_DIR = Path(__file__).parent.absolute()
SCRIPTS_DIR = _UTILS_DIR.parent
PROJECT_ROOT = SCRIPTS_DIR.parent

# Define standard directories (server can override YAMLS_DIR via FORGE_YAMLS_DIR for temp input)
YAMLS_DIR = Path(os.environ.get("FORGE_YAMLS_DIR", str(PROJECT_ROOT / "yamls")))
OUTPUTS_DIR = PROJECT_ROOT / "outputs"

# Export for use in other modules
__all__ = ["YAMLS_DIR", "OUTPUTS_DIR", "PROJECT_ROOT", "SCRIPTS_DIR"]

