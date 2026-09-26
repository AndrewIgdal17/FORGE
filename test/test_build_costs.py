"""Tests for build-cost selectors and load_costs signature."""
import inspect
import textwrap

import pytest

from forge.scripts.calc.build_costs import load_costs


def test_load_costs_has_no_total_miles_parameter():
    """Dead total_miles arg is removed from load_costs (appendix Eq 2 uses weighted miles)."""
    params = inspect.signature(load_costs).parameters
    assert "total_miles" not in params


def _write_build_yaml(tmp_path):
    (tmp_path / "10_project_category_build_costs.yaml").write_text(
        textwrap.dedent(
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
    )


def _load(tmp_path, monkeypatch, project_type, number_of_converters):
    _write_build_yaml(tmp_path)
    monkeypatch.setattr("forge.scripts.calc.build_costs.YAMLS_DIR", tmp_path)
    monkeypatch.setattr(
        "forge.scripts.calc.build_costs.calculate_weighted_miles",
        lambda: (10.0, 1.2),
    )
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


# ---------------------------------------------------------------------------
# load_and_escalate_costs — full pipeline equivalent for standalone fallbacks
# ---------------------------------------------------------------------------

_CONTINGENCIES = {
    "conductor_contingency": 0.10,
    "structure_contingency": 0.20,
    "converter_contingency": 0.15,
}


class _FakeProjectDetails:
    delay_years = 0
    project_type = "greenfield"


def _patch_load_and_escalate(tmp_path, monkeypatch, delay_years=0, escalation_rate=0.0, extra_yaml=""):
    yaml_text = textwrap.dedent(
        """\
        soft_cost_multiplier: 0.10
        project_categories_build_costs:
          test_cat:
            variable_conductor_cost_per_mile: 1000.0
            fixed_conductor_cost: 100.0
            variable_structure_cost_per_mile: 500.0
            fixed_converter_cost: 2000.0
        """
    ) + extra_yaml
    (tmp_path / "10_project_category_build_costs.yaml").write_text(yaml_text)
    monkeypatch.setattr("forge.scripts.calc.build_costs.YAMLS_DIR", tmp_path)
    monkeypatch.setattr(
        "forge.scripts.calc.build_costs.calculate_weighted_miles",
        lambda: (10.0, 1.2),
    )
    monkeypatch.setattr(
        "forge.scripts.utils.smart_loaders.get_financing_data_raw",
        lambda: {"financial": {"construction_cost_escalation_rate": escalation_rate}},
    )
    details = _FakeProjectDetails()
    details.delay_years = delay_years
    return details


def test_load_and_escalate_costs_exists():
    from forge.scripts.calc.build_costs import load_and_escalate_costs

    assert callable(load_and_escalate_costs)


def test_load_and_escalate_costs_escalates_contingency_fields(tmp_path, monkeypatch):
    """Delay escalation scales *_with_contingencies; bare fields stay unescalated."""
    from forge.scripts.calc.build_costs import load_and_escalate_costs, load_costs

    details = _patch_load_and_escalate(
        tmp_path, monkeypatch, delay_years=2, escalation_rate=0.05
    )
    unescalated = load_costs("test_cat", 2, _CONTINGENCIES, "greenfield")
    escalated = load_and_escalate_costs(
        "test_cat", 2, _CONTINGENCIES, "greenfield", details
    )

    factor = (1.05) ** 2
    assert escalated.conductor_cost == unescalated.conductor_cost
    assert escalated.structure_cost == unescalated.structure_cost
    assert escalated.converter_cost == unescalated.converter_cost
    assert escalated.total_cost == unescalated.total_cost
    assert abs(
        escalated.conductor_cost_with_contingencies
        - unescalated.conductor_cost_with_contingencies * factor
    ) < 1e-9
    assert abs(
        escalated.structure_cost_with_contingencies
        - unescalated.structure_cost_with_contingencies * factor
    ) < 1e-9
    assert abs(
        escalated.converter_cost_with_contingencies
        - unescalated.converter_cost_with_contingencies * factor
    ) < 1e-9
    assert abs(
        escalated.total_cost_with_contingencies
        - unescalated.total_cost_with_contingencies * factor
    ) < 1e-9
    assert escalated.weighted_miles == unescalated.weighted_miles
    assert escalated.average_terrain_multiplier == unescalated.average_terrain_multiplier


def test_load_and_escalate_costs_skips_escalation_when_delay_zero(tmp_path, monkeypatch):
    from forge.scripts.calc.build_costs import load_and_escalate_costs, load_costs

    details = _patch_load_and_escalate(
        tmp_path, monkeypatch, delay_years=0, escalation_rate=0.05
    )
    unescalated = load_costs("test_cat", 2, _CONTINGENCIES, "greenfield")
    result = load_and_escalate_costs(
        "test_cat", 2, _CONTINGENCIES, "greenfield", details
    )
    assert result.total_cost_with_contingencies == unescalated.total_cost_with_contingencies


def test_load_and_escalate_costs_applies_overrides(tmp_path, monkeypatch):
    """Overrides from the build-cost YAML are applied (same as main())."""
    from forge.scripts.calc.build_costs import load_and_escalate_costs, load_costs

    details = _patch_load_and_escalate(
        tmp_path,
        monkeypatch,
        delay_years=0,
        extra_yaml=textwrap.dedent(
            """\
            overrides:
              fixed_converter_cost: 9999.0
            """
        ),
    )
    without_overrides = load_costs("test_cat", 2, _CONTINGENCIES, "greenfield")
    with_overrides = load_and_escalate_costs(
        "test_cat", 2, _CONTINGENCIES, "greenfield", details
    )
    assert without_overrides.converter_cost == 4_000.0
    assert with_overrides.converter_cost == 19_998.0  # 9999 * 2 converters


def test_load_and_escalate_costs_does_not_swallow_unexpected_errors(tmp_path, monkeypatch):
    """Override YAML I/O may skip missing files; unexpected errors must propagate."""
    import yaml as _yaml
    from forge.scripts.calc.build_costs import load_and_escalate_costs

    details = _patch_load_and_escalate(tmp_path, monkeypatch)
    real_safe_load = _yaml.safe_load
    calls = {"n": 0}

    def _maybe_explode(stream):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("yaml exploded")
        return real_safe_load(stream)

    monkeypatch.setattr("forge.scripts.calc.build_costs.yaml.safe_load", _maybe_explode)
    with pytest.raises(RuntimeError, match="yaml exploded"):
        load_and_escalate_costs("test_cat", 2, _CONTINGENCIES, "greenfield", details)
