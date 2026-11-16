"""Spec 16: line vs converter O&M and insurance parts; numbers unchanged."""
import json
from pathlib import Path

import pytest

from forge.scripts.io.input_metadata import INPUT_METADATA
from forge.scripts.io.taxonomy import (
    INSURANCE_IDS,
    OANDM_IDS,
    TAXONOMY,
    TAXONOMY_TO_CALCULATOR_KEY,
)

from test.spec05_project import item, run
from test.spec11_scenarios import DC_RECONDUCTORING, scenario_changes

BEFORE = json.loads(
    (Path(__file__).parent / "data" / "spec16_before_numbers.json").read_text()
)
MOVED = {"AEP_LRGV_ACCC", "AEP_LRGV_ACSR_Rebuild", "DC_reconductoring"}
PROJECT = "01_project_technical_details.project."
ATRR_PARTS = frozenset(
    {"capital_recovery", "row_rent", *OANDM_IDS, *INSURANCE_IDS}
)


def _part_pv_sum(results: dict, line_id: str, conv_id: str) -> float:
    total = 0.0
    for tid in (line_id, conv_id):
        e = item(results, tid)
        if e["applies"] and e["value_pv"] is not None:
            total += e["value_pv"]
    return total


def _part_wacc_sum(results: dict, line_id: str, conv_id: str) -> float:
    total = 0.0
    for tid in (line_id, conv_id):
        e = item(results, tid)
        if e["applies"] and e["value_pv_wacc"] is not None:
            total += e["value_pv_wacc"]
    return total


def test_dc_greenfield_parts_sum_to_before():
    r = run(scenario_changes("SunZia_Delay2"))
    for tid in OANDM_IDS | INSURANCE_IDS:
        assert item(r, tid)["state"] == "measured"
    name = "SunZia_Delay2"
    assert _part_pv_sum(r, "oandm_line", "oandm_converter") == pytest.approx(
        BEFORE[name]["items"]["oandm"], rel=1e-9
    )
    assert _part_pv_sum(r, "insurance_line", "insurance_converter") == pytest.approx(
        BEFORE[name]["items"]["insurance"], rel=1e-9
    )
    assert _part_wacc_sum(r, "oandm_line", "oandm_converter") == pytest.approx(
        BEFORE[name]["costs"]["oandm"]["total_pv_wacc"], rel=1e-9
    )
    assert _part_wacc_sum(r, "insurance_line", "insurance_converter") == pytest.approx(
        BEFORE[name]["costs"]["insurance"]["pv_total_wacc"], rel=1e-9
    )


def _scenario_run(name: str) -> dict:
    if name == "DC_reconductoring":
        return run(scenario_changes("AEP_LRGV_ACCC", **DC_RECONDUCTORING))
    return run(scenario_changes(name))


def test_split_moves_no_number():
    for name in BEFORE:
        if name in MOVED:
            continue
        expected = BEFORE[name]
        r = _scenario_run(name)
        got_bcr = {k: v for k, v in r["bcr"].items() if k != "omitted"}
        for key, value in expected["bcr"].items():
            if key not in got_bcr:
                continue
            if value is None:
                assert got_bcr[key] is None, (name, key)
            else:
                assert got_bcr[key] == pytest.approx(value, rel=1e-9, abs=1e-6), (name, key)
        got_items = {e["taxonomy_id"]: e["value_pv"] for e in r["taxonomy_results"]}
        for key, value in expected["items"].items():
            if key in ("oandm", "insurance"):
                continue
            if value is None:
                assert got_items.get(key) is None, (name, key)
            else:
                assert got_items[key] == pytest.approx(value, rel=1e-9, abs=1e-6), (name, key)


@pytest.mark.parametrize("scenario", ("SunZia_Delay2", "CTT_Actual_Delay2"))
def test_revenue_requirement_sums_applying_parts(scenario):
    r = run(scenario_changes(scenario))
    total = 0.0
    for tid in ATRR_PARTS:
        e = item(r, tid)
        if e["applies"] and e["value_pv_wacc"] is not None:
            total += e["value_pv_wacc"]
    assert r["bcr"]["utility_benefits_pv"] == pytest.approx(total, rel=1e-9)


