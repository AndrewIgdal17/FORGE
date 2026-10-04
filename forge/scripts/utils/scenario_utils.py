"""Shared utilities for FORGE case study scenario runners."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from forge.data import get_defaults_template

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCENARIOS_DIR = REPO_ROOT / "scenarios"

logger = logging.getLogger(__name__)


def build_default_inputs() -> dict[str, Any]:
    """Return the canonical defaults template.

    Same dict shape as a .forge file's ``inputs`` key: YAML stems mapped to
    their parsed contents.
    """
    return get_defaults_template()


def run_scenario(inputs: dict, scenario_id: str) -> dict:
    """Run a single scenario through the FORGE calculation engine."""
    from forge import run_calculation

    return run_calculation(
        combined_data=inputs,
        scenario_id=scenario_id,
    )


def save_forge_file(
    inputs: dict, results: dict, name: str, scenario_id: str, source: str = "case_study"
) -> Path:
    """Save a complete .forge file with inputs, results, and metadata."""
    forge = {
        "version": "1.0",
        "customName": name,
        "inputs": inputs,
        "results": results,
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "scenario_id": scenario_id,
            "source": source,
        },
    }
    out_path = SCENARIOS_DIR / f"{name}.forge"
    with open(out_path, "w") as f:
        json.dump(forge, f, indent=2, default=str)
    logger.info(f"  Saved: {out_path}")
    return out_path


def fmt(val: float, prefix: str = "$") -> str:
    """Format large numbers with B/M suffixes."""
    if abs(val) >= 1e9:
        return f"{prefix}{val/1e9:.2f}B"
    elif abs(val) >= 1e6:
        return f"{prefix}{val/1e6:.1f}M"
    else:
        return f"{prefix}{val:,.0f}"
