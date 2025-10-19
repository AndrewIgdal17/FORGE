#Author: Andrew Igdal
# Date: 10/6/2025
# Description: This script calculates the cost of environmental reporting and compliance in the construction of a transmission project.

import pandas as pd
import numpy as np
import sys
import os
import yaml

# Load configuration from YAML file
config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'project_config.yaml')
with open(config_path, 'r') as file:
    config = yaml.safe_load(file)

# Extract environmental reporting costs
env_reporting_config = config['environmental_reporting']
EIS_cost = env_reporting_config['EIS_cost']
EIR_cost = env_reporting_config['EIR_cost']
NEPA_cost = env_reporting_config['NEPA_cost']
NHPA_cost = env_reporting_config['NHPA_cost']

# Total reporting and compliance costs
total_reporting_and_compliance_costs = EIS_cost + EIR_cost + NEPA_cost + NHPA_cost

print("================================================================")
print("Total reporting and compliance costs: ", total_reporting_and_compliance_costs)
print("================================================================")