"""Concurrent calls return the same results as sequential calls."""
import json
import math
import random
import threading
from pathlib import Path

import forge

GOLDEN_DIR = Path(__file__).resolve().parent / "golden"
_REL_TOL = 1e-9


def _scenario_ids():
    return sorted(p.stem for p in GOLDEN_DIR.glob("*.json"))


EXCLUDED_KEYS = {"timestamp", "provenance"}


def _strip_excluded(obj, excluded=EXCLUDED_KEYS):
    if isinstance(obj, dict):
        return {k: _strip_excluded(v, excluded) for k, v in obj.items() if k not in excluded}
    if isinstance(obj, list):
        return [_strip_excluded(v, excluded) for v in obj]
    return obj


def _approx_equal(actual, expected, rel_tol=_REL_TOL):
    """Recursively compare, using math.isclose for floats."""
    if isinstance(expected, dict):
        if not isinstance(actual, dict) or actual.keys() != expected.keys():
            return False
        return all(_approx_equal(actual[k], expected[k], rel_tol) for k in expected)
    if isinstance(expected, list):
        if not isinstance(actual, list) or len(actual) != len(expected):
            return False
        return all(_approx_equal(a, e, rel_tol) for a, e in zip(actual, expected))
    if isinstance(expected, float) and isinstance(actual, float):
        if math.isnan(expected) and math.isnan(actual):
            return True
        return math.isclose(actual, expected, rel_tol=rel_tol)
    return actual == expected


def _restore_scenario_id(obj, run_id, scenario_name):
    """Golden fixtures store the case-study name. Each concurrent run uses a unique id."""
    if isinstance(obj, dict):
        restored = {}
        for key, value in obj.items():
            if key == "scenario_id" and value == run_id:
                restored[key] = scenario_name
            else:
                restored[key] = _restore_scenario_id(value, run_id, scenario_name)
        return restored
    if isinstance(obj, list):
        return [_restore_scenario_id(value, run_id, scenario_name) for value in obj]
    return obj


def test_eight_threads_match_golden():
    """8 scenarios × 5 runs each, shuffled; every run of a scenario agrees."""
    scenarios = _scenario_ids()
    errors = []
    runs_by_scenario = {name: {} for name in scenarios}
    lock = threading.Lock()

    def worker(scenario_name, run_index):
        try:
            forge_file = forge.get_scenarios_path() / f"{scenario_name}.forge"
            with open(forge_file) as f:
                document = json.load(f)
            changes = forge.diff_changes(document["inputs"])
            changes.update({
                "02_project_physical_details.terrain.protected_area_acres.forested": 0.0,
                "02_project_physical_details.terrain.protected_area_acres.scrubbed_flat": 0.0,
                "02_project_physical_details.terrain.protected_area_acres.desert_barren": 0.0,
                "02_project_physical_details.terrain.protected_area_acres.rolling_hills": 0.0,
                "02_project_physical_details.terrain.protected_area_acres.mountain": 0.0,
            })
            resolved = forge.resolve_inputs(changes)
            run_id = f"{scenario_name}_{run_index}"
            results = forge.run_calculation(resolved, scenario_id=run_id)
            actual = json.loads(forge.canonical_dumps(_strip_excluded(results)))
            actual = _restore_scenario_id(actual, run_id, scenario_name)
            with lock:
                runs_by_scenario[scenario_name][run_index] = actual
        except Exception as exc:
            with lock:
                errors.append(f"{scenario_name} run {run_index}: {type(exc).__name__}: {exc}")

    tasks = [(s, i) for s in scenarios for i in range(5)]
    random.shuffle(tasks)

    threads = []
    for scenario, idx in tasks:
        t = threading.Thread(target=worker, args=(scenario, idx))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    for scenario_name in scenarios:
        runs = runs_by_scenario[scenario_name]
        if len(runs) != 5:
            errors.append(f"{scenario_name}: expected 5 runs, got {sorted(runs)}")
            continue
        for left in range(5):
            for right in range(left + 1, 5):
                if not _approx_equal(runs[left], runs[right]):
                    errors.append(f"{scenario_name} run {left} != run {right}")

    assert not errors, f"Concurrent mismatches: {errors}"
