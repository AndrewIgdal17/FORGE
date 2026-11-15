"""Spec 12 item 1: each forgone benefit takes the state of the benefit it compares (§VI)."""
import pytest

from test.spec05_project import measured, project_changes, run

PROJECT = "01_project_technical_details.project."
_DEDICATED = {
    PROJECT + "sending_source": "dedicated",
    PROJECT + "dedicated_resource.contract_price_per_mwh": 55.0,
    PROJECT + "dedicated_resource.emission_rate_kg_per_mwh.co2e": 0.0,
    PROJECT + "dedicated_resource.emission_rate_kg_per_mwh.so2": 0.0,
    PROJECT + "dedicated_resource.emission_rate_kg_per_mwh.nox": 0.0,
}
STATES = {"measured", "not_available", "does_not_apply"}


def test_dedicated_line_forgone_congestion_does_not_apply():
    block = run(project_changes(**_DEDICATED, **measured()))["delay_comparison"]
    assert block["states"]["delay_cost_cong"] == "does_not_apply"
    assert block["delay_cost_cong"] is None
    assert block["states"]["delay_cost_avoid"] == "measured"
    assert block["delay_cost_forgone"] == pytest.approx(block["delay_cost_avoid"])
    assert block["states"]["delay_cost_forgone"] == "measured"
    assert "congestion_benefit" not in block["omitted"]["delay_cost_forgone"]
    assert block["states"]["delta_nb_delay"] == "measured"


def test_margin_line_states_and_values():
    block = run(project_changes(**measured()))["delay_comparison"]
    assert block["states"]["delay_cost_cong"] == "measured"
    assert block["delay_cost_forgone"] == pytest.approx(
        block["delay_cost_cong"] + block["delay_cost_avoid"]
    )
    assert set(block["states"].values()) <= STATES


def test_routeless_forgone_not_available():
    nulls = measured(
        congestion_spread_per_mwh=None,
        hours_receiving_more_congested=None,
        hours_sending_more_congested=None,
        receiving_energy_value_per_mwh=None,
    )
    block = run(project_changes(**nulls))["delay_comparison"]
    assert block["states"]["delay_cost_cong"] == "not_available"
    assert block["states"]["delay_cost_avoid"] == "not_available"
    assert block["states"]["delay_cost_forgone"] == "not_available"
    assert block["delay_cost_forgone"] is None
