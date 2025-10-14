#Author: Andrew Igdal
# Date: 10/10/2025
# Description: This script calculates the terrain adjusted build cost for a transmission project.

import pandas as pd
import numpy as np

import sys
import os
import yaml

# Load configuration from YAML file
config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'project_config.yaml')
with open(config_path, 'r') as file:
    config = yaml.safe_load(file)

# Extract terrain miles
terrain_miles = config['terrain']['miles']

# Extract terrain multipliers
terrain_multipliers = config['terrain']['multipliers']

# Calculate terrain adjusted build cost
terrain_adjuster = sum(terrain_miles[terrain] * terrain_multipliers[terrain] for terrain in terrain_miles)/sum(terrain_miles.values())

# Print terrain adjusted build cost
print("================================================================")
print("Terrain Adjusted Build Cost: ", terrain_adjuster)
print("================================================================")
