"""FORGE — Framework for Open Reproducible Grid Economics."""

from forge.core import run_calculation, write_final_json_output, main
from forge.data import get_yamls_path, get_scenarios_path, get_defaults_template
from forge.contract import (
    calculator_info,
    canonical_dumps,
    diff_changes,
    get_defaults_id,
    resolve_inputs,
    validate_changes,
)
from forge.errors import UnknownInputPath, InvalidInputs, CalculationError
from forge.presets import get_grid_mix_presets

__all__ = [
    "run_calculation",
    "write_final_json_output",
    "main",
    "get_yamls_path",
    "get_scenarios_path",
    "get_defaults_template",
    "canonical_dumps",
    "get_defaults_id",
    "resolve_inputs",
    "validate_changes",
    "diff_changes",
    "calculator_info",
    "get_grid_mix_presets",
    "UnknownInputPath",
    "InvalidInputs",
    "CalculationError",
]

import logging

logging.getLogger("forge").addHandler(logging.NullHandler())
