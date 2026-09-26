# Centralized path configuration for FORGE calculator.
# After packaging, this file lives at forge/scripts/utils/path_config.py.
# PROJECT_ROOT resolves to the forge/ package root.

import os
from pathlib import Path

_UTILS_DIR = Path(__file__).parent.absolute()
SCRIPTS_DIR = _UTILS_DIR.parent
PROJECT_ROOT = SCRIPTS_DIR.parent  # forge/ package root

# YAMLS_DIR: inside the package (forge/yamls/) by default; env override for server temp input
YAMLS_DIR = Path(os.environ.get("FORGE_YAMLS_DIR", str(PROJECT_ROOT / "yamls")))

# OUTPUTS_DIR: writable output goes to cwd/outputs by default (not inside the installed package)
OUTPUTS_DIR = Path(os.environ.get("FORGE_OUTPUTS_DIR", str(Path.cwd() / "outputs")))

__all__ = ["YAMLS_DIR", "OUTPUTS_DIR", "PROJECT_ROOT", "SCRIPTS_DIR"]
