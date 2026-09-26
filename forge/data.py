"""Access bundled FORGE data (YAML templates, scenarios)."""
from __future__ import annotations

from importlib.resources import files
from pathlib import Path
from typing import Any


def get_yamls_path() -> Path:
    """Return absolute path to the bundled yamls/ directory."""
    return Path(str(files("forge") / "yamls"))


def get_scenarios_path() -> Path:
    """Return absolute path to the bundled scenarios/ directory."""
    return Path(str(files("forge") / "scenarios"))


def get_defaults_template() -> dict[str, Any]:
    """Load and merge all YAML templates into a combined defaults dict."""
    import yaml

    combined: dict[str, Any] = {}
    yamls_dir = get_yamls_path()
    for yaml_file in sorted(yamls_dir.glob("*.yaml")):
        if yaml_file.stem == "project_category_template":
            continue
        with yaml_file.open() as f:
            combined[yaml_file.stem] = yaml.safe_load(f)
    return combined
