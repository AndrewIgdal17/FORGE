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
