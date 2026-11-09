"""ROW agreement type defaults, fee_simple rejection, and legacy field tolerance."""
from __future__ import annotations

import copy

import pytest

from forge.contract import validate_changes
from forge.errors import InvalidInputs
from forge.scripts.io.yaml_loaders import load_project_technical_details
from forge.scripts.utils.run_context import RunState, reset_run_state, set_run_state

_FEE_SIMPLE_MSG = "fee_simple is no longer an agreement type. Choose another agreement."
_ROW_PATH = "01_project_technical_details.project.row_agreement_type"

_PROJECT_BASE = {
    "construction_type": "Overhead",
    "ac_dc": "AC",
    "number_of_converters": 0,
    "capacity_mw": 1792,
    "conductor_type": "Standard Aluminum Conductor",
    "converter_type": "NA",
    "converter_loss_percentage": None,
    "line_utilization": 0.65,
    "value_of_load_per_mwh": 42.0,
}

_TIMELINE = {
    "construction_years": 3,
    "delay_years": 1,
    "project_lifetime": 50,
}


def _technical_inputs(project: dict) -> dict:
    return {
        "01_project_technical_details": {
            "project": project,
            "timeline": copy.deepcopy(_TIMELINE),
        }
    }


def _load_with_inputs(inputs: dict):
    state = RunState(inputs=copy.deepcopy(inputs), scenario_id="test-row-agreement")
    token = set_run_state(state)
    try:
        return load_project_technical_details()
    finally:
        reset_run_state(token)


@pytest.mark.parametrize("project_type", ["greenfield", "reconductoring", "rebuild"])
def test_missing_agreement_defaults_to_permanent_easement_new(project_type):
    project = {**_PROJECT_BASE, "project_type": project_type}
    details = _load_with_inputs(_technical_inputs(project))
    assert details.row_agreement_type == "permanent_easement_new"


@pytest.mark.parametrize("project_type", ["greenfield", "reconductoring", "rebuild"])
def test_null_agreement_defaults_to_permanent_easement_new(project_type):
    project = {**_PROJECT_BASE, "project_type": project_type, "row_agreement_type": None}
    details = _load_with_inputs(_technical_inputs(project))
    assert details.row_agreement_type == "permanent_easement_new"


@pytest.mark.parametrize(
    "project_type",
    ["greenfield", "reconductoring", "rebuild"],
)
def test_legacy_uses_existing_row_true_still_defaults_agreement(project_type):
    project = {
        **_PROJECT_BASE,
        "project_type": project_type,
        "uses_existing_row": True,
    }
    details = _load_with_inputs(_technical_inputs(project))
    assert details.row_agreement_type == "permanent_easement_new"


def test_validate_changes_rejects_fee_simple():
    errors = validate_changes({_ROW_PATH: "fee_simple"})
    assert errors == [{"path": _ROW_PATH, "message": _FEE_SIMPLE_MSG}]


def test_loader_rejects_fee_simple():
    project = {**_PROJECT_BASE, "project_type": "greenfield", "row_agreement_type": "fee_simple"}
    with pytest.raises(InvalidInputs, match=_FEE_SIMPLE_MSG):
        _load_with_inputs(_technical_inputs(project))


def test_document_with_legacy_uses_existing_row_still_loads():
    project = {
        **_PROJECT_BASE,
        "project_type": "greenfield",
        "row_agreement_type": "permanent_easement_new",
        "uses_existing_row": False,
    }
    details = _load_with_inputs(_technical_inputs(project))
    assert details.row_agreement_type == "permanent_easement_new"
    assert details.project_type == "greenfield"
