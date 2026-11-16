"""Dry-run stored scenario rows against any calculator checkout (Spec 14)."""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parent.parent
try:
    import forge
except ImportError:
    sys.path.insert(0, str(ROOT))
    import forge
from forge.errors import CalculationError, InvalidInputs, UnknownInputPath

_METRIC_KEYS = ("net_benefit_pv", "bcr_societal", "bcr_utility", "bcr_ratepayer")


def _strip_run_meta(results: dict) -> dict:
    out = dict(results)
    out.pop("timestamp", None)
    out.pop("provenance", None)
    csv_eq = out.get("csv_equivalent")
    if isinstance(csv_eq, dict):
        trimmed = dict(csv_eq)
        trimmed.pop("timestamp", None)
        out["csv_equivalent"] = trimmed
    return out


def _metrics_from_results(results: dict | None) -> dict[str, float | None]:
    if results is None:
        return dict.fromkeys(_METRIC_KEYS, None)
    bcr = results.get("bcr") or {}
    return {key: bcr.get(key) for key in _METRIC_KEYS}


def run_row(row: dict, extra: Mapping[str, Any] | None = None) -> dict:
    merged = {**row["changes"], **(extra or {})}
    base = {
        "id": row["id"],
        "name": row["name"],
        "route_present": row["route_present"],
    }
    try:
        inputs = forge.resolve_inputs(merged)
        results = forge.run_calculation(inputs, scenario_id=row["name"])
        return {
            **base,
            "status": "ok",
            "message": "",
            "metrics": _metrics_from_results(results),
            "results": _strip_run_meta(results),
        }
    except (InvalidInputs, UnknownInputPath) as exc:
        message = getattr(exc, "message", None) or str(exc)
        return {
            **base,
            "status": "refused",
            "message": message,
            "metrics": dict.fromkeys(_METRIC_KEYS, None),
            "results": None,
        }
    except Exception as exc:
        return {
            **base,
            "status": "failed",
            "message": str(exc),
            "metrics": dict.fromkeys(_METRIC_KEYS, None),
            "results": None,
        }


def run_rows(
    rows: list[dict],
    patch: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict:
    patch = patch or {}
    out_rows = []
    for row in rows:
        extra = patch.get(row["id"])
        out_rows.append(run_row(row, extra))
    return {"calculator": forge.calculator_info(), "rows": out_rows}


def _leaf_equal(a: Any, b: Any, rel_tol: float) -> bool:
    if a is b:
        return True
    if isinstance(a, float) and isinstance(b, float):
        if math.isnan(a) and math.isnan(b):
            return True
        return math.isclose(a, b, rel_tol=rel_tol, abs_tol=rel_tol)
    return a == b


def changed_leaves(before: Any, after: Any, rel_tol: float = 1e-9) -> list[str]:
    paths: list[str] = []

    def walk(pb: Any, pa: Any, prefix: str) -> None:
        if isinstance(pb, dict) and isinstance(pa, dict):
            keys = set(pb) | set(pa)
            for key in sorted(keys):
                child = f"{prefix}.{key}" if prefix else key
                if key not in pb:
                    paths.append(child)
                elif key not in pa:
                    paths.append(child)
                else:
                    walk(pb[key], pa[key], child)
            return
        if isinstance(pb, list) and isinstance(pa, list):
            max_len = max(len(pb), len(pa))
            for i in range(max_len):
                child = f"{prefix}[{i}]"
                if i >= len(pb) or i >= len(pa):
                    paths.append(child)
                elif not _leaf_equal(pb[i], pa[i], rel_tol):
                    paths.append(child)
            return
        if not _leaf_equal(pb, pa, rel_tol):
            if prefix:
                paths.append(prefix)

    if not isinstance(before, dict) or not isinstance(after, dict):
        if not _leaf_equal(before, after, rel_tol):
            paths.append("")
        return paths

    walk(before, after, "")
    return sorted(paths)


def compare_runs(before: dict, after: dict) -> list[dict]:
    before_by_id = {r["id"]: r for r in before["rows"]}
    after_by_id = {r["id"]: r for r in after["rows"]}
    ids = sorted(set(before_by_id) | set(after_by_id), key=lambda i: before_by_id.get(i, after_by_id[i])["name"])
    compared: list[dict] = []
    for row_id in ids:
        b = before_by_id[row_id]
        a = after_by_id[row_id]
        res_b, res_a = b.get("results"), a.get("results")
        if res_b is not None and res_a is not None:
            n_changed = len(changed_leaves(res_b, res_a))
        else:
            n_changed = 0
        entry: dict[str, Any] = {
            "name": b["name"],
            "legacy": not b.get("route_present", True),
            "status_before": b["status"],
            "status_after": a["status"],
            "changed_leaves": n_changed,
        }
        for key in _METRIC_KEYS:
            entry[f"{key}_before"] = b["metrics"].get(key)
            entry[f"{key}_after"] = a["metrics"].get(key)
        compared.append(entry)
    return compared


def _fmt_metric(value: float | None) -> str:
    if value is None:
        return "—"
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return str(value)
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)


def _fmt_cell(before: float | None, after: float | None) -> str:
    return f"{_fmt_metric(before)} → {_fmt_metric(after)}"


def format_report(compared: list[dict]) -> str:
    lines = [
        "| Row | Legacy | Status | Net benefit | Societal | Utility | Ratepayer | Changed leaves |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in compared:
        legacy = "yes" if row["legacy"] else "no"
        status = f"{row['status_before']} → {row['status_after']}"
        lines.append(
            "| "
            + " | ".join(
                [
                    row["name"],
                    legacy,
                    status,
                    _fmt_cell(row["net_benefit_pv_before"], row["net_benefit_pv_after"]),
                    _fmt_cell(row["bcr_societal_before"], row["bcr_societal_after"]),
                    _fmt_cell(row["bcr_utility_before"], row["bcr_utility_after"]),
                    _fmt_cell(row["bcr_ratepayer_before"], row["bcr_ratepayer_after"]),
                    str(row["changed_leaves"]),
                ]
            )
            + " |"
        )
    return "\n".join(lines) + "\n"


def _cmd_run(args: argparse.Namespace) -> None:
    rows = json.loads(Path(args.rows).read_text())
    patch = None
    if args.patch:
        patch = json.loads(Path(args.patch).read_text())
    payload = run_rows(rows, patch)
    Path(args.out).write_text(json.dumps(payload, indent=2) + "\n")


def _cmd_compare(args: argparse.Namespace) -> None:
    before = json.loads(Path(args.before).read_text())
    after = json.loads(Path(args.after).read_text())
    table = format_report(compare_runs(before, after))
    Path(args.out).write_text(table)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Dry-run stored scenario rows")
    sub = parser.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="Run calculator on stored rows")
    run_p.add_argument("--rows", required=True)
    run_p.add_argument("--out", required=True)
    run_p.add_argument("--patch", default=None)
    run_p.set_defaults(func=_cmd_run)

    cmp_p = sub.add_parser("compare", help="Compare two dry-run JSON outputs")
    cmp_p.add_argument("--before", required=True)
    cmp_p.add_argument("--after", required=True)
    cmp_p.add_argument("--out", required=True)
    cmp_p.set_defaults(func=_cmd_compare)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()