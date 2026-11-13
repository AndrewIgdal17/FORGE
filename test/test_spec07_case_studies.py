"""Case-study terminals are the accepted 2026-11-12 table, and margin stays margin."""

import json

import pytest

import forge
from forge.emissions_data import (
    calendar_year,
    criteria_damage_2025_usd_per_kg,
    egrid_rates,
)
from test.spec05_project import ACRE_ZEROS, item, measured, project_changes
from test.spec07_regions import REGION_SENTINELS

SUNZIA = ("SunZia_Delay2", "SunZia_Delay17")
SAME_REGION = (
    "CTT_Actual_Delay2",
    "CTT_Counterfactual_Delay7",
    "AEP_LRGV_ACCC",
    "AEP_LRGV_ACSR_Rebuild",
    "AEP_LRGV_Laredo_NewBuild",
)
SUNZIA_SENDING = {
    "gea": "WestConnect_South",
    "egrid_subregion": "AZNM",
    "state": "NM",
}
SUNZIA_RECEIVING = {
    "gea": "WestConnect_South",
    "egrid_subregion": "AZNM",
    "state": "AZ",
}
ERCOT_END = {"gea": "ERCOT", "egrid_subregion": "ERCT", "state": "TX"}


def _path(name: str):
    return forge.get_scenarios_path() / f"{name}.forge"


def _document(name: str) -> dict:
    return json.loads(_path(name).read_text())


def _terminals(name: str) -> tuple[dict, dict, str]:
    technical = _document(name)["inputs"]["01_project_technical_details"]
    terminals = technical["terminals"]
    return terminals["sending"], terminals["receiving"], technical["project"]["sending_source"]


def _run(name: str) -> dict:
    changes = forge.diff_changes(_document(name)["inputs"])
    changes.update(ACRE_ZEROS)
    for path, value in REGION_SENTINELS.items():
        changes.setdefault(path, value)
    return forge.run_calculation(forge.resolve_inputs(changes))


def test_case_study_files_carry_the_accepted_terminals():
    names = SUNZIA + SAME_REGION
    assert len(names) == 7
    for name in names:
        text = _path(name).read_text()
        assert "SPP_South" not in text
        sending, receiving, source = _terminals(name)
        assert source == "margin"
        if name in SUNZIA:
            assert sending == SUNZIA_SENDING
            assert receiving == SUNZIA_RECEIVING
        else:
            assert sending == ERCOT_END
            assert receiving == ERCOT_END


@pytest.mark.parametrize("name", SAME_REGION)
def test_same_region_case_studies_avoid_nothing(name):
    results = _run(name)
    avoided = results["benefits"]["avoided_emissions"]
    assert avoided["rates_used"]["sending"]["source"] == "margin"
    assert avoided["rates_used"]["sending"]["gea"] == "ERCOT"
    assert avoided["rates_used"]["sending"]["egrid_subregion"] == "ERCT"
    assert avoided["rates_used"]["sending"]["state"] == "TX"
    assert avoided["rates_used"]["receiving"]["gea"] == "ERCOT"
    assert avoided["rates_used"]["receiving"]["egrid_subregion"] == "ERCT"
    assert avoided["rates_used"]["receiving"]["state"] == "TX"
    benefit = item(results, "avoided_emissions_benefit")
    assert benefit["available"] is False
    assert benefit["value_pv"] is None
    assert benefit["stream"] is None
    assert avoided["annual_kg_avoided"] is None
    assert avoided["net_binding_hours"] is None


@pytest.mark.parametrize("name", SUNZIA)
def test_sunzia_unmeasured_hours_leave_avoided_emissions_unavailable(name):
    """Stored SunZia hours are null. Terminals stay on rates_used."""
    results = _run(name)
    avoided = results["benefits"]["avoided_emissions"]
    assert avoided["rates_used"]["sending"]["source"] == "margin"
    assert avoided["rates_used"]["sending"] == {
        "gea": "WestConnect_South",
        "egrid_subregion": "AZNM",
        "state": "NM",
        "source": "margin",
    }
    assert avoided["rates_used"]["receiving"] == SUNZIA_RECEIVING
    assert avoided["annual_kg_avoided"] is None
    assert avoided["avoided_emissions_annual_values"] is None
    assert avoided["net_binding_hours"] is None
    assert isinstance(avoided["relief_mw"], (int, float))
    benefit = item(results, "avoided_emissions_benefit")
    assert benefit["available"] is False
    assert benefit["value_pv"] is None
    assert benefit["stream"] is None


def test_sunzia_state_gap_uses_net_binding_hours():
    """Same GEA, different states. Dollars use relief times net hours, not delivered energy."""
    changes = project_changes(**{
        "01_project_technical_details.timeline.project_lifetime": 1,
        **measured(
            congestion_spread_per_mwh=5,
            hours_receiving_more_congested=2000,
            hours_sending_more_congested=0,
            receiving_energy_value_per_mwh=30,
        ),
    })
    results = forge.run_calculation(forge.resolve_inputs(changes))
    avoided = results["benefits"]["avoided_emissions"]
    relief = results["derived_parameters"]["relief_mw"]
    assert relief == 500
    assert avoided["relief_mw"] == 500
    assert avoided["net_binding_hours"] == 2000
    factor = 500 * 2000
    assert avoided["annual_kg_avoided"]["co2e"] == pytest.approx([0.0])
    assert avoided["annual_kg_avoided"]["so2"] == pytest.approx([0.0])
    year = calendar_year(results["derived_parameters"]["t_cod"])
    so2_rate, nox_rate = egrid_rates("AZNM")
    dollars = avoided["avoided_emissions_annual_values"][0]
    so2_dollars = factor * so2_rate * (
        criteria_damage_2025_usd_per_kg("AZ", "so2", year)
        - criteria_damage_2025_usd_per_kg("NM", "so2", year)
    )
    nox_dollars = factor * nox_rate * (
        criteria_damage_2025_usd_per_kg("AZ", "nox", year)
        - criteria_damage_2025_usd_per_kg("NM", "nox", year)
    )
    assert dollars - nox_dollars == pytest.approx(so2_dollars, abs=1e-4)
    assert results["derived_parameters"]["energy_delivered_annual_mwh_yr"] != factor


def test_unknown_receiving_gea_has_no_cambium_row():
    changes = project_changes_delay_zero()
    inputs = forge.resolve_inputs(changes)
    inputs["01_project_technical_details"]["terminals"]["receiving"]["gea"] = "NOT_A_REGION"
    with pytest.raises(forge.InvalidInputs, match=r"No Cambium data for gea 'NOT_A_REGION'\."):
        forge.run_calculation(inputs)


def project_changes_delay_zero() -> dict:
    from test.spec05_project import project_changes

    return project_changes(**{"01_project_technical_details.timeline.delay_years": 0})
