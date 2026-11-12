import re

import yaml
from forge.contract import resolve_inputs
from forge.data import get_defaults_template, get_yamls_path
from test.spec07_regions import REGION_SENTINELS

_INDEX = re.compile(r"\[(\d+)\]")
_ACRE_PATHS = (
    "02_project_physical_details.terrain.protected_area_acres.forested",
    "02_project_physical_details.terrain.protected_area_acres.scrubbed_flat",
    "02_project_physical_details.terrain.protected_area_acres.desert_barren",
    "02_project_physical_details.terrain.protected_area_acres.rolling_hills",
    "02_project_physical_details.terrain.protected_area_acres.mountain",
)


def _entries(node, prefix=""):
    if isinstance(node, dict) and ("path" in node or ("value" in node and "unit" in node)):
        yield prefix, node
        return
    if isinstance(node, dict):
        for key, child in node.items():
            yield from _entries(child, f"{prefix}.{key}" if prefix else key)


def _walk(root, path):
    current = root
    for part in path.split("."):
        name, *indexes = _INDEX.split(part)
        indexes = [piece for piece in indexes if piece != ""]
        assert isinstance(current, dict) and name in current, path
        current = current[name]
        for raw in indexes:
            index = int(raw)
            assert isinstance(current, list) and index < len(current), path
            current = current[index]
    return current


# A blank template no longer resolves. These are the zeros the old defaults supplied.
_RUNNABLE = {
    "01_project_technical_details.project.capacity_mw": 500,
    "01_project_technical_details.project.value_of_load_per_mwh": 0.0,
    "17_congestion_reductions.greenfield_congestion_reductions.constraints.flow_factor": 0.0,
    "17_congestion_reductions.greenfield_congestion_reductions.prices.average_congestion_price": 0.0,
}
for path, value in REGION_SENTINELS.items():
    _RUNNABLE.setdefault(path, value)


def test_registry_paths_resolve_and_values_are_gone():
    document = yaml.safe_load((get_yamls_path() / "defaults_registry.yaml").read_text())
    template = get_defaults_template()
    for name, entry in _entries(document):
        assert "value" not in entry, name
        node = _walk(template, entry["path"])
        if not isinstance(node, list):
            changes = {path: 0.0 for path in _ACRE_PATHS}
            changes.update(_RUNNABLE)
            if entry["path"] not in changes:
                changes[entry["path"]] = None
            resolve_inputs(changes)
