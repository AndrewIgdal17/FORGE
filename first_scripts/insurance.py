#Author: Andrew Igdal
# Date: 10/2/2025
# Description: This script calculates the cost of insurance in nominal and real terms for transmission project annually, and over the project's lifetime.

import pandas as pd
import numpy as np
import sys
import os


#Infrastructure cost inputs
conductor_cost = float(input("Conductor cost in USD: "))
structure_cost = float(input("Structure cost in USD: "))
converter_cost = float(input("Converter cost in USD: "))

#Binary variable for converter presence
phi_converter = int(input("Phi converter (0 = no converter (AC Project), 1 = converter (DC Project)): "))

#Interest rate inputs
firm_interest_rate = float(input("Interest rate in decimal: "))
risk_free_interest_rate = float(input("Risk-free interest rate in decimal: "))

#Project lifetime input
project_lifetime = int(input("Project lifetime in years: "))

# Insurrance premium input
insurance_premium = float(input("Insurance premium in decimal: "))

# Length of project
project_length = float(input("Length of project in miles: "))

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