#Author: Andrew Igdal
# Date: 10/10/2025
# Description: This script calculates the benefit of curtailment reduction through a new project.

import pandas as pd
import numpy as np
import sys
import os
import yaml

# Load configuration from YAML file
config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'project_config.yaml')
with open(config_path, 'r') as file:
    config = yaml.safe_load(file)

