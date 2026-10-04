# Date: 2025-10-26
# Description: Emissions Reductions Calculation. This calculates the societal costs of emissions due to
# 1. Delays and long construction times slowing the deployment of new renewable energy capacity
# 2. Line losses being compensated for by generators (i.e. they have to burn more fuel to make up for losses)

from __future__ import annotations

import logging

# Standard library imports
from dataclasses import dataclass
from typing import Dict, Any, List, Tuple

from forge.scripts.utils.smart_output import SmartOutputManager

# Local utility imports
from forge.scripts.calc.energy_losses import (
    get_total_energy_losses,
    load_project_technical_details,
)
from forge.scripts.utils.smart_loaders import (
    load_emissions_details,
    load_grid_mix,
    load_financing_social_discount_rate,
)
from forge.scripts.utils.financial_utils import calculate_present_value, calculate_cod_year
from forge.scripts.utils.calculation_utils import from_percent

GRID_SOURCES = [
    "coal",
    "oil",
    "natural_gas",
    "solar",
    "wind",
    "hydro",
    "nuclear",
    "other",
]

logger = logging.getLogger(__name__)


@dataclass
class LifetimeEmissionsResults:
    """Results from lifetime emissions calculations."""
    yearly_emissions: List[Dict[str, float]]
    total_emissions: Dict[str, float]
    avg_annual_emissions: Dict[str, float]
    avg_annual_costs: float
    avg_annual_costs_by_pollutant: Dict[str, float]
    total_costs_by_pollutant: Dict[str, float]
    lifetime_cost: float
    lifetime_cost_pv: float
    total_costs_by_pollutant_pv: Dict[str, float]
    annual_values: List[float]

def calculate_energy_mix_by_year(
    energy_source_mix_details: Dict[str, Any], project_lifetime: int
) -> List[Dict[str, float]]:
    """
    Calculate energy mix for each year with growth/decay rates.

    Args:
        energy_source_mix_details: Dictionary with percentage and rate_of_change for each source
        project_lifetime: Number of years in project

    Returns:
        list: List of dictionaries, one per year, with normalized percentages for each source
    """
    sources = [
        "coal",
        "oil",
        "natural_gas",
        "solar",
        "wind",
        "hydro",
        "nuclear",
        "other",
    ]

    # Extract initial percentages and rates
    initial_mix = {}
    rates = {}
    for source in sources:
        initial_mix[source] = from_percent(
            energy_source_mix_details.get(source, {}).get("percentage", 0.0)
        )  # Convert to decimal
        rates[source] = energy_source_mix_details.get(source, {}).get(
            "rate_of_change", 0.0
        )

    energy_mix_by_year = []
    project_lifetime_int = int(project_lifetime)

    for tau in range(1, project_lifetime_int + 1):
        raw = {
            source: initial_mix[source] * (1 + rates[source]) ** (tau - 1)
            for source in sources
        }
        total = sum(raw.values())
        normalized = (
            {source: raw[source] / total for source in sources}
            if total > 0
            else raw
        )
        energy_mix_by_year.append(normalized)

    return energy_mix_by_year

def build_mix_input(
    percentages: Dict[str, float], rates: Dict[str, float]
) -> Dict[str, Any]:
    """Build a calculate_energy_mix_by_year() input dict from percentage + rate dicts.

    percentages values are in percentage form (0-100); rates are fractional
    annual growth/decline rates.
    """
    return {
        source: {
            "percentage": percentages.get(source, 0.0),
            "rate_of_change": rates.get(source, 0.0),
        }
        for source in GRID_SOURCES
    }

def compute_cod_state(
    grid_mix: Dict[str, Any], delay_years: float, construction_years: int
) -> Dict[str, float]:
    """Evolve the initial grid mix at pre-COD rates through COD; return percentages (0-100).

    This is the single-trajectory handoff point: the grid state at COD is exactly
    the without-line trajectory evaluated at T_COD (see design doc
    2026-07-07__single-trajectory-grid-mix-redesign.md). Both the with-line and
    without-line operational trajectories start from this same state.
    """
    t_cod_years = max(1, int(round(calculate_cod_year(delay_years, construction_years))))
    pre_cod_input = build_mix_input(grid_mix["initial"], grid_mix["rate_pre_cod"])
    pre_cod_trajectory = calculate_energy_mix_by_year(pre_cod_input, t_cod_years)
    cod_fractions = pre_cod_trajectory[-1]
    return {source: fraction * 100.0 for source, fraction in cod_fractions.items()}

