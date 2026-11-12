"""Access bundled FORGE data (YAML templates, scenarios)."""
from __future__ import annotations

import copy
from importlib.resources import files
from pathlib import Path
from typing import Any


def get_yamls_path() -> Path:
    """Return absolute path to the bundled yamls/ directory."""
    return Path(str(files("forge") / "yamls"))


def get_emissions_path() -> Path:
    return Path(str(files("forge") / "data" / "emissions"))


def get_cpi_path() -> Path:
    return Path(str(files("forge") / "data" / "cpi_u.csv"))


def iter_emissions_files() -> list[tuple[str, bytes]]:
    root = get_emissions_path()
    pairs = []
    for path in sorted(root.rglob("*")):
        if path.is_file():
            pairs.append((path.relative_to(root).as_posix(), path.read_bytes()))
    if not pairs:
        raise FileNotFoundError("forge/data/emissions is empty")
    return pairs


def get_scenarios_path() -> Path:
    """Return absolute path to the bundled scenarios/ directory."""
    return Path(str(files("forge") / "scenarios"))


_SKIP_STEMS = {"project_category_template", "defaults_registry"}
_DEFAULTS_TEMPLATE: dict[str, Any] | None = None


def _read_defaults_template() -> dict[str, Any]:
    import yaml

    combined: dict[str, Any] = {}
    for yaml_file in sorted(get_yamls_path().glob("*.yaml")):
        if yaml_file.stem in _SKIP_STEMS:
            continue
        with yaml_file.open() as handle:
            combined[yaml_file.stem] = yaml.safe_load(handle)
    return combined


def get_defaults_template() -> dict[str, Any]:
    """Return a deep copy of the bundled defaults.

    The files are read once per process. A calculation must not reread them.
    """
    global _DEFAULTS_TEMPLATE
    if _DEFAULTS_TEMPLATE is None:
        _DEFAULTS_TEMPLATE = _read_defaults_template()
    return copy.deepcopy(_DEFAULTS_TEMPLATE)
