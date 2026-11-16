"""Spec 17 F10: pay the net change in energy losses (reconductoring and rebuild)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import forge
from forge.emissions_data import (
    calendar_year,
    criteria_damage_2025_usd_per_kg,
    egrid_rates,
    lrmer_co2e,
    sc_co2_2025_usd_per_kg,
)
from forge.errors import InvalidInputs
from test.spec05_project import item, measured, run
from test.spec07_regions import REGION_SENTINELS
from test.spec11_scenarios import scenario_changes

P = "01_project_technical_details.project."
_FIXTURE = Path(__file__).resolve().parent / "data" / "spec17_greenfield_line_loss.json"

_NEW_OLD_KEYS = (
    "line_loss_mwh_yr_new",
    "line_loss_mwh_yr_old",
    "converter_loss_mwh_yr_new",
    "converter_loss_mwh_yr_old",
    "total_loss_mwh_yr_new",
    "total_loss_mwh_yr_old",
)

DC_REBUILD = scenario_changes(
    "AEP_LRGV_ACSR_Rebuild",
    **{
        P + "ac_dc": "DC",
        P + "capacity_mw": 1500,
        P + "conductor_type": "Advanced Aluminum Conductor",
        P + "converter_type": "LCC Converter",
        P + "number_of_converters": 2,
        P + "old_ac_dc": "DC",
        P + "old_capacity_mw": 2000,
        P + "old_conductor_type": "Standard Aluminum Conductor",
        P + "old_converter_type": "LCC Converter",
    },
    **measured(
        congestion_spread_per_mwh=None,
        hours_receiving_more_congested=None,
        hours_sending_more_congested=None,
        receiving_energy_value_per_mwh=None,
    ),
)


def _line_loss(results: dict) -> dict:
    ll = dict(results["costs"]["line_loss"])
    ll.pop("streams", None)
    return ll


def _norm_missing_inputs(obj: object) -> object:
    if isinstance(obj, dict):
        out = {key: _norm_missing_inputs(value) for key, value in obj.items()}
        if "missing_inputs" in out and out["missing_inputs"] is not None:
            out["missing_inputs"] = list(out["missing_inputs"])
        return out
    return obj


def test_accc_reconductoring_at_same_capacity_saves():
    changes = scenario_changes(
        "AEP_LRGV_ACCC", **{P + "capacity_mw": 1792}, **measured()
    )
    r = run(changes)
    ll = r["costs"]["line_loss"]
    assert ll["line_loss_mwh_yr"] == pytest.approx(
        ll["line_loss_mwh_yr_new"] - ll["line_loss_mwh_yr_old"]
    )
    assert ll["line_loss_mwh_yr"] < 0
    assert item(r, "line_loss_conductor")["value_pv"] < 0
    assert r["bcr"]["energy_losses_pv"] < 0
    r_no_losses = run(changes, no_linelosses=True)
    assert r["bcr"]["net_benefit_pv"] == pytest.approx(
        r_no_losses["bcr"]["net_benefit_pv"] - r["bcr"]["energy_losses_pv"]
    )
    assert item(r, "line_loss_converter")["state"] == "does_not_apply"


def test_rebuild_change_is_new_minus_old_at_old_capacity():
    rebuild = scenario_changes(
        "AEP_LRGV_ACSR_Rebuild",
        **{
            P + "capacity_mw": 2598,
            P + "conductor_type": "Advanced Aluminum Conductor",
        },
        **measured(),
    )
    r = run(rebuild)
    ll = r["costs"]["line_loss"]
    gf_new = scenario_changes(
        "AEP_LRGV_ACSR_Rebuild",
        **{
            P + "project_type": "greenfield",
            P + "capacity_mw": 2598,
            P + "conductor_type": "Advanced Aluminum Conductor",
            P + "row_agreement_type": None,
        },
        **measured(),
    )
    gf_old = scenario_changes(
        "AEP_LRGV_ACSR_Rebuild",
        **{
            P + "project_type": "greenfield",
            P + "capacity_mw": 1792,
            P + "conductor_type": "Standard Aluminum Conductor",
            P + "row_agreement_type": None,
        },
        **measured(),
    )
    ref_new = run(gf_new)["costs"]["line_loss"]["line_loss_mwh_yr"]
    ref_old = run(gf_old)["costs"]["line_loss"]["line_loss_mwh_yr"]
    assert ll["line_loss_mwh_yr_new"] == pytest.approx(ref_new, rel=1e-12)
    assert ll["line_loss_mwh_yr_old"] == pytest.approx(ref_old, rel=1e-12)
    assert ll["line_loss_mwh_yr"] == pytest.approx(ref_new - ref_old)


def test_bundled_rebuild_nets_to_zero():
    r = run(scenario_changes("AEP_LRGV_ACSR_Rebuild", **measured()))
    ll = r["costs"]["line_loss"]
    assert ll["line_loss_mwh_yr"] == 0.0
    assert item(r, "line_loss_conductor")["value_pv"] == 0.0
    assert item(r, "line_loss_conductor")["state"] == "measured"


def test_greenfield_line_loss_unchanged():
    fixture = json.loads(_FIXTURE.read_text())
    for name in ("SunZia_Delay2", "CTT_Actual_Delay2"):
        ll = _line_loss(run(scenario_changes(name, **measured())))
        for key, expected in fixture[name].items():
            actual = ll[key]
            if isinstance(expected, dict):
                assert _norm_missing_inputs(actual) == expected
            else:
                assert actual == pytest.approx(expected, rel=1e-9)
        for key in _NEW_OLD_KEYS:
            assert key not in ll


def test_loss_compensation_uses_net_energy():
    changes = scenario_changes(
        "AEP_LRGV_ACCC",
        **{
            P + "capacity_mw": 1792,
            "01_project_technical_details.timeline.project_lifetime": 1,
        },
        **REGION_SENTINELS,
        **measured(hours_sending_more_congested=876),
    )
    r = run(changes)
    assert r["costs"]["emissions"]["total_pv"] < 0
    ll = r["costs"]["line_loss"]
    emissions = r["costs"]["emissions"]
    resolved = forge.resolve_inputs(changes)
    fraction = resolved["16_emissions_reductions"]["emissions_reductions"][
        "compensation_percent"
    ]
    year = calendar_year(r["derived_parameters"]["t_cod"])
    gea = "CAISO"
    sub = "AZNM"
    state = "AZ"
    eps_co2e = lrmer_co2e(gea, year)
    eps_so2, eps_nox = egrid_rates(sub)
    c_co2e = sc_co2_2025_usd_per_kg(year)
    c_so2 = criteria_damage_2025_usd_per_kg(state, "so2", year)
    c_nox = criteria_damage_2025_usd_per_kg(state, "nox", year)
    bundle = eps_co2e * c_co2e + eps_so2 * c_so2 + eps_nox * c_nox
    expected = fraction * ll["total_loss_mwh_yr"] * bundle
    assert emissions["emissions_comp_annual_values"] == pytest.approx([expected])

    r_hi = run(
        scenario_changes(
            "AEP_LRGV_ACSR_Rebuild",
            **{
                "01_project_technical_details.timeline.project_lifetime": 1,
            },
            **REGION_SENTINELS,
            **measured(hours_sending_more_congested=876),
        )
    )
    ratio = (
        r_hi["costs"]["line_loss"]["total_loss_mwh_yr"]
        / ll["total_loss_mwh_yr"]
    )
    scaled = [
        v * ratio for v in emissions["emissions_comp_annual_values"]
    ]
    assert r_hi["costs"]["emissions"]["emissions_comp_annual_values"] == pytest.approx(
        scaled
    )


def test_dc_rebuild_to_smaller_rating_converter_not_available():
    r = run(DC_REBUILD)
    ll = r["costs"]["line_loss"]
    assert ll["converter_loss_mwh_yr"] == pytest.approx(
        ll["converter_loss_mwh_yr_new"] - ll["converter_loss_mwh_yr_old"]
    )
    assert ll["converter_loss_mwh_yr"] < 0
    assert item(r, "line_loss_converter")["state"] == "not_available"


def test_old_dc_line_needs_old_converter_type():
    bad = {**DC_REBUILD, P + "old_converter_type": None}
    with pytest.raises(InvalidInputs, match="old_converter_type"):
        run(bad)