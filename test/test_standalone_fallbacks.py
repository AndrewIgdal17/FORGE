"""Calc modules fail loudly without RunContext instead of re-deriving from YAML."""
import inspect
from unittest.mock import MagicMock

import pytest

from forge.scripts.calc.build_costs import BuildCosts
from forge.scripts.utils.run_context import clear_run_context, set_run_context


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

def _assert_no_standalone_fallback(source: str) -> None:
    assert "load_and_escalate_costs" not in source
    assert "requires a RunContext" in source


def test_environmental_mitigation_requires_run_context():
    from forge.scripts.calc import environmental_mitigation as em

    _assert_no_standalone_fallback(inspect.getsource(em.main))


def test_insurance_costs_requires_run_context():
    from forge.scripts.calc import insurance_costs as ins

    _assert_no_standalone_fallback(inspect.getsource(ins.main))


def test_oandm_line_om_requires_run_context():
    from forge.scripts.calc import oandm

    _assert_no_standalone_fallback(inspect.getsource(oandm.load_nonoverhead_line_om))


def test_oandm_converter_om_requires_run_context():
    from forge.scripts.calc import oandm

    _assert_no_standalone_fallback(inspect.getsource(oandm.load_converter_om_costs))


def test_oandm_converter_om_raises_without_run_context():
    from forge.scripts.calc import oandm

    clear_run_context()
    with pytest.raises(RuntimeError, match="RunContext"):
        oandm.load_converter_om_costs(
            ac_dc="DC",
            converter_type="VSC Converter",
            construction_type="Subsea",
            capacity_mw=1000,
            conductor_type="XLPE",
        )


def test_oandm_line_om_raises_without_run_context():
    from forge.scripts.calc import oandm

    clear_run_context()
    with pytest.raises(RuntimeError, match="RunContext"):
        oandm.load_nonoverhead_line_om(
            construction_type="Subsea",
            ac_dc="DC",
            capacity_mw=1000,
            conductor_type="XLPE",
            converter_type="VSC Converter",
        )


def test_oandm_converter_reads_ctx_build_costs(monkeypatch):
    """In-pipeline RunContext.build_costs is used when present (no reload)."""
    from forge.scripts.calc import oandm

    ctx = MagicMock()
    ctx.build_costs = _FAKE_COSTS
    set_run_context(ctx)
    try:
        def _should_not_run(*a, **k):
            raise AssertionError("load_and_escalate_costs must not run when ctx.build_costs is set")

        monkeypatch.setattr(
            "forge.scripts.calc.build_costs.load_and_escalate_costs", _should_not_run
        )
        result = oandm.load_converter_om_costs(
            ac_dc="DC",
            converter_type="VSC Converter",
            construction_type="Subsea",
            capacity_mw=1000,
            conductor_type="XLPE",
        )
        assert abs(result - 10_000.0) < 1e-9
    finally:
        clear_run_context()


def test_oandm_line_om_reads_ctx_build_costs(monkeypatch):
    from forge.scripts.calc import oandm

    ctx = MagicMock()
    ctx.build_costs = _FAKE_COSTS
    set_run_context(ctx)
    try:
        result = oandm.load_nonoverhead_line_om(
            construction_type="Subsea",
            ac_dc="DC",
            capacity_mw=1000,
            conductor_type="XLPE",
            converter_type="VSC Converter",
        )
        assert abs(result - 37_500.0) < 1e-9
    finally:
        clear_run_context()
