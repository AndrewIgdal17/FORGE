import re
from pathlib import Path

import pytest

import forge
from forge.scripts.io.input_metadata import INPUT_METADATA
from test.spec05_project import item, project_changes, run

ROOT = Path(forge.__file__).resolve().parent.parent

T = "01_project_technical_details.timeline."
D = "05_delays.annual_base_delay_cost"
MSG2 = "Annual direct delay cost is required when delay_years is 2. Enter 0 if there is none."


def test_missing_cost_with_delay_fails_naming_field_and_delay():
    changes = project_changes(**{T + "delay_years": 2, D: None})
    with pytest.raises(forge.InvalidInputs, match=re.escape(f"{D}: {MSG2}")):
        forge.resolve_inputs(changes)
    entry = next(e for e in forge.missing_required_inputs(changes) if e["path"] == D)
    assert (entry["stage"], entry["message"]) == ("before_route", MSG2)
    assert any(e["path"] == D for e in forge.missing_required_inputs(changes, capital_only=True))


def test_absent_key_is_the_same_as_null():
    changes = project_changes(**{T + "delay_years": 2})
    changes.pop(D)
    with pytest.raises(forge.InvalidInputs, match=re.escape(MSG2)):
        forge.resolve_inputs(changes)


def test_entered_zero_runs_and_is_measured_zero():
    r = run(project_changes(**{T + "delay_years": 2, D: 0}))
    assert (item(r, "base_delay")["state"], item(r, "base_delay")["value_pv"]) == ("measured", 0.0)
    assert r["delay_comparison"]["on_time_run"] is True


def test_no_delay_needs_no_entry():
    changes = project_changes(**{T + "delay_years": 0, D: None})
    assert not [e for e in forge.missing_required_inputs(changes) if e["path"] == D]
    r = run(changes)
    assert (item(r, "base_delay")["state"], item(r, "base_delay")["value_pv"]) == ("measured", 0.0)


def test_full_document_without_cost_is_refused():
    resolved = forge.resolve_inputs(project_changes(**{T + "delay_years": 2, D: 0}))
    resolved["05_delays"]["annual_base_delay_cost"] = None
    with pytest.raises(forge.InvalidInputs, match=re.escape(MSG2)):
        forge.run_calculation(resolved)


def test_no_default_anywhere():
    assert forge.get_defaults_template()["05_delays"]["annual_base_delay_cost"] is None
    assert INPUT_METADATA["delay_annual_base"].required_when == "delay_positive"
    reg = (ROOT / "forge/yamls/defaults_registry.yaml").read_text()
    block = reg.split("benefits:\n  congestion:\n    annual_base_delay_cost:")[1].split(
        "\n  capacity_value:"
    )[0]
    assert "Default 0" not in block