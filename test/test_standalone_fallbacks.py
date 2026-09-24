"""Standalone fallbacks must use load_and_escalate_costs, not re-derive CAPEX."""
import inspect
from types import SimpleNamespace
from unittest.mock import MagicMock

from scripts.calc.build_costs import BuildCosts
from scripts.utils.run_context import clear_run_context, set_run_context


_FAKE_COSTS = BuildCosts(
    total_cost=0.0,
    total_cost_with_contingencies=0.0,
    conductor_cost=0.0,
    structure_cost=0.0,
    converter_cost=0.0,
    conductor_cost_with_contingencies=1_000_000.0,
    structure_cost_with_contingencies=500_000.0,
    converter_cost_with_contingencies=2_000_000.0,
    weighted_miles=10.0,
    average_terrain_multiplier=1.0,
)

_FAKE_DETAILS = SimpleNamespace(
    project_type="greenfield",
    delay_years=2,
    number_of_converters=2,
    construction_type="Subsea",
    ac_dc="DC",
    capacity_mw=1000,
    conductor_type="XLPE",
    converter_type="VSC Converter",
)


def _assert_uses_load_and_escalate(source: str) -> None:
    assert "load_and_escalate_costs" in source
    assert "variable_conductor_cost_per_mile" not in source
    assert "fixed_converter_cost" not in source


def test_environmental_mitigation_fallback_uses_full_pipeline():
    from scripts.calc import environmental_mitigation as em

    _assert_uses_load_and_escalate(inspect.getsource(em.main))


def test_insurance_costs_fallback_uses_full_pipeline():
    from scripts.calc import insurance_costs as ins

    _assert_uses_load_and_escalate(inspect.getsource(ins.main))


def test_oandm_line_om_fallback_uses_full_pipeline():
    from scripts.calc import oandm

    _assert_uses_load_and_escalate(inspect.getsource(oandm.load_nonoverhead_line_om))


def test_oandm_converter_om_fallback_uses_full_pipeline():
    from scripts.calc import oandm

    _assert_uses_load_and_escalate(inspect.getsource(oandm.load_converter_om_costs))


def test_oandm_converter_fallback_reads_escalated_capex(monkeypatch):
    """When RunContext.build_costs is missing, converter O&M uses escalated CAPEX."""
    from scripts.calc import oandm

    clear_run_context()
    monkeypatch.setattr(
        "scripts.calc.build_costs.load_and_escalate_costs",
        lambda *a, **k: _FAKE_COSTS,
    )
    monkeypatch.setattr(
        "scripts.io.yaml_loaders.load_project_technical_details",
        lambda: _FAKE_DETAILS,
    )
    monkeypatch.setattr(
        "scripts.io.yaml_loaders.load_contingencies",
        lambda: {"conductor_contingency": 0.1, "structure_contingency": 0.1, "converter_contingency": 0.1},
    )

    result = oandm.load_converter_om_costs(
        ac_dc="DC",
        converter_type="VSC Converter",
        construction_type="Subsea",
        capacity_mw=1000,
        conductor_type="XLPE",
    )
    # 2_000_000 * 0.005 converter OM rate
    assert abs(result - 10_000.0) < 1e-9


def test_oandm_line_om_fallback_reads_escalated_line_capex(monkeypatch):
    """When RunContext.build_costs is missing, line O&M uses escalated conductor+structure."""
    from scripts.calc import oandm

    clear_run_context()
    monkeypatch.setattr(
        "scripts.calc.build_costs.load_and_escalate_costs",
        lambda *a, **k: _FAKE_COSTS,
    )
    monkeypatch.setattr(
        "scripts.io.yaml_loaders.load_project_technical_details",
        lambda: _FAKE_DETAILS,
    )
    monkeypatch.setattr(
        "scripts.io.yaml_loaders.load_contingencies",
        lambda: {"conductor_contingency": 0.1, "structure_contingency": 0.1, "converter_contingency": 0.1},
    )

    result = oandm.load_nonoverhead_line_om(
        construction_type="Subsea",
        ac_dc="DC",
        capacity_mw=1000,
        conductor_type="XLPE",
        converter_type="VSC Converter",
    )
    # (1_000_000 + 500_000) * 0.025 subsea OM rate
    assert abs(result - 37_500.0) < 1e-9


def test_ctx_build_costs_path_still_preferred(monkeypatch):
    """In-pipeline RunContext.build_costs is used when present (no reload)."""
    from scripts.calc import oandm

    ctx = MagicMock()
    ctx.build_costs = _FAKE_COSTS
    set_run_context(ctx)
    try:
        called = {"n": 0}

        def _should_not_run(*a, **k):
            called["n"] += 1
            raise AssertionError("load_and_escalate_costs must not run when ctx.build_costs is set")

        monkeypatch.setattr(
            "scripts.calc.build_costs.load_and_escalate_costs", _should_not_run
        )
        result = oandm.load_converter_om_costs(
            ac_dc="DC",
            converter_type="VSC Converter",
            construction_type="Subsea",
            capacity_mw=1000,
            conductor_type="XLPE",
        )
        assert called["n"] == 0
        assert abs(result - 10_000.0) < 1e-9
    finally:
        clear_run_context()
