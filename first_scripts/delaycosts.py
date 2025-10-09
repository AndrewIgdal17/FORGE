#Author: Andrew Igdal
# Date: 10/2/2025
# Description: This script calculates the cost of delays in the construction of a transmission project.

import pandas as pd
import numpy as np
import sys
import os
import yaml

# Load configuration from YAML file
config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'project_config.yaml')
with open(config_path, 'r') as file:
    config = yaml.safe_load(file)

# Extract delay timeline from AFUDC config (shared parameter)
delay_timeline = config['afudc']['delay_timeline']

# Extract firm interest rate for present value calculation
firm_interest_rate = config['financial']['firm_interest_rate']

# Extract delay costs
delay_costs_config = config['delay_costs']['annual_costs']
legal_delay_costs = delay_costs_config['legal']
administrative_overhead_delay_costs = delay_costs_config['administrative_overhead']
engineering_delay_costs = delay_costs_config['engineering']
permitting_delay_costs = delay_costs_config['permitting']
material_and_equipment_delay_costs = delay_costs_config['material_and_equipment']
labor_delay_costs = delay_costs_config['labor']
public_relations_delay_costs = delay_costs_config['public_relations']
environmental_delay_costs = delay_costs_config['environmental']
miscellaneous_delay_costs = delay_costs_config['miscellaneous']

# Total Delay Costs
total_delay_costs = (legal_delay_costs + administrative_overhead_delay_costs + engineering_delay_costs + permitting_delay_costs + 
                    material_and_equipment_delay_costs + labor_delay_costs + public_relations_delay_costs + environmental_delay_costs + miscellaneous_delay_costs)  

t = np.arange(1, delay_timeline + 1)

# Present Value of Total Delay Costs
present_value_total_delay_costs = np.sum(total_delay_costs * (1 / (1 + firm_interest_rate) ** t))

print("================================================================")
print("Annual delay costs: ", total_delay_costs)
print("Present value of total delay costs: ", present_value_total_delay_costs)
print("================================================================")