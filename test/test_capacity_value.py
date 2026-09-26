"""Tests for capacity value benefit computation and delivered-energy parameter checks."""
import inspect

import pytest

from forge.scripts.calc.congestion_reduction import (
    calculate_capacity_value_benefit,
    calculate_congestion_reduction_costs,
    require_value_of_load_per_mwh,
)

def test_capacity_value_basic():
    """Gate on, known inputs → expected annual and PV."""
    result = calculate_capacity_value_benefit(
        delta_c_effective=1792.0,
        capacity_credit=0.80,
        capacity_price=65000.0,
        applicability_gate=True,
        project_lifetime=50,
        delay_years=2,
        construction_years=2,
        wacc_real=0.0443,
        benefit_price_escalation_real=0.01,
    )
    # Annual: 1792 * 0.80 * 65000 = 93,184,000
    assert abs(result["capacity_value_annual"] - 93_184_000.0) < 1.0
    assert result["capacity_value_pv"] > 0

def test_capacity_value_gate_off():
    """Gate off → zero benefit regardless of other inputs."""
    result = calculate_capacity_value_benefit(
        delta_c_effective=1792.0,
        capacity_credit=0.80,
        capacity_price=65000.0,
        applicability_gate=False,
        project_lifetime=50,
        delay_years=2,
        construction_years=2,
        wacc_real=0.0443,
        benefit_price_escalation_real=0.01,
    )
    assert result["capacity_value_annual"] == 0.0
    assert result["capacity_value_pv"] == 0.0

def test_capacity_value_zero_credit():
    """Zero capacity credit → zero benefit."""
    result = calculate_capacity_value_benefit(
        delta_c_effective=1792.0,
        capacity_credit=0.0,
        capacity_price=65000.0,
        applicability_gate=True,
        project_lifetime=50,
        delay_years=2,
        construction_years=2,
        wacc_real=0.0443,
        benefit_price_escalation_real=0.01,
    )
    assert result["capacity_value_annual"] == 0.0
    assert result["capacity_value_pv"] == 0.0


def test_capacity_value_zero_price():
    """Zero capacity price → zero benefit (indicator_cap gates the product)."""
    result = calculate_capacity_value_benefit(
        delta_c_effective=1792.0,
        capacity_credit=0.80,
        capacity_price=0.0,
        applicability_gate=True,
        project_lifetime=50,
        delay_years=2,
        construction_years=2,
        wacc_real=0.0443,
        benefit_price_escalation_real=0.01,
    )
    assert result["capacity_value_annual"] == 0.0
    assert result["capacity_value_pv"] == 0.0


def test_missing_value_of_load_per_mwh_raises_keyerror():
    """Missing value_of_load_per_mwh must fail loudly, not default to 0."""
    with pytest.raises(KeyError, match="value_of_load_per_mwh"):
        require_value_of_load_per_mwh({"line_utilization": 0.5})


def test_value_of_load_per_mwh_present():
    """Present value_of_load_per_mwh is returned as float."""
    assert require_value_of_load_per_mwh({"value_of_load_per_mwh": 30.0}) == 30.0


def test_cong_delay_annual_is_explicit():
    """Appendix §10 identity: delay cost annual is assigned from congestion benefit annual."""
    src = inspect.getsource(calculate_congestion_reduction_costs)
    assert "cong_delay_annual = annual_congestion_benefit" in src
    assert "cong_delay_annual" in src.split("congestion_delay_cost_nominal")[1]
