"""O&M rate tables 14/15 must follow scenario-aware YAMLS_DIR, not STATIC_YAMLS_DIR."""
import inspect
from pathlib import Path
from unittest.mock import MagicMock

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


def _write_converter_yaml(tmp_path: Path, vsc_rate: float) -> None:
    (tmp_path / "15_category_om_converters.yaml").write_text(
        "converter_om_rate:\n"
        f"  VSC Converter: {vsc_rate}\n"
        "  LCC Converter: 0.005\n"
    )


def _write_structure_yaml(tmp_path: Path, subsea_rate: float) -> None:
    (tmp_path / "14_category_om_structures.yaml").write_text(
        "project_categories_om_structures:\n"
        "  Overhead:\n"
        "    base_om_per_mile_year: 19090\n"
        "  Subsea:\n"
        f"    om_pct_of_line_capex: {subsea_rate}\n"
        "om_real_escalation_rate: 0.02\n"
    )


def test_converter_om_uses_yamls_dir_not_canonical_rates(tmp_path, monkeypatch):
    """Custom converter rates in YAMLS_DIR take effect (API-mode scenario override)."""
    from forge.scripts.calc import oandm

    _write_converter_yaml(tmp_path, vsc_rate=0.01)
    monkeypatch.setattr(oandm, "YAMLS_DIR", tmp_path)

    ctx = MagicMock()
    ctx.build_costs = _FAKE_COSTS
    set_run_context(ctx)
    try:
        result = oandm.load_converter_om_costs(
            ac_dc="DC",
            converter_type="VSC Converter",
            construction_type="Subsea",
            capacity_mw=1000,
            conductor_type="XLPE",
        )
        # 2_000_000 * 0.01 custom rate. Canonical YAML is 0.005 → 10_000.
        assert abs(result - 20_000.0) < 1e-9
    finally:
        clear_run_context()


def test_nonoverhead_line_om_uses_yamls_dir_not_canonical_rates(tmp_path, monkeypatch):
    """Custom structure/line rates in YAMLS_DIR take effect (API-mode scenario override)."""
    from forge.scripts.calc import oandm

    _write_structure_yaml(tmp_path, subsea_rate=0.05)
    monkeypatch.setattr(oandm, "YAMLS_DIR", tmp_path)

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
        # (1_000_000 + 500_000) * 0.05 custom rate. Canonical YAML is 0.025 → 37_500.
        assert abs(result - 75_000.0) < 1e-9
    finally:
        clear_run_context()


def test_live_oandm_paths_read_yamls_dir_not_static():
    """Remaining live O&M loaders and main() must not use STATIC_YAMLS_DIR."""
    from forge.scripts.calc import oandm

    module_source = Path(oandm.__file__).read_text()
    assert "STATIC_YAMLS_DIR" not in module_source

    for fn in (
        oandm.load_vegetation_management_om_costs,
        oandm.load_converter_om_costs,
        oandm.load_nonoverhead_line_om,
        oandm.main,
    ):
        source = inspect.getsource(fn)
        assert "YAMLS_DIR" in source
        assert "STATIC_YAMLS_DIR" not in source
        if fn is not oandm.load_vegetation_management_om_costs:
            assert "14_category_om_structures.yaml" in source or "15_category_om_converters.yaml" in source
