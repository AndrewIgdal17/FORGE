# Author: Andrew Igdal
# Date: 2025-10-26
# Description: Emissions Reductions Calculation. This calculates the societal costs of emissions due to
# 1. Delays and long construction times slowing the deployment of new renewable energy capacity
# 2. Line losses being compensated for by generators (i.e. they have to burn more fuel to make up for losses)

import yaml


def load_emissions_reductions():
    with open("yamls/19_emissions_reductions.yaml", "r") as file:
        y = yaml.safe_load(file)
    return y


def calculate_emissions_reductions(y):
    return y
