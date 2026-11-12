"""Tests for InvalidInputs and CalculationError."""
import json

import pytest

import forge
from forge.errors import InvalidInputs, CalculationError
from test.spec07_regions import REGION_SENTINELS


def _runnable_inputs():
    """A case-study document that passes bootstrap.

    The defaults template leaves required inputs empty and has a category
    with no ROW width, so a module-loop test cannot start from
    get_defaults_template() alone.
    """
    forge_file = forge.get_scenarios_path() / "SunZia_Delay2.forge"
    with open(forge_file) as f:
        document = json.load(f)
    changes = forge.diff_changes(document["inputs"])
    changes.update({
        "02_project_physical_details.terrain.protected_area_acres.forested": 0.0,
        "02_project_physical_details.terrain.protected_area_acres.scrubbed_flat": 0.0,
        "02_project_physical_details.terrain.protected_area_acres.desert_barren": 0.0,
        "02_project_physical_details.terrain.protected_area_acres.rolling_hills": 0.0,
        "02_project_physical_details.terrain.protected_area_acres.mountain": 0.0,
    })
    for path, value in REGION_SENTINELS.items():
        changes.setdefault(path, value)
    return forge.resolve_inputs(changes)


def test_invalid_inputs_is_value_error():
    exc = InvalidInputs("capacity_mw must be > 0")
    assert isinstance(exc, ValueError)
    assert str(exc) == "capacity_mw must be > 0"
    assert exc.message == "capacity_mw must be > 0"


def test_calculation_error_chains_cause():
    cause = RuntimeError("boom")
    exc = CalculationError("wildfire_costs", cause)
    assert exc.module == "wildfire_costs"
    assert exc.__cause__ is cause
    assert "wildfire_costs" in str(exc)


def test_zero_capacity_raises_invalid_inputs():
    import forge
    from forge.data import get_defaults_template
    inputs = get_defaults_template()
    inputs["01_project_technical_details"]["project"]["capacity_mw"] = 0
    with pytest.raises(InvalidInputs, match="capacity_mw"):
        forge.run_calculation(inputs, scenario_id="zero_cap")


def test_module_failure_raises_calculation_error(monkeypatch):
    inputs = _runnable_inputs()

    def exploding_main():
        raise RuntimeError("kaboom")

    monkeypatch.setattr(
        "forge.scripts.utils.weighted_miles.main", exploding_main
    )
    with pytest.raises(CalculationError, match="weighted_miles"):
        forge.run_calculation(inputs, scenario_id="explode")


def test_invalid_inputs_from_module_is_not_wrapped(monkeypatch):
    inputs = _runnable_inputs()

    def invalid_main():
        raise InvalidInputs("user fixable module input")

    monkeypatch.setattr(
        "forge.scripts.utils.weighted_miles.main", invalid_main
    )
    with pytest.raises(InvalidInputs, match="user fixable") as raised:
        forge.run_calculation(inputs, scenario_id="invalid_mod")
    assert not isinstance(raised.value, CalculationError)
