# Author: Andrew Igdal
# Date: 2025-10-20
# Description: This script calculates the right-of-way costs for a transmission line.

import pandas as pd
import yaml
import numpy as np
import argparse

# From yaml 11_project_row_details.yaml, get the miles of the transmission line in each terrain type



# The categories that store the row widths are based on the project techincal details in yamls/01_project_technical_details.yaml
# specifically they are "construction_type\AC or DC\capacity MW\conductor type\converter type
# example an AC overhead 140 MW standard aluminum conductor no converter would be "Overhead/AC/140MW/Standard Aluminum Conductor/NA"
# Row widths given a certain category are in yamls/20_project_category_row_widths.yaml
# The number of miles (not the weighted miles) of the line are given in yamls/02_project_physical_details.yaml
# The costs of ROw acquistion, rent and holding are in yamls/11_project_row_details.yaml
# To get the real values we need to pull from yamls/03_financing.yaml


with open('../yamls/01_project_technical_details.yaml', 'r') as project_technical_details_file:
    project_technical_details_df = yaml.load(project_technical_details_file, Loader=yaml.FullLoader)
    construction_type = project_technical_details_df['project']['construction_type']
    ac_dc = project_technical_details_df['project']['ac_dc']
    capacity_mw = project_technical_details_df['project']['capacity_mw'] # need to add the suffix MW
    capacity_mw = f"{capacity_mw}MW"
    conductor_type = project_technical_details_df['project']['conductor_type'] # need to add the suffix Conductor
    conductor_type = f"{conductor_type}"
    converter_type = project_technical_details_df['project']['converter_type']

    category = f"{construction_type}/{ac_dc}/{capacity_mw}/{conductor_type}/{converter_type}"

    delay_year = project_technical_details_df['timeline']['delay_years']
    construction_years = project_technical_details_df['timeline']['construction_years']
    project_lifetime = project_technical_details_df['timeline']['project_lifetime']

with open('../yamls/20_project_category_row_widths.yaml', 'r') as project_category_row_widths_file:
    project_category_row_widths_df = yaml.load(project_category_row_widths_file, Loader=yaml.FullLoader)

    row_width_feet = project_category_row_widths_df[category]['row_width_feet']

with open('../yamls/02_project_physical_details.yaml', 'r') as project_physical_details_file:
    project_physical_details_df = yaml.load(project_physical_details_file, Loader=yaml.FullLoader)
# have to sum the miles of the line in each terrain type to get the total miles of the line
    total_miles = sum(project_physical_details_df['terrain']['terrain_miles'].values())


with open('../yamls/11_project_row_details.yaml', 'r') as project_row_details_file:
    project_row_details_df = yaml.load(project_row_details_file, Loader=yaml.FullLoader)

    acquisition_cost = project_row_details_df[category]['acquisition_cost']
    rent_cost = project_row_details_df[category]['rent_cost']
    hold_cost = project_row_details_df[category]['hold_cost']


with open('../yamls/03_financing.yaml', 'r') as financing_file:
    financing_df = yaml.load(financing_file, Loader=yaml.FullLoader)
    
    inflation_rate = financing_df['financial']['inflation_rate']
    base_year = financing_df['financial']['base_year']
    wacc_nominal = financing_df['financial']['wacc_nominal']

    # use fisher link to get real wacc 
    wacc_real = (1 + wacc_nominal) / (1 + inflation_rate) - 1
    
# First we need to convert the miles of the line given a width to acres
# We do this by taking the width, finding the area in feet of one mile of ROW, then convertig to acres
# then multiplying by the miles of the line (this doesnt vary by terrain type)

one_mile_of_row_in_feet = row_width_feet * 5280
one_mile_of_row_in_acres = one_mile_of_row_in_feet / 43560
total_acres = one_mile_of_row_in_acres * total_miles


# Holding costs are $ / acre * delay year (typically the $ / acre is .1 of the rent cost per year) so we 
# need to multiply the acres of ROW by the $/ acre of holding for per delay year holding
# then multiply by the number of delay years to get the total holding costs.
yearly_holding_cost = hold_cost * total_acres
total_holding_cost = yearly_holding_cost * delay_year

# Acquistion costs are $/acre so we need to multiply the acres of ROW by the acquistion cost per acre.
total_acquisition_cost = acquisition_cost * total_acres


# Rent costs are $ / acre * year so we need to multiply the acres of ROW by the rent cost per acre per year 
# for the per year rent cost. THen multiply by the number of years of rent (project lifeitme + construction years).
yearly_rent_cost = rent_cost * total_acres
total_rent_cost = yearly_rent_cost * (project_lifetime + construction_years)

rent_start_year = delay_year + 1
rent_total_years = project_lifetime + construction_years

# Now we need to get the present value of holding, acquisition, and rent costs.
def calculate_present_value(annual_cost, wacc_real, total_years, start_year = 1):
    "Gets the PV of payments over a given time period"
    total_pv = 0
    for year in range(start_year, start_year + total_years):
        total_pv += annual_cost / (1 + wacc_real) ** year
    return total_pv

total_holding_cost_pv = calculate_present_value(yearly_holding_cost, wacc_real, delay_year) # Holding costs are incurred annually throughout the delay period.
total_acquisition_cost_pv = total_acquisition_cost / (1 + wacc_real) ** delay_year # Aquistion costs discounted as a bulk payment incurred right at the end of the delay period.
total_rent_cost_pv = calculate_present_value(yearly_rent_cost, wacc_real, rent_total_years, rent_start_year) # Rent costs are incurred annually throughout the rent period.






# it so weird as I write and see the autocomplete make suggestions and theyre going the right direction but then I am not 
# thinking I'm just reading and knowing that it is suggesting what I was going to think of but am not yet thinking it. SO
# when I write (not code) but thoguhts I need to iignore the autocomplete suggestions and just think them through. Lol.


