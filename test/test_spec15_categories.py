"""Spec 15 — taxonomy categories, subtotals, and renamed reporting keys."""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import get_args

import pytest

from forge.scripts.io.taxonomy import (
    BCR_DEFINITIONS,
    BCR_EXCLUSION_VARIANTS,
    EXCLUDABLE_GROUPS,
    TAXONOMY_ITEMS,
    Category,
    DenominatorRule,
    NumeratorRule,
    get_items_by_category,
)
from test.spec05_project import item, measured, project_changes, run
from test.spec11_scenarios import scenario_changes
from test.test_spec11_cost_applies import DELAY
from test.test_golden import _approx_equal
from test.test_spec10_applies import _ROUTELESS

_DATA = Path(__file__).resolve().parent / "data" / "spec15_before.json"
_BEFORE = json.loads(_DATA.read_text())

_CATEGORY_LITERALS = (
    "capital",
    "delay_period",
    "operating",
    "external",
    "market",
    "transfer",
    "reporting",
    "project",
    "route",
    "financial",
)

_EXPECTED_COST_BENEFIT = {
    "build_conductor": ("capital", None),
    "build_structure": ("capital", None),
    "build_converter": ("capital", None),
    "row_acquisition": ("capital", None),
    "env_mitigation": ("capital", None),
    "base_delay": ("delay_period", None),
    "row_holding": ("delay_period", None),
    "oandm": ("operating", None),
    "insurance": ("operating", None),
    "row_rent": ("operating", None),
    "line_loss_conductor": ("operating", None),
    "line_loss_converter": ("operating", None),
    "wildfire_eac": ("external", "risk"),
    "outage_eac": ("external", "risk"),
    "emissions_comp": ("external", "emissions"),
    "congestion_benefit": ("market", None),
    "delivered_energy_benefit": ("market", None),
    "capacity_value_benefit": ("market", None),
    "avoided_emissions_benefit": ("external", None),
}

_BEFORE_EXCLUDABLE = {
    name: frozenset(group.taxonomy_ids)
    for name, group in EXCLUDABLE_GROUPS.items()
}

_BCR_SUMMARY_PAIRS = [
    ("capital_costs_pv", "reporting_category_capital_pv"),
    ("delay_period_costs_pv", "reporting_category_delay_period_pv"),
    ("operating_costs_pv", "reporting_category_operating_pv"),
    ("external_costs_pv", "reporting_category_external_pv"),
    ("external_risk_costs_pv", "reporting_category_external_risk_pv"),
    ("external_emissions_costs_pv", "reporting_category_external_emissions_pv"),
    ("benefits_market_pv", "benefits_market_pv"),
    ("benefits_external_pv", "benefits_external_pv"),
]

_COST_CATEGORIES = [
    "capital_costs_pv",
    "delay_period_costs_pv",
    "operating_costs_pv",
    "external_costs_pv",
    "external_risk_costs_pv",
    "external_emissions_costs_pv",
]

_NEW_BCR_KEYS = {
    "capital_costs_pv",
    "capital_costs_nominal",
    "delay_period_costs_pv",
    "delay_period_costs_nominal",
    "operating_costs_pv",
    "operating_costs_nominal",
    "external_costs_pv",
    "external_risk_costs_pv",
    "external_risk_costs_nominal",
    "external_emissions_costs_pv",
    "benefits_market_pv",
    "benefits_external_pv",
    "holding_pv",
}

_REMOVED_KEYS = {
    "hard_costs_pv",
    "soft_costs_pv",
    "risk_costs_pv",
    "risk_costs_nominal",
    "emissions_costs_pv",
    "benefits_remedial_pv",
    "benefits_enabling_pv",
    "benefits_avoided_emissions_pv",
}

_REMOVED_SUMMARY = {
    "reporting_category_hard_pv",
    "reporting_category_soft_pv",
    "reporting_category_risk_pv",
    "reporting_category_emissions_pv",
    "benefits_remedial_pv",
    "benefits_enabling_pv",
}

_FIVE_COST_TOTALS = (
    "total_capital_pv",
    "total_operational_pv",
    "total_energy_emissions_pv",
    "total_risk_pv",
    "total_delay_pv",
)

