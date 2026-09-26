# Date: 2025-01-28
# Description: Shared financial utility functions for present value calculations and amortization.
#              This module consolidates duplicated financial calculation functions from across scripts.

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Any, Tuple
from .constants import MIN_DISCOUNT_RATE, TIMING_PATTERN_TOLERANCE, DISCOUNT_GROWTH_EQUALITY_TOLERANCE, GROWTH_RATE_TOLERANCE


def validate_discount_rate(
    rate: float, rate_name: str = "discount_rate", min_value: float = MIN_DISCOUNT_RATE
) -> float:
    """
    Validate that a discount rate is not <= -1 (which would cause division by zero).

    Args:
        rate: The discount rate to validate
        rate_name: Name of the rate for error messages
        min_value: Minimum allowed value (default MIN_DISCOUNT_RATE to allow extreme deflation scenarios)

    Returns:
        float: The validated rate

    Raises:
        ValueError: If rate <= min_value
    """
    if rate <= min_value:
        raise ValueError(
            f"Invalid {rate_name}: {rate}. "
            f"Value must be > {min_value} to prevent division by zero in financial calculations. "
            f"A rate of {rate} would cause (1 + rate) to be <= 0, leading to invalid calculations."
        )
    return rate


def calculate_real_wacc(wacc_nominal: float, inflation_rate: float) -> float:
    """
    Calculate real WACC from nominal WACC and inflation rate using Fisher equation.

    Formula: real_wacc = (1 + nominal_wacc) / (1 + inflation_rate) - 1

    Args:
        wacc_nominal: Nominal weighted average cost of capital
        inflation_rate: Inflation rate

    Returns:
        float: Real WACC

    Raises:
        ValueError: If inflation_rate <= -1 (would cause division by zero)
    """
    validate_discount_rate(inflation_rate, "inflation_rate")
    return (1 + wacc_nominal) / (1 + inflation_rate) - 1


def calculate_present_value(
    annual_cost: float, wacc_real: float, total_years: float, start_year: float = 1.0
) -> float:
    """
    Calculate the present value of annual payments over a given time period.

    This function uses the real WACC (weighted average cost of capital) as the discount rate.
    The real WACC accounts for inflation using the Fisher equation.

    Args:
        annual_cost (float): Annual cost amount
        wacc_real (float): Real weighted average cost of capital (discount rate)
        total_years (float): Number of years over which payments occur
        start_year (float): Year when payments begin (can be fractional, default: 1.0)
                          For example, 1.5 means payments start mid-way through year 1

    Returns:
        float: Present value of the payment stream

    Raises:
        ValueError: If wacc_real <= MIN_DISCOUNT_RATE (would cause division by zero)
    """
    validate_discount_rate(wacc_real, "wacc_real")
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


def calculate_growing_annuity_pv(
    annual_amount: float,
    growth_rate: float,
    discount_rate: float,
    project_lifetime: int,
    delay_years: float = 0.0,
    construction_years: float = 0.0,
) -> float:
    """
    Calculate present value of a growing annuity with optional delay period discounting.
    
    This function calculates the PV of annual payments that grow at a constant rate,
    discounted at a given discount rate. It handles the edge case where discount rate
    equals growth rate, and optionally discounts for delay/construction periods.
    
    Formula:
    - If |d - g| < tolerance: PV = annual_amount * N / (1 + d)
    - Otherwise: PV = annual_amount * ((1 - ((1 + g) / (1 + d)) ** N) / (d - g))
    - If delay_period > 0: PV = PV / ((1 + d) ** delay_period)
    
    Args:
        annual_amount: Base annual amount (e.g., EAL or EAC)
        growth_rate: Annual growth rate (decimal, e.g., 0.02 for 2%)
        discount_rate: Discount rate (decimal, e.g., 0.05 for 5%)
        project_lifetime: Number of years in project lifetime
        delay_years: Years of delay before operations start (default: 0.0)
        construction_years: Years of construction (default: 0.0)
    
    Returns:
        float: Present value of the growing annuity, discounted for delay period if applicable
    
    Raises:
        ValueError: If discount_rate <= MIN_DISCOUNT_RATE
    """
    # Validate discount_rate to prevent division by zero
    validate_discount_rate(discount_rate)
    
    # Handle None values for delay_years and construction_years
    delay_years = delay_years if delay_years is not None else 0.0
    construction_years = construction_years if construction_years is not None else 0.0
    
    # Calculate present value with growing annuity
    g = growth_rate
    d = discount_rate
    N = project_lifetime
    
    if abs(d - g) < DISCOUNT_GROWTH_EQUALITY_TOLERANCE:  # Edge case: d = g
        pv = annual_amount * N / (1 + d)
    else:
        pv = annual_amount * ((1 - ((1 + g) / (1 + d)) ** N) / (d - g))
    
    # Discount for delay and construction periods
    # Risks only start accumulating after operations begin (after delay + construction)
    delay_period = delay_years + construction_years
    if delay_period > 0:
        pv = pv / ((1 + d) ** delay_period)
    
    return pv


