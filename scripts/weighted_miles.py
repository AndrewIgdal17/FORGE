# Author: Andrew Igdal
# Date: 2025-10-20
# Description: This script calculates the weighted miles of a transmission line.

from __future__ import annotations

import pandas as pd
import yaml
import numpy as np
import argparse
from typing import Tuple
from path_config import YAMLS_DIR


def calculate_weighted_miles() -> Tuple[float, float]:
    """
    Calculate weighted miles and average terrain multiplier from project physical details.

    From yaml 02_project_physical_details.yaml, get the miles of the transmission line in each terrain type.
    terrain_miles and terrain_multipliers are in project_physical_details_df, both contained under terrain.
    To get weighted miles, multiply terrain_miles[terrain_type] by terrain_multipliers[terrain_type]

    Returns:
        tuple: (weighted_miles, average_terrain_multiplier)
    """
    # From yaml 02_project_physical_details.yaml, get the miles of the transmission line in each terrain type
    try:
        with open(
            YAMLS_DIR / "02_project_physical_details.yaml", "r"
        ) as project_physical_details_file:
            project_physical_details_df = yaml.safe_load(project_physical_details_file)
        if not project_physical_details_df:
            raise ValueError("Physical details YAML file is empty or invalid")
    except FileNotFoundError:
        raise FileNotFoundError(
            f"Physical details YAML not found at {YAMLS_DIR / '02_project_physical_details.yaml'}"
        )
    except yaml.YAMLError as e:
        raise ValueError(f"Error parsing physical details YAML: {e}")

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


if __name__ == "__main__":
    weighted_miles, average_terrain_multiplier = calculate_weighted_miles()
    print(weighted_miles)
    print(average_terrain_multiplier)


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
