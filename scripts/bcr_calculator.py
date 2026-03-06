# Author: Andrew Igdal
# Date: 2025-11-04
# Description: Calculate benefit-cost ratios (BCR) for transmission projects.
#              Compares congestion/curtailment benefits against all project costs.

from __future__ import annotations

import csv
import os
import yaml
from dataclasses import dataclass
from typing import Dict, Any, Optional, Tuple
from path_config import OUTPUTS_DIR, YAMLS_DIR

# BCR viability threshold
BCR_VIABILITY_THRESHOLD = 1.0


@dataclass
class BCRConfig:
    """Configuration for BCR calculation exclusions.

    All flags default to False, meaning all modules are included by default.
    Set a flag to True to exclude that module from Primary BCR calculations.
    """

    no_emissions: bool = False
    no_linelosses: bool = False
    capital_only: bool = False
    no_wildfire: bool = False
    no_outages: bool = False
    no_oandm: bool = False
    no_insurance: bool = False
    no_delay_costs: bool = False
    no_congestion: bool = False
    no_curtailment: bool = False

    @classmethod
    def default(cls) -> "BCRConfig":
        """Create default config (all modules included)."""
        return cls()


def safe_divide(numerator: float, denominator: float) -> float:
    """
    Safely divide two numbers, returning 0 if denominator is <= 0.

    Prevents division by zero errors in BCR calculations.

    Args:
        numerator: The dividend
        denominator: The divisor

    Returns:
        float: numerator / denominator if denominator > 0, else 0.0
    """
    return numerator / denominator if denominator > 0 else 0.0


def format_bcr_viability(bcr_value: float) -> Tuple[str, str]:
    """
    Return (symbol, text) tuple for BCR viability display.

    Args:
        bcr_value: The BCR value to check

    Returns:
        tuple: (symbol, text) where symbol is "✅" or "❌" and text describes viability
    """
    if bcr_value >= BCR_VIABILITY_THRESHOLD:
        return ("✅", ">= 1.0: economically viable")
    else:
        return ("❌", "< 1.0: not economically viable")


