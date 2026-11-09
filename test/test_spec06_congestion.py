"""Sending-end source, 8,760-hour congestion, and the exceedance default."""
import pytest

import forge
from test.spec05_project import item, project_changes, run

P = "01_project_technical_details.project."
G = "17_congestion_reductions.greenfield_congestion_reductions."
# SunZia_Delay2 stores average_exceedance of 500. The default is null, which
# means the minimum does not bind. Reset it so these cases test that default.
BASE = {
    P + "capacity_mw": 2400,
    P + "line_utilization": 0.7,
    P + "value_of_load_per_mwh": 40.0,
    G + "constraints.flow_factor": 0.5,
    G + "constraints.average_exceedance": None,
    G + "prices.average_congestion_price": 5.0,
}
DED = {
    P + "sending_source": "dedicated",
    P + "dedicated_resource.contract_price_per_mwh": 55.0,
    P + "dedicated_resource.emission_rate_kg_per_mwh.co2e": 0.0,
    P + "dedicated_resource.emission_rate_kg_per_mwh.so2": 0.0,
    P + "dedicated_resource.emission_rate_kg_per_mwh.nox": 0.0,
}


def _annual(r, k):
    return r["benefits"]["congestion"][k]


def test_margin_earns_relief_not_delivered_energy():
    r = run(project_changes(**BASE))
    assert _annual(r, "congestion_benefit_annual") == pytest.approx(8760 * 0.5 * 2400 * 5.0)
    assert all(v == 0.0 for v in item(r, "delivered_energy_benefit")["stream"])


def test_dedicated_earns_net_delivered_energy_and_no_relief():
    r = run(project_changes(**{**BASE, **DED}))
    assert all(v == 0.0 for v in item(r, "congestion_benefit")["stream"])
    e = 2400 * 1.0 * 0.7 * 8760  # flow share fixed at 1
    assert _annual(r, "delivered_benefit_annual") == pytest.approx(e * (40.0 - 55.0))


def test_switching_back_keeps_flow_share():
    run(project_changes(**{**BASE, **DED}))
    b = run(project_changes(**{**BASE, **DED, P + "sending_source": "margin"}))
    assert _annual(b, "congestion_benefit_annual") == pytest.approx(8760 * 0.5 * 2400 * 5.0)


def test_exceedance_default_and_bound():
    a = run(project_changes(**BASE))
    b = run(project_changes(**{**BASE, G + "constraints.average_exceedance": 600.0}))
    assert _annual(b, "congestion_benefit_annual") == pytest.approx(
        _annual(a, "congestion_benefit_annual") / 2
    )


def test_negative_spread_gives_negative_relief():
    r = run(project_changes(**{**BASE, G + "prices.average_congestion_price": -2.0}))
    assert _annual(r, "congestion_benefit_annual") < 0


def test_capacity_value_same_under_both_sources():
    cv = {
        "20_capacity_value.applicability_gate": True,
        "20_capacity_value.capacity_credit": 0.5,
        "20_capacity_value.capacity_price": 50000.0,
    }
    a = run(project_changes(**{**BASE, **cv, G + "constraints.flow_factor": 1.0}))
    b = run(project_changes(**{**BASE, **DED, **cv}))
    assert _annual(a, "capacity_value_annual") == pytest.approx(
        _annual(b, "capacity_value_annual")
    )


def test_constrained_hours_is_unknown():
    assert forge.validate_changes({G + "constraints.constrained_hours": 100})


def test_losses_priced_at_entered_energy_value():
    a = run(project_changes(**BASE))
    b = run(project_changes(**{**BASE, P + "value_of_load_per_mwh": 80.0}))
    assert b["costs"]["line_loss"]["annual_cost"] == pytest.approx(
        2 * a["costs"]["line_loss"]["annual_cost"]
    )
