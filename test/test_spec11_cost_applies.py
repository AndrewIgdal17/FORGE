"""Spec 11: costs the method switches off do not apply; one state per result."""
import json
import pathlib

import pytest

from test.spec05_project import item, measured, project_changes, run
from test.spec11_scenarios import DC_RECONDUCTORING, SCENARIOS, numbers, scenario_changes

STATES = {"measured", "not_available", "does_not_apply"}
PROJECT = "01_project_technical_details.project."
_ROUTELESS = measured(
    congestion_spread_per_mwh=None,
    hours_receiving_more_congested=None,
    hours_sending_more_congested=None,
    receiving_energy_value_per_mwh=None,
)


def _consistent(entry: dict) -> None:
    assert entry["state"] in STATES
    assert (entry["state"] == "not_available") == (entry["available"] is False)
    assert (entry["state"] == "does_not_apply") == (entry["applies"] is False)


# --- Task 1: state -----------------------------------------------------------


def test_every_result_has_one_consistent_state():
    for changes in (project_changes(), project_changes(**_ROUTELESS)):
        r = run(changes)
        for entry in r["taxonomy_results"]:
            _consistent(entry)
        for entry in r["availability"].values():
            _consistent(entry)


def test_state_values_for_known_items():
    routeless = run(project_changes(**_ROUTELESS))
    assert item(routeless, "congestion_benefit")["state"] == "not_available"
    sunzia = run()
    assert item(sunzia, "delivered_energy_benefit")["state"] == "does_not_apply"
    assert item(sunzia, "build_conductor")["state"] == "measured"


# --- Task 2: the seven cost indicators ----------------------------------------

AGREEMENT = PROJECT + "row_agreement_type"
DELAY = "01_project_technical_details.timeline.delay_years"


def _states(results: dict, *ids: str) -> dict:
    return {tid: item(results, tid)["state"] for tid in ids}


@pytest.fixture(scope="module")
def runs():
    return {
        "dc_greenfield": run(project_changes(**measured())),  # SunZia: DC, easement
        "ac_greenfield": run(scenario_changes("CTT_Actual_Delay2")),  # AC, easement
        "ac_reconductoring": run(scenario_changes("AEP_LRGV_ACCC")),  # AC, lease
        "rebuild": run(scenario_changes("AEP_LRGV_ACSR_Rebuild")),  # AC, lease
    }


def test_structures(runs):
    assert item(runs["ac_reconductoring"], "build_structure")["state"] == "does_not_apply"
    assert item(runs["ac_greenfield"], "build_structure")["state"] == "measured"
    assert item(runs["rebuild"], "build_structure")["state"] == "measured"


def test_converter_stations(runs):
    assert item(runs["ac_greenfield"], "build_converter")["state"] == "does_not_apply"
    assert item(runs["ac_reconductoring"], "build_converter")["state"] == "does_not_apply"
    assert item(runs["dc_greenfield"], "build_converter")["state"] == "measured"
    assert item(runs["dc_greenfield"], "build_converter")["value_pv"] > 0


def test_converter_losses(runs):
    assert item(runs["ac_greenfield"], "line_loss_converter")["state"] == "does_not_apply"
    assert item(runs["dc_greenfield"], "line_loss_converter")["state"] == "measured"
    assert item(runs["dc_greenfield"], "line_loss_converter")["value_pv"] > 0


def test_dc_without_energy_value_converter_losses_not_available():  # Review Focus 1
    r = run(project_changes(**_ROUTELESS))
    assert item(r, "line_loss_converter")["state"] == "not_available"


def test_row_acquisition_and_holding(runs):
    lease = _states(runs["ac_reconductoring"], "row_acquisition", "row_holding")
    assert set(lease.values()) == {"does_not_apply"}
    easement = _states(runs["ac_greenfield"], "row_acquisition", "row_holding")
    assert set(easement.values()) == {"measured"}


def test_row_rent(runs):
    assert item(runs["ac_greenfield"], "row_rent")["state"] == "does_not_apply"
    assert item(runs["ac_reconductoring"], "row_rent")["state"] == "measured"
    assert item(runs["ac_reconductoring"], "row_rent")["value_pv"] > 0


def test_federal_hybrid_applies_all_three():  # Review Focus 3
    r = run(scenario_changes("CTT_Actual_Delay2", **{AGREEMENT: "federal_hybrid"}))
    states = _states(r, "row_acquisition", "row_holding", "row_rent")
    assert set(states.values()) == {"measured"}


def test_environmental_mitigation(runs):
    assert item(runs["ac_reconductoring"], "env_mitigation")["state"] == "does_not_apply"
    assert item(runs["ac_greenfield"], "env_mitigation")["state"] == "measured"
    assert item(runs["rebuild"], "env_mitigation")["state"] == "measured"


def test_zero_delay_holding_is_a_measured_zero():  # Review Focus 4
    r = run(scenario_changes("CTT_Actual_Delay2", **{DELAY: 0}))
    hold = item(r, "row_holding")
    assert hold["state"] == "measured"
    assert hold["value_pv"] == 0.0


def test_mitigation_indicator_and_multiplier():
    from forge.errors import InvalidInputs
    from forge.scripts.calc.environmental_mitigation import (
        disturbance_multiplier,
        mitigation_indicator,
    )

    assert mitigation_indicator("reconductoring") == 0.0
    assert mitigation_indicator("rebuild") == 1.0
    assert mitigation_indicator("greenfield") == 1.0
    assert disturbance_multiplier("rebuild", 0.5) == 0.5
    assert disturbance_multiplier("greenfield", 0.5) == 1.0
    for bad in ("reconductoring", "nope"):
        with pytest.raises(InvalidInputs):
            disturbance_multiplier(bad, 0.5)
    with pytest.raises(InvalidInputs):
        mitigation_indicator("nope")


