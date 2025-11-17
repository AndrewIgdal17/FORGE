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


def calculate_afudc_rate(financing_yaml):
    """
    Calculate AFUDC rate from capital structure or fall back to WACC.

    Per FERC USoA: AFUDC rate should reflect the utility's capital structure
    (equity return + debt cost). Falls back to WACC if capital structure not specified
    or if capital structure values are invalid (zero costs or percentages don't sum to 1.0).

    Args:
        financing_yaml (dict): Loaded financing YAML data

    Returns:
        tuple: (afudc_rate, source_description)
    """
    financial = financing_yaml.get("financial", {})
    cap_struct = financial.get("capital_structure")

    if cap_struct and all(
        k in cap_struct
        for k in ["equity_percent", "cost_of_equity", "debt_percent", "cost_of_debt"]
    ):
        # Validate capital structure values
        cost_of_equity = cap_struct["cost_of_equity"]
        cost_of_debt = cap_struct["cost_of_debt"]
        equity_percent = cap_struct["equity_percent"]
        debt_percent = cap_struct["debt_percent"]
        
        # Check if both costs are zero (invalid)
        if cost_of_equity == 0 and cost_of_debt == 0:
            # Fallback to WACC nominal
            rate = financial.get("wacc_nominal", 0.08)
            source = "WACC nominal (capital structure costs are zero)"
        # Check if percentages don't sum to 1.0 (within tolerance for floating point)
        elif abs(equity_percent + debt_percent - 1.0) > 0.001:
            # Fallback to WACC nominal
            rate = financial.get("wacc_nominal", 0.08)
            source = "WACC nominal (capital structure percentages don't sum to 1.0)"
        else:
            # Valid capital structure, calculate AFUDC rate
            rate = equity_percent * cost_of_equity + debt_percent * cost_of_debt
            source = "capital structure (equity + debt)"
    else:
        # Fallback to WACC nominal
        rate = financial.get("wacc_nominal", 0.08)
        source = "WACC nominal (capital structure not specified)"

    return rate, source


def calculate_afudc_capitalized_cost(
    nominal_cost,
    timing_pattern,
    delay_years,
    construction_years,
    afudc_rate,
    delay_has_active_work=False,
):
    """
    Capitalize a cost using AFUDC (compound forward to COD).

    Per FERC USoA Account 107 (CWIP): AFUDC applies when:
    (i) capital expenditures are being incurred, AND
    (ii) activities necessary to ready the project for service are in progress

    Logic:
    - Cost incurred during delay: AFUDC applies only if delay_has_active_work=True
    - Cost incurred during construction: AFUDC always applies
    - Assumes uniform spending within each period
    - Compounds to Commercial Operation Date (end of construction)

    Args:
        nominal_cost (float): Total nominal cost amount
        timing_pattern (dict): Dict with 'during_delay', 'during_construction', 'afudc_eligible'
        delay_years (float): Number of delay years
        construction_years (float): Number of construction years
        afudc_rate (float): AFUDC rate (annual)
        delay_has_active_work (bool): Whether active CWIP work continues during delay

    Returns:
        tuple: (capitalized_cost, afudc_amount)
    """
    # Check if cost is AFUDC-eligible
    if not timing_pattern.get("afudc_eligible", False):
        # Not eligible: return nominal cost with zero AFUDC
        return nominal_cost, 0.0

    # Total time to COD
    total_years_to_cod = delay_years + construction_years

    # Cost incurred during delay period
    delay_cost = nominal_cost * timing_pattern.get("during_delay", 0.0)

    # Cost incurred during construction period
    construction_cost = nominal_cost * timing_pattern.get("during_construction", 0.0)

    capitalized_cost = 0.0

    # 1) Process delay period costs
    if delay_cost > 0:
        if delay_has_active_work and delay_years > 0:
            # Active work during delay: AFUDC applies
            # Assume uniform spending: midpoint is delay_years / 2
            # Compound from midpoint to COD
            avg_years_to_cod = total_years_to_cod - (delay_years / 2)
            capitalized_cost += delay_cost * (1 + afudc_rate) ** avg_years_to_cod
        else:
            # No active work or no delay: costs incurred at start, compound full period
            if delay_years > 0:
                # Costs at start of delay, but no AFUDC during delay (suspended)
                # Compound only during construction period
                capitalized_cost += delay_cost * (1 + afudc_rate) ** construction_years
            else:
                # No delay period
                capitalized_cost += delay_cost

    # 2) Process construction period costs
    if construction_cost > 0 and construction_years > 0:
        # Uniform spending during construction: midpoint is construction_years / 2 before COD
        avg_years_to_cod = construction_years / 2
        capitalized_cost += construction_cost * (1 + afudc_rate) ** avg_years_to_cod
    else:
        # No construction period or zero construction cost
        capitalized_cost += construction_cost

    # Calculate AFUDC amount
    afudc_amount = capitalized_cost - nominal_cost

    return capitalized_cost, afudc_amount
