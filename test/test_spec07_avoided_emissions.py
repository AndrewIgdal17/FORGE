"""Avoided-emissions dollars from terminal rates and each end's own damage price."""

from types import SimpleNamespace

import pytest

from forge.emissions_data import calendar_year
from forge.scripts.calc.avoided_emissions import (
    calculate_avoided_emissions,
    resolve_rate_series,
)

_HFWD = (
    "01_project_technical_details.market_measurements.hours_receiving_more_congested"
)
_HREV = (
    "01_project_technical_details.market_measurements.hours_sending_more_congested"
)

# 2025$/kg from the BPT short-ton rows. NM and AZ share the AZNM SO2 row.
# Injected here; this test does not call the damage loader.
_KG_PER_SHORT_TON = 907.185
_CPI_2025 = 321.943
_CPI_2019 = 255.657
_SO2_AZNM_2019_PER_SHORT_TON = 15600.0
_NOX_AZ_2019_PER_SHORT_TON = 674.0 + 15900.0
_NOX_NM_2019_PER_SHORT_TON = 411.0 + 5060.0


def _usd_per_kg(usd_2019_per_short_ton: float) -> float:
    return usd_2019_per_short_ton / _KG_PER_SHORT_TON * _CPI_2025 / _CPI_2019


def _rates_used(
    source: str,
    *,
    receiving_gea: str,
    receiving_subregion: str,
    receiving_state: str,
    sending_gea: str,
    sending_subregion: str,
    sending_state: str,
) -> dict:
    return {
        "receiving": {
            "gea": receiving_gea,
            "egrid_subregion": receiving_subregion,
            "state": receiving_state,
        },
        "sending": {
            "gea": sending_gea,
            "egrid_subregion": sending_subregion,
            "state": sending_state,
        },
        "_source": source,
    }


def _benefit(**overrides):
    """Margin case: factor 100 from relief 100 and one net binding hour.

    CAMX / CAISO / CA receiving, AZNM / WestConnect_South / AZ sending.
    """
    rates = _rates_used(
        "margin",
        receiving_gea="CAISO",
        receiving_subregion="CAMX",
        receiving_state="CA",
        sending_gea="WestConnect_South",
        sending_subregion="AZNM",
        sending_state="AZ",
    )
    source = rates.pop("_source")
    kwargs = {
        "sending_source": source,
        "relief_mw": 100.0,
        "hours_forward": 1.0,
        "hours_reverse": 0.0,
        "e_deliv_mwh_per_year": None,
        "rcv_co2e": [400.0],
        "snd_co2e": [250.0],
        "rcv_so2": 0.02,
        "snd_so2": 0.05,
        "rcv_nox": 0.0,
        "snd_nox": 0.0,
        "c_co2e": [0.25],
        "c_so2_rcv": [10.0],
        "c_so2_snd": [4.0],
        "c_nox_rcv": [0.0],
        "c_nox_snd": [0.0],
        "t_cod": 2,
        "horizon": 2,
        "social_discount_rate": 0.02,
        "rates_used": rates,
    }
    kwargs.update(overrides)
    return calculate_avoided_emissions(**kwargs)


def test_margin_one_operating_year_prices_each_terminal():
    q_co2e = 100 * (400 - 250)
    q_so2 = 100 * (0.02 - 0.05)
    dollars = q_co2e * 0.25 + 100 * (0.02 * 10 - 0.05 * 4)
    out = _benefit(e_deliv_mwh_per_year=9999.0)
    assert out["annual_kg_avoided"]["so2"] == pytest.approx([q_so2])
    assert out["annual_kg_avoided"]["co2e"] == pytest.approx([q_co2e])
    assert out["avoided_emissions_annual_values"] == pytest.approx([dollars])
    assert out["streams"]["avoided_emissions_benefit"] == pytest.approx([0.0, dollars])
    assert out["avoided_emissions_pv"] == pytest.approx(dollars / (1.02 ** 2))
    assert out["avoided_emissions_nominal"] == pytest.approx(dollars)
    assert out["rates_used"]["receiving"] == {
        "gea": "CAISO",
        "egrid_subregion": "CAMX",
        "state": "CA",
    }
    assert out["rates_used"]["sending"]["gea"] == "WestConnect_South"
    assert out["rates_used"]["sending"]["egrid_subregion"] == "AZNM"
    assert out["rates_used"]["sending"]["state"] == "AZ"
    assert out["rates_used"]["sending"]["source"] == "margin"
    priced_as_one_so2_cost = q_co2e * 0.25 + q_so2 * 10
    assert dollars != pytest.approx(priced_as_one_so2_cost)
    assert out["relief_mw"] == 100
    assert out["net_binding_hours"] == 1
    assert "energy_delivered_annual_mwh_yr" not in out


