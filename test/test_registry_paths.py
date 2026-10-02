import re

import yaml
from forge.contract import resolve_inputs
from forge.data import get_defaults_template, get_yamls_path

_INDEX = re.compile(r"\[(\d+)\]")


def _entries(node, prefix=""):
    if isinstance(node, dict) and ("path" in node or ("value" in node and "unit" in node)):
        yield prefix, node
        return
    if isinstance(node, dict):
        for key, child in node.items():
            yield from _entries(child, f"{prefix}.{key}" if prefix else key)


def _walk(root, path):
    current = root
    for part in path.split("."):
        name, *indexes = _INDEX.split(part)
        indexes = [piece for piece in indexes if piece != ""]
        assert isinstance(current, dict) and name in current, path
        current = current[name]
        for raw in indexes:
            index = int(raw)
            assert isinstance(current, list) and index < len(current), path
            current = current[index]
    return current


def test_registry_paths_resolve_and_values_are_gone():
    document = yaml.safe_load((get_yamls_path() / "defaults_registry.yaml").read_text())
    template = get_defaults_template()
    for name, entry in _entries(document):
        assert "value" not in entry, name
        node = _walk(template, entry["path"])
        if not isinstance(node, list):
            resolve_inputs({entry["path"]: None})
