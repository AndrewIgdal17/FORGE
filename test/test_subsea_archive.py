from pathlib import Path

from forge.data import get_defaults_template, get_yamls_path


def _walk(node):
    if isinstance(node, dict):
        for key, value in node.items():
            yield key
            yield from _walk(value)
    elif isinstance(node, list):
        for value in node:
            yield from _walk(value)
    elif isinstance(node, str):
        yield node


def test_live_template_has_no_subsea_value():
    for item in _walk(get_defaults_template()):
        assert "subsea" not in str(item).lower()


def test_archive_keeps_the_marine_comment_and_is_not_loaded():
    archive = Path("forge/data/archive/subsea_defaults.yaml")
    text = archive.read_text()
    assert "MarketIntelo" in text
    assert "Subsea/AC/140MW" in text
    assert "marine_env_mitigation_pct_capex" in text
    readme = Path("forge/data/archive/README.md").read_text()
    assert "does not load it" in readme
    assert "archive/subsea" in readme
    loaded = {path.name for path in get_yamls_path().glob("*.yaml")}
    assert "subsea_defaults.yaml" not in loaded