def calculate_emissions_by_year(
    total_energy_compensated_mwh: float,
    energy_mix: Dict[str, float],
    emission_intensities: Dict[str, Any],
) -> Dict[str, float]:
    """
    Calculate emissions for a single year.

    Args:
        total_energy_compensated_mwh: Total energy compensated in MWh
        energy_mix: Dictionary of energy source percentages for the year
        emission_intensities: Dictionary of emission intensities by pollutant and source

    Returns:
        dict: Emissions in kg for each pollutant
    """
    pollutants = ["co2", "sox", "nox"]
    sources = [
        "coal",
        "oil",
        "natural_gas",
        "solar",
        "wind",
        "hydro",
        "nuclear",
        "other",
    ]

    emissions = {pollutant: 0.0 for pollutant in pollutants}

    # Map pollutant names to emission intensity keys
    intensity_key_map = {
        "co2": "co2_intensity_kg_per_mwh",
        "sox": "sox_intensity_kg_per_mwh",
        "nox": "nox_intensity_kg_per_mwh",
    }

    for pollutant in pollutants:
        intensity_key = intensity_key_map[pollutant]
        intensity_dict = emission_intensities.get(intensity_key, {})

        # Calculate emissions: E_k = TEC x sum_j (p_j x I_{j,k})
        for source in sources:
            p_j = energy_mix.get(source, 0.0)
            I_jk = intensity_dict.get(source, 0.0)
            emissions[pollutant] += total_energy_compensated_mwh * p_j * I_jk

    return emissions


def _as_nested_societal_costs(societal_costs: Dict[str, Any]) -> Dict[str, Dict[str, float]]:
    """Normalize nested or YAML-flat societal cost dicts to nested form.

    Nested: ``{pollutant: {"base_cost_per_kg": float, "growth_rate": float}}``
    YAML-flat: ``{pollutant_cost_per_kg, pollutant_cost_annual_growth, ...}``
    """
    if not societal_costs:
        return {}
    first_val = next(iter(societal_costs.values()))
    if isinstance(first_val, dict) and "base_cost_per_kg" in first_val:
        return societal_costs
    nested: Dict[str, Dict[str, float]] = {}
    prefixes = set()
    for key in societal_costs:
        if key.endswith("_cost_per_kg"):
            prefixes.add(key[: -len("_cost_per_kg")])
        elif key.endswith("_cost_annual_growth"):
            prefixes.add(key[: -len("_cost_annual_growth")])
    for pollutant in prefixes:
        nested[pollutant] = {
            "base_cost_per_kg": float(
                societal_costs.get(f"{pollutant}_cost_per_kg", 0.0)
            ),
            "growth_rate": float(
                societal_costs.get(f"{pollutant}_cost_annual_growth", 0.0)
            ),
        }
    return nested


def monetize_annual_emissions(
    emissions_by_pollutant: dict,
    societal_costs: dict,
    year_idx: int,
) -> float:
    """Compute total social cost for one year's emissions across all pollutants.

    Args:
        emissions_by_pollutant: {pollutant: kg} for one year
        societal_costs: {pollutant: {"base_cost_per_kg": float, "growth_rate": float}}
            Also accepts YAML-flat keys ({pollutant}_cost_per_kg /
            {pollutant}_cost_annual_growth) used by load_emissions_details().
        year_idx: 0-based year index (for cost escalation)

    Returns:
        Total cost ($) for this year, nominal (undiscounted).
    """
    nested = _as_nested_societal_costs(societal_costs)
    total = 0.0
    for pollutant, kg in emissions_by_pollutant.items():
        if pollutant not in nested:
            continue
        sc = nested[pollutant]
        cost_per_kg = sc["base_cost_per_kg"] * (1 + sc["growth_rate"]) ** year_idx
        total += kg * cost_per_kg
    return total


