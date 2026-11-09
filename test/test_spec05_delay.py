"""Cost of delay is an on-time comparison and stays outside the ratios."""
import pytest

from forge.scripts.io.taxonomy import TAXONOMY

from test.spec05_project import item, project_changes, run

COST_IDS = {tid for tid, entry in TAXONOMY.items() if entry.side == "cost"}
T = "01_project_technical_details.timeline."


def test_summary_delay_is_direct_delay_only():
    r = run(project_changes(**{T+"delay_years": 4, "05_delays.annual_base_delay_cost": 1000.0}))
    assert r["summary"]["total_delay_pv"] == pytest.approx(item(r, "base_delay")["value_pv"])


def test_forgone_benefits_are_differences_between_runs():
    r = run(project_changes(**{T+"delay_years": 4}))
    ot = run(project_changes(**{T+"delay_years": 0}))
    d = r["delay_comparison"]
    cong = item(ot, "congestion_benefit")["value_pv"] - item(r, "congestion_benefit")["value_pv"]
    avoid = item(ot, "avoided_emissions_benefit")["value_pv"] - item(r, "avoided_emissions_benefit")["value_pv"]
    assert d["delay_cost_cong"] == pytest.approx(cong)
    assert d["delay_cost_avoid"] == pytest.approx(avoid)
    assert d["delay_cost_forgone"] == pytest.approx(cong + avoid)
    assert d["delta_nb_delay"] == pytest.approx(ot["bcr"]["net_benefit_pv"] - r["bcr"]["net_benefit_pv"])
    assert d["on_time_run"] is True and d["baseline_delay_years"] == 0


def test_delay_is_outside_every_total_and_ratio():
    r = run(project_changes(**{T+"delay_years": 4, "05_delays.annual_base_delay_cost": 1000.0}))
    b = r["bcr"]
    assert b["delay_costs_pv"] == pytest.approx(item(r, "base_delay")["value_pv"])
    assert b["bcr_societal"] == pytest.approx(b["total_benefits_pv"] / b["total_costs_pv"])
    costs = sum(i["value_pv"] for i in r["taxonomy_results"] if i["taxonomy_id"] in COST_IDS)
    assert b["total_costs_pv"] == pytest.approx(costs)


def test_no_delay_runs_once(monkeypatch):
    import forge.core as core
    calls = []
    real = core._run_once
    monkeypatch.setattr(core, "_run_once", lambda *a, **k: calls.append(1) or real(*a, **k))
    d = run(project_changes(**{T+"delay_years": 0}))["delay_comparison"]
    assert len(calls) == 1 and d["on_time_run"] is False
    assert d["delay_cost_cong"] == 0.0 and d["delta_nb_delay"] == 0.0


def test_no_emissions_gives_none_not_zero():
    d = run(project_changes(**{T+"delay_years": 4}), no_emissions=True)["delay_comparison"]
    assert d["delay_cost_avoid"] is None and d["delay_cost_forgone"] is None
    assert d["delay_cost_cong"] is not None


def test_capital_only_has_no_block():
    assert run(project_changes(), capital_only=True)["delay_comparison"] is None


def test_comparison_is_deterministic_and_provenance_is_as_entered():
    a = run(project_changes(**{T+"delay_years": 4}))
    b = run(project_changes(**{T+"delay_years": 4}))
    assert a["delay_comparison"] == b["delay_comparison"]
    assert a["provenance"]["inputs_id"] == b["provenance"]["inputs_id"]
