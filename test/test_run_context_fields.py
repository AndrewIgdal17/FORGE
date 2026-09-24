"""Tests for expanded RunContext fields (homeless parameters)."""
import pytest
from scripts.utils.run_context import RunContext


def test_run_context_has_number_of_converters():
    ctx = RunContext(
        project_details=None, terrain_miles={}, terrain_multipliers={},
        total_miles=100.0, financing=None, contingencies={},
        category_string="test", row_width_feet=150.0,
        weighted_miles=100.0, average_terrain_multiplier=1.0,
        number_of_converters=2,
        social_discount_rate=0.03,
        afudc_rate=0.05, afudc_source="calculated",
        cod_year=2030.0, construction_start_year=2027.0,
    )
    assert ctx.number_of_converters == 2
    assert ctx.social_discount_rate == 0.03
    assert ctx.afudc_rate == 0.05
    assert ctx.afudc_source == "calculated"
    assert ctx.cod_year == 2030.0
    assert ctx.construction_start_year == 2027.0


def test_run_context_defaults_for_optional_fields():
    ctx = RunContext(
        project_details=None, terrain_miles={}, terrain_multipliers={},
        total_miles=100.0, financing=None, contingencies={},
        category_string="test", row_width_feet=150.0,
        weighted_miles=100.0, average_terrain_multiplier=1.0,
    )
    assert ctx.number_of_converters == 0
    assert ctx.social_discount_rate == 0.0
    assert ctx.afudc_rate == 0.0
    assert ctx.afudc_source == ""
    assert ctx.cod_year == 0.0
    assert ctx.construction_start_year == 0.0