_TRAJECTORY_PAIRS = [
    ("cum_C_capital", "capital_costs_pv"),
    ("cum_C_delay_period", "delay_period_costs_pv"),
    ("cum_C_operating", "operating_costs_pv"),
    ("cum_C_external", "external_costs_pv"),
    ("cum_C_external_risk", "external_risk_costs_pv"),
    ("cum_C_external_emissions", "external_emissions_costs_pv"),
    ("cum_B_market", "benefits_market_pv"),
    ("cum_B_external", "benefits_external_pv"),
]


def _item_pv_sum(results: dict, taxonomy_ids: frozenset[str] | set[str]) -> float | None:
    """Sum value_pv for applying, available items; same null rule as bcr_calculator."""
    rows = [
        e for e in results["taxonomy_results"]
        if e["taxonomy_id"] in taxonomy_ids and e.get("applies")
    ]
    if not rows:
        return 0.0
    available = [e for e in rows if e.get("available")]
    if not available:
        return None
    return sum(e["value_pv"] for e in available)


def _ids_for_category(category: str, *, side: str, subgroup: str | None = None) -> frozenset[str]:
    ids = {
        item.id
        for item in TAXONOMY_ITEMS
        if item.side == side
        and item.category == category
        and (subgroup is None or item.subgroup == subgroup)
    }
    return frozenset(ids)


_CATEGORY_ID_SETS = {
    "capital_costs_pv": _ids_for_category("capital", side="cost"),
    "delay_period_costs_pv": _ids_for_category("delay_period", side="cost"),
    "operating_costs_pv": _ids_for_category("operating", side="cost"),
    "external_costs_pv": _ids_for_category("external", side="cost"),
    "external_risk_costs_pv": _ids_for_category("external", side="cost", subgroup="risk"),
    "external_emissions_costs_pv": _ids_for_category(
        "external", side="cost", subgroup="emissions",
    ),
    "benefits_market_pv": _ids_for_category("market", side="benefit"),
    "benefits_external_pv": _ids_for_category("external", side="benefit"),
}


def test_every_result_item_has_one_category():
    got = {
        i.id: (i.category, i.subgroup)
        for i in TAXONOMY_ITEMS
        if i.side in ("cost", "benefit")
    }
    assert got == _EXPECTED_COST_BENEFIT
    assert get_args(Category) == _CATEGORY_LITERALS


def test_rules_after_rename():
    assert get_args(NumeratorRule) == (
        "all_benefits",
        "market",
        "capital_recovery",
        "revenue_requirement",
    )
    assert get_args(DenominatorRule) == (
        "all_costs",
        "atrr_delay",
        "revenue_requirement_loss",
    )
    assert BCR_DEFINITIONS["bcr_ratepayer"].numerator_rule == "market"
    for name, group in EXCLUDABLE_GROUPS.items():
        assert group.taxonomy_ids == _BEFORE_EXCLUDABLE[name]
    assert len(BCR_EXCLUSION_VARIANTS) == 6


def test_external_on_both_sides():
    benefit_ids = {i.id for i in get_items_by_category("external", side="benefit")}
    assert benefit_ids == {"avoided_emissions_benefit"}


def test_category_subtotals_equal_item_sums():
    r = run(project_changes(**{**measured(), DELAY: 3}))
    bcr = r["bcr"]
    summary = r["summary"]
    for bcr_key, id_set in _CATEGORY_ID_SETS.items():
        expected = _item_pv_sum(r, id_set)
        actual = bcr[bcr_key]
        if expected is None:
            assert actual is None, bcr_key
        else:
            assert actual == pytest.approx(expected, rel=1e-9), bcr_key
    for bcr_key, summary_key in _BCR_SUMMARY_PAIRS:
        assert summary[summary_key] == bcr[bcr_key], (bcr_key, summary_key)
    for key in _COST_CATEGORIES:
        assert key in bcr
        sk = dict(_BCR_SUMMARY_PAIRS)[key]
        assert sk in summary
    parts = [summary[k] for k in _FIVE_COST_TOTALS]
    assert sum(p for p in parts if p is not None) == pytest.approx(
        summary["total_costs_pv"], rel=1e-9,
    )


def test_old_keys_gone():
    r = run(project_changes(**{**measured(), DELAY: 3}))
    for key in _REMOVED_KEYS:
        assert key not in r["bcr"]
        assert key not in r["bcr"].get("omitted", {})
        assert key not in r["summary"]
        assert key not in r["csv_equivalent"]
    for key in _REMOVED_SUMMARY:
        assert key not in r["summary"]
    for key in _NEW_BCR_KEYS:
        assert key in r["csv_equivalent"]


