from __future__ import annotations

import hashlib
import json
import math
from typing import Any

from forge.data import get_defaults_template


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
