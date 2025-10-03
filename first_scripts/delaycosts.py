#Author: Andrew Igdal
# Date: 10/2/2025
# Description: This script calculates the cost of delays in the construction of a transmission project.

import pandas as pd
import numpy as np
import sys
import os

# Timeline
delay_timeline = float(input("Delay timeline in years: "))

#Delay cost categories

# Legal Delay Costs
legal_delay_costs = float(input("Legal delay costs in USD: "))

#Administrative Overhead Delay Costs
administrative_overhead_delay_costs = float(input("Administrative overhead delay costs in USD: "))

# Engineering Delay Costs
engineering_delay_costs = float(input("Engineering delay costs in USD: "))

# Permitting and Regulatory Compliance Delay Costs
permitting_delay_costs = float(input("Permitting delay costs in USD: "))

# Material and Equipment Delay Costs
material_and_equipment_delay_costs = float(input("Material and equipment delay costs in USD: "))

# Labor Delay Costs
labor_delay_costs = float(input("Labor delay costs in USD: "))

# Public Relations Delay Costs
public_relations_delay_costs = float(input("Public relations delay costs in USD: "))

# Environmental Delay Costs
environmental_delay_costs = float(input("Environmental delay costs in USD: "))

# Miscellaneous Delay Costs
miscellaneous_delay_costs = float(input("Miscellaneous delay costs in USD: "))

# Total Delay Costs
total_delay_costs = (legal_delay_costs + administrative_overhead_delay_costs + financial_delay_costs + engineering_delay_costs + permitting_delay_costs + 
                    material_and_equipment_delay_costs + labor_delay_costs + public_relations_delay_costs + environmental_delay_costs + miscellaneous_delay_costs)  

t = np.arange(1, delay_timeline + 1)

# Present Value of Total Delay Costs
present_value_total_delay_costs = np.sum(total_delay_costs * (1 / (1 + firm_interest_rate) ** t))

print("================================================================")
print("Annual delay costs: ", total_delay_costs)
print("Present value of total delay costs: ", present_value_total_delay_costs)
print("================================================================")