def test_routeless_market_is_not_available():
    r = run(project_changes(**_ROUTELESS))
    assert r["bcr"]["benefits_market_pv"] is None
    assert "congestion_benefit" in r["bcr"]["omitted"]["benefits_market_pv"]


def test_partial_market_unavailable_sums_available_items():
    from forge.scripts.calc.bcr_calculator import compute_all_bcrs
    from forge.scripts.io.taxonomy_adapters import TaxonomyResult

    def _r(tid: str, pv: float) -> TaxonomyResult:
        return TaxonomyResult(tid, value_pv=pv, value_nominal=pv, value_pv_wacc=pv)

    rs = [
        TaxonomyResult(
            "congestion_benefit",
            value_pv=None,
            value_nominal=None,
            value_pv_wacc=None,
            available=False,
        ),
        _r("delivered_energy_benefit", 100.0),
        _r("capacity_value_benefit", 50.0),
    ]
    b = compute_all_bcrs(rs)
    assert b["benefits_market_pv"] is not None
    assert b["benefits_market_pv"] == pytest.approx(150.0)
    assert b["omitted"]["benefits_market_pv"] == ["congestion_benefit"]


def test_societal_and_ratepayer_unchanged():
    keys = (
        "bcr_societal",
        "net_benefit_pv",
        "bcr_ratepayer",
        "net_benefit_ratepayer_pv",
    )
    for name, before in _BEFORE.items():
        r = run(scenario_changes(name))
        for key in keys:
            assert _approx_equal(r["bcr"][key], before[key]), (name, key)


def test_trajectory_buckets_match_subtotals():
    from test.test_spec07_1_not_available import CUMULATIVE_TO_BCR

    for pair in _TRAJECTORY_PAIRS:
        assert pair in CUMULATIVE_TO_BCR.items()
    r = run(project_changes(**{**measured(), DELAY: 3}))
    final = r["trajectory"][-1]
    bcr = r["bcr"]
    for traj_key, bcr_key in _TRAJECTORY_PAIRS:
        if final[traj_key] is not None and bcr[bcr_key] is not None:
            assert final[traj_key] == pytest.approx(bcr[bcr_key], rel=1e-9)
        else:
            assert final[traj_key] == bcr[bcr_key], (traj_key, bcr_key)


def _assembly_rows_with_row(
    *,
    acq_pv: float,
    acq_wacc: float,
    hold_pv: float,
    hold_wacc: float,
) -> list:
    from forge.scripts.io.taxonomy_adapters import TaxonomyResult

    def _r(i, pv, wacc):
        return TaxonomyResult(i, value_pv=pv, value_nominal=0.0, value_pv_wacc=wacc)

    return [
        _r("congestion_benefit", 300.0, 200.0),
        _r("oandm", 50.0, 40.0),
        _r("insurance", 10.0, 8.0),
        _r("row_rent", 0.0, 0.0),
        _r("line_loss_conductor", 20.0, 15.0),
        _r("line_loss_converter", 0.0, 0.0),
        _r("base_delay", 5.0, 4.0),
        TaxonomyResult(
            "capital_recovery",
            value_pv=None,
            value_nominal=0.0,
            value_pv_wacc=100.0,
        ),
        _r("build_conductor", 90.0, 70.0),
        _r("row_acquisition", acq_pv, acq_wacc),
        _r("row_holding", hold_pv, hold_wacc),
    ]


def test_holding_has_its_own_key():
    from forge.scripts.calc.bcr_calculator import compute_all_bcrs

    b = compute_all_bcrs(_assembly_rows_with_row(
        acq_pv=30.0, acq_wacc=30.0, hold_pv=7.0, hold_wacc=6.0,
    ))
    assert b["holding_pv"] == 7.0
    assert b["acquisition_pv"] == 30.0 == b["row_cost_pv"]
    assert b["capital_costs_pv"] == pytest.approx(90.0 + 30.0, rel=1e-9)
    assert b["delay_period_costs_pv"] == pytest.approx(5.0 + 7.0, rel=1e-9)
    assert b["bcr_utility"] == pytest.approx((100.0 + 40.0 + 8.0) / (100.0 + 40.0 + 8.0 + 4.0 + 6.0))
    assert b["total_costs_pv"] == pytest.approx(50 + 10 + 20 + 5 + 90 + 30 + 7, rel=1e-9)
    assembly_only = compute_all_bcrs([
        row
        for row in _assembly_rows_with_row(
            acq_pv=0.0, acq_wacc=0.0, hold_pv=0.0, hold_wacc=0.0,
        )
        if row.taxonomy_id not in ("row_acquisition", "row_holding")
    ])
    assert b["bcr_ratepayer"] == pytest.approx(assembly_only["bcr_ratepayer"])


