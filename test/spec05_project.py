"""Shared project fixture for the spec 05 cross-cutting-rules tests."""
from __future__ import annotations

import json

import forge

SCENARIO = "SunZia_Delay2"

_PROTECTED_ACRES = (
    "02_project_physical_details.terrain.protected_area_acres.forested",
    "02_project_physical_details.terrain.protected_area_acres.scrubbed_flat",
    "02_project_physical_details.terrain.protected_area_acres.desert_barren",
    "02_project_physical_details.terrain.protected_area_acres.rolling_hills",
    "02_project_physical_details.terrain.protected_area_acres.mountain",
)
ACRE_ZEROS = {path: 0.0 for path in _PROTECTED_ACRES}


_ENERGY = "01_project_technical_details.project.value_of_load_per_mwh"
_SPREAD = (
    "17_congestion_reductions.greenfield_congestion_reductions"
    ".prices.average_congestion_price"
)
# SunZia_Delay2's current energy value and greenfield congestion price.
# Task 5 writes the bundled files; until a file carries the leaf, the fixture does.
_BASE_ENERGY = 30.0
_BASE_SPREAD = 15.0


def project_changes(**overrides: object) -> dict:
    """forge.diff_changes(bundled scenario inputs), then the five
    protected-area acres set to 0.0, then the energy value and greenfield
    spread when the bundled file lacks them, then the overrides. Each override
    key is a dotted input path, passed through **{}:
    project_changes(**{"01_project_technical_details.timeline.delay_years": 2})."""
    forge_file = forge.get_scenarios_path() / f"{SCENARIO}.forge"
    with open(forge_file) as handle:
        document = json.load(handle)
    changes = forge.diff_changes(document["inputs"])
    changes.update(ACRE_ZEROS)
    project = document["inputs"]["01_project_technical_details"]["project"]
    prices = document["inputs"]["17_congestion_reductions"]["greenfield_congestion_reductions"]["prices"]
    if project.get("value_of_load_per_mwh") is None:
        changes.setdefault(_ENERGY, _BASE_ENERGY)
    if prices.get("average_congestion_price") is None:
        changes.setdefault(_SPREAD, _BASE_SPREAD)
    changes.update(overrides)
    return changes


def run(changes: dict | None = None, **flags) -> dict:
    """forge.run_calculation(forge.resolve_inputs(changes or project_changes()), **flags)."""
    return forge.run_calculation(
        forge.resolve_inputs(changes if changes is not None else project_changes()),
        **flags,
    )


def item(results: dict, taxonomy_id: str) -> dict:
    """The entry of results['taxonomy_results'] with that taxonomy_id; KeyError if absent."""
    for entry in results["taxonomy_results"]:
        if entry["taxonomy_id"] == taxonomy_id:
            return entry
    raise KeyError(taxonomy_id)
