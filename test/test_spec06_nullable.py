"""Range and type checks for numeric fields whose default is null."""
import pytest

import forge

FF = "17_congestion_reductions.greenfield_congestion_reductions.constraints.flow_factor"
VL = "01_project_technical_details.project.value_of_load_per_mwh"
SP = "17_congestion_reductions.greenfield_congestion_reductions.prices.average_congestion_price"


@pytest.mark.xfail(strict=True, reason="Task 3 adds nullable_number to these fields")
def test_nullable_numbers_are_range_and_type_checked():
    assert forge.validate_changes({FF: 1.5})
    assert forge.validate_changes({VL: -1.0})
    assert forge.validate_changes({SP: "x"})
    assert forge.validate_changes({SP: -3.0}) == []          # negative spread is allowed
    assert forge.validate_changes({FF: None}) == []          # null resets to default
