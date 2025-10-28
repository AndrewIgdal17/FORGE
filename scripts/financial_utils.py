# Author: Andrew Igdal
# Date: 2025-01-28
# Description: Shared financial utility functions for present value calculations and amortization.
#              This module consolidates duplicated financial calculation functions from across scripts.

import math


def calculate_present_value(annual_cost, wacc_real, total_years, start_year=1):
    """
    Calculate the present value of annual payments over a given time period.

    This function uses the real WACC (weighted average cost of capital) as the discount rate.
    The real WACC accounts for inflation using the Fisher equation.

    Args:
        annual_cost (float): Annual cost amount
        wacc_real (float): Real weighted average cost of capital (discount rate)
        total_years (int): Number of years over which payments occur
        start_year (int): Year when payments begin (default: 1)

    Returns:
        float: Present value of the payment stream
    """
    n_full_years = math.floor(total_years)
    frac = total_years - n_full_years
    total_pv = 0
    for year in range(n_full_years):
        t = start_year + year
        total_pv += annual_cost / (1 + wacc_real) ** t

    if frac > 0:
        t_frac = start_year + n_full_years + frac
        total_pv += annual_cost * frac / (1 + wacc_real) ** t_frac

    return total_pv


def calculate_amortized_cost(principal, wacc_real, project_lifetime):
    """
    Calculate annual amortized cost using standard amortization formula.

    This converts a lump-sum cost into equal annual payments over the project lifetime.
    Uses the real WACC as the discount rate.

    Args:
        principal (float): Initial cost (total build cost)
        wacc_real (float): Real weighted average cost of capital (discount rate)
        project_lifetime (int): Number of years to amortize over

    Returns:
        float: Annual amortized payment
    """
    if wacc_real == 0:
        return principal / project_lifetime

    # Standard amortization formula: A = P * [r(1+r)^n] / [(1+r)^n - 1]
    numerator = wacc_real * (1 + wacc_real) ** project_lifetime
    denominator = (1 + wacc_real) ** project_lifetime - 1

    return principal * numerator / denominator
