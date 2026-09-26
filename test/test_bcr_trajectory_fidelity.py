"""Per-ratio BCR fidelity check: trajectory final-year vs bcr_calculator."""
import pytest

from forge.scripts.calc.bcr_trajectory import _assert_per_ratio_fidelity, compute_trajectory


def test_ratio_fidelity_passes_when_core_ratios_match():
    final = {
        "bcr_societal": 1.25,
        "bcr_utility": 1.0,
        "bcr_ratepayer": 0.8,
    }
    bcr = {
        "bcr_societal": 1.25,
        "bcr_utility": 1.0,
        "bcr_ratepayer": 0.8,
    }
    _assert_per_ratio_fidelity(final, bcr)


def test_ratio_fidelity_fails_on_core_mismatch():
    final = {"bcr_societal": 1.0}
    bcr = {"bcr_societal": 2.0}
    with pytest.raises(AssertionError, match="bcr_societal"):
        _assert_per_ratio_fidelity(final, bcr)


def test_ratio_fidelity_skips_near_zero_calculator_value():
    final = {"bcr_societal": 999.0}
    bcr = {"bcr_societal": 0.0}
    _assert_per_ratio_fidelity(final, bcr)


def test_ratio_fidelity_uses_calculator_exclusion_keys():
    """Naive same-key lookup would skip this; the check must use bcr_excluding_*."""
    final = {"bcr_excl_wildfire": 1.0}
    bcr = {
        "bcr_excl_wildfire": 1.0,
        "bcr_excluding_wildfire_risk": 2.0,
    }
    with pytest.raises(AssertionError, match="bcr_excl_wildfire"):
        _assert_per_ratio_fidelity(final, bcr)


def test_ratio_fidelity_maps_all_exclusion_variants():
    final = {
        "bcr_excl_avoided_emissions": 1.10,
        "bcr_excl_emissions_costs": 1.20,
        "bcr_excl_all_emissions": 1.30,
        "bcr_excl_outage": 1.40,
        "bcr_excl_wildfire": 1.50,
        "bcr_excl_wf_out": 1.60,
    }
    bcr = {
        "bcr_excluding_avoided_emissions": 1.10,
        "bcr_excluding_emissions": 1.20,
        "bcr_excluding_avoided_emissions_and_emissions": 1.30,
        "bcr_excluding_outage_risk": 1.40,
        "bcr_excluding_wildfire_risk": 1.50,
        "bcr_excluding_wildfire_risk_and_outage_risk": 1.60,
    }
    _assert_per_ratio_fidelity(final, bcr)


def test_ratio_fidelity_reads_traj_bcr_excl_wf_out_alias():
    """Trajectory stores outage+wildfire as bcr_excl_wf_out, not taxonomy id."""
    final = {
        "bcr_excl_wf_out": 1.5,
        "bcr_excl_outage_wildfire": 99.0,
    }
    bcr = {"bcr_excluding_wildfire_risk_and_outage_risk": 1.5}
    _assert_per_ratio_fidelity(final, bcr)


def test_ratio_fidelity_treats_none_traj_as_zero():
    final = {"bcr_societal": None}
    bcr = {"bcr_societal": 1.5}
    with pytest.raises(AssertionError, match="bcr_societal"):
        _assert_per_ratio_fidelity(final, bcr)


def _zero_wacc_inputs():
    return {
        "01_project_technical_details": {
            "timeline": {
                "delay_years": 1,
                "construction_years": 1,
                "project_lifetime": 1,
            },
            "project": {
                "project_type": "greenfield",
                "row_agreement_type": "permanent_easement_new",
            },
        },
        "03_financing": {
            "financial": {
                "wacc_nominal": 0.0,
                "inflation_rate": 0.0,
                "social_discount_rate": 0.0,
            },
        },
        "04_insurance": {"insurance": {"escalation_rate": 0.0}},
        "11_project_row_details": {"row_rent_escalation_real": 0.0},
        "14_category_om_structures": {"om_real_escalation_rate": 0.0},
        "17_congestion_reductions": {"benefit_price_escalation_real": 0.0},
        "06_wildfire_costs": {"wildfire": {"risk_growth_rate": 0.0}},
        "07_outage_costs": {"outage": {"risk_growth_rate": 0.0}},
    }


def test_bcr_utility_uses_atrr_excluding_line_losses_and_congestion_delay():
    """Utility BCR is ATRR / (ATRR + base_delay) per taxonomy revenue_requirement / atrr_delay.

    ATRR = capital recovery + O&M + insurance + ROW rent. Line losses and
    congestion-delay opportunity cost are not in that basket.
    """
    delay_pv = 20.0
    congestion_delay_pv = 30.0
    rate_base = 100.0
    annual_om = 10.0
    annual_insurance = 5.0
    annual_loss = 50.0
    atrr = rate_base + annual_om + annual_insurance
    expected = atrr / (atrr + delay_pv)
    total_costs = delay_pv + congestion_delay_pv + annual_om + annual_insurance + annual_loss

    results = {
        "bcr": {
            "build_cost_pv": 0.0,
            "row_capital_pv": 0.0,
            "env_mitigation_pv": 0.0,
            "delay_cost_pv": delay_pv,
            "congestion_delay_cost_pv": congestion_delay_pv,
            "emissions_displacement_delay_pv": 0.0,
            "total_costs_pv": total_costs,
            "total_benefits_pv": 0.0,
            "bcr_utility": expected,
        },
        "benefits": {
            "congestion": {},
            "capital_recovery": {"rate_base_real": rate_base},
        },
        "costs": {
            "oandm": {"total_annual": annual_om},
            "insurance": {"annual_premium": annual_insurance},
            "line_loss": {"annual_cost": annual_loss},
            "row": {"row_rent_nominal": 0.0},
            "wildfire": {"EAL": 0.0},
            "outage": {"expected_annual_loss": 0.0},
        },
    }

    traj = compute_trajectory(results, _zero_wacc_inputs())
    assert traj[-1]["bcr_utility"] == pytest.approx(expected, rel=1e-9)
