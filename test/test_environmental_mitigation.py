import pytest

from forge.errors import InvalidInputs
from forge.scripts.calc.environmental_mitigation import (
    calculate_environmental_mitigation_costs,
    disturbance_multiplier,
)


def _yaml(uplift: float) -> dict:
    return {
        "environmental_mitigation": {
            "mitigation_uplift_factor": uplift,
            "wetland_compensation_ratio": 1.0,
            "habitat_compensation_ratio": 2.0,
            "disturbance_multiplier_rebuild": 0.5,
            "wetland_credit_cost_per_acre": 100.0,
            "habitat_credit_cost_per_credit": {
                "forested": 10.0,
                "scrubbed_flat": 10.0,
                "desert_barren": 10.0,
                "rolling_hills": 10.0,
                "mountain": 10.0,
            },
            "base_mitigation_cost_per_acre": {
                "overhead": {"forested": 4.0, "wetland": 8.0},
            },
        }
    }


def _price(uplift: float, project_type: str = "greenfield", gap_forested: float = 1.0):
    return calculate_environmental_mitigation_costs(
        _yaml(uplift),
        "Overhead/AC/500MW/Standard Aluminum Conductor/NA",
        {"forested": 10.0, "wetland": 1.0},
        {
            "forested": gap_forested,
            "scrubbed_flat": 0.0,
            "desert_barren": 0.0,
            "rolling_hills": 0.0,
            "mountain": 0.0,
        },
        project_type=project_type,
    )


def test_disturbance_multiplier_cases():
    assert disturbance_multiplier("reconductoring", 0.5) == 0.0
    assert disturbance_multiplier("rebuild", 0.5) == 0.5
    assert disturbance_multiplier("greenfield", 0.5) == 1.0
    with pytest.raises(InvalidInputs, match="project_type 'nope' is not allowed"):
        disturbance_multiplier("nope", 0.5)


def test_default_uplift_prices_wetland_acres_and_forested_credits():
    result = _price(1.25)
    assert result["wetlands_credits"] == pytest.approx(125.0)
    assert result["habitat_credit_count"] == pytest.approx(2.5)
    assert result["habitat_credits"] == pytest.approx(25.0)
    assert result["base_cost"] == pytest.approx(60.0)


def test_uplift_of_one_checks_the_raw_ratios():
    result = _price(1.0)
    assert result["wetlands_credits"] == pytest.approx(100.0)
    assert result["habitat_credit_count"] == pytest.approx(2.0)
    assert result["habitat_credits"] == pytest.approx(20.0)


def test_zero_protected_area_acres_cost_no_habitat_credits():
    result = _price(1.25, gap_forested=0.0)
    assert result["habitat_credit_count"] == 0.0
    assert result["habitat_credits"] == 0.0
    assert result["base_cost"] == pytest.approx(60.0)


def test_reconductoring_zeros_onsite_and_credits_and_rebuild_halves_them():
    zero = _price(1.25, project_type="reconductoring")
    assert zero["base_cost"] == 0.0
    assert zero["wetlands_credits"] == 0.0
    assert zero["habitat_credits"] == 0.0
    half = _price(1.25, project_type="rebuild")
    assert half["base_cost"] == pytest.approx(30.0)
    assert half["wetlands_credits"] == pytest.approx(62.5)
    assert half["habitat_credit_count"] == pytest.approx(1.25)
    assert half["habitat_credits"] == pytest.approx(12.5)