def calculate_nominal_growing_series(
    annual_amount: float,
    growth_rate: float,
    project_lifetime: int,
) -> float:
    """
    Calculate nominal total cost as sum of a geometric series (growing annual costs).
    
    This function calculates the sum of annual amounts that grow at a constant rate
    over the project lifetime. This is the nominal (undiscounted) total.
    
    Formula:
    - If |growth_rate| < tolerance: total = annual_amount * project_lifetime
    - Otherwise: total = annual_amount * ((1 + growth_rate) ** project_lifetime - 1) / growth_rate
    
    This represents the sum of the geometric series:
    sum((1 + g)^t for t=0 to N-1) = ((1 + g)^N - 1) / g
    
    Args:
        annual_amount: Base annual amount (e.g., EAL or EAC)
        growth_rate: Annual growth rate (decimal, e.g., 0.02 for 2%)
        project_lifetime: Number of years in project lifetime
    
    Returns:
        float: Nominal total cost (sum of growing annual costs, undiscounted)
    """
    if abs(growth_rate) < GROWTH_RATE_TOLERANCE:  # No growth
        return annual_amount * project_lifetime
    else:
        return annual_amount * ((1 + growth_rate) ** project_lifetime - 1) / growth_rate


def calculate_cod_year(delay_years: float, construction_years: int) -> float:
    """
    Calculate Commercial Operation Date (COD) year.
    
    COD is when the project becomes operational, which is:
    delay_years (delay period) + construction_years (construction) + 1
    If delay is fractional (e.g., 0.5 years), COD will be fractional (e.g., 2.5).
    
    Args:
        delay_years: Number of years of project delay before construction
        construction_years: Number of years of construction
        
    Returns:
        float: Year when project becomes operational (COD, can be fractional, e.g., 2.5)
    """
    return delay_years + construction_years + 1.0


def calculate_construction_start_year(delay_years: float) -> float:
    """
    Calculate construction start year (end of delay period).
    
    Construction begins immediately after the delay period ends.
    If delay is fractional (e.g., 0.5 years), construction starts mid-year.
    
    Args:
        delay_years: Number of years of project delay before construction
        
    Returns:
        float: Year when construction begins (can be fractional, e.g., 1.5)
    """
    return delay_years + 1.0


def calculate_amortized_cost(
    principal: float, wacc_real: float, project_lifetime: int
) -> float:
    """Level-annuity capital recovery factor.

    NOTE: This is NOT the FERC declining-balance formula rate used in the
    appendix revenue requirement (§Revenue, Eq REV-3). The appendix method
    is implemented in revenue.py. This function is retained as a general
    utility for potential future use outside the core methodology.

    Converts a lump-sum cost into equal annual payments over the project
    lifetime. Uses the real WACC as the discount rate.

    Args:
        principal (float): Initial cost (total build cost)
        wacc_real (float): Real weighted average cost of capital (discount rate)
        project_lifetime (int): Number of years to amortize over

    Returns:
        float: Annual amortized payment

    Raises:
        ValueError: If wacc_real <= MIN_DISCOUNT_RATE (would cause division by zero)
    """
    validate_discount_rate(wacc_real, "wacc_real")
    if wacc_real == 0:
        return principal / project_lifetime

    # Standard amortization formula: A = P * [r(1+r)^n] / [(1+r)^n - 1]
    numerator = wacc_real * (1 + wacc_real) ** project_lifetime
    denominator = (1 + wacc_real) ** project_lifetime - 1

    return principal * numerator / denominator


def calculate_afudc_rate(financing_yaml: Dict[str, Any]) -> Tuple[float, str]:
    """Return AFUDC rate (real WACC) for compounding real-dollar construction costs."""
    financial = financing_yaml["financial"]
    wacc_nominal = financial["wacc_nominal"]
    inflation_rate = financial["inflation_rate"]
    rate = calculate_real_wacc(wacc_nominal, inflation_rate)
    return rate, "WACC real"


