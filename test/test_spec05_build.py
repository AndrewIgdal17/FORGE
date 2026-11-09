"""Build costs follow the MISO profile with per-year real escalation."""
import pytest
import forge
from forge.scripts.utils.financial_utils import get_construction_spending_weights
from forge.scripts.utils.streams import pv
from test.spec05_project import item, project_changes, run

G = 1.04 / 1.03 - 1
T = "01_project_technical_details.timeline."
PROFILES = forge.get_defaults_template()["19_cost_timing_patterns"]["construction_spending_profiles"]


def _ratio(r, comp):
    b = r["costs"]["build"]
    w = r["derived_parameters"]["construction_spending_weights"]
    st = b["streams"][f"build_{comp}"]
    base = b[f"{comp}_base_cost"]
    return st, w, base


def test_each_year_escalates_on_the_calendar_no_delay():  # F1
    r = run(project_changes(**{T + "delay_years": 0, T + "construction_years": 3}))
    st, w, base = _ratio(r, "conductor")
    for t in (1, 2, 3):
        assert st[t - 1] == pytest.approx(w[t - 1] * base * (1 + G) ** (t - 1))


def test_each_year_escalates_on_the_calendar_with_delay():  # F1
    r = run(project_changes(**{T + "delay_years": 2, T + "construction_years": 3}))
    st, w, base = _ratio(r, "conductor")
    for t in (3, 4, 5):
        assert st[t - 1] == pytest.approx(w[t - 3] * base * (1 + G) ** (t - 1))


@pytest.mark.parametrize("c", range(1, 11))
def test_societal_and_capitalization_share_weights(c):  # F2
    r = run(project_changes(**{T + "delay_years": 1, T + "construction_years": c}))
    st, w, base = _ratio(r, "conductor")
    recovered = [st[t - 1] / (base * (1 + G) ** (t - 1)) for t in range(2, 2 + c)]
    assert recovered == pytest.approx(w, abs=1e-12)
    assert sum(w) == pytest.approx(1.0, abs=1e-12)
    assert w == pytest.approx(get_construction_spending_weights(c, PROFILES))


def test_build_pv_values():
    r = run(project_changes())
    i = item(r, "build_conductor")
    assert i["value_pv"] == pytest.approx(pv(i["stream"], 0.02))
    assert i["value_pv_wacc"] == pytest.approx(pv(i["stream"], 1.075 / 1.03 - 1))


def test_reconductoring_has_zero_structure_and_converter_streams():
    r = run(project_changes(**{
        "01_project_technical_details.project.project_type": "reconductoring",
        "01_project_technical_details.project.old_ac_dc": "DC",
        "01_project_technical_details.project.old_conductor_type": "Standard Aluminum Conductor",
        "01_project_technical_details.project.old_converter_type": "VSC Converter",
        "01_project_technical_details.project.old_capacity_mw": 1500,
    }))
    assert all(v == 0.0 for v in r["costs"]["build"]["streams"]["build_structure"])