# On AC lines with no measured energy value, the energy-loss subtotals held only
# not-available conductor losses and an AC converter loss reported as a measured
# $0. Under methodology §I.4 the converter loss does not apply, so these
# subtotals are now not available. Nothing else moves.
_NOW_NOT_AVAILABLE = {
    "energy_emissions_costs_nominal",
    "energy_emissions_costs_pv",
    "energy_losses_nominal",
    "energy_losses_pv",
}
_AC_WITHOUT_ENERGY_VALUE = {"CTT_Actual_Delay2", "AEP_LRGV_ACCC", "AEP_LRGV_ACSR_Rebuild"}
# Spec 16 F8: line O&M only on greenfield — BCR deltas covered by test_only_line_om_moves.
_LINE_OM_F8_SKIP_BCR = {"AEP_LRGV_ACCC", "AEP_LRGV_ACSR_Rebuild"}


def _legacy_operating_pv(got_items: dict, legacy_key: str) -> float | None:
    if legacy_key == "oandm":
        parts = ("oandm_line", "oandm_converter")
    elif legacy_key == "outage_eac":
        parts = ("outage_load_shed", "outage_redispatch")
    else:
        parts = ("insurance_line", "insurance_converter")
    total = 0.0
    any_measured = False
    for tid in parts:
        if tid not in got_items:
            return None
        v = got_items[tid]
        if v is not None:
            total += v
            any_measured = True
    return total if any_measured else None


def test_numbers_unchanged_from_5_1_1():
    expected = json.loads(
        (pathlib.Path(__file__).parent / "data" / "spec11_v511_numbers.json").read_text()
    )
    for name in SCENARIOS:
        results = run(scenario_changes(name))
        got = numbers(results)
        got_items = got["items"]
        for section in ("bcr", "items"):
            exp_keys = set(expected[name][section])
            if section == "items":
                exp_keys -= {"oandm", "insurance", "outage_eac"}
                assert exp_keys <= set(got_items), (name, exp_keys - set(got_items))
            else:
                assert set(got[section]) >= exp_keys, (name, section)
            for key, value in expected[name][section].items():
                if section == "items" and key in ("oandm", "insurance", "outage_eac"):
                    if key == "oandm" and name in _LINE_OM_F8_SKIP_BCR:
                        continue
                    got_val = _legacy_operating_pv(got_items, key)
                    if value is None:
                        assert got_val is None, (name, key)
                    else:
                        assert got_val == pytest.approx(value, rel=1e-9, abs=1e-6), (name, key)
                    continue
                if section == "bcr" and name in _LINE_OM_F8_SKIP_BCR:
                    continue
                if section == "bcr" and name in _AC_WITHOUT_ENERGY_VALUE and key in _NOW_NOT_AVAILABLE:
                    assert got[section][key] is None, (name, key)
                elif value is None:
                    assert got[section][key] is None, (name, key)
                else:
                    assert got[section][key] == pytest.approx(value, rel=1e-9, abs=1e-6), (name, key)


def test_capacity_inputs_are_not_marked_hidden():
    from forge.scripts.io.input_metadata import INPUT_METADATA

    fields = [f for f in INPUT_METADATA.values() if f.yaml_section == "20_capacity_value"]
    assert len(fields) == 3
    assert all(f.condition is None for f in fields)
    gate = next(f for f in fields if f.field_path == "applicability_gate")
    assert gate.help_text == (
        "Capacity value does not apply unless this is on. "
        "With it on, a credit or price of 0 gives a measured $0."
    )


def test_greenfield_without_wetland_or_habitat_credits_are_a_measured_zero():  # acceptance 5
    r = run(project_changes(**{"02_project_physical_details.terrain.terrain_miles.wetland": 0.0}))
    assert item(r, "env_mitigation")["state"] == "measured"
    assert r["costs"]["environmental"]["credits_pv"] == 0.0


def test_zero_delay_direct_delay_cost_is_a_measured_zero():  # acceptance 6
    r = run(scenario_changes("CTT_Actual_Delay2", **{DELAY: 0}))
    delay = item(r, "base_delay")
    assert delay["state"] == "measured"
    assert delay["value_pv"] == 0.0


def test_dc_reconductoring_converter_cost_off_losses_on():  # acceptance 11, Review Focus 2
    r = run(scenario_changes("AEP_LRGV_ACCC", **DC_RECONDUCTORING))
    assert item(r, "build_converter")["state"] == "does_not_apply"
    assert item(r, "build_structure")["state"] == "does_not_apply"
    assert item(r, "line_loss_converter")["applies"] is True
    for tid in ("oandm_converter", "insurance_converter"):
        assert item(r, tid)["state"] == "does_not_apply"


def test_line_om_greenfield_only(runs):
    for name in ("ac_reconductoring", "rebuild"):
        e = item(runs[name], "oandm_line")
        assert e["state"] == "does_not_apply" and e["value_pv"] is None
    for name in ("ac_greenfield", "dc_greenfield"):
        assert item(runs[name], "oandm_line")["state"] == "measured"


def test_converter_om_and_insurance(runs):
    for name in ("ac_greenfield", "ac_reconductoring", "rebuild"):
        for tid in ("oandm_converter", "insurance_converter"):
            e = item(runs[name], tid)
            assert e["state"] == "does_not_apply"
            assert e["value_pv"] is None and e["value_pv_wacc"] is None and e["stream"] is None
    for tid in ("oandm_converter", "insurance_converter"):
        assert item(runs["dc_greenfield"], tid)["state"] == "measured"
        assert item(runs["dc_greenfield"], tid)["value_pv"] > 0
    assert item(runs["ac_greenfield"], "insurance_line")["state"] == "measured"
