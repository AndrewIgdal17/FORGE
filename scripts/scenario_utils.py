"""Shared utilities for CTCC case study scenario runners."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
YAMLS_DIR = REPO_ROOT / "yamls"
SCENARIOS_DIR = REPO_ROOT / "scenarios"

_YAML_STEMS = [
    "01_project_technical_details",
    "02_project_physical_details",
    "03_financing",
    "04_insurance",
    "05_delays",
    "06_wildfire_costs",
    "07_outage_costs",
    "08_environmental_reporting(couldbeuseless)",
    "09_environmental_mitigation",
    "10_project_category_build_costs",
    "11_project_row_details",
    "12_project_om_vegetation_management",
    "13_category_om_conductors",
    "14_category_om_structures",
    "15_category_om_converters",
    "16_emissions_reductions",
    "17_congestion_curtailment_reductions",
    "18_energy_source_mix",
    "19_cost_timing_patterns",
    "20_project_category_row_widths",
    "21_project_category_circuit_and_resistance_detail",
]


def build_default_inputs() -> dict[str, Any]:
    """Build a complete CTCC input dict from the canonical repo YAML defaults.

    Returns the same dict structure that a .ctcc file's "inputs" key contains:
    keys are YAML filenames without extension, values are the parsed YAML content.
    """
    inputs: dict[str, Any] = {}
    for stem in _YAML_STEMS:
        yaml_path = YAMLS_DIR / f"{stem}.yaml"
        with open(yaml_path) as f:
            inputs[stem] = yaml.safe_load(f)
    return inputs


def run_scenario(inputs: dict, scenario_id: str) -> dict:
    """Run a single scenario through the CTCC calculation engine."""
    from ctcc import run_calculation

    return run_calculation(
        combined_data=inputs,
        scenario_id=scenario_id,
        quiet=True,
    )


def save_ctcc_file(
    inputs: dict, results: dict, name: str, scenario_id: str, source: str = "case_study"
) -> Path:
    """Save a complete .ctcc file with inputs, results, and metadata."""
    ctcc = {
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
    out_path = SCENARIOS_DIR / f"{name}.ctcc"
    with open(out_path, "w") as f:
        json.dump(ctcc, f, indent=2, default=str)
    print(f"  Saved: {out_path}")
    return out_path


def fmt(val: float, prefix: str = "$") -> str:
    """Format large numbers with B/M suffixes."""
    if abs(val) >= 1e9:
        return f"{prefix}{val/1e9:.2f}B"
    elif abs(val) >= 1e6:
        return f"{prefix}{val/1e6:.1f}M"
    else:
        return f"{prefix}{val:,.0f}"
