#Author: Andrew Igdal
# Date: 10/2/2025
# Description: This script calculates the environmental impact mitigation costs for transmission projects based on terrain types and miles.

import pandas as pd
import numpy as np
import sys
import os

# Interest rate inputs
firm_interest_rate = float(input("Interest rate in decimal: "))

# Project lifetime input
project_lifetime = int(input("Project lifetime in years: "))

# Terrain type and miles inputs
forested_miles = float(input("Forested terrain miles: "))
scrubbed_flat_miles = float(input("Scrubbed/Flat terrain miles: "))
wetland_miles = float(input("Wetland terrain miles: "))
farmland_miles = float(input("Farmland terrain miles: "))
desert_barren_miles = float(input("Desert/Barren Land terrain miles: "))
urban_miles = float(input("Urban terrain miles: "))
rolling_hills_miles = float(input("Rolling Hills (2-8% Slope) terrain miles: "))
mountain_miles = float(input("Mountain (>8% Slope) terrain miles: "))
subsea_miles = float(input("Subsea terrain miles: "))

# Environmental mitigation cost per mile by terrain type (USD per mile)
forested_cost_per_mile = float(input("Environmental mitigation cost per mile for Forested terrain (USD): "))
scrubbed_flat_cost_per_mile = float(input("Environmental mitigation cost per mile for Scrubbed/Flat terrain (USD): "))
wetland_cost_per_mile = float(input("Environmental mitigation cost per mile for Wetland terrain (USD): "))
farmland_cost_per_mile = float(input("Environmental mitigation cost per mile for Farmland terrain (USD): "))
desert_barren_cost_per_mile = float(input("Environmental mitigation cost per mile for Desert/Barren Land terrain (USD): "))
urban_cost_per_mile = float(input("Environmental mitigation cost per mile for Urban terrain (USD): "))
rolling_hills_cost_per_mile = float(input("Environmental mitigation cost per mile for Rolling Hills terrain (USD): "))
mountain_cost_per_mile = float(input("Environmental mitigation cost per mile for Mountain terrain (USD): "))
subsea_cost_per_mile = float(input("Environmental mitigation cost per mile for Subsea terrain (USD): "))

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

# Total environmental mitigation cost
total_environmental_mitigation_cost = (forested_total_cost + scrubbed_flat_total_cost + 
                                     wetland_total_cost + farmland_total_cost + 
                                     desert_barren_total_cost + urban_total_cost + 
                                     rolling_hills_total_cost + mountain_total_cost + 
                                     subsea_total_cost)

# Total project miles
total_project_miles = (forested_miles + scrubbed_flat_miles + wetland_miles + 
                      farmland_miles + desert_barren_miles + urban_miles + 
                      rolling_hills_miles + mountain_miles + subsea_miles)

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
