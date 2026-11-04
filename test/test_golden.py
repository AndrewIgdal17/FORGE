"""Every bundled case study must return the same results as its golden fixture.

The fixtures were recorded under the last 1.x release. Any field that
differs must be explained and the fixture updated in its own commit.

Floating-point comparisons use a relative tolerance of 1e-9 to account
for platform differences (macOS ARM vs Linux x86).
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

import forge

GOLDEN_DIR = Path(__file__).resolve().parent / "golden"
EXCLUDED_KEYS = {"timestamp", "provenance"}
_REL_TOL = 1e-9


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


def _scenario_ids():
    return sorted(p.stem for p in GOLDEN_DIR.glob("*.json"))


@pytest.fixture(params=_scenario_ids())
def scenario(request):
    return request.param


def test_bundled_scenario_omits_protected_area_acres(scenario):
    forge_file = forge.get_scenarios_path() / f"{scenario}.forge"
    document = json.loads(forge_file.read_text())
    with pytest.raises(forge.InvalidInputs, match="protected_area_acres are required"):
        forge.resolve_inputs(forge.diff_changes(document["inputs"]))