def calculate_lifetime_emissions(
    total_losses_mwh_per_year: float,
    alpha_compensation: float,
    energy_source_mix_details: Dict[str, Any],
    emission_intensities: Dict[str, Any],
    societal_costs: Dict[str, float],
    project_lifetime: int,
    social_discount_rate: float,
    delay_years: float,
    construction_years: int,
) -> LifetimeEmissionsResults:
    """
    Calculate emissions across project lifetime.

    Returns:
        tuple: (yearly_emissions, total_emissions, avg_annual_emissions, avg_annual_costs,
                avg_annual_costs_by_pollutant, total_costs_by_pollutant, lifetime_cost,
                lifetime_cost_pv, total_costs_by_pollutant_pv)
    """
    # Calculate start year (when project becomes operational)
    start_year = calculate_cod_year(delay_years, construction_years)

    # Calculate TEC (Total Energy Compensated)
    total_energy_compensated_mwh = alpha_compensation * total_losses_mwh_per_year

    # Calculate energy mix for each year
    energy_mix_by_year = calculate_energy_mix_by_year(
        energy_source_mix_details, project_lifetime
    )

    # Calculate emissions for each year
    yearly_emissions = []
    yearly_costs = []
    annual_values = []

    total_emissions = {"co2": 0.0, "sox": 0.0, "nox": 0.0}
    total_costs_by_pollutant = {"co2": 0.0, "sox": 0.0, "nox": 0.0}
    total_costs_by_pollutant_pv = {"co2": 0.0, "sox": 0.0, "nox": 0.0}
    lifetime_cost = 0.0
    lifetime_cost_pv = 0.0

    for year, energy_mix in enumerate(energy_mix_by_year, 1):
        emissions = calculate_emissions_by_year(
            total_energy_compensated_mwh, energy_mix, emission_intensities
        )
        yearly_emissions.append(emissions)

        year_idx = year - 1
        year_cost = monetize_annual_emissions(emissions, societal_costs, year_idx)
        yearly_costs.append(year_cost)
        annual_values.append(year_cost)
        lifetime_cost += year_cost

        year_discount_year = start_year + year - 1
        year_pv = year_cost / ((1 + social_discount_rate) ** year_discount_year)
        lifetime_cost_pv += year_pv

        for pollutant, emissions_kg in emissions.items():
            total_emissions[pollutant] += emissions_kg
            pollutant_cost = monetize_annual_emissions(
                {pollutant: emissions_kg}, societal_costs, year_idx
            )
            total_costs_by_pollutant[pollutant] += pollutant_cost
            pollutant_pv = pollutant_cost / (
                (1 + social_discount_rate) ** year_discount_year
            )
            total_costs_by_pollutant_pv[pollutant] += pollutant_pv

    # Calculate average annual emissions and costs
    if project_lifetime > 0:
        avg_annual_costs = lifetime_cost / project_lifetime
        avg_annual_emissions = {
            pollutant: total_emissions[pollutant] / project_lifetime
            for pollutant in total_emissions
        }
        avg_annual_costs_by_pollutant = {
            pollutant: total_costs_by_pollutant[pollutant] / project_lifetime
            for pollutant in total_costs_by_pollutant
        }
    else:
        avg_annual_costs = 0.0
        avg_annual_emissions = {p: 0.0 for p in total_emissions}
        avg_annual_costs_by_pollutant = {p: 0.0 for p in total_costs_by_pollutant}

    return LifetimeEmissionsResults(
        yearly_emissions=yearly_emissions,
        total_emissions=total_emissions,
        avg_annual_emissions=avg_annual_emissions,
        avg_annual_costs=avg_annual_costs,
        avg_annual_costs_by_pollutant=avg_annual_costs_by_pollutant,
        total_costs_by_pollutant=total_costs_by_pollutant,
        lifetime_cost=lifetime_cost,
        lifetime_cost_pv=lifetime_cost_pv,
        total_costs_by_pollutant_pv=total_costs_by_pollutant_pv,
        annual_values=annual_values,
    )

