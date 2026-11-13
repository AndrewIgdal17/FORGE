import pytest
import forge
from forge.errors import InvalidInputs, UnknownInputPath

SPREAD = "01_project_technical_details.market_measurements.congestion_spread_per_mwh"
HFWD = "01_project_technical_details.market_measurements.hours_receiving_more_congested"
HREV = "01_project_technical_details.market_measurements.hours_sending_more_congested"
VREC = "01_project_technical_details.market_measurements.receiving_energy_value_per_mwh"

def _changes(**measures):
    block = {
        "congestion_spread_per_mwh": None,
        "hours_receiving_more_congested": None,
        "hours_sending_more_congested": None,
        "receiving_energy_value_per_mwh": None,
    }
    block.update(measures)
    return {
        "01_project_technical_details.market_measurements.congestion_spread_per_mwh": block["congestion_spread_per_mwh"],
        "01_project_technical_details.market_measurements.hours_receiving_more_congested": block["hours_receiving_more_congested"],
        "01_project_technical_details.market_measurements.hours_sending_more_congested": block["hours_sending_more_congested"],
        "01_project_technical_details.market_measurements.receiving_energy_value_per_mwh": block["receiving_energy_value_per_mwh"],
    }

CASES = [
    {"hours_receiving_more_congested": 8761, "hours_sending_more_congested": 0, "congestion_spread_per_mwh": 1, "receiving_energy_value_per_mwh": 30},
    {"congestion_spread_per_mwh": 1.5, "receiving_energy_value_per_mwh": 30},
    {"congestion_spread_per_mwh": 1.5, "hours_receiving_more_congested": 0, "hours_sending_more_congested": 0, "receiving_energy_value_per_mwh": 30},
    {"congestion_spread_per_mwh": 0, "hours_receiving_more_congested": 10, "hours_sending_more_congested": 0, "receiving_energy_value_per_mwh": 30},
    {"congestion_spread_per_mwh": -1, "hours_receiving_more_congested": 0, "hours_sending_more_congested": 0, "receiving_energy_value_per_mwh": 30},
    {"congestion_spread_per_mwh": 1, "hours_receiving_more_congested": 9000, "hours_sending_more_congested": 0, "receiving_energy_value_per_mwh": 30},
    {"congestion_spread_per_mwh": 1, "hours_receiving_more_congested": 10.5, "hours_sending_more_congested": 0, "receiving_energy_value_per_mwh": 30},
    {"congestion_spread_per_mwh": 1, "hours_receiving_more_congested": 10, "hours_sending_more_congested": 0},
]

def test_acceptance_9_measurement_rules_are_invalid_inputs():
    for measures in CASES:
        with pytest.raises(InvalidInputs) as resolved:
            forge.resolve_inputs(_changes(**measures))
        assert not isinstance(resolved.value, UnknownInputPath)
        document = forge.get_defaults_template()
        acres = document["02_project_physical_details"]["terrain"]["protected_area_acres"]
        for key in acres:
            acres[key] = 0.0
        document["01_project_technical_details"]["market_measurements"].update(measures)
        with pytest.raises(InvalidInputs) as calculated:
            forge.run_calculation(document)
        assert "market_measurements" in str(calculated.value)
    missing = forge.missing_required_inputs({})
    assert not any("market_measurements" in item["path"] for item in missing)


def test_acceptance_14_results_schema_is_2():
    info = forge.calculator_info()
    assert info["results_schema"] == 2


def test_not_available_item_keeps_null_dollars():
    from forge.scripts.io.taxonomy_adapters import adapt_all_results
    congestion = {
        "availability": {
            "congestion_benefit": {
                "available": False,
                "missing_inputs": (
                    "01_project_technical_details.market_measurements.congestion_spread_per_mwh",
                ),
            }
        },
        "congestion_benefit_pv": None,
        "congestion_benefit_nominal": None,
        "congestion_benefit_annual": None,
        "congestion_benefit_pv_wacc": None,
        "delivered_benefit_pv": 0.0,
        "delivered_benefit_nominal": 0.0,
        "delivered_benefit_annual": 0.0,
        "delivered_benefit_pv_wacc": 0.0,
        "streams": {
            "congestion_benefit": None,
            "delivered_energy_benefit": [0.0],
        },
    }
    items = adapt_all_results({"benefits": {"congestion": congestion}, "costs": {}})
    benefit = next(item for item in items if item.taxonomy_id == "congestion_benefit")
    assert benefit.available is False
    assert benefit.value_pv is None
    assert benefit.value_nominal is None
