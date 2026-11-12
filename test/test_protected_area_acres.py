import pytest

import forge
from forge.contract import missing_protected_area_acres
from forge.errors import InvalidInputs
from test.spec07_regions import REGION_SENTINELS

PATHS = (
    "02_project_physical_details.terrain.protected_area_acres.forested",
    "02_project_physical_details.terrain.protected_area_acres.scrubbed_flat",
    "02_project_physical_details.terrain.protected_area_acres.desert_barren",
    "02_project_physical_details.terrain.protected_area_acres.rolling_hills",
    "02_project_physical_details.terrain.protected_area_acres.mountain",
)


def test_empty_changes_name_every_missing_path():
    with pytest.raises(InvalidInputs) as exc:
        forge.resolve_inputs({})
    message = str(exc.value)
    assert message.startswith("protected_area_acres are required. Missing: ")
    for path in PATHS:
        assert path in message


def test_explicit_zero_is_accepted_and_a_string_is_named():
    changes = {path: 0.0 for path in PATHS}
    changes.update({
        "01_project_technical_details.project.capacity_mw": 500,
        "01_project_technical_details.project.value_of_load_per_mwh": 0.0,
        "17_congestion_reductions.greenfield_congestion_reductions.constraints.flow_factor": 0.0,
        "17_congestion_reductions.greenfield_congestion_reductions.prices.average_congestion_price": 0.0,
    })
    for path, value in REGION_SENTINELS.items():
        changes.setdefault(path, value)
    resolved = forge.resolve_inputs(changes)
    assert missing_protected_area_acres(resolved) == []
    changes[PATHS[0]] = "nope"
    with pytest.raises(InvalidInputs, match=PATHS[0]):
        forge.resolve_inputs(changes)


def test_negative_forested_acres_are_required():
    changes = {path: 0 for path in PATHS}
    changes[PATHS[0]] = -1
    with pytest.raises(InvalidInputs) as exc:
        forge.resolve_inputs(changes)
    assert "02_project_physical_details.terrain.protected_area_acres.forested" in str(exc.value)