def get_wacc_nominal(financing_yaml: Dict[str, Any]) -> float:
    """Return nominal WACC from financing config."""
    financial = financing_yaml["financial"]
    return financial["wacc_nominal"]


def get_construction_spending_weights(
    construction_years: int,
    profiles: dict[str, list[float]],
) -> list[float]:
    """Derive annual spending weights for a given construction duration.

    Uses MISO MTEP25 Table 5-1 reference profiles (5-8 year) as anchor data.
    All profiles are pooled into a single normalized cumulative S-curve, then
    resampled to the target duration via piecewise linear interpolation.

    Args:
        construction_years: Target construction duration (integer >= 1).
        profiles: Dict mapping duration string to weight list, e.g.
                  {"5": [0.01, 0.04, 0.35, 0.35, 0.25], ...}.

    Returns:
        List of length construction_years, summing to 1.0.
    """
    if construction_years < 1:
        raise ValueError(f"construction_years must be >= 1, got {construction_years}")

    if construction_years == 1:
        return [1.0]

    # Build pooled cumulative data points on normalized time axis [0, 1].
    # Each profile contributes N+1 points: (0, 0) and (k/N, cumulative_k) for k=1..N.
    points: list[tuple[float, float]] = [(0.0, 0.0)]
    for dur_str, weights in profiles.items():
        n = len(weights)
        cumulative = 0.0
        for k, w in enumerate(weights, 1):
            cumulative += w
            t = k / n
            points.append((t, cumulative))

    # Sort by time, then deduplicate by averaging y-values at the same t
    points.sort()
    merged: list[tuple[float, float]] = []
    i = 0
    while i < len(points):
        t_i = points[i][0]
        ys = []
        while i < len(points) and abs(points[i][0] - t_i) < 1e-12:
            ys.append(points[i][1])
            i += 1
        merged.append((t_i, sum(ys) / len(ys)))

    ts = [p[0] for p in merged]
    cs = [p[1] for p in merged]

    # Piecewise linear interpolation: sample cumulative curve at year endpoints
    def interp(t_query: float) -> float:
        if t_query <= ts[0]:
            return cs[0]
        if t_query >= ts[-1]:
            return cs[-1]
        for j in range(len(ts) - 1):
            if ts[j] <= t_query <= ts[j + 1]:
                frac = (t_query - ts[j]) / (ts[j + 1] - ts[j])
                return cs[j] + frac * (cs[j + 1] - cs[j])
        return cs[-1]

    # Sample cumulative at the END of each year (k/N for k=0..N)
    N = construction_years
    cum_samples = [interp(k / N) for k in range(N + 1)]
    cum_samples[0] = 0.0
    cum_samples[-1] = 1.0

    # Annual weights = differences of cumulative
    weights_out = [cum_samples[k + 1] - cum_samples[k] for k in range(N)]

    # Renormalize to handle floating-point drift
    total = sum(weights_out)
    if total > 0:
        weights_out = [w / total for w in weights_out]

    return weights_out


