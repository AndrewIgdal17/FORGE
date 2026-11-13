"""Tests for capacity value benefit computation and the market energy value."""
import pytest

from forge.scripts.calc.congestion_reduction import calculate_capacity_value_benefit
from test.spec05_project import project_changes, run

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


_DEDICATED = {
    "01_project_technical_details.project.sending_source": "dedicated",
    "01_project_technical_details.project.dedicated_resource.contract_price_per_mwh": 55.0,
    "01_project_technical_details.project.dedicated_resource.emission_rate_kg_per_mwh.co2e": 0.0,
    "01_project_technical_details.project.dedicated_resource.emission_rate_kg_per_mwh.so2": 0.0,
    "01_project_technical_details.project.dedicated_resource.emission_rate_kg_per_mwh.nox": 0.0,
}
_ENERGY = "01_project_technical_details.market_measurements.receiving_energy_value_per_mwh"


def test_missing_receiving_energy_value_is_not_available():
    """A null receiving energy value does not raise. Dedicated delivery is not available."""
    results = run(project_changes(**_DEDICATED))
    benefit = results["benefits"]["congestion"]
    assert benefit["delivered_benefit_annual"] is None
    availability = benefit["availability"]["delivered_energy_benefit"]
    assert availability["available"] is False
    assert availability["missing_inputs"] == (_ENERGY,)
    assert benefit["congestion_benefit_annual"] == 0.0


def test_receiving_energy_value_prices_dedicated_delivery():
    """The market block's receiving energy value prices dedicated delivered energy."""
    results = run(project_changes(**{**_DEDICATED, _ENERGY: 30.0}))
    delivered_mwh = results["benefits"]["congestion"]["energy_delivered_annual_mwh_yr"]
    assert results["benefits"]["congestion"]["delivered_benefit_annual"] == pytest.approx(
        delivered_mwh * (30.0 - 55.0)
    )
