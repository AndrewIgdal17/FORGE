import pytest

from forge.contract import validate_changes
from forge.errors import InvalidInputs
from forge.scripts.calc.outage_costs import calculate_outage_costs
from forge.scripts.calc.wildfire_costs import calculate_wildfire_costs
from forge.scripts.utils.financial_utils import calculate_afudc_capitalized_cost


def test_validate_changes_rejects_zero_construction_years():
    errors = validate_changes({
        "01_project_technical_details.timeline.construction_years": 0,
    })
    assert errors == [{
        "path": "01_project_technical_details.timeline.construction_years",
        "message": "0 is below the minimum of 1",
    }]


def test_afudc_rejects_zero_construction_years():
    with pytest.raises(ValueError, match="construction_years must be >= 1"):
        calculate_afudc_capitalized_cost(
            100.0,
            {"during_delay": 0.0, "during_construction": 1.0, "afudc_eligible": True},
            0.0,
            0,
            0.05,
            False,
            spending_profiles={"5": [0.2, 0.2, 0.2, 0.2, 0.2]},
        )


def test_subsea_construction_type_is_not_an_option():
    errors = validate_changes({
        "01_project_technical_details.project.construction_type": "Subsea",
    })
    assert errors[0]["path"] == "01_project_technical_details.project.construction_type"
    assert errors[0]["message"] == (
        "'Subsea' is not one of the allowed options "
        "['Overhead', 'Underground Direct-Buried', 'Underground Tunnel']"
    )


def _outage_yaml() -> dict:
    return {
        "outage": {
            "risk_growth_rate": 0.0,
            "redispatch_cost_per_mwh": 0.0,
            "value_of_lost_load": {
                "tiers": [{"max_hours": ".inf", "value_per_mwh": 1.0}],
            },
            "outage_duration": 1.0,
            "outage_duration_multiplier": {"overhead": 1.0},
            "outage_rate": {"overhead": 0.0},
        }
    }


def _wildfire_yaml() -> dict:
    return {
        "wildfire": {
            "severity_per_event": 1.0,
            "risk_growth_rate": 0.0,
            "base_ignition_rate": 0.0,
            "ignition_rate_multiplier": {"overhead": 1.0},
        }
    }


def test_outage_costs_require_construction_years():
    yaml = _outage_yaml()
    terrain = {"forested": 1.0}
    with pytest.raises(TypeError, match="construction_years"):
        calculate_outage_costs(yaml, "overhead", terrain, 100, 10, 0.05)
    result = calculate_outage_costs(
        yaml, "overhead", terrain, 100, 10, 0.05, construction_years=1
    )
    assert result["pv_cost"] == pytest.approx(0.0)


def test_wildfire_costs_require_construction_years():
    yaml = _wildfire_yaml()
    terrain = {"forested": 1.0}
    with pytest.raises(TypeError, match="construction_years"):
        calculate_wildfire_costs(yaml, "overhead", terrain, 10, 0.05)
    result = calculate_wildfire_costs(
        yaml, "overhead", terrain, 10, 0.05, construction_years=1
    )
    assert result["pv_cost"] == pytest.approx(0.0)
