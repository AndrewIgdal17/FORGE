#Author: Andrew Igdal
# Date: 10/2/2025
# Description: This script calculates the environmental impact mitigation costs for transmission projects based on terrain types and miles.

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
project_lifetime = config['financial']['project_lifetime']

# Extract terrain miles
terrain_miles = config['terrain']['miles']
forested_miles = terrain_miles['forested']
scrubbed_flat_miles = terrain_miles['scrubbed_flat']
wetland_miles = terrain_miles['wetland']
farmland_miles = terrain_miles['farmland']
desert_barren_miles = terrain_miles['desert_barren']
urban_miles = terrain_miles['urban']
rolling_hills_miles = terrain_miles['rolling_hills']
mountain_miles = terrain_miles['mountain']
subsea_miles = terrain_miles['subsea']

# Extract environmental mitigation costs per mile
mitigation_costs = config['environmental_mitigation']['cost_per_mile']
forested_cost_per_mile = mitigation_costs['forested']
scrubbed_flat_cost_per_mile = mitigation_costs['scrubbed_flat']
wetland_cost_per_mile = mitigation_costs['wetland']
farmland_cost_per_mile = mitigation_costs['farmland']
desert_barren_cost_per_mile = mitigation_costs['desert_barren']
urban_cost_per_mile = mitigation_costs['urban']
rolling_hills_cost_per_mile = mitigation_costs['rolling_hills']
mountain_cost_per_mile = mitigation_costs['mountain']
subsea_cost_per_mile = mitigation_costs['subsea']

# Calculate total environmental mitigation costs by terrain type
forested_total_cost = forested_miles * forested_cost_per_mile
scrubbed_flat_total_cost = scrubbed_flat_miles * scrubbed_flat_cost_per_mile
wetland_total_cost = wetland_miles * wetland_cost_per_mile
farmland_total_cost = farmland_miles * farmland_cost_per_mile
desert_barren_total_cost = desert_barren_miles * desert_barren_cost_per_mile
urban_total_cost = urban_miles * urban_cost_per_mile
rolling_hills_total_cost = rolling_hills_miles * rolling_hills_cost_per_mile
mountain_total_cost = mountain_miles * mountain_cost_per_mile
subsea_total_cost = subsea_miles * subsea_cost_per_mile



# Total project miles
total_project_miles = (forested_miles + scrubbed_flat_miles + wetland_miles + 
                      farmland_miles + desert_barren_miles + urban_miles + 
                      rolling_hills_miles + mountain_miles + subsea_miles)

# Total environmental mitigation cost
total_environmental_mitigation_cost = (forested_total_cost + scrubbed_flat_total_cost + 
                                     wetland_total_cost + farmland_total_cost + 
                                     desert_barren_total_cost + urban_total_cost + 
                                     rolling_hills_total_cost + mountain_total_cost + 
                                     subsea_total_cost) * project_lifetime

# Present Value of Total Environmental Mitigation Costs
t = np.arange(1, project_lifetime + 1)
present_value_total_environmental_mitigation_cost = np.sum(total_environmental_mitigation_cost * (1 / (1 + firm_interest_rate) ** t))

print("================================================================")
print("ENVIRONMENTAL IMPACT MITIGATION COST BREAKDOWN")
print("================================================================")
print(f"Forested terrain: {forested_miles:.2f} miles × ${forested_cost_per_mile:,.2f} = ${forested_total_cost:,.2f}")
print(f"Scrubbed/Flat terrain: {scrubbed_flat_miles:.2f} miles × ${scrubbed_flat_cost_per_mile:,.2f} = ${scrubbed_flat_total_cost:,.2f}")
print(f"Wetland terrain: {wetland_miles:.2f} miles × ${wetland_cost_per_mile:,.2f} = ${wetland_total_cost:,.2f}")
print(f"Farmland terrain: {farmland_miles:.2f} miles × ${farmland_cost_per_mile:,.2f} = ${farmland_total_cost:,.2f}")
print(f"Desert/Barren Land terrain: {desert_barren_miles:.2f} miles × ${desert_barren_cost_per_mile:,.2f} = ${desert_barren_total_cost:,.2f}")
print(f"Urban terrain: {urban_miles:.2f} miles × ${urban_cost_per_mile:,.2f} = ${urban_total_cost:,.2f}")
print(f"Rolling Hills terrain: {rolling_hills_miles:.2f} miles × ${rolling_hills_cost_per_mile:,.2f} = ${rolling_hills_total_cost:,.2f}")
print(f"Mountain terrain: {mountain_miles:.2f} miles × ${mountain_cost_per_mile:,.2f} = ${mountain_total_cost:,.2f}")
print(f"Subsea terrain: {subsea_miles:.2f} miles × ${subsea_cost_per_mile:,.2f} = ${subsea_total_cost:,.2f}")
print("================================================================")
print(f"Total project miles: {total_project_miles:.2f}")
print(f"Total environmental mitigation cost: ${total_environmental_mitigation_cost:,.2f}")
print(f"Present value of total environmental mitigation cost: ${present_value_total_environmental_mitigation_cost:,.2f}")
print("================================================================")
