"""Externality streams are societal only; avoided emissions is its own benefit."""
import pytest

from forge.scripts.io.taxonomy import TAXONOMY
from forge.scripts.utils.streams import pv

from test.spec05_project import item, project_changes, run

EXT = ("wildfire_eac", "outage_eac", "emissions_comp", "avoided_emissions_benefit")
_SOURCE = "01_project_technical_details.project.sending_source"
_SEND = "01_project_technical_details.terminals.sending."
_RECV = "01_project_technical_details.terminals.receiving."
_RATE = "01_project_technical_details.project.dedicated_resource.emission_rate_kg_per_mwh."


def test_avoided_emissions_survive():
    """Two different margins. The benefit is the rate gap, and the source stays margin."""
    changes = project_changes(**{
        _SOURCE: "margin",
        _SEND + "gea": "WestConnect_South",
        _SEND + "egrid_subregion": "AZNM",
        _SEND + "state": "AZ",
        _RECV + "gea": "CAISO",
        _RECV + "egrid_subregion": "CAMX",
        _RECV + "state": "CA",
    })
    results = run(changes)
    mass = results["benefits"]["avoided_emissions"]["annual_kg_avoided"]["co2e"]
    assert any(year != 0.0 for year in mass)
    assert item(results, "avoided_emissions_benefit")["value_pv"] != 0.0


def test_avoided_emissions_zero_when_rates_equal():
    """The same margin at both ends. Equal rates, still margin, so the benefit is zero."""
    same = {
        _SOURCE: "margin",
        _SEND + "gea": "ERCOT",
        _SEND + "egrid_subregion": "ERCT",
        _SEND + "state": "TX",
        _RECV + "gea": "ERCOT",
        _RECV + "egrid_subregion": "ERCT",
        _RECV + "state": "TX",
    }
    results = run(project_changes(**same))
    benefit = item(results, "avoided_emissions_benefit")
    assert benefit["value_pv"] == 0.0
    assert benefit["stream"] == pytest.approx([0.0] * len(benefit["stream"]))
    mass = results["benefits"]["avoided_emissions"]["annual_kg_avoided"]
    for pollutant in ("co2e", "so2", "nox"):
        assert mass[pollutant] == pytest.approx([0.0] * len(mass[pollutant]))


def test_dedicated_wind_avoids_positive_co2e_mass():
    """A dedicated wind resource at rate 0. Not a case study. Avoided CO2e mass is positive."""
    changes = project_changes(**{
        _SOURCE: "dedicated",
        "01_project_technical_details.project.dedicated_resource.contract_price_per_mwh": 0.0,
        _RATE + "co2e": 0.0,
        _RATE + "so2": 0.0,
        _RATE + "nox": 0.0,
    })
    mass = run(changes)["benefits"]["avoided_emissions"]["annual_kg_avoided"]["co2e"]
    assert sum(mass) > 0.0


def test_externalities_societal_only():
    r = run(project_changes())
    for tid in EXT:
        i = item(r, tid)
        assert i["value_pv_wacc"] is None
        assert i["value_pv"] == pytest.approx(pv(i["stream"], 0.02), rel=1e-9)


def test_taxonomy_has_31_items_and_no_removed_ids():
    ids = {t.id for t in TAXONOMY.values()}
    assert len(ids) == 31
    assert not ids & {"emissions_fac", "emissions_displacement_delay", "congestion_delay"}


def test_wildfire_grows_from_base_year():                              # A2
    T = "01_project_technical_details.timeline."
    WG = "06_wildfire_costs.wildfire.risk_growth_rate"
    a = run(project_changes(**{T+"delay_years": 2, T+"construction_years": 3, WG: 0.02}))
    b = run(project_changes(**{T+"delay_years": 2, T+"construction_years": 3, WG: 0.0}))
    assert item(a, "wildfire_eac")["stream"][5] == pytest.approx(item(b, "wildfire_eac")["stream"][5] * 1.02**5)