def _utility_atrr_and_delay(r: dict) -> tuple[float, float]:
    from forge.scripts.calc.bcr_calculator import _ATRR_IDS, _DELAY_PERIOD_IDS
    from test.spec05_project import item

    atrr = 0.0
    for tid in _ATRR_IDS:
        row = item(r, tid)
        if row["applies"] and row["available"]:
            atrr += row["value_pv_wacc"]
    delay = 0.0
    for tid in _DELAY_PERIOD_IDS:
        row = item(r, tid)
        if row["applies"] and row["available"]:
            delay += row["value_pv_wacc"]
    return atrr, delay


def test_utility_ratio_easement_falls_by_holding():
    name = "CTT_Actual_Delay2"
    before = _BEFORE[name]["bcr_utility"]
    r = run(scenario_changes(name))
    atrr, d = _utility_atrr_and_delay(r)
    assert r["bcr"]["bcr_utility"] == pytest.approx(atrr / (atrr + d), rel=1e-9)
    assert r["bcr"]["bcr_utility"] < before
    assert r["bcr"]["holding_pv"] > 0


def test_utility_ratio_lease_unchanged():
    name = "AEP_LRGV_ACCC"
    before = _BEFORE[name]["bcr_utility"]
    r = run(scenario_changes(name))
    assert item(r, "row_holding")["state"] == "does_not_apply"
    assert r["bcr"]["bcr_utility"] == pytest.approx(before, rel=1e-9)


def test_zero_delay_holding_measured_zero():
    from test.test_spec11_cost_applies import DELAY

    r = run(scenario_changes("CTT_Actual_Delay2", **{DELAY: 0}))
    b = r["bcr"]
    assert b["holding_pv"] == 0.0
    assert b["delay_period_costs_pv"] == 0.0
    atrr, d = _utility_atrr_and_delay(r)
    assert b["bcr_utility"] == pytest.approx(atrr / (atrr + d), rel=1e-9)


def test_rate_base_unchanged():
    for name, before in _BEFORE.items():
        r = run(scenario_changes(name))
        rb = r["benefits"]["capital_recovery"]["rate_base"]
        assert rb == pytest.approx(before["rate_base"], rel=1e-9), name


def test_rate_base_missing_makes_capital_recovery_unavailable():
    import forge
    from forge.core import _bootstrap_run_context
    from forge.scripts.calc import revenue
    from forge.scripts.calc.bcr_calculator import compute_all_bcrs
    from forge.scripts.calc.revenue import get_rate_base
    from forge.scripts.io.json_output_manager import JSONOutputManager
    from forge.scripts.io.taxonomy_adapters import TaxonomyResult, adapt_all_results
    from forge.scripts.utils.run_context import RunState, reset_run_state, set_run_state

    inputs = forge.resolve_inputs(project_changes())
    state = RunState(inputs=inputs, scenario_id="rate_base_missing")
    token = set_run_state(state)
    mgr = JSONOutputManager(scenario_id="rate_base_missing")
    mgr.costs["build"] = {"total_pv": 1.0}
    mgr.costs["row"] = {"total_afudc": 2.0}
    mgr.costs["environmental"] = {"total_afudc": 3.0}
    state.aggregator = mgr
    try:
        _bootstrap_run_context()
        assert get_rate_base() is None
        revenue.main()
        cr = mgr.benefits["capital_recovery"]
        assert cr["availability"]["capital_recovery"] == {
            "available": False,
            "applies": True,
            "missing_inputs": ["costs.build.total_afudc"],
        }
        assert cr["capital_recovery_pv"] is None
        assert cr["rate_base"] is None
        taxonomy = adapt_all_results(mgr.get_json_results())
        b = compute_all_bcrs(taxonomy)
        assert b["omitted"]["bcr_utility"] == ["capital_recovery"]
        solo = compute_all_bcrs([
            TaxonomyResult(
                "capital_recovery",
                value_pv=None,
                value_nominal=None,
                value_pv_wacc=None,
                available=False,
                missing_inputs=("costs.build.total_afudc",),
            ),
        ])
        assert solo["bcr_utility"] is None
        assert solo["omitted"]["bcr_utility"] == ["capital_recovery"]
    finally:
        reset_run_state(token)