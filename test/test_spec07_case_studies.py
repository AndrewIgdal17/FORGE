"""Case-study terminals are the accepted 2026-11-12 table, and margin stays margin."""

import json

import pytest

import forge
from forge.emissions_data import (
    calendar_year,
    criteria_damage_2025_usd_per_kg,
    egrid_rates,
)
from test.spec05_project import ACRE_ZEROS, item
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
    stream = item(results, "avoided_emissions_benefit")["stream"]
    assert stream
    assert stream == pytest.approx([0.0] * len(stream))


@pytest.mark.parametrize("name", SUNZIA)
def test_sunzia_co2e_mass_is_zero_and_so2_dollars_follow_the_state_gap(name):
    results = _run(name)
    avoided = results["benefits"]["avoided_emissions"]
    delivered = results["benefits"]["congestion"]["energy_delivered_annual_mwh_yr"]
    co2e_kg = avoided["annual_kg_avoided"]["co2e"]
    assert co2e_kg == pytest.approx([0.0] * len(co2e_kg))
    assert delivered > 0
    so2_rate, nox_rate = egrid_rates("AZNM")
    t_cod = results["derived_parameters"]["t_cod"]
    lifetime = len(avoided["avoided_emissions_annual_values"])
    for index, dollars in enumerate(avoided["avoided_emissions_annual_values"]):
        year = calendar_year(t_cod + index)
        c_az = criteria_damage_2025_usd_per_kg("AZ", "so2", year)
        c_nm = criteria_damage_2025_usd_per_kg("NM", "so2", year)
        so2_dollars = delivered * so2_rate * (c_az - c_nm)
        c_az_nox = criteria_damage_2025_usd_per_kg("AZ", "nox", year)
        c_nm_nox = criteria_damage_2025_usd_per_kg("NM", "nox", year)
        nox_dollars = delivered * nox_rate * (c_az_nox - c_nm_nox)
        # CO2e mass is zero, so the year's dollars are the two criteria terms.
        # The SO2 term is delivered energy times the shared AZNM rate times
        # (c_AZ - c_NM). Subtracting the NOx term from the year's dollars
        # leaves a few billionths from float cancellation.
        assert dollars - nox_dollars == pytest.approx(so2_dollars, abs=1e-4)
    assert lifetime == len(co2e_kg)
    assert calendar_year(t_cod) >= 2025


def test_unknown_receiving_gea_has_no_cambium_row():
    changes = project_changes_delay_zero()
    inputs = forge.resolve_inputs(changes)
    inputs["01_project_technical_details"]["terminals"]["receiving"]["gea"] = "NOT_A_REGION"
    with pytest.raises(forge.InvalidInputs, match=r"No Cambium data for gea 'NOT_A_REGION'\."):
        forge.run_calculation(inputs)


def project_changes_delay_zero() -> dict:
    from test.spec05_project import project_changes

    return project_changes(**{"01_project_technical_details.timeline.delay_years": 0})