def print_emissions_results(
    alpha_compensation: float,
    energy_source_mix_details: Dict[str, Any],
    avg_annual_emissions: Dict[str, float],
    societal_costs: Dict[str, float],
    avg_annual_costs: float,
    avg_annual_costs_by_pollutant: Dict[str, float],
    total_emissions: Dict[str, float],
    total_costs_by_pollutant: Dict[str, float],
    lifetime_cost: float,
    lifetime_cost_pv: float,
    total_costs_by_pollutant_pv: Dict[str, float],
    total_losses_mwh_per_year: float,
    total_energy_compensated_mwh: float,
) -> None:
    """Print organized emissions results."""
    # Compensation Configuration
    logger.info("=" * 60)
    logger.info("COMPENSATION CONFIGURATION")
    logger.info("=" * 60)
    logger.info(f"Compensation percentage (alpha): {alpha_compensation:.1%}")
    logger.info(f"Total energy losses: {total_losses_mwh_per_year:,.2f} MWh/yr")
    logger.info(f"Total energy compensated (TEC): {total_energy_compensated_mwh:,.2f} MWh/yr")
    logger.info("")

    # Energy Source Mix - Initial
    logger.info("=" * 60)
    logger.info("INITIAL ENERGY SOURCE MIX")
    logger.info("=" * 60)
    sources = [
        "coal",
        "oil",
        "natural_gas",
        "solar",
        "wind",
        "hydro",
        "nuclear",
        "other",
    ]
    for source in sources:
        percentage = energy_source_mix_details.get(source, {}).get("percentage", 0.0)
        rate = energy_source_mix_details.get(source, {}).get("rate_of_change", 0.0)
        logger.info(f"{source.capitalize()}: {percentage:.2f}% (rate: {rate:.1%})")
    logger.info("")

    # Average Annual Emissions
    logger.info("=" * 60)
    logger.info("AVERAGE ANNUAL LOSS-COMPENSATION EMISSIONS")
    logger.info("=" * 60)
    logger.info(f"CO2: {avg_annual_emissions['co2']:,.2f} kg/yr")
    logger.info(f"SOx: {avg_annual_emissions['sox']:,.2f} kg/yr")
    logger.info(f"NOx: {avg_annual_emissions['nox']:,.2f} kg/yr")
    logger.info("")

    # Societal Costs
    logger.info("=" * 60)
    logger.info("SOCIETAL COSTS")
    logger.info("=" * 60)
    logger.info(f"CO2 cost: ${societal_costs['co2_cost_per_kg']:.3f}/kg")
    logger.info(f"SOx cost: ${societal_costs['sox_cost_per_kg']:.1f}/kg")
    logger.info(f"NOx cost: ${societal_costs['nox_cost_per_kg']:.1f}/kg")
    logger.info("")

    # Annual Emissions Cost
    logger.info("=" * 60)
    logger.info("AVERAGE ANNUAL LOSS-COMPENSATION EMISSIONS COST")
    logger.info("=" * 60)
    logger.info(f"CO2 cost: ${avg_annual_costs_by_pollutant['co2']:,.2f}/yr")
    logger.info(f"SOx cost: ${avg_annual_costs_by_pollutant['sox']:,.2f}/yr")
    logger.info(f"NOx cost: ${avg_annual_costs_by_pollutant['nox']:,.2f}/yr")
    logger.info(f"Total average annual cost: ${avg_annual_costs:,.2f}/yr")
    logger.info("")

    # Lifetime Totals
    logger.info("=" * 60)
    logger.info("LIFETIME LOSS-COMPENSATION EMISSIONS TOTALS")
    logger.info("=" * 60)
    logger.info(f"Total CO2 emissions: {total_emissions['co2']:,.2f} kg")
    logger.info(f"Total SOx emissions: {total_emissions['sox']:,.2f} kg")
    logger.info(f"Total NOx emissions: {total_emissions['nox']:,.2f} kg")
    logger.info("")
    logger.info(f"Total CO2 cost (nominal): ${total_costs_by_pollutant['co2']:,.2f}")
    logger.info(f"Total SOx cost (nominal): ${total_costs_by_pollutant['sox']:,.2f}")
    logger.info(f"Total NOx cost (nominal): ${total_costs_by_pollutant['nox']:,.2f}")
    logger.info("")
    logger.info(f"Total lifetime emissions cost (nominal): ${lifetime_cost:,.2f}")
    logger.info("")
    logger.info("=" * 60)
    logger.info("LIFETIME LOSS-COMPENSATION EMISSIONS COSTS (PRESENT VALUE)")
    logger.info("=" * 60)
    logger.info(f"Total CO2 cost (PV): ${total_costs_by_pollutant_pv['co2']:,.2f}")
    logger.info(f"Total SOx cost (PV): ${total_costs_by_pollutant_pv['sox']:,.2f}")
    logger.info(f"Total NOx cost (PV): ${total_costs_by_pollutant_pv['nox']:,.2f}")
    logger.info("")
    logger.info(f"Total lifetime emissions cost (PV): ${lifetime_cost_pv:,.2f}")
    logger.info("")

