"""F3: the ROW agreement defaults by project type when none is chosen.

Greenfield defaults to a new permanent easement (acquisition and holding, no
rent). Reconductoring and rebuild default to a lease or license of the existing
corridor (rent from year 1, no acquisition or holding).
"""

import json

import pytest

import forge
from forge.errors import InvalidInputs
from test.spec07_regions import REGION_SENTINELS

AGREEMENT = "01_project_technical_details.project.row_agreement_type"
ZONE_MILES = "11_project_row_details.right_of_way.zone_1.miles"
ACRES = {
    f"02_project_physical_details.terrain.protected_area_acres.{k}": 0.0
    for k in ("forested", "scrubbed_flat", "desert_barren", "rolling_hills", "mountain")
}


def _run(scenario: str, **overrides) -> dict:
    doc = json.loads((forge.get_scenarios_path() / f"{scenario}.forge").read_text())
    changes = forge.diff_changes(doc["inputs"])
    changes.update(ACRES)
    changes.update({ZONE_MILES: 50.0})
    for path, value in REGION_SENTINELS.items():
        changes.setdefault(path, value)
    changes.update(overrides)
    return forge.run_calculation(forge.resolve_inputs(changes))


def _row(results: dict) -> dict:
    return results["costs"]["row"]


def test_template_leaves_the_agreement_unchosen():
    project = forge.get_defaults_template()["01_project_technical_details"]["project"]
    assert project["row_agreement_type"] is None


def test_greenfield_defaults_to_a_new_easement():
    row = _row(_run("SunZia_Delay2", **{AGREEMENT: None}))
    assert row["acquisition_nominal"] > 0
    assert row["rent_nominal"] == 0


def test_rebuild_defaults_to_a_lease():
    row = _row(_run("AEP_LRGV_ACSR_Rebuild", **{AGREEMENT: None}))
    assert row["acquisition_nominal"] == 0
    assert row["rent_nominal"] > 0


def test_reconductoring_defaults_to_a_lease():
    row = _row(_run("AEP_LRGV_ACCC", **{AGREEMENT: None}))
    assert row["acquisition_nominal"] == 0
    assert row["rent_nominal"] > 0


@pytest.mark.parametrize(
    "chosen, acquires, rents",
    [
        ("permanent_easement_new", True, False),
        ("lease_license_existing", False, True),
        ("federal_hybrid", True, True),
    ],
)
def test_a_chosen_agreement_is_kept_for_rebuild(chosen, acquires, rents):
    row = _row(_run("AEP_LRGV_ACSR_Rebuild", **{AGREEMENT: chosen}))
    assert (row["acquisition_nominal"] > 0) is acquires
    assert (row["rent_nominal"] > 0) is rents


def test_fee_simple_is_rejected_with_the_message():
    with pytest.raises(InvalidInputs, match="fee_simple is no longer an agreement type"):
        _run("SunZia_Delay2", **{AGREEMENT: "fee_simple"})


def test_fee_simple_change_names_the_fix():
    errors = forge.validate_changes({AGREEMENT: "fee_simple"})
    assert errors == [{
        "path": AGREEMENT,
        "message": "fee_simple is no longer an agreement type. Choose another agreement.",
    }]