def test_dedicated_sending_rates_are_zero():
    e_deliv = 100.0
    rcv_co2e = 400.0
    rcv_so2 = 0.02
    c_ca = 10.0
    c_co2e = 0.25
    given = {
        "receiving": {
            "gea": "CAISO",
            "egrid_subregion": "CAMX",
            "state": "CA",
        },
        "sending": {
            "gea": "WestConnect_South",
            "egrid_subregion": "AZNM",
            "state": "AZ",
        },
    }
    given["sending"]["gea"] = None
    out = _benefit(
        sending_source="dedicated",
        e_deliv_mwh_per_year=e_deliv,
        relief_mw=999.0,
        hours_forward=10.0,
        hours_reverse=0.0,
        snd_co2e=[0.0],
        snd_so2=0.0,
        snd_nox=0.0,
        rcv_co2e=[rcv_co2e],
        rcv_so2=rcv_so2,
        c_so2_rcv=[c_ca],
        c_co2e=[c_co2e],
        rates_used=given,
    )
    so2_dollars = e_deliv * rcv_so2 * c_ca
    assert out["annual_kg_avoided"]["co2e"] == pytest.approx([e_deliv * rcv_co2e])
    assert out["avoided_emissions_annual_values"] == pytest.approx(
        [e_deliv * rcv_co2e * c_co2e + so2_dollars]
    )
    assert out["rates_used"]["sending"]["source"] == "dedicated"
    assert out["rates_used"]["sending"]["gea"] is None
    assert out["energy_delivered_annual_mwh_yr"] == e_deliv
    assert out["net_binding_hours"] is None
    assert "relief_mw" not in out
    assert "source" not in given["sending"]


def test_same_state_margin_is_zero():
    rates = _rates_used(
        "margin",
        receiving_gea="WestConnect_South",
        receiving_subregion="AZNM",
        receiving_state="AZ",
        sending_gea="WestConnect_South",
        sending_subregion="AZNM",
        sending_state="AZ",
    )
    rates.pop("_source")
    out = _benefit(
        rcv_co2e=[400.0],
        snd_co2e=[400.0],
        rcv_so2=0.02,
        snd_so2=0.02,
        rcv_nox=0.20,
        snd_nox=0.20,
        c_co2e=[0.25],
        c_so2_rcv=[10.0],
        c_so2_snd=[10.0],
        c_nox_rcv=[20.0],
        c_nox_snd=[20.0],
        rates_used=rates,
    )
    assert out["streams"]["avoided_emissions_benefit"] == pytest.approx([0.0, 0.0])
    assert out["avoided_emissions_annual_values"] == pytest.approx([0.0])
    assert out["avoided_emissions_pv"] == pytest.approx(0.0)
    assert out["avoided_emissions_nominal"] == pytest.approx(0.0)
    for pollutant in ("co2e", "so2", "nox"):
        assert out["annual_kg_avoided"][pollutant] == pytest.approx([0.0])


def test_different_states_same_rates_price_each_terminal():
    """SunZia shape: same GEA, same subregion, NM sending into AZ."""
    e_deliv = 100.0
    eps_co2e = 250.0
    eps_so2 = 0.05
    eps_nox = 0.20
    c_co2e = 0.25
    c_so2_rcv = _usd_per_kg(_SO2_AZNM_2019_PER_SHORT_TON)
    c_so2_snd = _usd_per_kg(_SO2_AZNM_2019_PER_SHORT_TON)
    c_nox_rcv = _usd_per_kg(_NOX_AZ_2019_PER_SHORT_TON)
    c_nox_snd = _usd_per_kg(_NOX_NM_2019_PER_SHORT_TON)
    rates = _rates_used(
        "margin",
        receiving_gea="WestConnect_South",
        receiving_subregion="AZNM",
        receiving_state="AZ",
        sending_gea="WestConnect_South",
        sending_subregion="AZNM",
        sending_state="NM",
    )
    rates.pop("_source")
    out = _benefit(
        rcv_co2e=[eps_co2e],
        snd_co2e=[eps_co2e],
        rcv_so2=eps_so2,
        snd_so2=eps_so2,
        rcv_nox=eps_nox,
        snd_nox=eps_nox,
        c_co2e=[c_co2e],
        c_so2_rcv=[c_so2_rcv],
        c_so2_snd=[c_so2_snd],
        c_nox_rcv=[c_nox_rcv],
        c_nox_snd=[c_nox_snd],
        rates_used=rates,
    )
    so2_dollars = e_deliv * eps_so2 * (c_so2_rcv - c_so2_snd)
    nox_dollars = e_deliv * eps_nox * (c_nox_rcv - c_nox_snd)
    co2e_dollars = 0.0
    assert out["annual_kg_avoided"]["co2e"] == pytest.approx([0.0])
    assert out["annual_kg_avoided"]["so2"] == pytest.approx([0.0])
    assert out["annual_kg_avoided"]["nox"] == pytest.approx([0.0])
    assert out["avoided_emissions_annual_values"] == pytest.approx(
        [co2e_dollars + so2_dollars + nox_dollars]
    )
    q_so2 = e_deliv * (eps_so2 - eps_so2)
    q_nox = e_deliv * (eps_nox - eps_nox)
    priced_with_one_damage_cost = q_so2 * c_so2_rcv + q_nox * c_nox_rcv
    assert out["avoided_emissions_annual_values"] != pytest.approx(
        [priced_with_one_damage_cost]
    )


