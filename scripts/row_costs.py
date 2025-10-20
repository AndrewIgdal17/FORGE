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


with open('../yamls/01_project_technical_details.yaml', 'r') as project_technical_details_file:
    project_technical_details_df = yaml.load(project_technical_details_file, Loader=yaml.FullLoader)
    construction_type = project_technical_details_df['construction_type']
    ac_dc = project_technical_details_df['ac_dc']
    capacity_mw = project_technical_details_df['capacity_mw'] # need to add the suffix MW
    capacity_mw = f"{capacity_mw}MW"
    conductor_type = project_technical_details_df['conductor_type'] # need to add the suffix Conductor
    conductor_type = f"{conductor_type}"
    converter_type = project_technical_details_df['converter_type']

    category = f"{construction_type}/{ac_dc}/{capacity_mw}/{conductor_type}/{converter_type}"

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


    
# First we need to convert the miles of the line given a width to acres


# Acquistion costs are $/acre so we need to multiply the acres of ROW by the acquistion cost per acre.


# Holding costs are $ / acre * delay year (typically the $ / acre is .1 of the rent cost per year) so we 
# need to multiply the acres of ROW by the $/ acre of holding for per delay year holding
# then multiply by the number of delay years to get the total holding costs.




# Rent costs are $ / acre * year so we need to multiply the acres of ROW by the rent cost per acre per year 
# for the per year rent cost. THen multiply by the number of years of rent.




# it so weird as I write and see the autocomplete make suggestions and theyre going the right direction but then I am not 
# thinking I'm just reading and knowing that it is suggesting what I was going to think of but am not yet thinking it. SO
# when I write (not code) but thoguhts I need to iignore the autocomplete suggestions and just think them through. Lol.


