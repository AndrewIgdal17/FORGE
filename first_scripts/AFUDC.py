#Author: Andrew Igdal
# Date: 10/08/2025
# Description: This script calculates the cost of AFUDC in the construction of a transmission project.

import pandas as pd
import numpy as np
import sys
import os

#Terrain adjusted build cost
terrain_adjusted_build_cost = float(input("Terrain adjusted build cost in USD: "))

#Construction and delaytimeline
construction_timeline = float(input("Construction timeline in years: "))
delay_timeline = float(input("Delay timeline in years: "))


#Funding types and % of funding
short_term_debt_% = float(input("Short-term debt %: "))
long_term_debt_% = float(input("Long-term debt %: "))
preferred_stock_% = float(input("Preferred stock %: "))
common_stock_% = float(input("Common stock %: "))
internal_reserves_% = float(input("Internal reserves %: "))

#Funding types and rates
short_term_debt_rate = float(input("Short-term debt rate in decimal: "))
long_term_debt_rate = float(input("Long-term debt rate in decimal: "))
preferred_stock_rate = float(input("Preferred stock rate in decimal: "))
common_stock_rate = float(input("Common stock rate in decimal: "))
internal_reserves_rate = float(input("Internal reserves rate in decimal: "))

# Funding types and changes to rates of delay years

short_term_debt_rate_change = float(input("Short-term debt rate change in decimal: "))
long_term_debt_rate_change = float(input("Long-term debt rate change in decimal: "))
preferred_stock_rate_change = float(input("Preferred stock rate change in decimal: "))
common_stock_rate_change = float(input("Common stock rate change in decimal: "))
internal_reserves_rate_change = float(input("Internal reserves rate change in decimal: "))

# Final rates
short_term_debt_rate_final = short_term_debt_rate * (1 + short_term_debt_rate_change * delay_timeline)
long_term_debt_rate_final = long_term_debt_rate * (1 + long_term_debt_rate_change * delay_timeline)
preferred_stock_rate_final = preferred_stock_rate * (1 + preferred_stock_rate_change * delay_timeline)
common_stock_rate_final = common_stock_rate * (1 + common_stock_rate_change * delay_timeline)
internal_reserves_rate_final = internal_reserves_rate * (1 + internal_reserves_rate_change * delay_timeline)

# Amount funded by each type of funding
short_term_debt_amount = short_term_debt_% * terrain_adjusted_build_cost
long_term_debt_amount = long_term_debt_% * terrain_adjusted_build_cost
preferred_stock_amount = preferred_stock_% * terrain_adjusted_build_cost
common_stock_amount = common_stock_% * terrain_adjusted_build_cost
internal_reserves_amount = internal_reserves_% * terrain_adjusted_build_cost

# Total amount funded
total_amount_funded = short_term_debt_amount + long_term_debt_amount + preferred_stock_amount + common_stock_amount + internal_reserves_amount

# Weighted cost
short_term_debt_weighted_cost_% = short_term_debt_% * short_term_debt_rate_final
long_term_debt_weighted_cost_% = long_term_debt_% * long_term_debt_rate_final
preferred_stock_weighted_cost_% = preferred_stock_% * preferred_stock_rate_final
common_stock_weighted_cost_% = common_stock_% * common_stock_rate_final
internal_reserves_weighted_cost_% = internal_reserves_% * internal_reserves_rate_final

# Total weighted cost
total_weighted_cost_of_capital = short_term_debt_weighted_cost_% + long_term_debt_weighted_cost_% + preferred_stock_weighted_cost_% + common_stock_weighted_cost_% + internal_reserves_weighted_cost_%

# AFUDC
afudc = terrain_adjusted_build_cost * ((1+total_weighted_cost_of_capital)**construction_timeline - 1)