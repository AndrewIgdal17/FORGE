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
