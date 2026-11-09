"""Tests for build-cost selectors and load_costs signature."""
import inspect
import textwrap

import pytest
import yaml

from forge.scripts.calc.build_costs import load_costs
from forge.scripts.utils.run_context import RunState, reset_run_state, set_run_state


def test_load_costs_has_no_total_miles_parameter():
    """Dead total_miles arg is removed from load_costs (appendix Eq 2 uses weighted miles)."""
    params = inspect.signature(load_costs).parameters
    assert "total_miles" not in params


_BUILD_YAML = textwrap.dedent(
    """\
    soft_cost_multiplier: 0.10
    project_categories_build_costs:
      test_cat:
        variable_conductor_cost_per_mile: 1000.0
        fixed_conductor_cost: 100.0
        variable_structure_cost_per_mile: 500.0
        fixed_converter_cost: 2000.0
    """
)


def _activate_build_inputs(monkeypatch, yaml_text):
    build_data = yaml.safe_load(yaml_text)
    state = RunState(
        inputs={"10_project_category_build_costs": build_data},
        scenario_id="test",
    )
    token = set_run_state(state)
    monkeypatch.setattr(
        "forge.scripts.calc.build_costs.calculate_weighted_miles",
        lambda: (10.0, 1.2),
    )
    return token


def _load(tmp_path, monkeypatch, project_type, number_of_converters):
    token = _activate_build_inputs(monkeypatch, _BUILD_YAML)
    try:
        return load_costs(
            category="test_cat",
            number_of_converters=number_of_converters,
            contingencies={
                "conductor_contingency": 0.10,
                "structure_contingency": 0.20,
                "converter_contingency": 0.15,
            },
            project_type=project_type,
        )
    finally:
        reset_run_state(token)


def test_reconductoring_keeps_ungated_components_and_gates_contingencies(
    tmp_path, monkeypatch
):
    """ξ_structure=0 zeros gated totals; component fields stay ungated (appendix Eq 2)."""
    result = _load(tmp_path, monkeypatch, "reconductoring", number_of_converters=2)

    assert result.conductor_cost == 10_100.0
    assert result.structure_cost == 5_000.0
    assert result.converter_cost == 4_000.0
    assert result.total_cost == 10_100.0

    assert result.structure_cost_with_contingencies == 0.0
    assert result.converter_cost_with_contingencies == 0.0
    # conductor: 10100 * 1.10 contingency * 1.10 soft-cost
    assert abs(result.conductor_cost_with_contingencies - 12_221.0) < 1e-9
    assert abs(result.total_cost_with_contingencies - 12_221.0) < 1e-9


def test_greenfield_dc_includes_all_gated_components(tmp_path, monkeypatch):
    """ξ_structure=1 and ξ_DC=1 include structure and converter in totals."""
    result = _load(tmp_path, monkeypatch, "greenfield", number_of_converters=2)

    assert result.conductor_cost == 10_100.0
    assert result.structure_cost == 5_000.0
    assert result.converter_cost == 4_000.0
    assert result.total_cost == 19_100.0

    # conductor: 10100 * 1.10 * 1.10 = 12221
    # structure: 5000 * 1.20 * 1.10 = 6600
    # converter: 4000 * 1.15 * 1.10 = 5060
    assert abs(result.conductor_cost_with_contingencies - 12_221.0) < 1e-9
    assert abs(result.structure_cost_with_contingencies - 6_600.0) < 1e-9
    assert abs(result.converter_cost_with_contingencies - 5_060.0) < 1e-9
    assert abs(result.total_cost_with_contingencies - 23_881.0) < 1e-9


def test_greenfield_ac_gates_converter_when_no_converters(tmp_path, monkeypatch):
    """ξ_DC=0 when number_of_converters is 0."""
    result = _load(tmp_path, monkeypatch, "greenfield", number_of_converters=0)

    assert result.converter_cost == 0.0
    assert result.total_cost == 15_100.0  # conductor + structure
    assert result.converter_cost_with_contingencies == 0.0

