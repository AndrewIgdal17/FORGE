#Author: Andrew Igdal
# Date: 10/2/2025
# Description: This script calculates the cost of insurance in nominal and real terms for transmission project annually, and over the project's lifetime.

import pandas as pd
import numpy as np
import sys
import os
import yaml

# Load configuration from YAML file
config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'project_config.yaml')
with open(config_path, 'r') as file:
    config = yaml.safe_load(file)

# Extract financial parameters
firm_interest_rate = config['financial']['firm_interest_rate']
risk_free_interest_rate = config['financial']['risk_free_interest_rate']
project_lifetime = config['financial']['project_lifetime']

# Extract project length (total miles from terrain configuration)
terrain_miles = config['terrain']['miles']
project_length = sum(terrain_miles.values())

# Extract insurance configuration
insurance_config = config['insurance']
insurance_premium = insurance_config['premium_rate']
infrastructure_costs = insurance_config['infrastructure_costs']
conductor_cost = infrastructure_costs['conductor_per_mile']
structure_cost = infrastructure_costs['structure_per_mile']
converter_cost = infrastructure_costs['converter_total']
phi_converter = 1 if insurance_config['has_converter'] else 0

# annual payment
mile_line_payment_ = (conductor_cost + structure_cost) * insurance_premium
line_payment = mile_line_payment_ * project_length

converter_payment = converter_cost * insurance_premium * phi_converter

# total annual payment
total_annual_payment = line_payment + converter_payment

# total project lifetime payment
total_lifetime_payment = total_annual_payment * project_lifetime


# present value of total project lifetime payment to the firm 

t = np.arange(1, project_lifetime + 1)

present_value_total_lifetime_payment = np.sum(total_annual_payment * (1 / (1 + firm_interest_rate) ** t))


print("================================================================")
print("Annual insurance cost: ", total_annual_payment)
print("Total project lifetime insurance cost: ", total_lifetime_payment)
print("Present value of total project lifetime insurance cost to the firm: ", present_value_total_lifetime_payment)
print("================================================================")