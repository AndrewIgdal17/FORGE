# Date: 2025-10-20
# Description: This script calculates the weighted miles of a transmission line.

from __future__ import annotations

import logging

import pandas as pd
import numpy as np
import argparse
from typing import Tuple
from forge.scripts.utils.inputs import section
from .run_context import get_run_context

logger = logging.getLogger(__name__)


def calculate_weighted_miles() -> Tuple[float, float]:
    """
    Calculate weighted miles and average terrain multiplier from project physical details.

    From yaml 02_project_physical_details.yaml, get the miles of the transmission line in each terrain type.
    terrain_miles and terrain_multipliers are in project_physical_details_df, both contained under terrain.
    To get weighted miles, multiply terrain_miles[terrain_type] by terrain_multipliers[terrain_type]

    Returns:
        tuple: (weighted_miles, average_terrain_multiplier)
    """
    ctx = get_run_context()
    if ctx is not None:
        return ctx.weighted_miles, ctx.average_terrain_multiplier

    project_physical_details_df = section("02_project_physical_details")
    if not project_physical_details_df:
        raise ValueError("Physical details YAML file is empty or invalid")

    # terrain_miles and terrain_multipliers are in project_physical_details_df, both contained under terrain.
    # To get weighted miles, multiply terrain_miles[terrain_type] by terrain_multipliers[terrain_type]

    weighted_miles = 0

    for terrain_type, terrain_miles in project_physical_details_df["terrain"][
        "terrain_miles"
    ].items():
        if terrain_miles is None:  # Handle None values
            terrain_miles = 0
        weighted_miles += (
            terrain_miles
            * project_physical_details_df["terrain"]["terrain_multipliers"][
                terrain_type
            ]
        )

    total_miles = sum(
        project_physical_details_df["terrain"]["terrain_miles"].values()
    )
    if total_miles == 0:
        average_terrain_multiplier = 0.0
    else:
        average_terrain_multiplier = weighted_miles / total_miles

    return weighted_miles, average_terrain_multiplier


def main() -> None:
    """Entry point for orchestrator or standalone run."""
    weighted_miles, average_terrain_multiplier = calculate_weighted_miles()
    logger.info(weighted_miles)
    logger.info(average_terrain_multiplier)




# =============================================================================
# DETAILED SYNTAX EXPLANATION
# =============================================================================
#
# Let's break down exactly how the weighted miles calculation works:
#
# 1. DICTIONARY ITERATION:
#    for terrain_type, terrain_miles in project_physical_details_df['terrain']['terrain_miles'].items():
#
#    - project_physical_details_df['terrain']['terrain_miles'] is a dictionary like:
#      {'forested': 25, 'scrubbed_flat': 35, 'wetland': 5, ...}
#
#    - .items() returns key-value pairs: ('forested', 25), ('scrubbed_flat', 35), etc.
#
#    - The loop unpacks each pair: terrain_type = 'forested', terrain_miles = 25
#
# 2. MULTIPLICATION AND ACCUMULATION:
#    weighted_miles += terrain_miles * project_physical_details_df['terrain']['terrain_multipliers'][terrain_type]
#
#    - terrain_miles is the value from terrain_miles dictionary (e.g., 25 for forested)
#
#    - project_physical_details_df['terrain']['terrain_multipliers'][terrain_type]
#      uses terrain_type as a key to get the corresponding multiplier
#      (e.g., if terrain_type = 'forested', this gets 2.25)
#
#    - The multiplication: 25 * 2.25 = 56.25
#
#    - += adds this result to weighted_miles (running total)
#
# 3. EXAMPLE ITERATION:
#    First iteration: terrain_type='forested', terrain_miles=25
#    Calculation: 25 * 2.25 = 56.25
#    weighted_miles = 0 + 56.25 = 56.25
#
#    Second iteration: terrain_type='scrubbed_flat', terrain_miles=35
#    Calculation: 35 * 1.0 = 35.0
#    weighted_miles = 56.25 + 35.0 = 91.25
#
#    And so on for each terrain type...
#
# =============================================================================
