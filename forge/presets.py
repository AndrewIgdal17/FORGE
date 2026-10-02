"""Access bundled FORGE grid-mix presets."""
from __future__ import annotations

from importlib.resources import files
from typing import Any

_SOURCES = {"coal", "oil", "natural_gas", "solar", "wind", "hydro", "nuclear", "other"}
_GROUPS = ("initial", "rate_pre_cod", "rate_post_cod")


def get_grid_mix_presets() -> list[dict[str, Any]]:
    """Load and validate the bundled grid-mix presets."""
    import yaml

    path = files("forge") / "presets" / "grid_mix.yaml"
    presets = yaml.safe_load(path.read_text())

    for preset in presets:
        grid_mix = preset["grid_mix"]
        if set(grid_mix) != set(_GROUPS):
            raise ValueError(f"preset {preset['id']!r} has invalid grid_mix groups")
        for group in _GROUPS:
            if set(grid_mix[group]) != _SOURCES:
                raise ValueError(f"preset {preset['id']!r} has invalid sources in {group!r}")

    return presets
