import pytest

from forge.contract import validate_changes
from forge.errors import InvalidInputs
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
