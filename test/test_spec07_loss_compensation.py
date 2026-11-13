"""Loss-compensation dollars from terminal emission rates."""

import pytest

from forge.scripts.calc.emissions import calculate_loss_compensation

_RECEIVING = {"gea": "MISO_Central", "egrid_subregion": "SRMW", "state": "MO"}
_SENDING = {"gea": "MISO_North", "egrid_subregion": "MROW", "state": "MN"}
_HOURS_REV = (
    "01_project_technical_details.market_measurements.hours_sending_more_congested"
)


def _price(**overrides):
    kwargs = {
        "rcv_co2e": [100.0],
        "snd_co2e": [400.0],
        "rcv_so2": 0.01,
        "rcv_nox": 0.10,
        "snd_so2": 0.05,
        "snd_nox": 0.20,
        "c_co2e": [0.25],
        "c_so2_rcv": [8.0],
        "c_nox_rcv": [4.0],
        "c_so2_snd": [10.0],
        "c_nox_snd": [20.0],
        "share_receiving": 0.1,
        "sending_source": "margin",
        "t_cod": 2,
        "horizon": 2,
        "social_discount_rate": 0.02,
        "receiving": _RECEIVING,
        "sending": _SENDING,
    }
    kwargs.update(overrides)
    return calculate_loss_compensation(1000.0, 1.0, **kwargs)


def test_one_operating_year_in_2026_matches_the_hand_formula():
    e_comp = 1000.0
    snd_bundle = 400.0 * 0.25 + 0.05 * 10.0 + 0.20 * 20.0
    rcv_bundle = 100.0 * 0.25 + 0.01 * 8.0 + 0.10 * 4.0
    expected = e_comp * (0.9 * snd_bundle + 0.1 * rcv_bundle)
    out = _price()
    assert out["rates_used"]["share_receiving"] == 0.1
    assert out["rates_used"]["sending"]["source"] == "margin"
    assert out["rates_used"]["receiving"]["state"] == "MO"
    assert out["emissions_comp_annual_values"] == pytest.approx([expected])
    assert out["streams"]["emissions_comp"] == pytest.approx([0.0, expected])
    assert out["total_pv"] == pytest.approx(expected / (1.02 ** 2))
    assert out["annual_kg"]["sending"]["co2e"] == pytest.approx([e_comp * 0.9 * 400.0])
    assert out["annual_kg"]["receiving"]["co2e"] == pytest.approx([e_comp * 0.1 * 100.0])
    assert out["annual_kg"]["sending"]["so2"] == pytest.approx([e_comp * 0.9 * 0.05])
    assert out["annual_kg"]["receiving"]["nox"] == pytest.approx([e_comp * 0.1 * 0.10])
    assert out["annual_kg"]["total"]["co2e"] == pytest.approx(
        [e_comp * 0.9 * 400.0 + e_comp * 0.1 * 100.0]
    )
    assert out["damage_cost_per_kg"]["sending"]["co2e"] == [0.25]
    assert out["damage_cost_per_kg"]["receiving"]["so2"] == [8.0]
    assert out["damage_cost_per_kg"]["sending"]["co2e"] == out["damage_cost_per_kg"]["receiving"]["co2e"]
    assert out["availability"]["emissions_comp"]["available"] is True
    assert "total_pv_wacc" not in out


def test_dedicated_uses_resource_rates_and_sending_damage():
    e_comp = 100.0
    expected = e_comp * (10.0 * 0.5 + 0.2 * 4.0 + 0.3 * 6.0)
    out = calculate_loss_compensation(
        e_comp,
        1.0,
        rcv_co2e=[999.0],
        snd_co2e=[10.0],
        rcv_so2=999.0,
        rcv_nox=999.0,
        snd_so2=0.2,
        snd_nox=0.3,
        c_co2e=[0.5],
        c_so2_rcv=[1.0],
        c_nox_rcv=[1.0],
        c_so2_snd=[4.0],
        c_nox_snd=[6.0],
        share_receiving=0.4,
        sending_source="dedicated",
        t_cod=1,
        horizon=1,
        social_discount_rate=0.0,
        receiving=_RECEIVING,
        sending={"gea": None, "egrid_subregion": None, "state": "MN"},
    )
    assert out["rates_used"]["share_receiving"] is None
    assert out["rates_used"]["sending"]["source"] == "dedicated"
    assert out["rates_used"]["sending"]["gea"] is None
    assert out["emissions_comp_annual_values"] == pytest.approx([expected])
    assert out["annual_kg"]["sending"]["co2e"] == pytest.approx([e_comp * 10.0])
    assert out["annual_kg"]["sending"]["so2"] == pytest.approx([e_comp * 0.2])
    assert out["annual_kg"]["receiving"]["co2e"] == pytest.approx([0.0])
    assert out["annual_kg"]["receiving"]["so2"] == pytest.approx([0.0])
    assert out["annual_kg"]["receiving"]["nox"] == pytest.approx([0.0])
    assert out["annual_kg"]["total"]["nox"] == pytest.approx([e_comp * 0.3])
    assert out["availability"]["emissions_comp"]["available"] is True
    assert out["availability"]["emissions_comp"]["missing_inputs"] == ()


def test_margin_without_reverse_hours_is_not_available():
    out = _price(share_receiving=None)
    assert out["rates_used"]["share_receiving"] is None
    assert out["rates_used"]["sending"]["gea"] == "MISO_North"
    assert out["rates_used"]["sending"]["source"] == "margin"
    assert out["total_nominal"] is None
    assert out["total_pv"] is None
    assert out["annual_cost"] is None
    assert out["emissions_comp_annual_values"] is None
    assert out["streams"]["emissions_comp"] is None
    assert out["annual_kg"] is None
    assert out["damage_cost_per_kg"] is None
    assert out["availability"]["emissions_comp"]["available"] is False
    assert out["availability"]["emissions_comp"]["missing_inputs"] == (_HOURS_REV,)
