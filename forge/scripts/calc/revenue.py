# Date: 2025-11-XX
# Description: Calculate rate-based revenue requirement (utility perspective).
#              FERC-style declining-balance formula rate: straight-line depreciation
#              plus return on the declining undepreciated rate base at the real WACC.
#              Rate base = AFUDC capital (real dollars at COD).

from __future__ import annotations

import logging

# Standard library imports
import yaml
from typing import Tuple, Dict, Any

from forge.scripts.utils.smart_output import SmartOutputManager

# Local utility imports
from forge.scripts.utils.smart_loaders import (
    load_financing_details,
    load_project_technical_details as load_project_technical_details_centralized,
    get_financing_data_raw,
)
from forge.scripts.utils.financial_utils import calculate_cod_year

try:
    from forge.scripts.utils.run_context import get_output_manager
except ImportError:
    def get_output_manager():
        return None

logger = logging.getLogger(__name__)


def load_rate_based_revenue_parameters() -> bool:
    """
    Load rate-based revenue parameters from financing data.
    Supports both YAML and JSON input modes.

    Returns:
        bool: enabled
    """
    try:
        financing_data = get_financing_data_raw()
        if not financing_data:
            raise ValueError("Financing data is empty or invalid")
        revenue_config = financing_data.get("financial", {}).get("revenue", {})
        rate_based_config = revenue_config.get("rate_based", {})

        enabled = rate_based_config.get("enabled", False)

        return enabled
    except FileNotFoundError:
        raise FileNotFoundError(
            f"Financing data not found"
        )
    except yaml.YAMLError as e:
        raise ValueError(f"Error parsing financing data: {e}")

def load_project_technical_details() -> Tuple[float, int, int]:
    """
    Load project technical details for timeline information using centralized loader.

    Returns:
        tuple: (delay_years, construction_years, project_lifetime)
    """
    from forge.scripts.io.yaml_loaders import ProjectTechnicalDetails
    project_details: ProjectTechnicalDetails = load_project_technical_details_centralized()
    return project_details.delay_years, project_details.construction_years, project_details.project_lifetime

def get_rate_base() -> float:
    """
    Get rate base (AFUDC capital at COD) from the shared run aggregator.

    Rate base = build_cost_afudc + row_cost_afudc + env_mitigation_afudc.
    Rate base in real (base-year) dollars after AFUDC compounding at real WACC.

    Returns:
        float: Rate base (real, AFUDC-capitalized), or 0 if not found
    """
    try:
        shared = get_output_manager()
        if shared is not None and getattr(shared, "costs", None) is not None:
            build_afudc = shared.require_upstream("costs", "build", "total_afudc")
            row_afudc = shared.require_upstream("costs", "row", "total_afudc")
            env_afudc = shared.require_upstream("costs", "environmental", "total_afudc")
            return build_afudc + row_afudc + env_afudc
    except KeyError as exc:
        logger.warning("Rate base lookup failed: %s", exc)
    return 0.0

def main() -> None:
    """
    Main function to calculate and display rate-based revenue requirement.
    Uses a FERC-style declining-balance formula rate: real rate base,
    straight-line depreciation plus return on the declining balance,
    discounted at real WACC.
    """
    # Check if rate-based revenue is enabled
    enabled = load_rate_based_revenue_parameters()

    if not enabled:
        logger.info("=" * 60)
        logger.info("RATE-BASED REVENUE CALCULATION SKIPPED")
        logger.info("(revenue.rate_based.enabled = false in financing.yaml)")
        logger.info("=" * 60)
        # Still write zeros to CSV for consistency
        csv_manager = SmartOutputManager()
        results = {
            "capital_recovery_real": 0,
            "capital_recovery_pv": 0,
            "annual_revenue": 0,
            "rate_base": 0,
            "rate_base_real": 0,
            "annual_revenue_real": 0,
            "revenue_year_1": 0,
            "revenue_year_n": 0,
        }
        csv_manager.add_revenue(results)
        csv_manager.write_batch_summary()
        return

    # Load project details
    delay_years, construction_years, project_lifetime = load_project_technical_details()

    # Load financing details
    financing = load_financing_details()

    # Get rate base (AFUDC capital at COD, real $) from batch summary or JSON outputs
    rate_base = get_rate_base()

    if rate_base == 0:
        logger.warning("⚠️  Warning: Rate base (AFUDC capital) is zero. Revenue will be zero.")
        logger.info(
            "   Make sure build_costs.py, row_costs.py, and environmental_mitigation.py"
        )
        logger.info("   have run before revenue.py")

    cod_year = calculate_cod_year(delay_years, construction_years)
    rate_base_real = rate_base

    from forge.scripts.utils.run_context import add_derived
    add_derived({"rate_base": rate_base, "rate_base_real": rate_base_real})

    # Declining-balance revenue requirement (FERC formula rate)
    # R_t = RB/n + RB * r * (1 - (t-1)/n) for t = 1..n
    n = project_lifetime
    r_wacc_real = financing.wacc_real

    capital_recovery_pv = 0.0
    capital_recovery_real = 0.0
    annual_revenues = []

    for t in range(1, n + 1):
        depreciation_t = rate_base_real / n
        return_t = rate_base_real * r_wacc_real * (1 - (t - 1) / n)
        revenue_t = depreciation_t + return_t
        annual_revenues.append(revenue_t)
        capital_recovery_real += revenue_t
        discount_year = cod_year + t - 1
        capital_recovery_pv += revenue_t / (1 + r_wacc_real) ** discount_year

    revenue_year_1 = annual_revenues[0] if annual_revenues else 0.0
    revenue_year_n = annual_revenues[-1] if annual_revenues else 0.0

    # NPV neutrality check: PV should equal RB discounted to base year
    expected_pv = rate_base_real / (1 + r_wacc_real) ** (cod_year - 1)
    assert abs(capital_recovery_pv - expected_pv) / max(expected_pv, 1.0) < 1e-6, (
        f"NPV neutrality violated: capital_recovery_pv={capital_recovery_pv:.2f}, expected={expected_pv:.2f}"
    )

    logger.info("=" * 60)
    logger.info("RATE-BASED REVENUE REQUIREMENT CALCULATION (declining balance, real WACC)")
    logger.info("=" * 60)
    logger.info(f"Rate Base (real, AFUDC-capitalized): ${rate_base:,.2f}")
    logger.info(f"Real WACC:                      {r_wacc_real:.2%}")
    logger.info(f"Project Lifetime:                {n} years")
    logger.info(f"Revenue Year 1 (real $/year):    ${revenue_year_1:,.2f}")
    logger.info(f"Revenue Year {n} (real $/year):   ${revenue_year_n:,.2f}")
    logger.info(f"Undiscounted Total (real):      ${capital_recovery_real:,.2f}")
    logger.info("")
    logger.info(
        f"PRESENT VALUE (discounted to base year ({financing.base_year}) using real WACC ({financing.wacc_real:.2%}):"
    )
    logger.info(f"Capital Recovery PV:            ${capital_recovery_pv:,.2f}")
    logger.info("=" * 60)

    # CSV Output
    csv_manager = SmartOutputManager()
    results = {
        "capital_recovery_real": capital_recovery_real,
        "capital_recovery_pv": capital_recovery_pv,
        "annual_revenue": revenue_year_1,
        "rate_base": rate_base,
        "rate_base_real": rate_base_real,
        "annual_revenue_real": revenue_year_1,
        "revenue_year_1": revenue_year_1,
        "revenue_year_n": revenue_year_n,
    }
    csv_manager.add_revenue(results)
    csv_manager.write_batch_summary()
