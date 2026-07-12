"""Tests for capacity value benefit computation."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from congestion_curtailment_reduction import calculate_capacity_value_benefit


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
