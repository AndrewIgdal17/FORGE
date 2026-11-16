# Date: 2025-01-28
# Description: Shared financial utility functions for present value calculations and amortization.
#              This module consolidates duplicated financial calculation functions from across scripts.

from __future__ import annotations

from typing import Dict, Any, Tuple
from .constants import MIN_DISCOUNT_RATE


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


def fisher_real(r_nom: float, inflation: float) -> float:
    """
    Convert a nominal rate to a real rate with the Fisher relation.

    Formula: r_real = (1 + r_nom) / (1 + inflation) - 1

    Args:
        r_nom: Nominal rate
        inflation: Inflation rate

    Returns:
        float: Real rate
    """
    return (1 + r_nom) / (1 + inflation) - 1


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
    return fisher_real(wacc_nominal, inflation_rate)


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


def capitalize_yearly_spending(
    yearly: list[float],
    t_cod: int,
    afudc_rate: float,
) -> float:
    """Capitalize construction-period spending to COD.

    Year ``t`` is ``yearly[t - 1]``. Each amount in a year ``t < t_cod``
    compounds from mid-year to the end of year ``t_cod - 1``. A non-zero
    amount in year ``t >= t_cod`` is an error.
    """
    for t, amount in enumerate(yearly, start=1):
        if t >= t_cod and amount != 0:
            raise ValueError(
                f"spending in year {t} is at or after COD year {t_cod}"
            )
    total = 0.0
    last_construction_year = t_cod - 1
    for t, amount in enumerate(yearly, start=1):
        if t >= t_cod:
            break
        years_to_cod = last_construction_year - t + 0.5
        total += amount * (1.0 + afudc_rate) ** years_to_cod
    return total

