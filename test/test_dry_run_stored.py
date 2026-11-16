"""Unit tests for scripts/dry_run_stored.py (Spec 14 dry-run tool)."""
from __future__ import annotations

import math

import pytest

from scripts.dry_run_stored import changed_leaves, compare_runs, format_report, run_row
from test.spec05_project import project_changes

METRIC_KEYS = ("net_benefit_pv", "bcr_societal", "bcr_utility", "bcr_ratepayer")


def test_changed_leaves_paths():
    before = {"a": 1.0, "b": [1, 2]}
    after = {"a": 1.0 + 1e-12, "b": [1, 3], "c": 0}
    assert changed_leaves(before, after) == ["b[1]", "c"]


def test_compare_runs_hand_built():
    before = {
        "calculator": {"version": "1"},
        "rows": [
            {
                "id": "a",
                "name": "LegacyRow",
                "route_present": False,
                "status": "ok",
                "message": "",
                "metrics": dict.fromkeys(METRIC_KEYS, 1.0),
                "results": {"x": 1},
            },
            {
                "id": "b",
                "name": "Routed",
                "route_present": True,
                "status": "ok",
                "message": "",
                "metrics": dict.fromkeys(METRIC_KEYS, 2.0),
                "results": {"x": 2},
            },
        ],
    }
    after = {
        "calculator": {"version": "2"},
        "rows": [
            {
                "id": "a",
                "name": "LegacyRow",
                "route_present": False,
                "status": "ok",
                "message": "",
                "metrics": dict.fromkeys(METRIC_KEYS, 1.0),
                "results": {"x": 1},
            },
            {
                "id": "b",
                "name": "Routed",
                "route_present": True,
                "status": "refused",
                "message": "bad",
                "metrics": dict.fromkeys(METRIC_KEYS, None),
                "results": None,
            },
        ],
    }
    compared = compare_runs(before, after)
    assert len(compared) == 2
    legacy = next(r for r in compared if r["name"] == "LegacyRow")
    assert legacy["legacy"] is True
    assert legacy["status_before"] == "ok"
    assert legacy["status_after"] == "ok"
    assert legacy["changed_leaves"] == 0
    routed = next(r for r in compared if r["name"] == "Routed")
    assert routed["legacy"] is False
    assert routed["status_before"] == "ok"
    assert routed["status_after"] == "refused"
    assert routed["changed_leaves"] == 0


def test_format_report_header():
    table = format_report([])
    assert table.startswith("| Row | Legacy | Status |")


def test_run_row_refused_unknown_path():
    out = run_row(
        {
            "id": "x",
            "name": "n",
            "route_present": False,
            "changes": {"no.such.path": 1},
        }
    )
    assert out["status"] == "refused"
    assert out["id"] == "x"
    assert out["name"] == "n"


def test_run_row_ok_finite_metrics():
    out = run_row(
        {
            "id": "sunzia",
            "name": "SunZia_Delay2",
            "route_present": True,
            "changes": project_changes(),
        }
    )
    assert out["status"] == "ok"
    for key in METRIC_KEYS:
        value = out["metrics"][key]
        assert value is not None
        assert math.isfinite(float(value))


def test_format_report_extra_metric_column():
    compared = [
        {
            "name": "Row",
            "legacy": False,
            "status_before": "ok",
            "status_after": "ok",
            "net_benefit_pv_before": 1.0,
            "net_benefit_pv_after": 1.0,
            "bcr_societal_before": 1.0,
            "bcr_societal_after": 1.0,
            "bcr_utility_before": 1.0,
            "bcr_utility_after": 1.0,
            "bcr_ratepayer_before": 1.0,
            "bcr_ratepayer_after": 1.0,
            "changed_leaves": 0,
            "extra_columns": [
                {
                    "label": "bcr.hard_costs_pv:bcr.capital_costs_pv",
                    "before": 10.0,
                    "after": 8.0,
                }
            ],
        }
    ]
    table = format_report(compared)
    assert "bcr.hard_costs_pv:bcr.capital_costs_pv" in table
    assert "10 → 8" in table


def test_format_report_extra_metric_absent():
    from scripts.dry_run_stored import _ABSENT

    compared = [
        {
            "name": "Row",
            "legacy": True,
            "status_before": "ok",
            "status_after": "ok",
            "net_benefit_pv_before": None,
            "net_benefit_pv_after": None,
            "bcr_societal_before": None,
            "bcr_societal_after": None,
            "bcr_utility_before": 1.0,
            "bcr_utility_after": 1.0,
            "bcr_ratepayer_before": None,
            "bcr_ratepayer_after": None,
            "changed_leaves": 0,
            "extra_columns": [
                {"label": "bcr.holding_pv", "before": _ABSENT, "after": 5.0},
            ],
        }
    ]
    table = format_report(compared)
    assert "absent → 5" in table


def test_compare_runs_extra_metrics():
    before = {
        "calculator": {},
        "rows": [
            {
                "id": "1",
                "name": "R",
                "route_present": True,
                "status": "ok",
                "metrics": dict.fromkeys(METRIC_KEYS, 1.0),
                "results": {"bcr": {"hard_costs_pv": 10.0, "capital_costs_pv": 9.0}},
            }
        ],
    }
    after = {
        "calculator": {},
        "rows": [
            {
                "id": "1",
                "name": "R",
                "route_present": True,
                "status": "ok",
                "metrics": dict.fromkeys(METRIC_KEYS, 1.0),
                "results": {"bcr": {"hard_costs_pv": 8.0, "capital_costs_pv": 8.0}},
            }
        ],
    }
    paths = [("bcr.hard_costs_pv", "bcr.capital_costs_pv")]
    compared = compare_runs(before, after, metric_paths=paths)
    assert compared[0]["extra_columns"][0]["before"] == 10.0
    assert compared[0]["extra_columns"][0]["after"] == 8.0