def test_dc_reconductoring():  # Review Focus 1
    r = _scenario_run("DC_reconductoring")
    for tid in ("oandm_line", "oandm_converter", "insurance_converter"):
        assert item(r, tid)["state"] == "does_not_apply"
    assert r["bcr"]["oandm_pv"] == 0.0
    assert item(r, "line_loss_converter")["applies"] is True
    assert item(r, "insurance_line")["state"] == "measured"
    ins = r["costs"]["insurance"]
    assert ins["line_annual_premium"] == pytest.approx(
        ins["line_rate"] * r["derived_parameters"]["conductor_cost_with_contingencies"]
    )


def test_rebuild_insurance_on_conductor_and_structures():
    r = _scenario_run("AEP_LRGV_ACSR_Rebuild")
    ins = r["costs"]["insurance"]
    dp = r["derived_parameters"]
    base = dp["conductor_cost_with_contingencies"] + dp["structure_cost_with_contingencies"]
    assert ins["line_annual_premium"] == pytest.approx(ins["line_rate"] * base)


def test_only_line_om_moves():
    for name in MOVED:
        before = BEFORE[name]
        r = _scenario_run(name)
        oandm_legacy = before["items"]["oandm"]
        assert r["bcr"]["total_costs_pv"] == pytest.approx(
            before["bcr"]["total_costs_pv"] - oandm_legacy, rel=1e-9, abs=1e-6
        )
        assert r["bcr"]["utility_benefits_pv"] == pytest.approx(
            before["bcr"]["utility_benefits_pv"]
            - before["costs"]["oandm"]["total_pv_wacc"],
            rel=1e-9,
            abs=1e-6,
        )
        assert r["bcr"]["insurance_pv"] == pytest.approx(
            before["costs"]["insurance"]["pv_total"], rel=1e-9, abs=1e-6
        )
        assert r["bcr"]["total_benefits_pv"] == pytest.approx(
            before["bcr"]["total_benefits_pv"], rel=1e-9, abs=1e-6
        )


def test_dc_without_converters():
    r = run(
        scenario_changes(
            "SunZia_Delay2",
            **{PROJECT + "number_of_converters": 0},
        )
    )
    assert item(r, "build_converter")["state"] == "does_not_apply"
    for tid in ("oandm_converter", "insurance_converter"):
        e = item(r, tid)
        assert e["state"] == "does_not_apply"
        assert e["value_pv"] is None
        assert e["value_pv_wacc"] is None
        assert e["stream"] is None


def test_modules_not_run():
    r = run(scenario_changes("SunZia_Delay2"), no_oandm=True, no_insurance=True)
    for e in r["taxonomy_results"]:
        assert not e["taxonomy_id"].startswith("oandm")
        assert not e["taxonomy_id"].startswith("insurance")
    assert r["bcr"]["oandm_pv"] == 0.0 == r["bcr"]["insurance_pv"]


_LABELS = {
    "oandm_line": "Line O&M",
    "oandm_converter": "Converter O&M",
    "insurance_line": "Line insurance",
    "insurance_converter": "Converter insurance",
}


def test_taxonomy_ids():
    assert OANDM_IDS | INSURANCE_IDS <= set(TAXONOMY)
    assert "oandm" not in TAXONOMY
    assert "insurance" not in TAXONOMY
    for tid, label in _LABELS.items():
        assert TAXONOMY[tid].category == "operating"
        assert TAXONOMY[tid].label == label
        assert TAXONOMY_TO_CALCULATOR_KEY[tid] == tid + "_pv"


def test_metadata_ids():
    legacy = {"oandm", "insurance"}
    assert not any(f.taxonomy_id in legacy for f in INPUT_METADATA.values())
    routes = {
        "converter_om_lcc": "oandm_converter",
        "converter_om_vsc": "oandm_converter",
        "insurance_premium_converter": "insurance_converter",
        "struct_om_overhead": "oandm_line",
        "struct_om_ug_direct_buried": "oandm_line",
        "struct_om_ug_tunnel": "oandm_line",
        "om_real_escalation_rate": "oandm_line",
        "insurance_premium_rate": "insurance_line",
        "insurance_premium_overhead": "insurance_line",
        "insurance_premium_underground_direct_buried": "insurance_line",
        "insurance_premium_underground_tunnel": "insurance_line",
        "insurance_escalation_rate": "insurance_line",
    }
    for field_id, tid in routes.items():
        assert INPUT_METADATA[field_id].taxonomy_id == tid
    veg = [f for f in INPUT_METADATA.values() if f.field_path.startswith("vegetation_management")]
    assert veg and all(f.taxonomy_id == "oandm_line" for f in veg)