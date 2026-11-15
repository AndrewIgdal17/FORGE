"""Spec 10: benefits that do not apply drop out of every sum."""
import pytest

from forge.scripts.io.taxonomy_adapters import TaxonomyResult, _copy_availability
from test.spec05_project import item, measured, project_changes, run

MARGIN = "01_project_technical_details.project.sending_source"
GATE = "20_capacity_value.applicability_gate"
PRICE = "20_capacity_value.capacity_price"
_DEDICATED = {
    MARGIN: "dedicated",
    "01_project_technical_details.project.dedicated_resource.contract_price_per_mwh": 55.0,
    "01_project_technical_details.project.dedicated_resource.emission_rate_kg_per_mwh.co2e": 0.0,
    "01_project_technical_details.project.dedicated_resource.emission_rate_kg_per_mwh.so2": 0.0,
    "01_project_technical_details.project.dedicated_resource.emission_rate_kg_per_mwh.nox": 0.0,
}


def test_margin_line_delivered_energy_does_not_apply():
    r = run()  # bundled SunZia_Delay2: margin, gate on
    assert item(r, "delivered_energy_benefit")["applies"] is False
    assert item(r, "delivered_energy_benefit")["available"] is True
    assert item(r, "congestion_benefit")["applies"] is True
    assert item(r, "capacity_value_benefit")["applies"] is True
    assert r["availability"]["delivered_energy_benefit"]["applies"] is False


def test_dedicated_line_congestion_does_not_apply():
    r = run(project_changes(**_DEDICATED, **measured()))
    assert item(r, "congestion_benefit")["applies"] is False
    assert item(r, "congestion_benefit")["value_pv"] == 0.0
    assert item(r, "delivered_energy_benefit")["applies"] is True


def test_gate_off_capacity_value_does_not_apply():
    r = run(project_changes(**{GATE: False}))
    assert item(r, "capacity_value_benefit")["applies"] is False
    assert item(r, "capacity_value_benefit")["available"] is True


def test_gate_on_price_zero_is_a_measured_zero():  # Review Focus 5
    r = run(project_changes(**{GATE: True, PRICE: 0.0}))
    cap = item(r, "capacity_value_benefit")
    assert cap["applies"] is True
    assert cap["available"] is True
    assert cap["value_pv"] == 0.0


def test_every_item_carries_applies():
    r = run()
    assert all(isinstance(e["applies"], bool) for e in r["taxonomy_results"])


def test_not_applying_and_not_available_raises():
    module = {
        "availability": {
            "congestion_benefit": {
                "available": False,
                "missing_inputs": ("x",),
                "applies": False,
            }
        }
    }
    with pytest.raises(ValueError):
        _copy_availability(module, [TaxonomyResult("congestion_benefit", None, None)])


_ROUTELESS = {
    MARGIN: "margin",
    GATE: False,
    **measured(
        congestion_spread_per_mwh=None,
        hours_receiving_more_congested=None,
        hours_sending_more_congested=None,
        receiving_energy_value_per_mwh=None,
    ),
}


def test_routeless_margin_line_ratios_not_available():  # spec acceptance 1
    r = run(project_changes(**_ROUTELESS))
    b = r["bcr"]
    for key in (
        "bcr_societal",
        "bcr_ratepayer",
        "net_benefit_pv",
        "net_benefit_ratepayer_pv",
        "total_benefits_pv",
    ):
        assert b[key] is None, key
    assert r["summary"]["total_benefits_pv"] is None
    assert r["delay_comparison"]["delta_nb_delay"] is None
    assert b["bcr_utility"] == pytest.approx(0.9902051338550503)
    assert b["omitted"]["total_benefits_pv"] == [
        "avoided_emissions_benefit",
        "congestion_benefit",
    ]
    assert b["benefits_enabling_pv"] == 0.0  # nothing in the set applies


def test_sunzia_ratios_unchanged():  # spec acceptance 2
    b = run()["bcr"]
    assert b["bcr_societal"] == pytest.approx(0.15623096978640783)
    assert b["bcr_ratepayer"] == pytest.approx(0.5281776435390445)
    assert b["bcr_utility"] == pytest.approx(0.9902051338550503)


def test_no_omitted_list_names_an_item_that_does_not_apply():  # spec acceptance 6
    for changes in (
        project_changes(),
        project_changes(**_ROUTELESS),
        project_changes(**_DEDICATED, **measured()),
    ):
        r = run(changes)
        off = {e["taxonomy_id"] for e in r["taxonomy_results"] if not e["applies"]}
        for ids in r["bcr"]["omitted"].values():
            assert not off & set(ids)


def test_dedicated_without_energy_value_omits_delivered_not_congestion():  # Review Focus 4
    nulls = {k: v for k, v in _ROUTELESS.items() if k not in (MARGIN, GATE)}
    r = run(project_changes(**_DEDICATED, **nulls))
    omitted = r["bcr"]["omitted"]["total_benefits_pv"]
    assert "delivered_energy_benefit" in omitted
    assert "congestion_benefit" not in omitted
