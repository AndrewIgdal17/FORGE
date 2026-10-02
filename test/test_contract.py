import forge
from forge.contract import canonical_dumps


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