def load_scenario_data(
    scenario_id: str, output_dir: str = str(OUTPUTS_DIR)
) -> Optional[Dict[str, Any]]:
    """
    Load scenario data from batch_summary.csv for the given scenario_id.
    Uses robust lookup: exact match, then partial match, then last row fallback.

    Args:
        scenario_id: Unique identifier for the scenario
        output_dir: Directory containing batch_summary.csv

    Returns:
        Dictionary with all data for the scenario, or None if not found
    """
    batch_path = os.path.join(output_dir, "batch_summary.csv")

    if not os.path.exists(batch_path):
        print(f"Warning: batch_summary.csv not found at {batch_path}")
        return None

    def convert_row_to_numeric(row: Dict[str, str]) -> Dict[str, Any]:
        """Convert numeric strings to floats in a row."""
        converted = {}
        for key, value in row.items():
            if value and value != "":
                try:
                    converted[key] = float(value)
                except (ValueError, TypeError):
                    converted[key] = value  # Keep as string if not numeric
            else:
                # Empty string means key doesn't exist (don't add to dict)
                # This ensures "key" in data works correctly
                pass
        return converted

    with open(batch_path, "r", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

        if len(rows) == 0:
            print(f"Warning: batch_summary.csv is empty")
            return None

        # Strategy 1: Try exact match first
        for row in rows:
            row_id = row.get("scenario_id", "")
            if row_id == scenario_id:
                return convert_row_to_numeric(row)

        # Strategy 2: Try partial match (for cases where scenario_id format differs)
        # Check if scenario_id contains or is contained in row's scenario_id
        for row in rows:
            row_scenario_id = str(row.get("scenario_id", ""))
            if scenario_id in row_scenario_id or row_scenario_id in scenario_id:
                print(
                    f"Info: Using partial match for scenario_id '{scenario_id}' (found '{row_scenario_id}')"
                )
                return convert_row_to_numeric(row)

        # Strategy 3: Try prefix match (for sensitivity analysis runs)
        # Extract prefix (e.g., "sample_0" from "sample_0_1234567890")
        scenario_prefix = (
            scenario_id.split("_")[0] if "_" in scenario_id else scenario_id
        )
        for row in rows:
            row_scenario_id = str(row.get("scenario_id", ""))
            if row_scenario_id.startswith(scenario_prefix + "_"):
                print(
                    f"Info: Using prefix match for scenario_id '{scenario_id}' (found '{row_scenario_id}')"
                )
                return convert_row_to_numeric(row)

        # Strategy 4: Fallback to last row (for batch sensitivity runs where exact ID may differ)
        print(f"Warning: scenario_id '{scenario_id}' not found in batch_summary.csv")
        print(
            f"Info: Using last row as fallback (this is normal for batch sensitivity analysis)"
        )
        return convert_row_to_numeric(rows[-1])


def safe_get_numeric(data: Dict[str, Any], key: str, default: float = 0.0) -> float:
    """
    Safely get numeric value from dictionary, handling missing keys, empty strings, None, and 0.0.

    This is for individual component values only. Do NOT use for subtotals.
    The subtotal logic (e.g., capital_costs_pv) uses explicit checks that reject 0.0 values
    to avoid using incorrectly initialized CSV values.

    Args:
        data: Dictionary to read from
        key: Key to look up
        default: Default value if key is missing (default: 0.0)

    Returns:
        float: Numeric value (defaults to 0.0 for missing/invalid values)
    """
    return data.get(key, default) or default


def prefer_csv_subtotal(
    data: Dict[str, Any], key: str, calculated_value: float
) -> float:
    """
    Prefer CSV subtotal value if it exists and is valid, otherwise use calculated value.

    CSV subtotals are considered valid if they:
    - Exist in the dictionary
    - Are not empty strings
    - Are not 0.0 (which indicates uninitialized value)

    This is used for subtotals that may be written to CSV by early-running scripts
    before they're actually calculated. We prefer the CSV value if it's valid, but
    fall back to calculating from components if the CSV value is missing or invalid.

    Args:
        data: Dictionary containing CSV data
        key: Key to look up in dictionary
        calculated_value: Value calculated from components (fallback)

    Returns:
        float: CSV value if valid, otherwise calculated value
    """
    if key in data and data[key] != "" and data[key] != 0.0:
        return data[key]
    else:
        return calculated_value


def calculate_benefits(data: Dict[str, Any]) -> Dict[str, float]:
    """
    Calculate total benefits from scenario data.

    System total benefits (societal) include only real resource benefits:
      - Congestion reduction savings
      - Curtailment reduction savings
      - Benefit of delivered energy (throughput value at electricity price)
    Revenue (rate-based revenue requirement) is a transfer, not a net social
    benefit; it is excluded from system totals but still returned in the dict
    for Utility/Ratepayer BCRs.

    Note: Line losses are now always treated as costs, not benefits, for both
    greenfield and reconductoring projects.

    Args:
        data: Dictionary with scenario data

    Returns:
        Dictionary with benefit breakdown and total (both nominal and PV)
    """
    # Present value benefits
    congestion_benefit_pv = safe_get_numeric(data, "congestion_benefit_pv")
    curtailment_benefit_pv = safe_get_numeric(data, "curtailment_benefit_pv")
    delivered_benefit_pv = safe_get_numeric(data, "delivered_benefit_pv")

    # Nominal benefits
    congestion_benefit_nominal = safe_get_numeric(data, "congestion_benefit_nominal")
    curtailment_benefit_nominal = safe_get_numeric(data, "curtailment_benefit_nominal")
    delivered_benefit_nominal = safe_get_numeric(data, "delivered_benefit_nominal")

    # Line losses are now always costs, never benefits
    # (Both greenfield and reconductoring report absolute losses as positive costs)

    # Add revenue (rate-based revenue requirement)
    revenue_pv = safe_get_numeric(data, "revenue_pv")
    revenue_nominal = safe_get_numeric(data, "revenue_nominal")

    calculated_total_benefits = (
        congestion_benefit_pv + curtailment_benefit_pv + delivered_benefit_pv
    )
    total_benefits_pv = prefer_csv_subtotal(
        data, "total_benefits_pv", calculated_total_benefits
    )
    calculated_total_benefits_nominal = (
        congestion_benefit_nominal
        + curtailment_benefit_nominal
        + delivered_benefit_nominal
    )
    total_benefits_nominal = prefer_csv_subtotal(
        data, "total_benefits_nominal", calculated_total_benefits_nominal
    )

    # Also calculate haircut benefits (conservative estimate)
    # Haircut applies to congestion/curtailment only; delivered energy has no haircut
    congestion_benefit_haircut = safe_get_numeric(data, "congestion_benefit_haircut_pv")
    curtailment_benefit_haircut = safe_get_numeric(
        data, "curtailment_benefit_haircut_pv"
    )
    calculated_total_benefits_haircut = (
        congestion_benefit_haircut + curtailment_benefit_haircut + delivered_benefit_pv
    )
    total_benefits_haircut_pv = prefer_csv_subtotal(
        data, "total_benefits_haircut_pv", calculated_total_benefits_haircut
    )

    return {
        "congestion_benefit_pv": congestion_benefit_pv,
        "curtailment_benefit_pv": curtailment_benefit_pv,
        "delivered_benefit_pv": delivered_benefit_pv,
        "delivered_benefit_nominal": delivered_benefit_nominal,
        "congestion_benefit_haircut_pv": congestion_benefit_haircut,
        "curtailment_benefit_haircut_pv": curtailment_benefit_haircut,
        "line_loss_benefit_pv": 0,  # Line losses are always costs, never benefits
        "revenue_pv": revenue_pv,
        "total_benefits_pv": total_benefits_pv,
        "total_benefits_nominal": total_benefits_nominal,
        "total_benefits_haircut_pv": total_benefits_haircut_pv,
    }


def calculate_costs(data: Dict[str, Any]) -> Dict[str, float]:
    """
    Calculate total costs from scenario data.

    Costs include:
      - Capital: build, ROW, environmental mitigation
      - Operational: O&M, insurance (operational only)
      - Energy & Emissions: line losses (greenfield), emissions
      - Risk: wildfire, outage, insurance (wildfire liability)
      - Delay: construction delay, congestion/curtailment delay, residual congestion

    Args:
        data: Dictionary with scenario data

    Returns:
        Dictionary with cost breakdown by category and total (both nominal and PV)
    """
    # Capital costs (PV) - ROW = capital only (acquisition + holding), not rent
    build_cost_pv = safe_get_numeric(data, "build_cost_pv")
    row_capital_pv = safe_get_numeric(data, "row_capital_pv") or safe_get_numeric(
        data, "row_cost_pv"
    )
    row_cost_pv = safe_get_numeric(data, "row_cost_pv")
    env_mitigation_pv = safe_get_numeric(data, "env_mitigation_pv")
    calculated_capital = build_cost_pv + row_capital_pv + env_mitigation_pv
    capital_costs_pv = prefer_csv_subtotal(data, "capital_costs_pv", calculated_capital)

    # Capital costs (Nominal)
    build_cost_nominal = safe_get_numeric(data, "build_cost_nominal")
    row_capital_nominal = safe_get_numeric(data, "row_capital_nominal") or safe_get_numeric(
        data, "row_cost_nominal"
    )
    row_cost_nominal = safe_get_numeric(data, "row_cost_nominal")
    env_mitigation_nominal = safe_get_numeric(data, "env_mitigation_nominal")
    calculated_capital_nominal = (
        build_cost_nominal + row_capital_nominal + env_mitigation_nominal
    )
    capital_costs_nominal = prefer_csv_subtotal(
        data, "capital_costs_nominal", calculated_capital_nominal
    )

    # Operational costs (PV) - O&M, insurance, ROW rent (residual exceedance is in energy/emissions)
    oandm_pv = safe_get_numeric(data, "oandm_pv")
    insurance_pv = safe_get_numeric(data, "insurance_pv")
    row_rent_pv = safe_get_numeric(data, "row_rent_pv")
    residual_exceedance_pv = safe_get_numeric(data, "residual_exceedance_pv")
    calculated_operational = oandm_pv + insurance_pv + row_rent_pv
    operational_costs_pv = prefer_csv_subtotal(
        data, "operational_costs_pv", calculated_operational
    )

    # Operational costs (Nominal)
    oandm_nominal = safe_get_numeric(data, "oandm_nominal")
    insurance_nominal = safe_get_numeric(data, "insurance_nominal")
    row_rent_nominal = safe_get_numeric(data, "row_rent_nominal")
    residual_exceedance_nominal = safe_get_numeric(data, "residual_exceedance_nominal")
    calculated_operational_nominal = oandm_nominal + insurance_nominal + row_rent_nominal
    operational_costs_nominal = prefer_csv_subtotal(
        data, "operational_costs_nominal", calculated_operational_nominal
    )

    # Energy & Emissions costs (PV) - Energy losses, emissions, and residual exceedance (system cost only)
    emissions_pv = safe_get_numeric(data, "emissions_cost_pv")
    energy_losses_pv = safe_get_numeric(data, "energy_losses_pv") or safe_get_numeric(
        data, "line_loss_cost_pv"
    )
    energy_losses_pv = max(0, energy_losses_pv)
    conductor_loss_pv = safe_get_numeric(data, "conductor_loss_pv")
    converter_loss_pv = safe_get_numeric(data, "converter_loss_pv")
    calculated_energy_emissions = (
        energy_losses_pv + emissions_pv + residual_exceedance_pv
    )
    energy_emissions_costs_pv = prefer_csv_subtotal(
        data, "energy_emissions_costs_pv", calculated_energy_emissions
    )

    # Energy & Emissions costs (Nominal) - includes residual exceedance
    emissions_nominal = safe_get_numeric(data, "emissions_cost_nominal")
    energy_losses_nominal = safe_get_numeric(
        data, "energy_losses_nominal"
    ) or safe_get_numeric(data, "line_loss_cost_nominal")
    energy_losses_nominal = max(0, energy_losses_nominal)
    calculated_energy_emissions_nominal = (
        energy_losses_nominal + emissions_nominal + residual_exceedance_nominal
    )
    energy_emissions_costs_nominal = prefer_csv_subtotal(
        data, "energy_emissions_costs_nominal", calculated_energy_emissions_nominal
    )

    # Risk costs (PV) - Wildfire, outage, and wildfire liability insurance
    wildfire_pv = safe_get_numeric(data, "wildfire_pv")
    outage_pv = safe_get_numeric(data, "outage_pv")
    wildfire_liability_insurance_pv = safe_get_numeric(
        data, "wildfire_liability_insurance_pv"
    )
    # Backward compatibility for older CSVs (pre-rename)
    if wildfire_liability_insurance_pv == 0:
        wildfire_liability_insurance_pv = safe_get_numeric(
            data, "wildfire_liability_pv"
        )

    calculated_risk = wildfire_pv + outage_pv + wildfire_liability_insurance_pv
    risk_costs_pv = prefer_csv_subtotal(data, "risk_costs_pv", calculated_risk)

    # Risk costs (Nominal)
    wildfire_nominal = safe_get_numeric(data, "wildfire_nominal")
    outage_nominal = safe_get_numeric(data, "outage_nominal")
    wildfire_liability_nominal = safe_get_numeric(data, "wildfire_liability_nominal")
    calculated_risk_nominal = (
        wildfire_nominal + outage_nominal + wildfire_liability_nominal
    )
    risk_costs_nominal = prefer_csv_subtotal(
        data, "risk_costs_nominal", calculated_risk_nominal
    )

    # Delay costs (PV)
    delay_cost_pv = safe_get_numeric(data, "delay_cost_pv")
    congestion_delay_pv = safe_get_numeric(data, "congestion_delay_cost_pv")
    curtailment_delay_pv = safe_get_numeric(data, "curtailment_delay_cost_pv")
    calculated_delay = delay_cost_pv + congestion_delay_pv + curtailment_delay_pv
    delay_costs_pv = (
        data["delay_costs_pv"]
        if (
            "delay_costs_pv" in data
            and data["delay_costs_pv"] != ""
            and data["delay_costs_pv"] != 0.0
        )
        else calculated_delay
    )

    # Delay costs (Nominal)
    delay_cost_nominal = safe_get_numeric(data, "delay_cost_nominal")
    congestion_delay_nominal = safe_get_numeric(data, "congestion_delay_cost_nominal")
    curtailment_delay_nominal = safe_get_numeric(data, "curtailment_delay_cost_nominal")
    calculated_delay_nominal = (
        delay_cost_nominal + congestion_delay_nominal + curtailment_delay_nominal
    )
    delay_costs_nominal = prefer_csv_subtotal(
        data, "delay_costs_nominal", calculated_delay_nominal
    )

    # Totals
    calculated_total = (
        capital_costs_pv
        + operational_costs_pv
        + energy_emissions_costs_pv
        + risk_costs_pv
        + delay_costs_pv
    )
    total_costs_pv = prefer_csv_subtotal(data, "total_costs_pv", calculated_total)
    calculated_total_nominal = (
        capital_costs_nominal
        + operational_costs_nominal
        + energy_emissions_costs_nominal
        + risk_costs_nominal
        + delay_costs_nominal
    )
    total_costs_nominal = prefer_csv_subtotal(
        data, "total_costs_nominal", calculated_total_nominal
    )

    return {
        # Capital (PV)
        "build_cost_pv": build_cost_pv,
        "row_cost_pv": row_cost_pv,
        "row_capital_pv": row_capital_pv,
        "row_rent_pv": row_rent_pv,
        "env_mitigation_pv": env_mitigation_pv,
        "capital_costs_pv": capital_costs_pv,
        # Operational (PV)
        "oandm_pv": oandm_pv,
        "insurance_pv": insurance_pv,
        "residual_exceedance_pv": residual_exceedance_pv,
        "operational_costs_pv": operational_costs_pv,
        # ROW nominals for display
        "row_capital_nominal": row_capital_nominal,
        "row_rent_nominal": row_rent_nominal,
        # Energy & Emissions (PV)
        "energy_losses_pv": energy_losses_pv,
        "conductor_loss_pv": conductor_loss_pv,
        "converter_loss_pv": converter_loss_pv,
        "emissions_cost_pv": emissions_pv,
        "energy_emissions_costs_pv": energy_emissions_costs_pv,
        # Risk (PV)
        "wildfire_pv": wildfire_pv,
        "outage_pv": outage_pv,
        "wildfire_liability_insurance_pv": wildfire_liability_insurance_pv,
        "risk_costs_pv": risk_costs_pv,
        # Delay (PV)
        "delay_cost_pv": delay_cost_pv,
        "congestion_delay_cost_pv": congestion_delay_pv,
        "curtailment_delay_cost_pv": curtailment_delay_pv,
        "delay_costs_pv": delay_costs_pv,
        # Totals (PV)
        "total_costs_pv": total_costs_pv,
        # Totals (Nominal)
        "capital_costs_nominal": capital_costs_nominal,
        "operational_costs_nominal": operational_costs_nominal,
        "energy_emissions_costs_nominal": energy_emissions_costs_nominal,
        "risk_costs_nominal": risk_costs_nominal,
        "delay_costs_nominal": delay_costs_nominal,
        "total_costs_nominal": total_costs_nominal,
    }


def calculate_bcr_metrics(
    benefits: Dict[str, float],
    costs: Dict[str, float],
    config: BCRConfig = None,
) -> Dict[str, float]:
    """
    Calculate benefit-cost ratios and net benefits.

    Args:
        benefits: Dictionary with benefit breakdown
        costs: Dictionary with cost breakdown
        config: BCR configuration (defaults to all modules included)

    Returns:
        Dictionary with BCR metrics (both nominal and PV)
    """
    if config is None:
        config = BCRConfig.default()
    # Present value metrics
    # Use conservative (haircut) benefits for all BCR calculations
    total_benefits_pv = benefits["total_benefits_haircut_pv"]
    total_costs_pv = costs["total_costs_pv"]
    capital_costs_pv = costs["capital_costs_pv"]
    risk_costs_pv = costs["risk_costs_pv"]  # Wildfire + Outage + Wildfire Liability
    energy_emissions_costs_pv = costs[
        "energy_emissions_costs_pv"
    ]  # Line Losses + Emissions

    # Separate emissions and energy losses (total = conductor + converter) for individual calculations
    emissions_pv = safe_get_numeric(costs, "emissions_cost_pv")
    energy_losses_pv = safe_get_numeric(costs, "energy_losses_pv")

    # Separate wildfire and outage risk for individual calculations
    wildfire_pv = safe_get_numeric(costs, "wildfire_pv")
    outage_pv = safe_get_numeric(costs, "outage_pv")
    wildfire_liability_pv = safe_get_numeric(costs, "wildfire_liability_insurance_pv")
    # Wildfire risk = wildfire + wildfire liability (grouped together)
    wildfire_risk_pv = wildfire_pv + wildfire_liability_pv

    # Extract benefit components early (needed for utility/TSP and ratepayer calculations)
    congestion_benefit_pv = safe_get_numeric(benefits, "congestion_benefit_haircut_pv")
    curtailment_benefit_pv = safe_get_numeric(
        benefits, "curtailment_benefit_haircut_pv"
    )
    delivered_benefit_pv = safe_get_numeric(benefits, "delivered_benefit_pv")
    revenue_pv = safe_get_numeric(benefits, "revenue_pv")

    # Nominal metrics
    total_benefits_nominal = benefits["total_benefits_nominal"]
    total_costs_nominal = costs["total_costs_nominal"]

    # Calculate costs excluding risk (wildfire + outage + wildfire liability)
    total_costs_excluding_risk_pv = total_costs_pv - risk_costs_pv

    # Calculate costs excluding only emissions (keep energy losses)
    total_costs_excluding_emissions_pv = total_costs_pv - emissions_pv

    # Calculate costs excluding only energy losses (keep emissions)
    total_costs_excluding_linelosses_pv = total_costs_pv - energy_losses_pv

    # Calculate costs excluding emissions and energy losses (keep risk)
    total_costs_excluding_emissions_and_linelosses_pv = (
        total_costs_pv - energy_emissions_costs_pv
    )

    # Calculate costs excluding emissions and risk (keep energy losses)
    total_costs_excluding_emissions_and_risk_pv = (
        total_costs_pv - emissions_pv - risk_costs_pv
    )

    # Calculate costs excluding energy losses and risk (keep emissions)
    total_costs_excluding_linelosses_and_risk_pv = (
        total_costs_pv - energy_losses_pv - risk_costs_pv
    )

    # Calculate costs excluding emissions, energy losses, and risk (all three)
    total_costs_excluding_emissions_and_linelosses_and_risk_pv = (
        total_costs_pv - energy_emissions_costs_pv - risk_costs_pv
    )

    # Calculate costs excluding wildfire risk only (4 combinations)
    total_costs_excluding_wildfire_risk_pv = total_costs_pv - wildfire_risk_pv
    total_costs_excluding_emissions_and_wildfire_risk_pv = (
        total_costs_pv - emissions_pv - wildfire_risk_pv
    )
    total_costs_excluding_linelosses_and_wildfire_risk_pv = (
        total_costs_pv - energy_losses_pv - wildfire_risk_pv
    )
    total_costs_excluding_emissions_and_linelosses_and_wildfire_risk_pv = (
        total_costs_pv - energy_emissions_costs_pv - wildfire_risk_pv
    )

    # Calculate costs excluding outage risk only (4 combinations)
    total_costs_excluding_outage_risk_pv = total_costs_pv - outage_pv
    total_costs_excluding_emissions_and_outage_risk_pv = (
        total_costs_pv - emissions_pv - outage_pv
    )
    total_costs_excluding_linelosses_and_outage_risk_pv = (
        total_costs_pv - energy_losses_pv - outage_pv
    )
    total_costs_excluding_emissions_and_linelosses_and_outage_risk_pv = (
        total_costs_pv - energy_emissions_costs_pv - outage_pv
    )

    # Rename existing combined risk exclusions to wildfire_risk_and_outage_risk (4 combinations)
    total_costs_excluding_wildfire_risk_and_outage_risk_pv = (
        total_costs_excluding_risk_pv
    )
    total_costs_excluding_emissions_and_wildfire_risk_and_outage_risk_pv = (
        total_costs_excluding_emissions_and_risk_pv
    )
    total_costs_excluding_linelosses_and_wildfire_risk_and_outage_risk_pv = (
        total_costs_excluding_linelosses_and_risk_pv
    )
    total_costs_excluding_emissions_and_linelosses_and_wildfire_risk_and_outage_risk_pv = (
        total_costs_excluding_emissions_and_linelosses_and_risk_pv
    )

    # Calculate capital + delay costs
    delay_costs_pv = safe_get_numeric(costs, "delay_costs_pv")
    capital_and_delay_costs_pv = capital_costs_pv + delay_costs_pv

    # Prevent division by zero
    # All BCRs use conservative (haircut) benefits
    bcr_system = safe_divide(total_benefits_pv, total_costs_pv)
    bcr_capital = safe_divide(total_benefits_pv, capital_costs_pv)
    bcr_capital_and_delay = safe_divide(total_benefits_pv, capital_and_delay_costs_pv)
    bcr_excluding_risk = safe_divide(total_benefits_pv, total_costs_excluding_risk_pv)
    bcr_excluding_emissions = safe_divide(
        total_benefits_pv, total_costs_excluding_emissions_pv
    )
    bcr_excluding_linelosses = safe_divide(
        total_benefits_pv, total_costs_excluding_linelosses_pv
    )
    bcr_excluding_emissions_and_linelosses = safe_divide(
        total_benefits_pv, total_costs_excluding_emissions_and_linelosses_pv
    )
    bcr_excluding_emissions_and_risk = safe_divide(
        total_benefits_pv, total_costs_excluding_emissions_and_risk_pv
    )
    bcr_excluding_linelosses_and_risk = safe_divide(
        total_benefits_pv, total_costs_excluding_linelosses_and_risk_pv
    )
    bcr_excluding_emissions_and_linelosses_and_risk = safe_divide(
        total_benefits_pv, total_costs_excluding_emissions_and_linelosses_and_risk_pv
    )

    # BCR metrics excluding wildfire risk only (4 combinations)
    bcr_excluding_wildfire_risk = safe_divide(
        total_benefits_pv, total_costs_excluding_wildfire_risk_pv
    )
    bcr_excluding_emissions_and_wildfire_risk = safe_divide(
        total_benefits_pv, total_costs_excluding_emissions_and_wildfire_risk_pv
    )
    bcr_excluding_linelosses_and_wildfire_risk = safe_divide(
        total_benefits_pv, total_costs_excluding_linelosses_and_wildfire_risk_pv
    )
    bcr_excluding_emissions_and_linelosses_and_wildfire_risk = safe_divide(
        total_benefits_pv,
        total_costs_excluding_emissions_and_linelosses_and_wildfire_risk_pv,
    )

    # BCR metrics excluding outage risk only (4 combinations)
    bcr_excluding_outage_risk = safe_divide(
        total_benefits_pv, total_costs_excluding_outage_risk_pv
    )
    bcr_excluding_emissions_and_outage_risk = safe_divide(
        total_benefits_pv, total_costs_excluding_emissions_and_outage_risk_pv
    )
    bcr_excluding_linelosses_and_outage_risk = safe_divide(
        total_benefits_pv, total_costs_excluding_linelosses_and_outage_risk_pv
    )
    bcr_excluding_emissions_and_linelosses_and_outage_risk = safe_divide(
        total_benefits_pv,
        total_costs_excluding_emissions_and_linelosses_and_outage_risk_pv,
    )

    # Rename existing combined BCR metrics to wildfire_risk_and_outage_risk (4 combinations)
    bcr_excluding_wildfire_risk_and_outage_risk = bcr_excluding_risk
    bcr_excluding_emissions_and_wildfire_risk_and_outage_risk = (
        bcr_excluding_emissions_and_risk
    )
    bcr_excluding_linelosses_and_wildfire_risk_and_outage_risk = (
        bcr_excluding_linelosses_and_risk
    )
    bcr_excluding_emissions_and_linelosses_and_wildfire_risk_and_outage_risk = (
        bcr_excluding_emissions_and_linelosses_and_risk
    )

    # Utility/TSP Perspective
    # Benefits: Only revenue (rate base recovery)
    utility_benefits_pv = revenue_pv
    # Costs: What utility actually pays (capital + delay + operational)
    operational_costs_pv = safe_get_numeric(costs, "operational_costs_pv")
    utility_costs_pv = capital_costs_pv + delay_costs_pv + operational_costs_pv
    bcr_utility = safe_divide(utility_benefits_pv, utility_costs_pv)
    net_benefit_utility_pv = utility_benefits_pv - utility_costs_pv

    # Ratepayer Perspective
    # Benefits: What ratepayers receive (congestion + curtailment + delivered energy)
    ratepayer_benefits_pv = (
        congestion_benefit_pv + curtailment_benefit_pv + delivered_benefit_pv
    )
    # Costs: What ratepayers pay (revenue/rate base + energy losses socialized through rates)
    ratepayer_costs_pv = revenue_pv + energy_losses_pv
    bcr_ratepayer = safe_divide(ratepayer_benefits_pv, ratepayer_costs_pv)
    net_benefit_ratepayer_pv = ratepayer_benefits_pv - ratepayer_costs_pv

    # Net benefits (using conservative benefits)
    net_benefit_pv = total_benefits_pv - total_costs_pv
    net_benefit_nominal = total_benefits_nominal - total_costs_nominal
    net_benefit_excluding_risk_pv = total_benefits_pv - total_costs_excluding_risk_pv
    net_benefit_excluding_emissions_pv = (
        total_benefits_pv - total_costs_excluding_emissions_pv
    )
    net_benefit_excluding_linelosses_pv = (
        total_benefits_pv - total_costs_excluding_linelosses_pv
    )
    net_benefit_excluding_emissions_and_linelosses_pv = (
        total_benefits_pv - total_costs_excluding_emissions_and_linelosses_pv
    )
    net_benefit_excluding_emissions_and_risk_pv = (
        total_benefits_pv - total_costs_excluding_emissions_and_risk_pv
    )
    net_benefit_excluding_linelosses_and_risk_pv = (
        total_benefits_pv - total_costs_excluding_linelosses_and_risk_pv
    )
    net_benefit_excluding_emissions_and_linelosses_and_risk_pv = (
        total_benefits_pv - total_costs_excluding_emissions_and_linelosses_and_risk_pv
    )

    # Net benefit metrics excluding wildfire risk only (4 combinations)
    net_benefit_excluding_wildfire_risk_pv = (
        total_benefits_pv - total_costs_excluding_wildfire_risk_pv
    )
    net_benefit_excluding_emissions_and_wildfire_risk_pv = (
        total_benefits_pv - total_costs_excluding_emissions_and_wildfire_risk_pv
    )
    net_benefit_excluding_linelosses_and_wildfire_risk_pv = (
        total_benefits_pv - total_costs_excluding_linelosses_and_wildfire_risk_pv
    )
    net_benefit_excluding_emissions_and_linelosses_and_wildfire_risk_pv = (
        total_benefits_pv
        - total_costs_excluding_emissions_and_linelosses_and_wildfire_risk_pv
    )

    # Net benefit metrics excluding outage risk only (4 combinations)
    net_benefit_excluding_outage_risk_pv = (
        total_benefits_pv - total_costs_excluding_outage_risk_pv
    )
    net_benefit_excluding_emissions_and_outage_risk_pv = (
        total_benefits_pv - total_costs_excluding_emissions_and_outage_risk_pv
    )
    net_benefit_excluding_linelosses_and_outage_risk_pv = (
        total_benefits_pv - total_costs_excluding_linelosses_and_outage_risk_pv
    )
    net_benefit_excluding_emissions_and_linelosses_and_outage_risk_pv = (
        total_benefits_pv
        - total_costs_excluding_emissions_and_linelosses_and_outage_risk_pv
    )

    # Rename existing combined net benefit metrics to wildfire_risk_and_outage_risk (4 combinations)
    net_benefit_excluding_wildfire_risk_and_outage_risk_pv = (
        net_benefit_excluding_risk_pv
    )
    net_benefit_excluding_emissions_and_wildfire_risk_and_outage_risk_pv = (
        net_benefit_excluding_emissions_and_risk_pv
    )
    net_benefit_excluding_linelosses_and_wildfire_risk_and_outage_risk_pv = (
        net_benefit_excluding_linelosses_and_risk_pv
    )
    net_benefit_excluding_emissions_and_linelosses_and_wildfire_risk_and_outage_risk_pv = (
        net_benefit_excluding_emissions_and_linelosses_and_risk_pv
    )

    net_benefit_capital_only_pv = total_benefits_pv - capital_costs_pv
    net_benefit_capital_and_delay_pv = total_benefits_pv - capital_and_delay_costs_pv

    # Calculate Primary BCR
    # Always calculate from flags - if no flags are set (all False), calculation includes everything = System BCR
    # If flags are set, calculation excludes disabled modules = Custom BCR
    # Primary benefits = congestion + curtailment + delivered energy (per config). Revenue is excluded as a transfer.

    primary_benefits_pv = 0.0
    if not config.no_congestion:
        primary_benefits_pv += congestion_benefit_pv
    if not config.no_curtailment:
        primary_benefits_pv += curtailment_benefit_pv
    primary_benefits_pv += delivered_benefit_pv

    # Costs included:
    # - Capital costs (always: build, ROW, environmental)
    # - Delay costs (always included, even if --no_delay_costs flag is set)
    # - O&M (if not no_oandm)
    # - Insurance (if not no_insurance)
    # - Wildfire (if not no_wildfire)
    # - Outage (if not no_outages)
    # - Energy losses (if not no_linelosses)
    # - Emissions (if not no_emissions)
    wildfire_pv = safe_get_numeric(costs, "wildfire_pv")
    outage_pv = safe_get_numeric(costs, "outage_pv")
    wildfire_liability_pv = safe_get_numeric(costs, "wildfire_liability_insurance_pv")
    oandm_pv = safe_get_numeric(costs, "oandm_pv")
    insurance_pv = safe_get_numeric(costs, "insurance_pv")

    primary_costs_pv = capital_costs_pv + delay_costs_pv
    if not config.no_oandm:
        primary_costs_pv += oandm_pv
    if not config.no_insurance:
        primary_costs_pv += insurance_pv
    if not config.no_wildfire:
        primary_costs_pv += wildfire_pv + wildfire_liability_pv
    if not config.no_outages:
        primary_costs_pv += outage_pv
    if not config.no_linelosses:
        primary_costs_pv += energy_losses_pv
    if not config.no_emissions:
        primary_costs_pv += emissions_pv

    # Calculate Primary BCR
    bcr_primary = safe_divide(primary_benefits_pv, primary_costs_pv)
    net_benefit_primary_pv = primary_benefits_pv - primary_costs_pv

    result = {
        "bcr_system": bcr_system,
        "bcr_capital": bcr_capital,
        "bcr_capital_and_delay": bcr_capital_and_delay,
        "bcr_primary": bcr_primary,
        # Renamed combined risk BCRs
        "bcr_excluding_wildfire_risk_and_outage_risk": bcr_excluding_wildfire_risk_and_outage_risk,
        "bcr_excluding_emissions_and_wildfire_risk_and_outage_risk": bcr_excluding_emissions_and_wildfire_risk_and_outage_risk,
        "bcr_excluding_linelosses_and_wildfire_risk_and_outage_risk": bcr_excluding_linelosses_and_wildfire_risk_and_outage_risk,
        "bcr_excluding_emissions_and_linelosses_and_wildfire_risk_and_outage_risk": bcr_excluding_emissions_and_linelosses_and_wildfire_risk_and_outage_risk,
        # Existing emissions/linelosses BCRs (unchanged)
        "bcr_excluding_emissions": bcr_excluding_emissions,
        "bcr_excluding_linelosses": bcr_excluding_linelosses,
        "bcr_excluding_emissions_and_linelosses": bcr_excluding_emissions_and_linelosses,
        # New wildfire-only BCRs
        "bcr_excluding_wildfire_risk": bcr_excluding_wildfire_risk,
        "bcr_excluding_emissions_and_wildfire_risk": bcr_excluding_emissions_and_wildfire_risk,
        "bcr_excluding_linelosses_and_wildfire_risk": bcr_excluding_linelosses_and_wildfire_risk,
        "bcr_excluding_emissions_and_linelosses_and_wildfire_risk": bcr_excluding_emissions_and_linelosses_and_wildfire_risk,
        # New outage-only BCRs
        "bcr_excluding_outage_risk": bcr_excluding_outage_risk,
        "bcr_excluding_emissions_and_outage_risk": bcr_excluding_emissions_and_outage_risk,
        "bcr_excluding_linelosses_and_outage_risk": bcr_excluding_linelosses_and_outage_risk,
        "bcr_excluding_emissions_and_linelosses_and_outage_risk": bcr_excluding_emissions_and_linelosses_and_outage_risk,
        # Stakeholder perspectives
        "bcr_utility": bcr_utility,
        "bcr_ratepayer": bcr_ratepayer,
        # Net benefits
        "net_benefit_pv": net_benefit_pv,
        "net_benefit_nominal": net_benefit_nominal,
        "net_benefit_primary_pv": net_benefit_primary_pv,
        # Renamed combined risk net benefits
        "net_benefit_excluding_wildfire_risk_and_outage_risk_pv": net_benefit_excluding_wildfire_risk_and_outage_risk_pv,
        "net_benefit_excluding_emissions_and_wildfire_risk_and_outage_risk_pv": net_benefit_excluding_emissions_and_wildfire_risk_and_outage_risk_pv,
        "net_benefit_excluding_linelosses_and_wildfire_risk_and_outage_risk_pv": net_benefit_excluding_linelosses_and_wildfire_risk_and_outage_risk_pv,
        "net_benefit_excluding_emissions_and_linelosses_and_wildfire_risk_and_outage_risk_pv": net_benefit_excluding_emissions_and_linelosses_and_wildfire_risk_and_outage_risk_pv,
        # Existing emissions/linelosses net benefits (unchanged)
        "net_benefit_excluding_emissions_pv": net_benefit_excluding_emissions_pv,
        "net_benefit_excluding_linelosses_pv": net_benefit_excluding_linelosses_pv,
        "net_benefit_excluding_emissions_and_linelosses_pv": net_benefit_excluding_emissions_and_linelosses_pv,
        # New wildfire-only net benefits
        "net_benefit_excluding_wildfire_risk_pv": net_benefit_excluding_wildfire_risk_pv,
        "net_benefit_excluding_emissions_and_wildfire_risk_pv": net_benefit_excluding_emissions_and_wildfire_risk_pv,
        "net_benefit_excluding_linelosses_and_wildfire_risk_pv": net_benefit_excluding_linelosses_and_wildfire_risk_pv,
        "net_benefit_excluding_emissions_and_linelosses_and_wildfire_risk_pv": net_benefit_excluding_emissions_and_linelosses_and_wildfire_risk_pv,
        # New outage-only net benefits
        "net_benefit_excluding_outage_risk_pv": net_benefit_excluding_outage_risk_pv,
        "net_benefit_excluding_emissions_and_outage_risk_pv": net_benefit_excluding_emissions_and_outage_risk_pv,
        "net_benefit_excluding_linelosses_and_outage_risk_pv": net_benefit_excluding_linelosses_and_outage_risk_pv,
        "net_benefit_excluding_emissions_and_linelosses_and_outage_risk_pv": net_benefit_excluding_emissions_and_linelosses_and_outage_risk_pv,
        # Capital and stakeholder net benefits
        "net_benefit_capital_only_pv": net_benefit_capital_only_pv,
        "net_benefit_capital_and_delay_pv": net_benefit_capital_and_delay_pv,
        "net_benefit_utility_pv": net_benefit_utility_pv,
        "net_benefit_ratepayer_pv": net_benefit_ratepayer_pv,
        # Total costs exclusions (for reference)
        "total_costs_excluding_wildfire_risk_and_outage_risk_pv": total_costs_excluding_wildfire_risk_and_outage_risk_pv,
        "total_costs_excluding_emissions_and_wildfire_risk_and_outage_risk_pv": total_costs_excluding_emissions_and_wildfire_risk_and_outage_risk_pv,
        "total_costs_excluding_linelosses_and_wildfire_risk_and_outage_risk_pv": total_costs_excluding_linelosses_and_wildfire_risk_and_outage_risk_pv,
        "total_costs_excluding_emissions_and_linelosses_and_wildfire_risk_and_outage_risk_pv": total_costs_excluding_emissions_and_linelosses_and_wildfire_risk_and_outage_risk_pv,
        "total_costs_excluding_emissions_pv": total_costs_excluding_emissions_pv,
        "total_costs_excluding_linelosses_pv": total_costs_excluding_linelosses_pv,
        "total_costs_excluding_emissions_and_linelosses_pv": total_costs_excluding_emissions_and_linelosses_pv,
        "total_costs_excluding_wildfire_risk_pv": total_costs_excluding_wildfire_risk_pv,
        "total_costs_excluding_emissions_and_wildfire_risk_pv": total_costs_excluding_emissions_and_wildfire_risk_pv,
        "total_costs_excluding_linelosses_and_wildfire_risk_pv": total_costs_excluding_linelosses_and_wildfire_risk_pv,
        "total_costs_excluding_emissions_and_linelosses_and_wildfire_risk_pv": total_costs_excluding_emissions_and_linelosses_and_wildfire_risk_pv,
        "total_costs_excluding_outage_risk_pv": total_costs_excluding_outage_risk_pv,
        "total_costs_excluding_emissions_and_outage_risk_pv": total_costs_excluding_emissions_and_outage_risk_pv,
        "total_costs_excluding_linelosses_and_outage_risk_pv": total_costs_excluding_linelosses_and_outage_risk_pv,
        "total_costs_excluding_emissions_and_linelosses_and_outage_risk_pv": total_costs_excluding_emissions_and_linelosses_and_outage_risk_pv,
    }

    return result


def calculate_and_display_bcr(
    scenario_id: str,
    output_dir: str = str(OUTPUTS_DIR),
    config: BCRConfig = None,
) -> Optional[Dict[str, Any]]:
    """
    Main function to calculate and display BCR analysis.
    Always attempts to return results even if some calculations fail.

    Args:
        scenario_id: Unique identifier for the scenario
        output_dir: Directory containing batch_summary.csv
        config: BCR configuration (defaults to all modules included)

    Returns:
        Dictionary with all BCR results, or None only if CSV doesn't exist or is empty
    """
    if config is None:
        config = BCRConfig.default()

    # Load scenario data (now with robust lookup)
    data = load_scenario_data(scenario_id, output_dir)
    if data is None:
        print(f"Error: Could not load scenario data for '{scenario_id}'")
        return None

    # Calculate benefits and costs with error handling
    try:
        benefits = calculate_benefits(data)
    except Exception as e:
        import traceback

        traceback.print_exc()
        print(f"Warning: Error calculating benefits: {e}")
        # Return partial results with zero benefits
        benefits = {
            "congestion_benefit_pv": 0,
            "curtailment_benefit_pv": 0,
            "revenue_pv": 0,
            "total_benefits_pv": 0,
            "total_benefits_nominal": 0,
            "total_benefits_haircut_pv": 0,
        }

    try:
        costs = calculate_costs(data)
    except Exception as e:
        import traceback

        traceback.print_exc()
        print(f"Warning: Error calculating costs: {e}")
        # Return partial results with zero costs
        costs = {
            "capital_costs_pv": 0,
            "operational_costs_pv": 0,
            "energy_emissions_costs_pv": 0,
            "risk_costs_pv": 0,
            "delay_costs_pv": 0,
            "total_costs_pv": 0,
        }

    # Calculate BCR metrics with error handling
    try:
        bcr_metrics = calculate_bcr_metrics(
            benefits,
            costs,
            config=config,
        )
    except Exception as e:
        import traceback

        traceback.print_exc()
        print(f"Warning: Error calculating BCR metrics: {e}")
        # Return zero BCR metrics if calculation fails (use new metric names)
        bcr_metrics = {
            "bcr_system": 0,
            "bcr_capital": 0,
            "bcr_capital_and_delay": 0,
            "bcr_primary": 0,
            "bcr_excluding_wildfire_risk_and_outage_risk": 0,
            "bcr_excluding_emissions": 0,
            "bcr_excluding_emissions_and_wildfire_risk_and_outage_risk": 0,
            "net_benefit_pv": 0,
            "net_benefit_nominal": 0,
            "net_benefit_primary_pv": 0,
            "net_benefit_excluding_wildfire_risk_and_outage_risk_pv": 0,
        }

    # Combine all results (always return something, even if partial)
    results = {
        **benefits,
        **costs,
        **bcr_metrics,
    }

    # Display results (only if not in simple mode - check via environment or suppress)
    try:
        print_bcr_summary(
            benefits,
            costs,
            bcr_metrics,
            data,
            config=config,
        )
    except Exception as e:
        # Don't fail if printing fails, but log it
        pass

    return results


def print_bcr_summary(
    benefits: Dict[str, float],
    costs: Dict[str, float],
    bcr_metrics: Dict[str, float],
    data: Dict[str, Any],
    config: BCRConfig = None,
) -> None:
    """
    Print formatted BCR summary to terminal.

    Args:
        benefits: Dictionary with benefit breakdown
        costs: Dictionary with cost breakdown
        bcr_metrics: Dictionary with BCR metrics
        data: Original scenario data
        config: BCR configuration (defaults to all modules included)
    """
    if config is None:
        config = BCRConfig.default()

    # Check if any custom flags are set (for display purposes)
    has_custom_flags = any(
        [
            config.no_wildfire,
            config.no_outages,
            config.no_oandm,
            config.no_insurance,
            config.no_delay_costs,
            config.no_congestion,
            config.no_curtailment,
            config.no_emissions,
            config.no_linelosses,
        ]
    )

    print()
    print("=" * 80)
    print("BENEFIT-COST RATIO ANALYSIS")
    print("=" * 80)
    print()

    # Display Primary BCR prominently
    print("PRIMARY BCR:")
    if not has_custom_flags:
        print("  (All modules included - equals System BCR)")
    else:
        print("  (Custom calculation based on selected modules)")
    print(f"  Primary BCR:                  {bcr_metrics.get('bcr_primary', 0):>6.3f}")
    net_benefit_primary = bcr_metrics.get("net_benefit_primary_pv", 0)
    print(f"  Net Benefit (PV):              ${net_benefit_primary:>15,.0f}")
    print()

    # Benefits section
    print("BENEFITS (Present Value):")
    print(
        f"  Congestion Reduction (haircut): ${benefits['congestion_benefit_haircut_pv']:>15,.0f}"
    )
    print(
        f"  Curtailment Reduction (haircut): ${benefits['curtailment_benefit_haircut_pv']:>15,.0f}"
    )

    energy_losses_pv = safe_get_numeric(data, "energy_losses_pv") or safe_get_numeric(
        data, "line_loss_cost_pv"
    )
    # Energy losses are always costs (positive) for both greenfield and reconductoring
    # Don't display in benefits section - they're shown in costs section below
    # if line_loss_pv > 0:
    #     print(
    #         f"  Line Loss Cost:              ${line_loss_pv:>15,.0f}  (cost - see below)"
    #     )

    # Add revenue display
    revenue_pv = safe_get_numeric(benefits, "revenue_pv")
    if revenue_pv > 0:
        print(f"  Revenue (Rate-Based):        ${revenue_pv:>15,.0f}")

    print("  " + "-" * 78)
    print(
        f"  Total Benefits (haircut):    ${benefits['total_benefits_haircut_pv']:>15,.0f}"
    )
    print("  (societal; excludes revenue transfer)")
    print()

    # Costs section
    print("COSTS (Present Value):")
    print("  Capital Costs:")
    print(f"    Build:                     ${costs['build_cost_pv']:>15,.0f}")
    print(f"    Right-of-Way (capital):    ${costs['row_capital_pv']:>15,.0f}")
    print(f"    Environmental:             ${costs['env_mitigation_pv']:>15,.0f}")
    print(f"    Subtotal:                  ${costs['capital_costs_pv']:>15,.0f}")
    print()
    print("  Operational Costs:")
    print(f"    O&M:                       ${costs['oandm_pv']:>15,.0f}")
    print(f"    Insurance (operational):  ${costs['insurance_pv']:>15,.0f}")
    row_rent_pv = costs.get("row_rent_pv", 0) or 0
    if row_rent_pv > 0:
        print(f"    ROW rent (operational):    ${row_rent_pv:>15,.0f}")
    print(f"    Subtotal:                  ${costs['operational_costs_pv']:>15,.0f}")
    print()
    print("  Energy & Emissions Costs:")
    converter_loss_pv = costs.get("converter_loss_pv", 0) or 0
    conductor_loss_pv = costs.get("conductor_loss_pv", 0) or 0
    energy_losses_pv = costs.get("energy_losses_pv", 0) or 0
    if converter_loss_pv > 0:
        print(f"    Converter Losses:          ${converter_loss_pv:>15,.0f}")
        print(f"    Conductor Losses:          ${conductor_loss_pv:>15,.0f}")
    else:
        print(f"    Energy Losses:             ${energy_losses_pv:>15,.0f}")
    print(f"    Residual Exceedance:       ${costs['residual_exceedance_pv']:>15,.0f}")
    print(f"    Emissions:                 ${costs['emissions_cost_pv']:>15,.0f}")
    print(
        f"    Subtotal:                  ${costs['energy_emissions_costs_pv']:>15,.0f}"
    )
    print()
    print("  Risk Costs:")
    print(f"    Wildfire:                  ${costs['wildfire_pv']:>15,.0f}")
    print(f"    Outage:                    ${costs['outage_pv']:>15,.0f}")
    wf_liab_pv = costs.get("wildfire_liability_insurance_pv", 0) or 0
    if wf_liab_pv > 0:
        print(f"    Insurance (wildfire liab): ${wf_liab_pv:>15,.0f}")
    else:
        yaml_enabled = False
        try:
            with open(YAMLS_DIR / "04_insurance.yaml", "r") as f:
                cfg = yaml.safe_load(f)
            yaml_enabled = (
                cfg.get("insurance", {})
                .get("wildfire_liability", {})
                .get("enabled", False)
            )
        except Exception:
            pass
        dev_flag_set = "CTCC_NO_WF_LIABILITY" in os.environ
        if not yaml_enabled and dev_flag_set:
            msg = "both flags false, not calculated"
        elif not yaml_enabled:
            msg = "yaml flag false, not calculated"
        elif dev_flag_set:
            msg = "dev flag false, not calculated"
        else:
            msg = "not calculated"
        print(f"    Insurance (wildfire liab):  {msg}")
    print(f"    Subtotal:                  ${costs['risk_costs_pv']:>15,.0f}")
    print()
    print("  Delay Costs:")
    print(f"    Construction Delay:        ${costs['delay_cost_pv']:>15,.0f}")
    print(
        f"    Congestion Delay:          ${costs['congestion_delay_cost_pv']:>15,.0f}"
    )
    print(
        f"    Curtailment Delay:         ${costs['curtailment_delay_cost_pv']:>15,.0f}"
    )
    print(f"    Subtotal:                  ${costs['delay_costs_pv']:>15,.0f}")
    print()
    print("  " + "-" * 78)
    print(f"  Total Costs:                 ${costs['total_costs_pv']:>15,.0f}")
    print()

    # BCR metrics
    print("BENEFIT-COST RATIOS:")

    # Primary BCR (prominently displayed first)
    bcr_primary = bcr_metrics.get("bcr_primary", 0)
    primary_viable_symbol, primary_viable_text = format_bcr_viability(bcr_primary)
    if not has_custom_flags:
        primary_label = "Primary BCR (all modules):"
    else:
        primary_label = "Primary BCR (custom):"
    print(
        f"  {primary_label:28s} {bcr_primary:>6.3f}  {primary_viable_symbol} ({primary_viable_text})"
    )
    print()

    bcr_system = bcr_metrics["bcr_system"]
    viable_symbol, viable_text = format_bcr_viability(bcr_system)

    print(
        f"  System BCR (conservative):    {bcr_system:>6.3f}  {viable_symbol} ({viable_text})"
    )
    print(f"  Capital BCR:                 {bcr_metrics['bcr_capital']:>6.3f}")
    print(
        f"  Capital + Delay BCR:         {bcr_metrics['bcr_capital_and_delay']:>6.3f}"
    )
    print()

    # Utility/TSP Perspective
    bcr_utility = bcr_metrics.get("bcr_utility", 0)
    utility_viable_symbol, utility_viable_text = format_bcr_viability(bcr_utility)
    print(
        f"  Utility/TSP BCR:            {bcr_utility:>6.3f}  {utility_viable_symbol} ({utility_viable_text})"
    )

    # Ratepayer Perspective
    bcr_ratepayer = bcr_metrics.get("bcr_ratepayer", 0)
    ratepayer_viable_symbol, ratepayer_viable_text = format_bcr_viability(bcr_ratepayer)
    print(
        f"  Ratepayer BCR:               {bcr_ratepayer:>6.3f}  {ratepayer_viable_symbol} ({ratepayer_viable_text})"
    )
    print()

    # Print all BCRs systematically (8 combined + 4 wildfire-only + 4 outage-only = 16 total exclusion BCRs)
    risk_costs_pv = costs["risk_costs_pv"]
    emissions_pv = safe_get_numeric(costs, "emissions_cost_pv")
    energy_losses_pv = safe_get_numeric(costs, "energy_losses_pv")
    energy_emissions_costs_pv = costs["energy_emissions_costs_pv"]

    # 1. No exclusions (already shown above as System BCR)

    # 2. Exclude risk only
    bcr_excluding_risk = bcr_metrics.get(
        "bcr_excluding_wildfire_risk_and_outage_risk",
        bcr_metrics.get("bcr_excluding_risk", 0),
    )
    viable_symbol_norisk, viable_text_norisk = format_bcr_viability(bcr_excluding_risk)
    print(
        f"  System BCR (excl. risk):     {bcr_excluding_risk:>6.3f}  {viable_symbol_norisk} ({viable_text_norisk})"
    )
    print(f"    (Excludes ${risk_costs_pv:>15,.0f} in wildfire/outage/liability costs)")

    # 3. Exclude emissions only
    bcr_excluding_emissions = bcr_metrics["bcr_excluding_emissions"]
    viable_symbol_emissions, viable_text_emissions = format_bcr_viability(
        bcr_excluding_emissions
    )
    print(
        f"  System BCR (excl. emissions): {bcr_excluding_emissions:>6.3f}  {viable_symbol_emissions} ({viable_text_emissions})"
    )
    print(
        f"    (Excludes ${emissions_pv:>15,.0f} in emissions costs, keeps energy losses)"
    )

    # 4. Exclude energy losses only
    bcr_excluding_linelosses = bcr_metrics["bcr_excluding_linelosses"]
    viable_symbol_linelosses, viable_text_linelosses = format_bcr_viability(
        bcr_excluding_linelosses
    )
    print(
        f"  System BCR (excl. energy losses): {bcr_excluding_linelosses:>6.3f}  {viable_symbol_linelosses} ({viable_text_linelosses})"
    )
    print(
        f"    (Excludes ${energy_losses_pv:>15,.0f} in energy loss costs, keeps emissions)"
    )

    # 5. Exclude emissions and line losses
    bcr_excluding_emissions_and_linelosses = bcr_metrics[
        "bcr_excluding_emissions_and_linelosses"
    ]
    viable_symbol_emissions_linelosses, viable_text_emissions_linelosses = (
        format_bcr_viability(bcr_excluding_emissions_and_linelosses)
    )
    print(
        f"  System BCR (excl. emissions & line losses): {bcr_excluding_emissions_and_linelosses:>6.3f}  {viable_symbol_emissions_linelosses} ({viable_text_emissions_linelosses})"
    )
    print(
        f"    (Excludes ${energy_emissions_costs_pv:>15,.0f} in emissions + energy losses costs)"
    )

    # 6. Exclude emissions and risk
    bcr_excluding_emissions_and_risk = bcr_metrics.get(
        "bcr_excluding_emissions_and_wildfire_risk_and_outage_risk",
        bcr_metrics.get("bcr_excluding_emissions_and_risk", 0),
    )
    viable_symbol_emissions_risk, viable_text_emissions_risk = format_bcr_viability(
        bcr_excluding_emissions_and_risk
    )
    excluded_emissions_risk = emissions_pv + risk_costs_pv
    print(
        f"  System BCR (excl. emissions & risk): {bcr_excluding_emissions_and_risk:>6.3f}  {viable_symbol_emissions_risk} ({viable_text_emissions_risk})"
    )
    print(
        f"    (Excludes ${excluded_emissions_risk:>15,.0f} in emissions + risk costs, keeps energy losses)"
    )

    # 7. Exclude energy losses and risk
    bcr_excluding_linelosses_and_risk = bcr_metrics.get(
        "bcr_excluding_linelosses_and_wildfire_risk_and_outage_risk",
        bcr_metrics.get("bcr_excluding_linelosses_and_risk", 0),
    )
    viable_symbol_linelosses_risk, viable_text_linelosses_risk = format_bcr_viability(
        bcr_excluding_linelosses_and_risk
    )
    excluded_linelosses_risk = energy_losses_pv + risk_costs_pv
    print(
        f"  System BCR (excl. energy losses & risk): {bcr_excluding_linelosses_and_risk:>6.3f}  {viable_symbol_linelosses_risk} ({viable_text_linelosses_risk})"
    )
    print(
        f"    (Excludes ${excluded_linelosses_risk:>15,.0f} in energy losses + risk costs, keeps emissions)"
    )

    # 8. Exclude emissions, line losses, and risk (all three)
    bcr_excluding_emissions_and_linelosses_and_risk = bcr_metrics.get(
        "bcr_excluding_emissions_and_linelosses_and_wildfire_risk_and_outage_risk",
        bcr_metrics.get("bcr_excluding_emissions_and_linelosses_and_risk", 0),
    )
    viable_symbol_all_three, viable_text_all_three = format_bcr_viability(
        bcr_excluding_emissions_and_linelosses_and_risk
    )
    excluded_all_three = energy_emissions_costs_pv + risk_costs_pv
    print(
        f"  System BCR (excl. emissions & line losses & risk): {bcr_excluding_emissions_and_linelosses_and_risk:>6.3f}  {viable_symbol_all_three} ({viable_text_all_three})"
    )
    print(
        f"    (Excludes ${excluded_all_three:>15,.0f} in emissions + energy losses + risk costs)"
    )
    print()

    # Print wildfire-only BCRs (4 combinations)
    wildfire_risk_pv = safe_get_numeric(costs, "wildfire_pv")
    wildfire_liability_insurance_pv = safe_get_numeric(
        costs, "wildfire_liability_insurance_pv"
    )
    wildfire_risk_total_pv = wildfire_risk_pv + wildfire_liability_insurance_pv

    print("  Wildfire-Only Exclusions:")
    bcr_excluding_wildfire_risk = bcr_metrics.get("bcr_excluding_wildfire_risk", 0)
    viable_symbol_wf, viable_text_wf = format_bcr_viability(bcr_excluding_wildfire_risk)
    print(
        f"    BCR (excl. wildfire risk): {bcr_excluding_wildfire_risk:>6.3f}  {viable_symbol_wf} ({viable_text_wf})"
    )
    print(
        f"      (Excludes ${wildfire_risk_total_pv:>15,.0f} in wildfire + liability costs, keeps outage risk)"
    )

    bcr_excluding_emissions_and_wildfire_risk = bcr_metrics.get(
        "bcr_excluding_emissions_and_wildfire_risk", 0
    )
    viable_symbol_em_wf, viable_text_em_wf = format_bcr_viability(
        bcr_excluding_emissions_and_wildfire_risk
    )
    print(
        f"    BCR (excl. emissions & wildfire risk): {bcr_excluding_emissions_and_wildfire_risk:>6.3f}  {viable_symbol_em_wf} ({viable_text_em_wf})"
    )
    print(
        f"      (Excludes ${emissions_pv + wildfire_risk_total_pv:>15,.0f} in emissions + wildfire costs, keeps energy losses & outage)"
    )

    bcr_excluding_linelosses_and_wildfire_risk = bcr_metrics.get(
        "bcr_excluding_linelosses_and_wildfire_risk", 0
    )
    viable_symbol_ll_wf, viable_text_ll_wf = format_bcr_viability(
        bcr_excluding_linelosses_and_wildfire_risk
    )
    print(
        f"    BCR (excl. energy losses & wildfire risk): {bcr_excluding_linelosses_and_wildfire_risk:>6.3f}  {viable_symbol_ll_wf} ({viable_text_ll_wf})"
    )
    print(
        f"      (Excludes ${energy_losses_pv + wildfire_risk_total_pv:>15,.0f} in energy losses + wildfire costs, keeps emissions & outage)"
    )

    bcr_excluding_emissions_and_linelosses_and_wildfire_risk = bcr_metrics.get(
        "bcr_excluding_emissions_and_linelosses_and_wildfire_risk", 0
    )
    viable_symbol_em_ll_wf, viable_text_em_ll_wf = format_bcr_viability(
        bcr_excluding_emissions_and_linelosses_and_wildfire_risk
    )
    print(
        f"    BCR (excl. emissions & energy losses & wildfire risk): {bcr_excluding_emissions_and_linelosses_and_wildfire_risk:>6.3f}  {viable_symbol_em_ll_wf} ({viable_text_em_ll_wf})"
    )
    print(
        f"      (Excludes ${energy_emissions_costs_pv + wildfire_risk_total_pv:>15,.0f} in emissions + energy losses + wildfire costs, keeps outage)"
    )
    print()

    # Print outage-only BCRs (4 combinations)
    outage_risk_pv = safe_get_numeric(costs, "outage_pv")

    print("  Outage-Only Exclusions:")
    bcr_excluding_outage_risk = bcr_metrics.get("bcr_excluding_outage_risk", 0)
    viable_symbol_out, viable_text_out = format_bcr_viability(bcr_excluding_outage_risk)
    print(
        f"    BCR (excl. outage risk): {bcr_excluding_outage_risk:>6.3f}  {viable_symbol_out} ({viable_text_out})"
    )
    print(
        f"      (Excludes ${outage_risk_pv:>15,.0f} in outage costs, keeps wildfire risk)"
    )

    bcr_excluding_emissions_and_outage_risk = bcr_metrics.get(
        "bcr_excluding_emissions_and_outage_risk", 0
    )
    viable_symbol_em_out, viable_text_em_out = format_bcr_viability(
        bcr_excluding_emissions_and_outage_risk
    )
    print(
        f"    BCR (excl. emissions & outage risk): {bcr_excluding_emissions_and_outage_risk:>6.3f}  {viable_symbol_em_out} ({viable_text_em_out})"
    )
    print(
        f"      (Excludes ${emissions_pv + outage_risk_pv:>15,.0f} in emissions + outage costs, keeps energy losses & wildfire)"
    )

    bcr_excluding_linelosses_and_outage_risk = bcr_metrics.get(
        "bcr_excluding_linelosses_and_outage_risk", 0
    )
    viable_symbol_ll_out, viable_text_ll_out = format_bcr_viability(
        bcr_excluding_linelosses_and_outage_risk
    )
    print(
        f"    BCR (excl. energy losses & outage risk): {bcr_excluding_linelosses_and_outage_risk:>6.3f}  {viable_symbol_ll_out} ({viable_text_ll_out})"
    )
    print(
        f"      (Excludes ${energy_losses_pv + outage_risk_pv:>15,.0f} in energy losses + outage costs, keeps emissions & wildfire)"
    )

    bcr_excluding_emissions_and_linelosses_and_outage_risk = bcr_metrics.get(
        "bcr_excluding_emissions_and_linelosses_and_outage_risk", 0
    )
    viable_symbol_em_ll_out, viable_text_em_ll_out = format_bcr_viability(
        bcr_excluding_emissions_and_linelosses_and_outage_risk
    )
    print(
        f"    BCR (excl. emissions & energy losses & outage risk): {bcr_excluding_emissions_and_linelosses_and_outage_risk:>6.3f}  {viable_symbol_em_ll_out} ({viable_text_em_ll_out})"
    )
    print(
        f"      (Excludes ${energy_emissions_costs_pv + outage_risk_pv:>15,.0f} in emissions + energy losses + outage costs, keeps wildfire)"
    )
    print()

    # Net Benefits section - Print all 16 combinations
    print("NET BENEFITS:")

    # 1. No exclusions
    net_benefit_pv = bcr_metrics["net_benefit_pv"]
    net_symbol_pv = "✅" if net_benefit_pv >= 0 else "❌"
    net_text_pv = (
        "positive: benefits exceed costs"
        if net_benefit_pv >= 0
        else "negative: costs exceed benefits"
    )
    print(
        f"  Net Benefit (PV):            ${net_benefit_pv:>15,.0f}  {net_symbol_pv} ({net_text_pv})"
    )

    # Utility/TSP Net Benefit
    net_benefit_utility_pv = bcr_metrics.get("net_benefit_utility_pv", 0)
    utility_net_symbol = "✅" if net_benefit_utility_pv >= 0 else "❌"
    utility_net_text = (
        "positive: benefits exceed costs"
        if net_benefit_utility_pv >= 0
        else "negative: costs exceed benefits"
    )
    print(
        f"  Net Benefit Utility (PV):     ${net_benefit_utility_pv:>15,.0f}  {utility_net_symbol} ({utility_net_text})"
    )

    # Ratepayer Net Benefit
    net_benefit_ratepayer_pv = bcr_metrics.get("net_benefit_ratepayer_pv", 0)
    ratepayer_net_symbol = "✅" if net_benefit_ratepayer_pv >= 0 else "❌"
    ratepayer_net_text = (
        "positive: benefits exceed costs"
        if net_benefit_ratepayer_pv >= 0
        else "negative: costs exceed benefits"
    )
    print(
        f"  Net Benefit Ratepayer (PV):   ${net_benefit_ratepayer_pv:>15,.0f}  {ratepayer_net_symbol} ({ratepayer_net_text})"
    )

    # 2. Exclude risk only (both wildfire and outage)
    net_benefit_excluding_risk_pv = bcr_metrics.get(
        "net_benefit_excluding_wildfire_risk_and_outage_risk_pv",
        bcr_metrics.get("net_benefit_excluding_risk_pv", 0),
    )
    net_symbol_norisk = "✅" if net_benefit_excluding_risk_pv >= 0 else "❌"
    net_text_norisk = (
        "positive: benefits exceed costs"
        if net_benefit_excluding_risk_pv >= 0
        else "negative: costs exceed benefits"
    )
    print(
        f"  Net Benefit (PV, excl. risk):    ${net_benefit_excluding_risk_pv:>15,.0f}  {net_symbol_norisk} ({net_text_norisk})"
    )

    # 3. Exclude emissions only
    net_benefit_excluding_emissions_pv = bcr_metrics.get(
        "net_benefit_excluding_emissions_pv", 0
    )
    net_symbol_emissions = "✅" if net_benefit_excluding_emissions_pv >= 0 else "❌"
    net_text_emissions = (
        "positive: benefits exceed costs"
        if net_benefit_excluding_emissions_pv >= 0
        else "negative: costs exceed benefits"
    )
    print(
        f"  Net Benefit (PV, excl. emissions): ${net_benefit_excluding_emissions_pv:>15,.0f}  {net_symbol_emissions} ({net_text_emissions})"
    )

    # 4. Exclude line losses only
    net_benefit_excluding_linelosses_pv = bcr_metrics.get(
        "net_benefit_excluding_linelosses_pv", 0
    )
    net_symbol_linelosses = "✅" if net_benefit_excluding_linelosses_pv >= 0 else "❌"
    net_text_linelosses = (
        "positive: benefits exceed costs"
        if net_benefit_excluding_linelosses_pv >= 0
        else "negative: costs exceed benefits"
    )
    print(
        f"  Net Benefit (PV, excl. line losses): ${net_benefit_excluding_linelosses_pv:>15,.0f}  {net_symbol_linelosses} ({net_text_linelosses})"
    )

    # 5. Exclude emissions and line losses
    net_benefit_excluding_emissions_and_linelosses_pv = bcr_metrics.get(
        "net_benefit_excluding_emissions_and_linelosses_pv", 0
    )
    net_symbol_emissions_linelosses = (
        "✅" if net_benefit_excluding_emissions_and_linelosses_pv >= 0 else "❌"
    )
    net_text_emissions_linelosses = (
        "positive: benefits exceed costs"
        if net_benefit_excluding_emissions_and_linelosses_pv >= 0
        else "negative: costs exceed benefits"
    )
    print(
        f"  Net Benefit (PV, excl. emissions & line losses): ${net_benefit_excluding_emissions_and_linelosses_pv:>15,.0f}  {net_symbol_emissions_linelosses} ({net_text_emissions_linelosses})"
    )

    # 6. Exclude emissions and risk (both wildfire and outage)
    net_benefit_excluding_emissions_and_risk_pv = bcr_metrics.get(
        "net_benefit_excluding_emissions_and_wildfire_risk_and_outage_risk_pv",
        bcr_metrics.get("net_benefit_excluding_emissions_and_risk_pv", 0),
    )
    net_symbol_emissions_risk = (
        "✅" if net_benefit_excluding_emissions_and_risk_pv >= 0 else "❌"
    )
    net_text_emissions_risk = (
        "positive: benefits exceed costs"
        if net_benefit_excluding_emissions_and_risk_pv >= 0
        else "negative: costs exceed benefits"
    )
    print(
        f"  Net Benefit (PV, excl. emissions & risk): ${net_benefit_excluding_emissions_and_risk_pv:>15,.0f}  {net_symbol_emissions_risk} ({net_text_emissions_risk})"
    )

    # 7. Exclude line losses and risk (both wildfire and outage)
    net_benefit_excluding_linelosses_and_risk_pv = bcr_metrics.get(
        "net_benefit_excluding_linelosses_and_wildfire_risk_and_outage_risk_pv",
        bcr_metrics.get("net_benefit_excluding_linelosses_and_risk_pv", 0),
    )
    net_symbol_linelosses_risk = (
        "✅" if net_benefit_excluding_linelosses_and_risk_pv >= 0 else "❌"
    )
    net_text_linelosses_risk = (
        "positive: benefits exceed costs"
        if net_benefit_excluding_linelosses_and_risk_pv >= 0
        else "negative: costs exceed benefits"
    )
    print(
        f"  Net Benefit (PV, excl. line losses & risk): ${net_benefit_excluding_linelosses_and_risk_pv:>15,.0f}  {net_symbol_linelosses_risk} ({net_text_linelosses_risk})"
    )

    # 8. Exclude emissions, line losses, and risk (all three - both wildfire and outage)
    net_benefit_excluding_emissions_and_linelosses_and_risk_pv = bcr_metrics.get(
        "net_benefit_excluding_emissions_and_linelosses_and_wildfire_risk_and_outage_risk_pv",
        bcr_metrics.get(
            "net_benefit_excluding_emissions_and_linelosses_and_risk_pv", 0
        ),
    )
    net_symbol_all_three = (
        "✅"
        if net_benefit_excluding_emissions_and_linelosses_and_risk_pv >= 0
        else "❌"
    )
    net_text_all_three = (
        "positive: benefits exceed costs"
        if net_benefit_excluding_emissions_and_linelosses_and_risk_pv >= 0
        else "negative: costs exceed benefits"
    )
    print(
        f"  Net Benefit (PV, excl. emissions & line losses & risk): ${net_benefit_excluding_emissions_and_linelosses_and_risk_pv:>15,.0f}  {net_symbol_all_three} ({net_text_all_three})"
    )
    print()

    # Print wildfire-only net benefits (4 combinations)
    print("  Wildfire-Only Exclusions:")
    net_benefit_excluding_wildfire_risk_pv = bcr_metrics.get(
        "net_benefit_excluding_wildfire_risk_pv", 0
    )
    net_symbol_wf = "✅" if net_benefit_excluding_wildfire_risk_pv >= 0 else "❌"
    net_text_wf = (
        "positive: benefits exceed costs"
        if net_benefit_excluding_wildfire_risk_pv >= 0
        else "negative: costs exceed benefits"
    )
    print(
        f"    Net Benefit (PV, excl. wildfire risk): ${net_benefit_excluding_wildfire_risk_pv:>15,.0f}  {net_symbol_wf} ({net_text_wf})"
    )

    net_benefit_excluding_emissions_and_wildfire_risk_pv = bcr_metrics.get(
        "net_benefit_excluding_emissions_and_wildfire_risk_pv", 0
    )
    net_symbol_em_wf = (
        "✅" if net_benefit_excluding_emissions_and_wildfire_risk_pv >= 0 else "❌"
    )
    net_text_em_wf = (
        "positive: benefits exceed costs"
        if net_benefit_excluding_emissions_and_wildfire_risk_pv >= 0
        else "negative: costs exceed benefits"
    )
    print(
        f"    Net Benefit (PV, excl. emissions & wildfire risk): ${net_benefit_excluding_emissions_and_wildfire_risk_pv:>15,.0f}  {net_symbol_em_wf} ({net_text_em_wf})"
    )

    net_benefit_excluding_linelosses_and_wildfire_risk_pv = bcr_metrics.get(
        "net_benefit_excluding_linelosses_and_wildfire_risk_pv", 0
    )
    net_symbol_ll_wf = (
        "✅" if net_benefit_excluding_linelosses_and_wildfire_risk_pv >= 0 else "❌"
    )
    net_text_ll_wf = (
        "positive: benefits exceed costs"
        if net_benefit_excluding_linelosses_and_wildfire_risk_pv >= 0
        else "negative: costs exceed benefits"
    )
    print(
        f"    Net Benefit (PV, excl. line losses & wildfire risk): ${net_benefit_excluding_linelosses_and_wildfire_risk_pv:>15,.0f}  {net_symbol_ll_wf} ({net_text_ll_wf})"
    )

    net_benefit_excluding_emissions_and_linelosses_and_wildfire_risk_pv = (
        bcr_metrics.get(
            "net_benefit_excluding_emissions_and_linelosses_and_wildfire_risk_pv", 0
        )
    )
    net_symbol_em_ll_wf = (
        "✅"
        if net_benefit_excluding_emissions_and_linelosses_and_wildfire_risk_pv >= 0
        else "❌"
    )
    net_text_em_ll_wf = (
        "positive: benefits exceed costs"
        if net_benefit_excluding_emissions_and_linelosses_and_wildfire_risk_pv >= 0
        else "negative: costs exceed benefits"
    )
    print(
        f"    Net Benefit (PV, excl. emissions & line losses & wildfire risk): ${net_benefit_excluding_emissions_and_linelosses_and_wildfire_risk_pv:>15,.0f}  {net_symbol_em_ll_wf} ({net_text_em_ll_wf})"
    )
    print()

    # Print outage-only net benefits (4 combinations)
    print("  Outage-Only Exclusions:")
    net_benefit_excluding_outage_risk_pv = bcr_metrics.get(
        "net_benefit_excluding_outage_risk_pv", 0
    )
    net_symbol_out = "✅" if net_benefit_excluding_outage_risk_pv >= 0 else "❌"
    net_text_out = (
        "positive: benefits exceed costs"
        if net_benefit_excluding_outage_risk_pv >= 0
        else "negative: costs exceed benefits"
    )
    print(
        f"    Net Benefit (PV, excl. outage risk): ${net_benefit_excluding_outage_risk_pv:>15,.0f}  {net_symbol_out} ({net_text_out})"
    )

    net_benefit_excluding_emissions_and_outage_risk_pv = bcr_metrics.get(
        "net_benefit_excluding_emissions_and_outage_risk_pv", 0
    )
    net_symbol_em_out = (
        "✅" if net_benefit_excluding_emissions_and_outage_risk_pv >= 0 else "❌"
    )
    net_text_em_out = (
        "positive: benefits exceed costs"
        if net_benefit_excluding_emissions_and_outage_risk_pv >= 0
        else "negative: costs exceed benefits"
    )
    print(
        f"    Net Benefit (PV, excl. emissions & outage risk): ${net_benefit_excluding_emissions_and_outage_risk_pv:>15,.0f}  {net_symbol_em_out} ({net_text_em_out})"
    )

    net_benefit_excluding_linelosses_and_outage_risk_pv = bcr_metrics.get(
        "net_benefit_excluding_linelosses_and_outage_risk_pv", 0
    )
    net_symbol_ll_out = (
        "✅" if net_benefit_excluding_linelosses_and_outage_risk_pv >= 0 else "❌"
    )
    net_text_ll_out = (
        "positive: benefits exceed costs"
        if net_benefit_excluding_linelosses_and_outage_risk_pv >= 0
        else "negative: costs exceed benefits"
    )
    print(
        f"    Net Benefit (PV, excl. line losses & outage risk): ${net_benefit_excluding_linelosses_and_outage_risk_pv:>15,.0f}  {net_symbol_ll_out} ({net_text_ll_out})"
    )

    net_benefit_excluding_emissions_and_linelosses_and_outage_risk_pv = bcr_metrics.get(
        "net_benefit_excluding_emissions_and_linelosses_and_outage_risk_pv", 0
    )
    net_symbol_em_ll_out = (
        "✅"
        if net_benefit_excluding_emissions_and_linelosses_and_outage_risk_pv >= 0
        else "❌"
    )
    net_text_em_ll_out = (
        "positive: benefits exceed costs"
        if net_benefit_excluding_emissions_and_linelosses_and_outage_risk_pv >= 0
        else "negative: costs exceed benefits"
    )
    print(
        f"    Net Benefit (PV, excl. emissions & line losses & outage risk): ${net_benefit_excluding_emissions_and_linelosses_and_outage_risk_pv:>15,.0f}  {net_symbol_em_ll_out} ({net_text_em_ll_out})"
    )
    print()
    print("=" * 80)
    print()


if __name__ == "__main__":
    # For testing - use the most recent scenario_id
    import sys

    if len(sys.argv) > 1:
        scenario_id = sys.argv[1]
    else:
        # Try to get the most recent scenario_id from batch_summary.csv
        batch_path = OUTPUTS_DIR / "batch_summary.csv"
        if os.path.exists(batch_path):
            with open(batch_path, "r") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                if rows:
                    scenario_id = rows[-1]["scenario_id"]
                    print(f"Using most recent scenario_id: {scenario_id}")
                else:
                    print("No scenarios found in batch_summary.csv")
                    sys.exit(1)
        else:
            print("batch_summary.csv not found")
            sys.exit(1)

    results = calculate_and_display_bcr(scenario_id)

    if results:
        print(f"\nBCR calculation completed for scenario {scenario_id}")
    else:
        print(f"\nBCR calculation failed for scenario {scenario_id}")
