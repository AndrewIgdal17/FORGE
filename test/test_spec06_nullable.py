"""Range and type checks for numeric fields whose default is null."""
import forge

FF = "17_congestion_reductions.greenfield_congestion_reductions.constraints.flow_factor"
SPREAD = "01_project_technical_details.market_measurements.congestion_spread_per_mwh"
HOURS = "01_project_technical_details.market_measurements.hours_receiving_more_congested"
ENERGY = "01_project_technical_details.market_measurements.receiving_energy_value_per_mwh"


def test_nullable_numbers_are_range_and_type_checked():
    assert forge.validate_changes({FF: 1.5})
    assert forge.validate_changes({SPREAD: "x"})
    assert forge.validate_changes({SPREAD: -3.0})
    assert forge.validate_changes({HOURS: 10.5})
    assert forge.validate_changes({ENERGY: None}) == []
    assert forge.validate_changes({SPREAD: None}) == []
    assert forge.validate_changes({FF: None}) == []
