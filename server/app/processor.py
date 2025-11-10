"""Utility module that transforms inbound JSON payloads."""

from __future__ import annotations

from typing import Any, Dict, Iterator, List, Tuple


def generate_result(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a derived JSON response based on the incoming payload."""
    mode = str(payload.get("mode", "simple")).lower()
    if mode == "bulk":
        combined = payload.get("combinedData") or {}
        flattened = list(_flatten_items(combined))
        lines = [f"{key}: {value}" for key, value in flattened]
        return {
            "mode": "bulk",
            "entries": len(lines),
            "lines": lines,
            "text": "\n".join(lines),
        }

    message = str(payload.get("message", ""))
    numbers: List[float] = [
        float(value)
        for value in payload.get("values", [])
        if _is_number(value)
    ]

    return {
        "mode": "simple",
        "originalMessage": message,
        "characterCount": len(message),
        "valuesProvided": len(numbers),
        "sum": sum(numbers),
        "average": sum(numbers) / len(numbers) if numbers else None,
    }


def _flatten_items(item: Any, prefix: str | None = None) -> Iterator[Tuple[str, Any]]:
    """Yield dotted-path keys for nested dict/list structures."""
    if isinstance(item, dict):
        for key, value in item.items():
            new_prefix = f"{prefix}.{key}" if prefix else str(key)
            yield from _flatten_items(value, new_prefix)
    elif isinstance(item, list):
        for index, value in enumerate(item):
            new_prefix = f"{prefix}[{index}]" if prefix else f"[{index}]"
            yield from _flatten_items(value, new_prefix)
    else:
        if prefix is None:
            prefix = ""
        yield prefix, item


def _is_number(value: Any) -> bool:
    """Determine whether value can be interpreted as a float."""
    try:
        float(value)
    except (TypeError, ValueError):
        return False
    return True
