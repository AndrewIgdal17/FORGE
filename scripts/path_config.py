# Date: 2025-01-XX
# Description: Centralized path configuration for FORGE scripts.
#              Provides absolute paths based on script location to ensure
#              scripts work when run from any directory or imported as modules.

import os
from pathlib import Path

# Get the directory where this file is located (scripts/)
SCRIPT_DIR = Path(__file__).parent.absolute()

# Get project root (parent of scripts/)
PROJECT_ROOT = SCRIPT_DIR.parent

# Define standard directories (server can override YAMLS_DIR via FORGE_YAMLS_DIR for temp input)
YAMLS_DIR = Path(os.environ.get("FORGE_YAMLS_DIR", str(PROJECT_ROOT / "yamls")))
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
SCRIPTS_DIR = SCRIPT_DIR

# Export for use in other modules
__all__ = ["YAMLS_DIR", "OUTPUTS_DIR", "PROJECT_ROOT", "SCRIPTS_DIR"]

