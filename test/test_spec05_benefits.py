"""Benefit streams grow from year one at one real rate; congestion delay is gone."""
import pytest

import forge
from forge.scripts.utils.streams import pv

from test.spec05_project import item, project_changes, run

GB = "17_congestion_reductions.benefit_price_escalation_real"
T = "01_project_technical_details.timeline."
BEN_IDS = ("congestion_benefit", "delivered_energy_benefit", "capacity_value_benefit",
           "line_loss_conductor", "line_loss_converter")


def test_default_benefit_growth():
    assert forge.get_defaults_template()["17_congestion_reductions"]["benefit_price_escalation_real"] == 0.01


def test_growth_from_base_year():                                    # A2
    r = run(project_changes(**{T+"delay_years": 2, T+"construction_years": 3, GB: 0.02}))
    x = r["benefits"]["congestion"]["congestion_benefit_annual"]
    assert item(r, "congestion_benefit")["stream"][5] == pytest.approx(1.02**5 * x)


def test_one_parameter_drives_all_benefit_priced_streams():          # A4
    a = run(project_changes(**{GB: 0.03}))
    b = run(project_changes(**{GB: 0.01}))
    t0 = a["derived_parameters"]["t_cod"]
    for tid in BEN_IDS:
        st = item(a, tid)["stream"]
        if st[t0 - 1] != 0.0:
            assert st[t0] / st[t0 - 1] == pytest.approx(1.03)
    others = {i["taxonomy_id"] for i in a["taxonomy_results"]} - set(BEN_IDS)
    for tid in others:
        stream_a = item(a, tid)["stream"]
        # Task 9 removes this skip. Wildfire, outage, and emissions have no stream yet.
        if stream_a is None:
            continue
        assert stream_a == pytest.approx(item(b, tid)["stream"])


def test_two_present_values_per_flow():                              # A1
    i = item(run(project_changes()), "congestion_benefit")
    assert i["value_pv"] == pytest.approx(pv(i["stream"], 0.02), rel=1e-9)
    assert i["value_pv_wacc"] == pytest.approx(pv(i["stream"], 1.075 / 1.03 - 1), rel=1e-9)
    assert i["value_pv"] != pytest.approx(i["value_pv_wacc"])


def test_congestion_delay_is_gone():
    r = run(project_changes(**{T+"delay_years": 4}))
    assert "congestion_delay" not in {i["taxonomy_id"] for i in r["taxonomy_results"]}
    assert not any(k.startswith("congestion_delay_cost") for k in r["benefits"]["congestion"])
