"""Sending-end source inputs and the one required-input check."""
import pytest

import forge
from forge.errors import InvalidInputs

P = "01_project_technical_details.project."
FF = "17_congestion_reductions.greenfield_congestion_reductions.constraints.flow_factor"
SP = "17_congestion_reductions.greenfield_congestion_reductions.prices.average_congestion_price"


def _paths(lst):
    return {(m["path"], m["stage"]) for m in lst}


def test_blank_greenfield_margin_draft():
    miss = forge.missing_required_inputs({P + "project_type": "greenfield"})
    p = _paths(miss)
    assert (P + "capacity_mw", "before_route") in p
    assert (FF, "before_route") in p
    assert (SP, "after_route") in p
    assert (P + "value_of_load_per_mwh", "after_route") in p
    assert all(m["message"] == f'{m["label"]} is required.' for m in miss)


def test_dedicated_requires_price_and_rates_not_spread_or_flow_share():
    miss = _paths(forge.missing_required_inputs({
        P + "sending_source": "dedicated",
        P + "capacity_mw": 500,
    }))
    for k in (
        "contract_price_per_mwh",
        "emission_rate_kg_per_mwh.co2e",
        "emission_rate_kg_per_mwh.so2",
        "emission_rate_kg_per_mwh.nox",
    ):
        assert (P + "dedicated_resource." + k, "before_route") in miss
    assert not any(path in (FF, SP) for path, _ in miss)


def test_rebuild_requires_old_line_fields():
    miss = _paths(forge.missing_required_inputs({
        P + "project_type": "rebuild",
        P + "capacity_mw": 500,
    }))
    assert (P + "old_capacity_mw", "before_route") in miss
    assert (FF, "before_route") not in miss


def test_capital_only_needs_no_after_route_fields():
    miss = forge.missing_required_inputs(
        {P + "capacity_mw": 500, FF: 0.5},
        capital_only=True,
    )
    assert all(m["stage"] != "after_route" for m in miss)


def test_resolve_inputs_raises_naming_fields():
    with pytest.raises(InvalidInputs, match="is required"):
        forge.resolve_inputs({P + "capacity_mw": 500})
