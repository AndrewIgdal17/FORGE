"""Detail rows carry both present values and add up to their item (6.0.1).

The utility and ratepayer views discount at the real WACC, so a breakdown row
needs its WACC present value, and the rows of a breakdown must sum to the item
at either rate.
"""
from __future__ import annotations

import pytest

from test.spec05_project import item, run
from test.spec11_scenarios import scenario_changes


@pytest.fixture(scope="module")
def sunzia() -> dict:
    return run(scenario_changes("SunZia_Delay2"))


def _detail(entry: dict) -> dict[str, dict]:
    return {row["dimension_key"]: row for row in entry["detail"]}


def test_line_om_breaks_into_base_and_vegetation(sunzia):
    line = item(sunzia, "oandm_line")
    rows = _detail(line)
    assert set(rows) == {"base", "vegetation"}
    for key in ("value_pv", "value_pv_wacc", "value_nominal", "value_annual"):
        assert sum(r[key] for r in rows.values()) == pytest.approx(line[key], rel=1e-9), key
    assert rows["base"]["value_pv_wacc"] < rows["base"]["value_pv"]


def test_mitigation_detail_sums_at_both_rates(sunzia):
    env = item(sunzia, "env_mitigation")
    rows = _detail(env)
    assert set(rows) == {"base", "credits"}
    for key in ("value_pv", "value_pv_wacc", "value_nominal"):
        assert sum(r[key] for r in rows.values()) == pytest.approx(env[key], rel=1e-9), key


def test_societal_only_detail_has_no_wacc(sunzia):
    for row in item(sunzia, "emissions_comp")["detail"]:
        assert row["value_pv_wacc"] is None


def test_every_detail_row_serializes_wacc(sunzia):
    for entry in sunzia["taxonomy_results"]:
        for row in entry["detail"]:
            assert "value_pv_wacc" in row
