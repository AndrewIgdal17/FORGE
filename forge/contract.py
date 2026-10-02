from __future__ import annotations

import copy
import hashlib
import json
import math
import re
from collections.abc import Mapping
from importlib.metadata import PackageNotFoundError, distribution, version
from typing import Any

from forge.data import get_defaults_template
from forge.errors import UnknownInputPath

_INDEX = re.compile(r"\[(\d+)\]")
_SCALAR = (int, float, str, bool, type(None))


def _encode(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _encode(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_encode(item) for item in value]
    if isinstance(value, float) and math.isinf(value):
        return "Infinity" if value > 0 else "-Infinity"
    if isinstance(value, float) and math.isnan(value):
        return "NaN"
    return value


def canonical_dumps(value: Any) -> str:
    return json.dumps(
        _encode(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def get_defaults_id() -> str:
    digest = hashlib.sha256(canonical_dumps(get_defaults_template()).encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def calculator_info() -> dict:
    try:
        package_version = version("forge-calc")
    except PackageNotFoundError:
        package_version = "0.0.0"
    commit = None
    try:
        raw = distribution("forge-calc").read_text("direct_url.json")
    except (PackageNotFoundError, FileNotFoundError):
        raw = None
    if raw:
        url_info = json.loads(raw)
        commit = (url_info.get("vcs_info") or {}).get("commit_id")
    return {
        "package": "forge-calc",
        "version": package_version,
        "commit": commit,
        "defaults_id": get_defaults_id(),
    }


def _walk(root: dict, path: str):
    current = root
    parent = None
    key: str | int | None = None
    for part in path.split("."):
        name, *indexes = _INDEX.split(part)
        indexes = [piece for piece in indexes if piece != ""]
        parent, key = current, name
        if not isinstance(current, dict) or name not in current:
            raise KeyError(path)
        current = current[name]
        for raw in indexes:
            index = int(raw)
            parent, key = current, index
            if not isinstance(current, list) or index >= len(current):
                raise KeyError(path)
            current = current[index]
    return parent, key


def _decode(value: Any) -> Any:
    if value == "Infinity":
        return float("inf")
    if value == "-Infinity":
        return float("-inf")
    if value == "NaN":
        return float("nan")
    return value


def resolve_inputs(changes: Mapping[str, Any]) -> dict:
    resolved = copy.deepcopy(get_defaults_template())
    bad: list[str] = []
    for path, value in changes.items():
        decoded = _decode(value)
        if not isinstance(decoded, _SCALAR):
            bad.append(path)
            continue
        try:
            parent, key = _walk(resolved, path)
        except KeyError:
            bad.append(path)
            continue
        if isinstance(parent[key], (dict, list)):
            bad.append(path)
            continue
        parent[key] = decoded
    if bad:
        raise UnknownInputPath(bad)
    return resolved


_MISSING = object()


def diff_changes(full_inputs: Mapping) -> dict[str, Any]:
    """Diff a full input document down to the leaves that differ from the template.

    A template key absent from ``full_inputs`` (at any depth, including a whole
    missing dict or list) means "use the template default": no change is
    recorded and no error is raised. A document key with no template slot is
    ignored, including nested keys, matching the template's own extra-key
    behavior. ``UnknownInputPath`` is only raised when a present value sits
    where the template expects a dict or list, or a list's length differs.
    """
    template = get_defaults_template()
    changes: dict[str, Any] = {}

    def walk(template_node, input_node, prefix: str) -> None:
        if input_node is _MISSING:
            return
        if isinstance(template_node, dict):
            if not isinstance(input_node, dict):
                raise UnknownInputPath([prefix])
            for key, child in template_node.items():
                path = f"{prefix}.{key}" if prefix else key
                walk(child, input_node.get(key, _MISSING), path)
            return
        if isinstance(template_node, list):
            if not isinstance(input_node, list) or len(input_node) != len(template_node):
                raise UnknownInputPath([prefix])
            for index, child in enumerate(template_node):
                walk(child, input_node[index], f"{prefix}[{index}]")
            return
        if canonical_dumps(template_node) != canonical_dumps(input_node):
            changes[prefix] = _encode(input_node)

    walk(template, full_inputs, "")
    return changes
