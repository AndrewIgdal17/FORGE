from __future__ import annotations

import copy
import hashlib
import json
import math
import re
from collections.abc import Mapping
from functools import lru_cache
from importlib.metadata import PackageNotFoundError, distribution, version
from typing import Any

from forge.data import get_defaults_template
from forge.errors import UnknownInputPath
from forge.scripts.io.input_metadata import input_metadata_to_dict

_INDEX = re.compile(r"\[(\d+)\]")
_SCALAR = (int, float, str, bool, type(None))
_MAX_STRING_LENGTH = 200
_NUMERIC_INPUT_TYPES = ("number", "currency", "percent")


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


@lru_cache(maxsize=1)
def _metadata_by_path() -> dict[str, dict]:
    return {
        f"{field['yaml_section']}.{field['field_path']}": field
        for field in input_metadata_to_dict()
    }


def _check_bounds(decoded: Any, validation: dict) -> str | None:
    minimum = validation.get("min")
    if minimum is not None and decoded < minimum:
        return f"{decoded} is below the minimum of {minimum}"
    maximum = validation.get("max")
    if maximum is not None and decoded > maximum:
        return f"{decoded} is above the maximum of {maximum}"
    return None


def _validate_against_metadata(path: str, decoded: Any, field: dict, template: dict) -> str | None:
    input_type = field.get("input_type")
    validation = field.get("validation") or {}

    leaf_is_null = False
    try:
        parent, key = _walk(template, path)
        leaf_is_null = parent[key] is None
    except KeyError:
        pass

    if input_type in _NUMERIC_INPUT_TYPES:
        if leaf_is_null:
            # The default is null, so metadata's declared type can't be
            # trusted as the ground truth (e.g. design-comparison fields
            # that hold strings but default to the generic "number" type).
            return None
        if not isinstance(decoded, (int, float)) or isinstance(decoded, bool):
            return "must be a number"
        return _check_bounds(decoded, validation)

    if input_type == "toggle":
        if leaf_is_null:
            return None
        if not isinstance(decoded, bool):
            return "must be a boolean"
        return None

    if input_type in ("dropdown", "dynamic_dropdown"):
        options = validation.get("options")
        if options is not None:
            if decoded not in options:
                return f"{decoded!r} is not one of the allowed options {options}"
            return None
        option_sets = validation.get("optionSets") or {}
        pooled = [item for values in option_sets.values() for item in values]
        is_numeric_pool = pooled and all(
            isinstance(item, (int, float)) and not isinstance(item, bool) for item in pooled
        )
        if is_numeric_pool:
            # The applicable option set depends on another field (dependsOn)
            # that may not be present in this partial change set. Fall back
            # to a plausible-range check across all option sets combined.
            if not isinstance(decoded, (int, float)) or isinstance(decoded, bool):
                return "must be a number"
            return _check_bounds(decoded, {"min": min(pooled), "max": max(pooled)})
        # Non-numeric dependsOn options can't be validated without knowing
        # the dependent field's value; skip the enum check in that case.
        return None

    return _check_bounds(decoded, validation)


def _validate_against_template(path: str, decoded: Any, template: dict) -> str | None:
    try:
        parent, key = _walk(template, path)
    except KeyError:
        return "unknown input path"
    leaf = parent[key]
    if leaf is None:
        return None  # any value may replace a null default
    if isinstance(leaf, bool):
        if not isinstance(decoded, bool):
            return "expected a boolean"
        return None
    if isinstance(leaf, (int, float)):
        if not isinstance(decoded, (int, float)) or isinstance(decoded, bool):
            return "expected a number"
        return None
    if isinstance(leaf, str):
        if not isinstance(decoded, str):
            return "expected a string"
        return None
    return "does not refer to a scalar leaf"


def validate_changes(changes: Mapping[str, Any]) -> list[dict]:
    """Validate proposed input changes before they are applied.

    Returns a list of ``{"path": ..., "message": ...}`` entries, one per
    invalid path. An empty list means every change is valid.
    """
    metadata = _metadata_by_path()
    template = get_defaults_template()
    errors: list[dict] = []
    for path, raw_value in changes.items():
        decoded = _decode(raw_value)
        if not isinstance(decoded, _SCALAR):
            errors.append({"path": path, "message": "value must be a scalar (not a dict or list)"})
            continue
        if decoded is None:
            # Null always resets a field to its template default.
            continue
        if isinstance(decoded, str) and len(decoded) > _MAX_STRING_LENGTH:
            errors.append({
                "path": path,
                "message": f"string exceeds {_MAX_STRING_LENGTH} characters",
            })
            continue
        field = metadata.get(path)
        if field is not None:
            message = _validate_against_metadata(path, decoded, field, template)
        else:
            message = _validate_against_template(path, decoded, template)
        if message:
            errors.append({"path": path, "message": message})
    return errors


def resolve_inputs(changes: Mapping[str, Any]) -> dict:
    errors = validate_changes(changes)
    if errors:
        raise UnknownInputPath([error["path"] for error in errors])
    resolved = copy.deepcopy(get_defaults_template())
    for path, value in changes.items():
        parent, key = _walk(resolved, path)
        parent[key] = _decode(value)
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
