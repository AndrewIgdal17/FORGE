"""Tests for appendix incremental comparison sign conventions (Phase 2.72b T15).

Appendix §Reporting L2025-2027:
  ΔC = C^B - C^P  (avoided-cost: positive = P has lower cost)
  ΔB = B^P - B^B  (positive = P has higher benefit)
  ΔNB = ΔB + ΔC = NB^P - NB^B
"""
from scripts.calc.bcr_calculator import compute_incremental_comparison


def test_self_comparison_is_all_zeros():
    """Comparing a scenario to itself yields zero deltas."""
    bcr = {"total_costs_pv": 100.0, "total_benefits_pv": 140.0}
    delta = compute_incremental_comparison(bcr, bcr)
    assert delta["delta_cost_pv"] == 0.0
    assert delta["delta_benefit_pv"] == 0.0
    assert delta["delta_net_benefit_pv"] == 0.0


def test_cheaper_project_has_positive_delta_cost():
    """ΔC = C^B - C^P: project cheaper than baseline → positive avoided cost."""
    bcr_p = {"total_costs_pv": 80.0, "total_benefits_pv": 100.0}
    bcr_b = {"total_costs_pv": 100.0, "total_benefits_pv": 100.0}
    delta = compute_incremental_comparison(bcr_p, bcr_b)
    assert delta["delta_cost_pv"] == 20.0
    assert delta["delta_benefit_pv"] == 0.0
    assert delta["delta_net_benefit_pv"] == 20.0


def test_higher_benefit_project_has_positive_delta_benefit():
    """ΔB = B^P - B^B: project with more benefit → positive delta_benefit."""
    bcr_p = {"total_costs_pv": 100.0, "total_benefits_pv": 150.0}
    bcr_b = {"total_costs_pv": 100.0, "total_benefits_pv": 100.0}
    delta = compute_incremental_comparison(bcr_p, bcr_b)
    assert delta["delta_cost_pv"] == 0.0
    assert delta["delta_benefit_pv"] == 50.0
    assert delta["delta_net_benefit_pv"] == 50.0


def test_delta_net_benefit_equals_nb_p_minus_nb_b():
    """ΔNB = ΔB + ΔC = NB^P - NB^B."""
    bcr_p = {"total_costs_pv": 70.0, "total_benefits_pv": 200.0}  # NB^P = 130
    bcr_b = {"total_costs_pv": 100.0, "total_benefits_pv": 120.0}  # NB^B = 20
    delta = compute_incremental_comparison(bcr_p, bcr_b)
    assert delta["delta_cost_pv"] == 30.0
    assert delta["delta_benefit_pv"] == 80.0
    assert delta["delta_net_benefit_pv"] == 110.0
    nb_p = bcr_p["total_benefits_pv"] - bcr_p["total_costs_pv"]
    nb_b = bcr_b["total_benefits_pv"] - bcr_b["total_costs_pv"]
    assert delta["delta_net_benefit_pv"] == nb_p - nb_b
