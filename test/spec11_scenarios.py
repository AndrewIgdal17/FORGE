"""Bundled scenarios as change maps, for the Spec 11 tests."""
from __future__ import annotations

import json

import forge
from test.spec05_project import ACRE_ZEROS
from test.spec07_regions import REGION_SENTINELS

SCENARIOS = ("SunZia_Delay2", "CTT_Actual_Delay2", "AEP_LRGV_ACCC", "AEP_LRGV_ACSR_Rebuild")

_PROJECT = "01_project_technical_details.project."

DC_RECONDUCTORING: dict[str, object] = {
    _PROJECT + "ac_dc": "DC",
    _PROJECT + "old_ac_dc": "DC",
    _PROJECT + "number_of_converters": 2,
    _PROJECT + "converter_type": "VSC Converter",
    _PROJECT + "old_converter_type": "VSC Converter",
    _PROJECT + "capacity_mw": 2400,
    _PROJECT + "old_capacity_mw": 2400,
}


def scenario_changes(name: str, **overrides: object) -> dict:
    """forge.diff_changes(bundled inputs) with protected acres 0, region sentinels, then overrides."""
    with open(forge.get_scenarios_path() / f"{name}.forge") as handle:
        document = json.load(handle)
    changes = forge.diff_changes(document["inputs"])
    changes.update(ACRE_ZEROS)
    for path, value in REGION_SENTINELS.items():
        changes.setdefault(path, value)
    changes.update(overrides)
    return changes


def numbers(results: dict) -> dict:
    """Every ratio and total in bcr, and every item's value_pv."""
    bcr = {k: v for k, v in results["bcr"].items() if k != "omitted" and (v is None or isinstance(v, (int, float)))}
    items = {e["taxonomy_id"]: e["value_pv"] for e in results["taxonomy_results"]}
    return {"bcr": bcr, "items": items}