def main() -> None:
    """
    Main function to calculate and display emissions costs from transmission line losses.

    This script calculates the societal costs of emissions (CO2, SOx, NOx) associated with
    compensating for transmission line energy losses. The calculation accounts for:
    - Total energy losses from the transmission line (line losses + converter losses)
    - Compensation percentage (fraction of losses that require additional generation)
    - Energy source mix for compensation (with growth/decay rates over project lifetime)
    - Emission intensities for each energy source
    - Societal costs per kg of each pollutant

    The script calculates annual and lifetime emissions, monetizes them using societal costs,
    and calculates present values using the social discount rate. Results are printed to console
    and written via SmartOutputManager (JSON).

    Outputs:
        - Prints detailed emissions results by pollutant (CO2, SOx, NOx)
        - Writes JSON via SmartOutputManager (shared in-process aggregator, or a JSON file)
        - Calculates both nominal and present value costs
    """
    # Load emissions details
    (
        alpha_compensation,
        emission_intensities_details,
        societal_costs_details,
    ) = load_emissions_details()

    # Load financing details
    social_discount_rate = load_financing_social_discount_rate()

    # Get delay and construction years from project details
    project_details = load_project_technical_details()

    # Loss-compensation uses the grid WITH the line's influence during operations:
    # COD state (initial mix evolved at pre-COD rates through COD) evolved forward
    # at post-COD rates. See design doc 2026-07-07__single-trajectory-grid-mix-redesign.md.
    grid_mix = load_grid_mix()
    cod_state_pct = compute_cod_state(
        grid_mix, project_details.delay_years, project_details.construction_years
    )
    energy_source_mix_details = build_mix_input(
        cod_state_pct, grid_mix["rate_post_cod"]
    )

    # Calculate total energy losses
    loss_data = get_total_energy_losses()
    total_losses_mwh_per_year = loss_data["total_losses_mwh_per_year"]
    project_lifetime_from_losses = loss_data["project_lifetime"]

    # Calculate emissions across lifetime
    emissions_results = calculate_lifetime_emissions(
        total_losses_mwh_per_year,
        alpha_compensation,
        energy_source_mix_details,
        emission_intensities_details,
        societal_costs_details,
        project_details.project_lifetime,
        social_discount_rate,
        project_details.delay_years,
        project_details.construction_years,
    )

    # Calculate TEC for display
    total_energy_compensated_mwh = alpha_compensation * total_losses_mwh_per_year

    from forge.scripts.utils.run_context import add_derived
    add_derived({"total_energy_compensated_mwh": total_energy_compensated_mwh})

    # Print results
    print_emissions_results(
        alpha_compensation,
        energy_source_mix_details,
        emissions_results.avg_annual_emissions,
        societal_costs_details,
        emissions_results.avg_annual_costs,
        emissions_results.avg_annual_costs_by_pollutant,
        emissions_results.total_emissions,
        emissions_results.total_costs_by_pollutant,
        emissions_results.lifetime_cost,
        emissions_results.lifetime_cost_pv,
        emissions_results.total_costs_by_pollutant_pv,
        total_losses_mwh_per_year,
        total_energy_compensated_mwh,
    )

    # ========================================================================
    # CSV OUTPUT - Write results to batch summary and detail CSV
    # ========================================================================

    # Initialize CSV output manager
    csv_manager = SmartOutputManager()

    # Prepare results dictionary
    results = {
        "total_nominal": emissions_results.lifetime_cost,
        "total_pv": emissions_results.lifetime_cost_pv,
        "annual_cost": emissions_results.avg_annual_costs,
        "co2_emissions_kg": emissions_results.total_emissions["co2"],
        "co2_cost_nominal": emissions_results.total_costs_by_pollutant["co2"],
        "co2_cost_pv": emissions_results.total_costs_by_pollutant_pv["co2"],
        "sox_emissions_kg": emissions_results.total_emissions["sox"],
        "sox_cost_nominal": emissions_results.total_costs_by_pollutant["sox"],
        "sox_cost_pv": emissions_results.total_costs_by_pollutant_pv["sox"],
        "nox_emissions_kg": emissions_results.total_emissions["nox"],
        "nox_cost_nominal": emissions_results.total_costs_by_pollutant["nox"],
        "nox_cost_pv": emissions_results.total_costs_by_pollutant_pv["nox"],
        # Year-by-year nominal costs (length = project_lifetime), for the BCR
        # trajectory module.
        "emissions_comp_annual_values": emissions_results.annual_values,
    }

    # Write to output manager (loss-compensation emissions)
    csv_manager.add_emissions_comp_costs(results)
    csv_manager.write_batch_summary()
