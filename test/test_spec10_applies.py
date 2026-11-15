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
