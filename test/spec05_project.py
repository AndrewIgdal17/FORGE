"""Shared project fixture for the spec 05 cross-cutting-rules tests."""
from __future__ import annotations

import json

import forge
from test.spec07_regions import REGION_SENTINELS

SCENARIO = "SunZia_Delay2"

_PROTECTED_ACRES = (
    "02_project_physical_details.terrain.protected_area_acres.forested",
    "02_project_physical_details.terrain.protected_area_acres.scrubbed_flat",
    "02_project_physical_details.terrain.protected_area_acres.desert_barren",
    "02_project_physical_details.terrain.protected_area_acres.rolling_hills",
    "02_project_physical_details.terrain.protected_area_acres.mountain",
)
ACRE_ZEROS = {path: 0.0 for path in _PROTECTED_ACRES}


def measured(**measures: object) -> dict:
    """A valid market-measurement change map.

    Spread, both hour counts, and the receiving energy value are all set.
    The defaults are SunZia_Delay2's stored all-hours spread (15 * 4000 / 8760)
    and energy value (30). Callers that need a number pass this on their changes.
    """
    block = {
        "congestion_spread_per_mwh": 15 * 4000 / 8760,
        "hours_receiving_more_congested": 4000,
        "hours_sending_more_congested": 0,
        "receiving_energy_value_per_mwh": 30.0,
    }
    block.update(measures)
    prefix = "01_project_technical_details.market_measurements."
    return {prefix + key: value for key, value in block.items()}


def project_changes(**overrides: object) -> dict:
    """forge.diff_changes(bundled scenario inputs), then the five
    protected-area acres set to 0.0, then a terminal region when the bundled
    file left that path out, then the overrides. Each override key is a
    dotted input path, passed through **{}:
    project_changes(**{"01_project_technical_details.timeline.delay_years": 2})."""
    forge_file = forge.get_scenarios_path() / f"{SCENARIO}.forge"
    with open(forge_file) as handle:
        document = json.load(handle)
    changes = forge.diff_changes(document["inputs"])
    changes.update(ACRE_ZEROS)
    for path, value in REGION_SENTINELS.items():
        changes.setdefault(path, value)
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
