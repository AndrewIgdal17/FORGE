#Author: Andrew Igdal
# Date: 10/6/2025
# Description: This script calculates the cost of environmental reporting and compliance in the construction of a transmission project.

import pandas as pd
import numpy as np
import sys
import os


# Reporting and compliance costs
EIS_cost = float(input("EIS cost in USD: "))
EIR_cost = float(input("EIR cost in USD: "))
NEPA_cost = float(input("NEPA cost in USD: "))
NHPA_cost = float(input("NHPA cost in USD: "))

# Total reporting and compliance costs
total_reporting_and_compliance_costs = EIS_cost + EIR_cost + NEPA_cost + NHPA_cost

print("================================================================")
print("Total reporting and compliance costs: ", total_reporting_and_compliance_costs)
print("================================================================")