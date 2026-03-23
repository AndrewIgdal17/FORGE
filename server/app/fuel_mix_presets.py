"""Load reference fuel / energy_source_mix presets for the web UI (file-backed; DB later)."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Set

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
FUEL_MIX_PRESETS_FILE = BASE_DIR / "json" / "fuel_mix_presets.json"

EXPECTED_SOURCES: Set[str] = {
    "coal",
    "oil",
    "natural_gas",
    "solar",
    "wind",
    "hydro",
    "nuclear",
    "other",
}


def _validate_preset(entry: Dict[str, Any], index: int) -> bool:
    if not isinstance(entry, dict):
        logger.warning("fuel_mix_presets: preset[%s] is not an object", index)
        return False
    pid = entry.get("id")
    label = entry.get("label")
    mix = entry.get("energy_source_mix")
    if not isinstance(pid, str) or not pid.strip():
        logger.warning("fuel_mix_presets: preset[%s] missing id", index)
        return False
    if not isinstance(label, str) or not label.strip():
        logger.warning("fuel_mix_presets: preset[%s] missing label", index)
        return False
    if not isinstance(mix, dict):
        logger.warning("fuel_mix_presets: preset %r missing energy_source_mix object", pid)
        return False
    for src in EXPECTED_SOURCES:
        block = mix.get(src)
        if not isinstance(block, dict):
            logger.warning("fuel_mix_presets: preset %r missing source %r", pid, src)
            return False
        pct = block.get("percentage")
        roc = block.get("rate_of_change")
        if not isinstance(pct, (int, float)):
            logger.warning("fuel_mix_presets: preset %r %s.percentage invalid", pid, src)
            return False
        if not isinstance(roc, (int, float)):
            logger.warning("fuel_mix_presets: preset %r %s.rate_of_change invalid", pid, src)
            return False
    extras = set(mix.keys()) - EXPECTED_SOURCES
    if extras:
        logger.warning("fuel_mix_presets: preset %r has unknown sources %s", pid, extras)
        return False
    return True


def load_fuel_mix_presets() -> Dict[str, Any]:
    """
    Return { "presets": [ ... ] } from server/json/fuel_mix_presets.json.
    Invalid entries are skipped; if the file is missing or invalid, returns { "presets": [] }.
    """
    if not FUEL_MIX_PRESETS_FILE.is_file():
        logger.warning("fuel_mix_presets: file missing at %s", FUEL_MIX_PRESETS_FILE)
        return {"presets": []}

    try:
        raw = json.loads(FUEL_MIX_PRESETS_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("fuel_mix_presets: failed to read JSON: %s", exc)
        return {"presets": []}

    if not isinstance(raw, dict):
        logger.warning("fuel_mix_presets: root must be an object")
        return {"presets": []}

    presets_list = raw.get("presets")
    if not isinstance(presets_list, list):
        logger.warning("fuel_mix_presets: presets must be an array")
        return {"presets": []}

    valid: List[Dict[str, Any]] = []
    for i, entry in enumerate(presets_list):
        if _validate_preset(entry, i):
            valid.append(entry)

    return {"presets": valid}
