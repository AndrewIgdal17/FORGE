"""Operating cost streams grow from year one; capital recovery is WACC-only."""
import pytest

from test.spec05_project import item, project_changes, run

T = "01_project_technical_details.timeline."


def test_operating_streams_grow_from_year_one():                    # A2
    r = run(project_changes(**{T+"delay_years": 2, T+"construction_years": 3,
                               "14_category_om_structures.om_real_escalation_rate": 0.02}))
    st = item(r, "oandm")["stream"]
    assert st[6] / st[5] == pytest.approx(1.02)
    r0 = run(project_changes(**{T+"delay_years": 2, T+"construction_years": 3,
                                "14_category_om_structures.om_real_escalation_rate": 0.0}))
    assert st[5] == pytest.approx(item(r0, "oandm")["stream"][5] * 1.02**5)


def test_capital_bases_do_not_depend_on_delay():
    a = run(project_changes(**{T+"delay_years": 0}))
    b = run(project_changes(**{T+"delay_years": 5}))
    assert a["costs"]["insurance"]["annual_premium"] == pytest.approx(b["costs"]["insurance"]["annual_premium"])


def test_capital_recovery_is_wacc_only():
    i = item(run(project_changes()), "capital_recovery")
    assert i["value_pv"] is None and i["value_pv_wacc"] > 0


def test_base_delay_stream_spans_delay_years():
    r = run(project_changes(**{T+"delay_years": 3, "05_delays.annual_base_delay_cost": 1000.0}))
    st = item(r, "base_delay")["stream"]
    assert st[:3] == [1000.0] * 3 and all(v == 0.0 for v in st[3:])
    assert item(r, "base_delay")["value_pv"] == pytest.approx(sum(1000 / 1.02**t for t in (1, 2, 3)))
