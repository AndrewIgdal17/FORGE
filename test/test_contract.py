import hashlib
import math

import forge
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
    })
    assert resolved["01_project_technical_details"]["project"]["capacity_mw"] == 1792
    assert math.isinf(resolved["07_outage_costs"]["outage"]["value_of_lost_load"]["tiers"][9]["max_hours"])
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