def test_zero_net_binding_hours_returns_a_zero_stream():
    out = _benefit(hours_forward=5, hours_reverse=5)
    assert out["net_binding_hours"] == 0
    assert out["availability"]["avoided_emissions_benefit"]["available"] is True
    assert out != {}
    assert out["streams"]["avoided_emissions_benefit"] == [0.0, 0.0]
    assert len(out["streams"]["avoided_emissions_benefit"]) == 2
    assert out["avoided_emissions_annual_values"] == pytest.approx([0.0])
    assert out["avoided_emissions_pv"] == pytest.approx(0.0)
    assert out["avoided_emissions_nominal"] == pytest.approx(0.0)


def test_delayed_cod_uses_the_2030_co2e_rate():
    table = {2026: 400.0, 2030: 180.0}
    snd = 250.0
    e_deliv = 100.0
    assert calendar_year(2) == 2026
    assert calendar_year(6) == 2030
    early = _benefit(
        t_cod=2,
        horizon=2,
        rcv_co2e=[table[calendar_year(2)]],
        snd_co2e=[snd],
    )
    late = _benefit(
        t_cod=6,
        horizon=6,
        rcv_co2e=[table[calendar_year(6)]],
        snd_co2e=[snd],
    )
    assert early["annual_kg_avoided"]["co2e"] == pytest.approx(
        [e_deliv * (table[2026] - snd)]
    )
    assert late["annual_kg_avoided"]["co2e"] == pytest.approx(
        [e_deliv * (table[2030] - snd)]
    )
    assert late["streams"]["avoided_emissions_benefit"][:5] == [0.0] * 5


def test_margin_without_hour_counts_is_not_available():
    out = _benefit(hours_forward=None, hours_reverse=None, relief_mw=80)
    assert out["relief_mw"] == 80
    assert out["net_binding_hours"] is None
    assert out["avoided_emissions_pv"] is None
    assert out["avoided_emissions_nominal"] is None
    assert out["avoided_emissions_annual_values"] is None
    assert out["streams"]["avoided_emissions_benefit"] is None
    assert out["annual_kg_avoided"] is None
    assert out["rates_used"]["sending"]["gea"] == "WestConnect_South"
    assert out["rates_used"]["sending"]["source"] == "margin"
    assert out["rates_used"]["receiving"]["state"] == "CA"
    assert out["availability"]["avoided_emissions_benefit"]["available"] is False
    assert out["availability"]["avoided_emissions_benefit"]["missing_inputs"] == (
        _HFWD,
        _HREV,
    )


def test_dedicated_resource_rates_skip_a_missing_sending_gea(monkeypatch):
    import forge.emissions_data as emissions_data

    def _lrmer(gea, year):
        if gea is None:
            raise AssertionError("sending Cambium lookup")
        return 10.0

    def _egrid(subregion):
        if subregion is None:
            raise AssertionError("sending eGRID lookup")
        return (0.1, 0.2)

    monkeypatch.setattr(emissions_data, "lrmer_co2e", _lrmer)
    monkeypatch.setattr(emissions_data, "egrid_rates", _egrid)
    details = SimpleNamespace(
        sending_source="dedicated",
        sending_gea=None,
        sending_egrid_subregion=None,
        sending_state="AZ",
        receiving_gea="CAISO",
        receiving_egrid_subregion="CAMX",
        receiving_state="CA",
        emission_rate_co2e=0.0,
        emission_rate_so2=0.0,
        emission_rate_nox=0.0,
    )
    series = resolve_rate_series(
        details, [2026], hours_forward=None, hours_reverse=None
    )
    assert series["snd_co2e"] == [0.0]
    assert series["snd_so2"] == 0.0
    assert series["snd_nox"] == 0.0
    assert series["rcv_co2e"] == [10.0]
    assert series["sending"]["gea"] is None
    assert series["sending"]["egrid_subregion"] is None
    assert series["sending"]["state"] == "AZ"
    assert series["receiving"]["gea"] == "CAISO"
    assert series["receiving"]["egrid_subregion"] == "CAMX"
