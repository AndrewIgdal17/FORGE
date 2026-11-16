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
from test.spec05_project import measured, project_changes, run
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
    for key in _NEW_BCR_KEYS - {"holding_pv"}:
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