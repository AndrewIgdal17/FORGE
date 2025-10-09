#Author: Andrew Igdal
# Date: 10/08/2025
# Description: This script calculates the cost of AFUDC in the construction of a transmission project.

import pandas as pd
import numpy as np
import sys
import os
import yaml

# Load configuration from YAML file
config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'project_config.yaml')
with open(config_path, 'r') as file:
    config = yaml.safe_load(file)

# Extract AFUDC parameters
afudc_config = config['afudc']
terrain_adjusted_build_cost = afudc_config['terrain_adjusted_build_cost']
construction_timeline = afudc_config['construction_timeline']
delay_timeline = afudc_config['delay_timeline']

# Extract funding percentages
funding_percentages = afudc_config['funding_percentages']
short_term_debt_pct = funding_percentages['short_term_debt']
long_term_debt_pct = funding_percentages['long_term_debt']
preferred_stock_pct = funding_percentages['preferred_stock']
common_stock_pct = funding_percentages['common_stock']
internal_reserves_pct = funding_percentages['internal_reserves']

# Extract initial funding rates
funding_rates = afudc_config['funding_rates']
short_term_debt_rate = funding_rates['short_term_debt']
long_term_debt_rate = funding_rates['long_term_debt']
preferred_stock_rate = funding_rates['preferred_stock']
common_stock_rate = funding_rates['common_stock']
internal_reserves_rate = funding_rates['internal_reserves']

# Extract rate changes
rate_changes = afudc_config['rate_changes']
short_term_debt_rate_change = rate_changes['short_term_debt']
long_term_debt_rate_change = rate_changes['long_term_debt']
preferred_stock_rate_change = rate_changes['preferred_stock']
common_stock_rate_change = rate_changes['common_stock']
internal_reserves_rate_change = rate_changes['internal_reserves']

# Final rates
short_term_debt_rate_final = short_term_debt_rate * (1 + short_term_debt_rate_change * delay_timeline)
long_term_debt_rate_final = long_term_debt_rate * (1 + long_term_debt_rate_change * delay_timeline)
preferred_stock_rate_final = preferred_stock_rate * (1 + preferred_stock_rate_change * delay_timeline)
common_stock_rate_final = common_stock_rate * (1 + common_stock_rate_change * delay_timeline)
internal_reserves_rate_final = internal_reserves_rate * (1 + internal_reserves_rate_change * delay_timeline)

# Amount funded by each type of funding
short_term_debt_amount = short_term_debt_pct * terrain_adjusted_build_cost
long_term_debt_amount = long_term_debt_pct * terrain_adjusted_build_cost
preferred_stock_amount = preferred_stock_pct * terrain_adjusted_build_cost
common_stock_amount = common_stock_pct * terrain_adjusted_build_cost
internal_reserves_amount = internal_reserves_pct * terrain_adjusted_build_cost

# Total amount funded
total_amount_funded = short_term_debt_amount + long_term_debt_amount + preferred_stock_amount + common_stock_amount + internal_reserves_amount

# Weighted cost
short_term_debt_weighted_cost_pct = short_term_debt_pct * short_term_debt_rate_final
long_term_debt_weighted_cost_pct = long_term_debt_pct * long_term_debt_rate_final
preferred_stock_weighted_cost_pct = preferred_stock_pct * preferred_stock_rate_final
common_stock_weighted_cost_pct = common_stock_pct * common_stock_rate_final
internal_reserves_weighted_cost_pct = internal_reserves_pct * internal_reserves_rate_final

# Total weighted cost
total_weighted_cost_of_capital = short_term_debt_weighted_cost_pct + long_term_debt_weighted_cost_pct + preferred_stock_weighted_cost_pct + common_stock_weighted_cost_pct + internal_reserves_weighted_cost_pct

# AFUDC
afudc = terrain_adjusted_build_cost * ((1+total_weighted_cost_of_capital)**construction_timeline - 1)

print("================================================================")
print("AFUDC CALCULATION RESULTS")
print("================================================================")
print(f"Terrain adjusted build cost: ${terrain_adjusted_build_cost:,.2f}")
print(f"Construction timeline: {construction_timeline} years")
print(f"Delay timeline: {delay_timeline} years")
print(f"Total weighted cost of capital: {total_weighted_cost_of_capital:.4f} ({total_weighted_cost_of_capital*100:.2f}%)")
print(f"AFUDC: ${afudc:,.2f}")
print("================================================================")