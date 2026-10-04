"""O&M rate tables 14/15 must follow the active run's inputs, not a static YAML dir."""
import inspect
from pathlib import Path
from unittest.mock import MagicMock

import yaml

from forge.scripts.calc.build_costs import BuildCosts
from forge.scripts.utils.run_context import (
    RunState,
    reset_run_state,
    set_run_context,
    set_run_state,
)

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


def _converter_inputs(vsc_rate: float) -> dict:
    return yaml.safe_load(
        "converter_om_rate:\n"
        f"  VSC Converter: {vsc_rate}\n"
        "  LCC Converter: 0.005\n"
    )


def _structure_inputs(subsea_rate: float) -> dict:
    return yaml.safe_load(
        "project_categories_om_structures:\n"
        "  Overhead:\n"
        "    base_om_per_mile_year: 19090\n"
        "  Subsea:\n"
        f"    om_pct_of_line_capex: {subsea_rate}\n"
        "om_real_escalation_rate: 0.02\n"
    )


def test_converter_om_uses_run_inputs_not_canonical_rates():
    """Custom converter rates on the active run take effect."""
    from forge.scripts.calc import oandm

    state = RunState(
        inputs={"15_category_om_converters": _converter_inputs(0.01)},
        scenario_id="test",
    )
    token = set_run_state(state)
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
        reset_run_state(token)


def test_nonoverhead_line_om_uses_run_inputs_not_canonical_rates():
    """Custom structure/line rates on the active run take effect."""
    from forge.scripts.calc import oandm

    state = RunState(
        inputs={"14_category_om_structures": _structure_inputs(0.05)},
        scenario_id="test",
    )
    token = set_run_state(state)
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
        reset_run_state(token)


def test_live_oandm_paths_read_section_not_static():
    """Remaining live O&M loaders and main() must read section(), not STATIC_YAMLS_DIR."""
    from forge.scripts.calc import oandm

    module_source = Path(oandm.__file__).read_text()
    assert "STATIC_YAMLS_DIR" not in module_source
    assert "YAMLS_DIR" not in module_source

    for fn in (
        oandm.load_vegetation_management_om_costs,
        oandm.load_converter_om_costs,
        oandm.load_nonoverhead_line_om,
        oandm.main,
    ):
        source = inspect.getsource(fn)
        assert "section(" in source
        assert "STATIC_YAMLS_DIR" not in source
        assert "YAMLS_DIR" not in source
        if fn is not oandm.load_vegetation_management_om_costs:
            assert "14_category_om_structures" in source or "15_category_om_converters" in source
