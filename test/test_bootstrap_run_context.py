"""Shared RunContext bootstrap must live in one helper used by both entry points."""
import inspect
from types import SimpleNamespace

import pytest

from forge.scripts.utils.run_context import clear_run_context, get_run_context


def test_bootstrap_run_context_sets_and_returns_populated_context(monkeypatch):
    from forge import _bootstrap_run_context

    project = SimpleNamespace(
        number_of_converters=2,
        delay_years=1.0,
        construction_years=3.0,
        capacity_mw=500,
    )
    financing = SimpleNamespace(
        wacc_real=0.04,
        wacc_nominal=0.07,
        inflation_rate=0.02,
    )
    terrain_miles = {"flat": 10.0, "mountain": 5.0}
    terrain_multipliers = {"flat": 1.0, "mountain": 1.5}
    physical_raw = {
        "terrain": {
            "terrain_miles": terrain_miles,
            "terrain_multipliers": terrain_multipliers,
        }
    }
    fin_raw = {"financial": {"social_discount_rate": 0.03}}
    contingencies = {"conductor": 0.1}

    monkeypatch.setattr(
        "forge.scripts.io.yaml_loaders.load_project_technical_details", lambda: project
    )
    monkeypatch.setattr(
        "forge.scripts.io.yaml_loaders.load_financing_details", lambda: financing
    )
    monkeypatch.setattr(
        "forge.scripts.io.yaml_loaders.load_contingencies", lambda: contingencies
    )
    monkeypatch.setattr("forge.scripts.io.yaml_loaders.load_row_widths", lambda cat: 150.0)
    monkeypatch.setattr(
        "forge.scripts.utils.smart_loaders.get_physical_data_raw", lambda: physical_raw
    )
    monkeypatch.setattr(
        "forge.scripts.utils.smart_loaders.get_financing_data_raw", lambda: fin_raw
    )
    monkeypatch.setattr(
        "forge.scripts.utils.calculation_utils.build_category_string",
        lambda **kw: "Overhead/AC/500MW/ACSR/NA",
    )
    monkeypatch.setattr(
        "forge.scripts.utils.weighted_miles.calculate_weighted_miles",
        lambda: (12.5, 1.2),
    )
    monkeypatch.setattr(
        "forge.scripts.utils.financial_utils.calculate_afudc_rate",
        lambda raw: (0.05, "calculated"),
    )
    monkeypatch.setattr(
        "forge.scripts.utils.financial_utils.calculate_cod_year",
        lambda delay, construction: 2030.0,
    )
    monkeypatch.setattr(
        "forge.scripts.utils.financial_utils.calculate_construction_start_year",
        lambda delay: 2027.0,
    )

    clear_run_context()
    try:
        ctx = _bootstrap_run_context()
        assert ctx is get_run_context()
        assert ctx.project_details is project
        assert ctx.financing is financing
        assert ctx.contingencies == contingencies
        assert ctx.terrain_miles == terrain_miles
        assert ctx.terrain_multipliers == terrain_multipliers
        assert ctx.total_miles == 15.0
        assert ctx.category_string == "Overhead/AC/500MW/ACSR/NA"
        assert ctx.row_width_feet == 150.0
        assert ctx.weighted_miles == 12.5
        assert ctx.average_terrain_multiplier == 1.2
        assert ctx.number_of_converters == 2
        assert ctx.social_discount_rate == 0.03
        assert ctx.afudc_rate == 0.05
        assert ctx.afudc_source == "calculated"
        assert ctx.cod_year == 2030.0
        assert ctx.construction_start_year == 2027.0
        derived = ctx.derived_parameters
        assert derived["category_string"] == ctx.category_string
        assert derived["wacc_real"] == 0.04
        assert derived["wacc_nominal"] == 0.07
        assert derived["inflation_rate"] == 0.02
        assert derived["social_discount_rate"] == ctx.social_discount_rate
        assert derived["afudc_rate"] == ctx.afudc_rate
        assert derived["cod_year"] == ctx.cod_year
        assert derived["construction_start_year"] == ctx.construction_start_year
        assert derived["contingencies"] == contingencies
        assert derived["total_miles"] == 15.0
    finally:
        clear_run_context()


def test_bootstrap_rejects_zero_capacity_mw(monkeypatch):
    from forge import _bootstrap_run_context

    project = SimpleNamespace(
        number_of_converters=0,
        delay_years=1.0,
        construction_years=3.0,
        capacity_mw=0,
    )
    monkeypatch.setattr(
        "forge.scripts.io.yaml_loaders.load_project_technical_details", lambda: project
    )

    clear_run_context()
    try:
        with pytest.raises(ValueError, match="capacity_mw is required and must be > 0"):
            _bootstrap_run_context()
    finally:
        clear_run_context()


def test_run_calculation_and_main_share_bootstrap():
    import forge

    helper_src = inspect.getsource(forge._bootstrap_run_context)
    assert "set_run_context(" in helper_src
    assert "add_derived(" in helper_src

    for fn in (forge.run_calculation, forge.main):
        src = inspect.getsource(fn)
        assert "_bootstrap_run_context()" in src
        assert "load_project_technical_details()" not in src
        assert "set_run_context(RunContext(" not in src
        assert "add_derived({" not in src