def calculate_afudc_capitalized_cost(
    nominal_cost: float,
    timing_pattern: Dict[str, Any],
    delay_years: float,
    construction_years: float,
    afudc_rate: float,
    delay_has_active_work: bool = False,
    spending_profiles: dict[str, list[float]] | None = None,
) -> Tuple[float, float]:
    """
    Capitalize a cost using AFUDC (compound forward to COD).

    Per FERC USoA Account 107 (CWIP): AFUDC applies when:
    (i) capital expenditures are being incurred, AND
    (ii) activities necessary to ready the project for service are in progress

    Logic:
    - Cost incurred during delay: uniform annual spending, each year's spend
      compounded from its midpoint to COD.
    - Cost incurred during construction: year-by-year compounding using S-curve
      spending weights from MISO MTEP25 Table 5-1 (when spending_profiles is
      provided). Each year's spend is compounded from its midpoint to COD.
      Falls back to uniform annual weights when profiles are not available.
    - Compounds to Commercial Operation Date (end of construction).

    Args:
        nominal_cost (float): Total nominal cost amount
        timing_pattern (dict): Dict with 'during_delay', 'during_construction', 'afudc_eligible'
        delay_years (float): Number of delay years
        construction_years (float): Number of construction years
        afudc_rate (float): AFUDC rate (annual)
        delay_has_active_work (bool): Whether active CWIP work continues during delay
        spending_profiles: Optional dict mapping duration string to annual weight
            list (e.g. {"5": [0.01, 0.04, 0.35, 0.35, 0.25], ...}). When provided,
            weights are interpolated via get_construction_spending_weights().

    Returns:
        tuple: (capitalized_cost, afudc_amount)

    Raises:
        ValueError: If afudc_rate <= MIN_DISCOUNT_RATE (would cause division by zero)
        ValueError: If AFUDC-eligible and during_delay + during_construction != 1.0 (within TIMING_PATTERN_TOLERANCE)

    For AFUDC-eligible patterns, during_delay and during_construction must sum to 1.0 (within TIMING_PATTERN_TOLERANCE).
    """
    validate_discount_rate(afudc_rate, "afudc_rate")
    # Check if cost is AFUDC-eligible
    if not timing_pattern.get("afudc_eligible", False):
        # Not eligible: return nominal cost with zero AFUDC
        return nominal_cost, 0.0

    theta_d = timing_pattern["during_delay"]
    theta_c = timing_pattern["during_construction"]
    if abs((theta_d + theta_c) - 1.0) > TIMING_PATTERN_TOLERANCE:
        raise ValueError(
            f"Cost timing pattern (during_delay + during_construction) must sum to 1.0 (tolerance {TIMING_PATTERN_TOLERANCE}). "
            f"Got during_delay={theta_d}, during_construction={theta_c}, sum={theta_d + theta_c}."
        )

    # Total time to COD
    total_years_to_cod = delay_years + construction_years

    # Cost incurred during delay period
    delay_cost = nominal_cost * timing_pattern["during_delay"]

    # Cost incurred during construction period
    construction_cost = nominal_cost * timing_pattern["during_construction"]

    capitalized_cost = 0.0

    # 1) Process delay period costs (uniform annual spending)
    if delay_cost > 0:
        if delay_has_active_work and delay_years > 0:
            n_delay = int(delay_years)
            if n_delay >= 1:
                annual_delay_spend = delay_cost / n_delay
                for yr in range(n_delay):
                    years_to_cod = total_years_to_cod - (yr + 0.5)
                    capitalized_cost += annual_delay_spend * (1 + afudc_rate) ** years_to_cod
            else:
                capitalized_cost += delay_cost * (1 + afudc_rate) ** construction_years
        else:
            if delay_years > 0:
                capitalized_cost += delay_cost * (1 + afudc_rate) ** construction_years
            else:
                capitalized_cost += delay_cost

    # 2) Process construction period costs (year-by-year S-curve compounding)
    if construction_cost > 0 and construction_years > 0:
        n_years = int(construction_years)
        if spending_profiles and n_years >= 1:
            weights = get_construction_spending_weights(n_years, spending_profiles)
        else:
            weights = [1.0 / n_years] * n_years if n_years >= 1 else [1.0]
        for yr, w in enumerate(weights):
            years_to_cod = construction_years - (yr + 0.5)
            capitalized_cost += construction_cost * w * (1 + afudc_rate) ** years_to_cod
    else:
        capitalized_cost += construction_cost

    # Calculate AFUDC amount
    afudc_amount = capitalized_cost - nominal_cost

    return capitalized_cost, afudc_amount


@dataclass
class AFUDCSetup:
    """AFUDC configuration and parameters."""
    timing_patterns: Dict[str, Any]
    apply_afudc: bool
    delay_active: bool
    afudc_rate: float
    afudc_source: str
    spending_profiles: dict[str, list[float]] | None = None


def load_afudc_setup() -> AFUDCSetup:
    """
    Load all AFUDC-related configuration and parameters.
    
    Returns:
        AFUDCSetup dataclass containing:
            - timing_patterns: Cost timing patterns dictionary
            - apply_afudc: Whether to apply AFUDC
            - delay_active: Whether delay period has active work
            - afudc_rate: Calculated AFUDC rate
            - afudc_source: Description of AFUDC rate source
    """
    from .smart_loaders import (
        load_cost_timing_patterns,
        load_afudc_config,
        get_financing_data_raw,
    )
    
    cost_timing_data = load_cost_timing_patterns()
    timing_patterns = cost_timing_data["cost_timing_patterns"]
    spending_profiles = cost_timing_data.get("construction_spending_profiles")
    apply_afudc, delay_active = load_afudc_config()
    financing_yaml = get_financing_data_raw()
    afudc_rate, afudc_source = calculate_afudc_rate(financing_yaml)
    
    return AFUDCSetup(
        timing_patterns=timing_patterns,
        apply_afudc=apply_afudc,
        delay_active=delay_active,
        afudc_rate=afudc_rate,
        afudc_source=afudc_source,
        spending_profiles=spending_profiles,
    )
