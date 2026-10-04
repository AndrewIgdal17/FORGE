"""Every bundled case study must return the same results as its golden fixture.

The fixtures were recorded under the last 1.x release. Any field that
differs must be explained and the fixture updated in its own commit.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

import forge

GOLDEN_DIR = Path(__file__).resolve().parent / "golden"
EXCLUDED_KEYS = {"timestamp", "provenance"}


def _strip_excluded(obj, excluded=EXCLUDED_KEYS):
    if isinstance(obj, dict):
        return {k: _strip_excluded(v, excluded) for k, v in obj.items() if k not in excluded}
    if isinstance(obj, list):
        return [_strip_excluded(v, excluded) for v in obj]
    return obj


def _scenario_ids():
    return sorted(p.stem for p in GOLDEN_DIR.glob("*.json"))


@pytest.fixture(params=_scenario_ids())
def scenario(request):
    return request.param


def test_case_study_matches_golden(scenario):
    golden_path = GOLDEN_DIR / f"{scenario}.json"
    expected = json.loads(golden_path.read_text())

    forge_file = forge.get_scenarios_path() / f"{scenario}.forge"
    with open(forge_file) as f:
        document = json.load(f)
    full_inputs = document["inputs"]
    changes = forge.diff_changes(full_inputs)
    resolved = forge.resolve_inputs(changes)
    results = forge.run_calculation(resolved, scenario_id=scenario)
    actual = json.loads(forge.canonical_dumps(_strip_excluded(results)))

    assert actual == expected, f"Golden mismatch for {scenario}"
