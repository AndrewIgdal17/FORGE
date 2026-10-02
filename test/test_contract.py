import hashlib
import json
import math
from pathlib import Path

import pytest

import forge
import forge.contract
from forge.contract import canonical_dumps
from forge.errors import UnknownInputPath


def test_defaults_id_is_stable_and_skips_the_registry():
    first = forge.get_defaults_id()
    second = forge.get_defaults_id()
    assert first == second
    assert first.startswith("sha256:")
    template = forge.get_defaults_template()
    assert "defaults_registry" not in template
    assert "project_category_template" not in template
    assert canonical_dumps(float("inf")) == '"Infinity"'
    assert canonical_dumps(float("-inf")) == '"-Infinity"'
    assert canonical_dumps(float("nan")) == '"NaN"'


def test_template_has_the_missing_leaves():
    template = forge.get_defaults_template()
    overrides = template["10_project_category_build_costs"]["overrides"]
    assert overrides == {
        "variable_conductor_cost_per_mile": None,
        "fixed_conductor_cost": None,
        "variable_structure_cost_per_mile": None,
        "fixed_converter_cost": None,
    }
    assert template["01_project_technical_details"]["project"]["old_converter_type"] is None
    from forge.scripts.io.input_metadata import input_metadata_to_dict

    fields = input_metadata_to_dict()
    premium = next(field for field in fields if field["id"] == "insurance_premium_rate")
    assert premium["field_path"] == "insurance.premium_rate_default"


def test_resolve_inputs_applies_leaves_and_rejects_the_rest():
    assert forge.resolve_inputs({}) == forge.get_defaults_template()
    resolved = forge.resolve_inputs({
        "01_project_technical_details.project.capacity_mw": 1792,
        "07_outage_costs.outage.value_of_lost_load.tiers[9].max_hours": "Infinity",
        "01_project_technical_details.project.old_converter_type": "NaN",
    })
    assert resolved["01_project_technical_details"]["project"]["capacity_mw"] == 1792
    assert math.isinf(resolved["07_outage_costs"]["outage"]["value_of_lost_load"]["tiers"][9]["max_hours"])
    assert math.isnan(resolved["01_project_technical_details"]["project"]["old_converter_type"])
    try:
        forge.resolve_inputs({
            "no.such.path": 1,
            "01_project_technical_details.project.capacity_mw": {"nested": True},
        })
    except UnknownInputPath as exc:
        assert "no.such.path" in exc.paths
        assert "01_project_technical_details.project.capacity_mw" in exc.paths
    else:
        raise AssertionError("expected UnknownInputPath")


def test_calculator_info_and_provenance():
    info = forge.calculator_info()
    assert info["package"] == "forge-calc"
    assert info["version"]
    assert info["defaults_id"] == forge.get_defaults_id()
    assert "commit" in info
    inputs = forge.resolve_inputs({"01_project_technical_details.project.capacity_mw": 1792})
    results = forge.run_calculation(inputs, scenario_id="prov-test")
    provenance = results["provenance"]
    assert provenance["defaults_id"] == info["defaults_id"]
    assert provenance["inputs_id"] == "sha256:" + hashlib.sha256(
        canonical_dumps(inputs).encode("utf-8")
    ).hexdigest()


def _assert_present_leaves_match(template_node, resolved_node, input_node):
    """Compare resolved_node against input_node for every leaf present in input_node.

    Walks template_node to find the shape. A key/index missing from input_node
    (template default was used, no case-study value to check) is skipped. A
    whole missing dict or list is skipped entirely.
    """
    if isinstance(template_node, dict):
        if not isinstance(input_node, dict):
            return
        for key, child in template_node.items():
            if key in input_node:
                _assert_present_leaves_match(child, resolved_node[key], input_node[key])
        return
    if isinstance(template_node, list):
        if not isinstance(input_node, list) or len(input_node) != len(template_node):
            return
        for index, child in enumerate(template_node):
            _assert_present_leaves_match(child, resolved_node[index], input_node[index])
        return
    assert forge.canonical_dumps(resolved_node) == forge.canonical_dumps(input_node)


def test_diff_changes_raises_on_present_value_type_mismatches(monkeypatch):
    tiny_template = {
        "section": {
            "nested": {"leaf": 1},
            "items": [1, 2],
        }
    }
    monkeypatch.setattr(forge.contract, "get_defaults_template", lambda: tiny_template)

    with pytest.raises(UnknownInputPath) as exc:
        forge.diff_changes({"section": {"nested": 5, "items": [1, 2]}})
    assert exc.value.paths == ["section.nested"]

    with pytest.raises(UnknownInputPath) as exc:
        forge.diff_changes({"section": {"nested": {"leaf": 1}, "items": "oops"}})
    assert exc.value.paths == ["section.items"]

    with pytest.raises(UnknownInputPath) as exc:
        forge.diff_changes({"section": {"nested": {"leaf": 1}, "items": [1]}})
    assert exc.value.paths == ["section.items"]


def test_grid_mix_presets_exclude_the_false_default():
    presets = forge.get_grid_mix_presets()
    ids = [item["id"] for item in presets]
    assert ids == ["illustrative_high_renewables"]
    mix = presets[0]["grid_mix"]["initial"]
    assert set(mix) == {"coal", "oil", "natural_gas", "solar", "wind", "hydro", "nuclear", "other"}
    assert abs(sum(mix.values()) - 100) < 1e-9


def test_each_case_study_round_trips_through_changes():
    template = forge.get_defaults_template()
    scenarios = Path(forge.get_scenarios_path())
    names = sorted(path.name for path in scenarios.glob("*.forge"))
    assert len(names) == 8
    for name in names:
        document = json.loads((scenarios / name).read_text())
        inputs = document["inputs"]
        changes = forge.diff_changes(inputs)
        resolved = forge.resolve_inputs(changes)
        _assert_present_leaves_match(template, resolved, inputs)
