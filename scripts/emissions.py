# Author: Andrew Igdal
# Date: 2025-10-26
# Description: Emissions Reductions Calculation. This calculates the societal costs of emissions due to
# 1. Delays and long construction times slowing the deployment of new renewable energy capacity
# 2. Line losses being compensated for by generators (i.e. they have to burn more fuel to make up for losses)

from __future__ import annotations

# Standard library imports
import sys
import os
from typing import Dict, Any, List, Tuple

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from smart_output import CTCCOutputManager

# Local utility imports
from energy_losses import (
    get_total_energy_losses,
    load_project_technical_details,
)
from smart_loaders import (
    load_emissions_details,
    load_financing_social_discount_rate,
    get_project_data_raw,
)
from financial_utils import calculate_present_value
from calculation_utils import from_percent




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

    # Calculate mix for each year
    energy_mix_by_year = []
    current_mix = initial_mix.copy()

    # Convert project_lifetime to int for range() (it may be a float)
    project_lifetime_int = int(project_lifetime)
    for year in range(1, project_lifetime_int + 1):
        # Apply growth/decay rates
        next_mix = {}
        for source in sources:
            next_mix[source] = current_mix[source] * (1 + rates[source])

        # Normalize to sum to 1.0
        total = sum(next_mix.values())
        if total > 0:
            normalized_mix = {source: next_mix[source] / total for source in sources}
        else:
            normalized_mix = next_mix

        energy_mix_by_year.append(normalized_mix)
        current_mix = normalized_mix

    return energy_mix_by_year


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

        # Calculate emissions: E_k = TEC × Σ_j (p_j × I_{j,k})
        for source in sources:
            p_j = energy_mix.get(source, 0.0)
            I_jk = intensity_dict.get(source, 0.0)
            emissions[pollutant] += total_energy_compensated_mwh * p_j * I_jk

    return emissions


def calculate_lifetime_emissions(
    total_losses_mwh_per_year: float,
    compensation_percent: float,
    energy_source_mix_details: Dict[str, Any],
    emission_intensities: Dict[str, Any],
    societal_costs: Dict[str, float],
    project_lifetime: int,
    social_discount_rate: float,
    delay_years: float,
    construction_years: int,
) -> Tuple[
    List[Dict[str, float]],
    Dict[str, float],
    Dict[str, float],
    float,
    Dict[str, float],
    Dict[str, float],
    float,
    float,
    Dict[str, float],
]:
    """
    Calculate emissions across project lifetime.

    Returns:
        tuple: (yearly_emissions, total_emissions, avg_annual_emissions, avg_annual_costs,
                avg_annual_costs_by_pollutant, total_costs_by_pollutant, lifetime_cost,
                lifetime_cost_pv, total_costs_by_pollutant_pv)
    """
    # Calculate start year (when project becomes operational)
    start_year = int(delay_years) + int(construction_years) + 1

    # Calculate TEC (Total Energy Compensated)
    total_energy_compensated_mwh = compensation_percent * total_losses_mwh_per_year

    # Calculate energy mix for each year
    energy_mix_by_year = calculate_energy_mix_by_year(
        energy_source_mix_details, project_lifetime
    )

    # Calculate emissions for each year
    yearly_emissions = []
    yearly_costs = []

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

        # Calculate costs for this year: C_k = E_k × c_k
        year_cost = 0.0
        for pollutant, emissions_kg in emissions.items():
            cost_per_kg = societal_costs.get(f"{pollutant}_cost_per_kg", 0.0)
            pollutant_cost = emissions_kg * cost_per_kg
            year_cost += pollutant_cost
            total_emissions[pollutant] += emissions_kg
            total_costs_by_pollutant[pollutant] += pollutant_cost

        yearly_costs.append(year_cost)
        lifetime_cost += year_cost

        # Calculate present value for this year
        year_discount_year = start_year + year - 1
        year_pv = year_cost / ((1 + social_discount_rate) ** year_discount_year)
        lifetime_cost_pv += year_pv

        # Track PV by pollutant
        for pollutant, emissions_kg in emissions.items():
            cost_per_kg = societal_costs.get(f"{pollutant}_cost_per_kg", 0.0)
            pollutant_cost = emissions_kg * cost_per_kg
            pollutant_pv = pollutant_cost / (
                (1 + social_discount_rate) ** year_discount_year
            )
            total_costs_by_pollutant_pv[pollutant] += pollutant_pv

    # Calculate average annual emissions and costs
    avg_annual_costs = lifetime_cost / project_lifetime
    avg_annual_emissions = {
        pollutant: total_emissions[pollutant] / project_lifetime
        for pollutant in total_emissions
    }
    avg_annual_costs_by_pollutant = {
        pollutant: total_costs_by_pollutant[pollutant] / project_lifetime
        for pollutant in total_costs_by_pollutant
    }

    return (
        yearly_emissions,
        total_emissions,
        avg_annual_emissions,
        avg_annual_costs,
        avg_annual_costs_by_pollutant,
        total_costs_by_pollutant,
        lifetime_cost,
        lifetime_cost_pv,
        total_costs_by_pollutant_pv,
    )


def print_emissions_results(
    compensation_percent: float,
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
    print("=" * 60)
    print("COMPENSATION CONFIGURATION")
    print("=" * 60)
    print(f"Compensation percentage (α): {compensation_percent:.1%}")
    print(f"Total energy losses: {total_losses_mwh_per_year:,.2f} MWh/yr")
    print(f"Total energy compensated (TEC): {total_energy_compensated_mwh:,.2f} MWh/yr")
    print()

    # Energy Source Mix - Initial
    print("=" * 60)
    print("INITIAL ENERGY SOURCE MIX")
    print("=" * 60)
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
        print(f"{source.capitalize()}: {percentage:.2f}% (rate: {rate:.1%})")
    print()

    # Average Annual Emissions
    print("=" * 60)
    print("AVERAGE ANNUAL EMISSIONS")
    print("=" * 60)
    print(f"CO2: {avg_annual_emissions['co2']:,.2f} kg/yr")
    print(f"SOx: {avg_annual_emissions['sox']:,.2f} kg/yr")
    print(f"NOx: {avg_annual_emissions['nox']:,.2f} kg/yr")
    print()

    # Societal Costs
    print("=" * 60)
    print("SOCIETAL COSTS")
    print("=" * 60)
    print(f"CO2 cost: ${societal_costs['co2_cost_per_kg']:.3f}/kg")
    print(f"SOx cost: ${societal_costs['sox_cost_per_kg']:.1f}/kg")
    print(f"NOx cost: ${societal_costs['nox_cost_per_kg']:.1f}/kg")
    print()

    # Annual Emissions Cost
    print("=" * 60)
    print("AVERAGE ANNUAL EMISSIONS COST")
    print("=" * 60)
    print(f"CO2 cost: ${avg_annual_costs_by_pollutant['co2']:,.2f}/yr")
    print(f"SOx cost: ${avg_annual_costs_by_pollutant['sox']:,.2f}/yr")
    print(f"NOx cost: ${avg_annual_costs_by_pollutant['nox']:,.2f}/yr")
    print(f"Total average annual cost: ${avg_annual_costs:,.2f}/yr")
    print()

    # Lifetime Totals
    print("=" * 60)
    print("LIFETIME EMISSIONS TOTALS")
    print("=" * 60)
    print(f"Total CO2 emissions: {total_emissions['co2']:,.2f} kg")
    print(f"Total SOx emissions: {total_emissions['sox']:,.2f} kg")
    print(f"Total NOx emissions: {total_emissions['nox']:,.2f} kg")
    print()
    print(f"Total CO2 cost (nominal): ${total_costs_by_pollutant['co2']:,.2f}")
    print(f"Total SOx cost (nominal): ${total_costs_by_pollutant['sox']:,.2f}")
    print(f"Total NOx cost (nominal): ${total_costs_by_pollutant['nox']:,.2f}")
    print()
    print(f"Total lifetime emissions cost (nominal): ${lifetime_cost:,.2f}")
    print()
    print("=" * 60)
    print("LIFETIME EMISSIONS COSTS (PRESENT VALUE)")
    print("=" * 60)
    print(f"Total CO2 cost (PV): ${total_costs_by_pollutant_pv['co2']:,.2f}")
    print(f"Total SOx cost (PV): ${total_costs_by_pollutant_pv['sox']:,.2f}")
    print(f"Total NOx cost (PV): ${total_costs_by_pollutant_pv['nox']:,.2f}")
    print()
    print(f"Total lifetime emissions cost (PV): ${lifetime_cost_pv:,.2f}")
    print()


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
    and written to CSV outputs via CTCCOutputManager.

    Outputs:
        - Prints detailed emissions results by pollutant (CO2, SOx, NOx)
        - Writes to emissions_costs.csv and batch_summary.csv
        - Calculates both nominal and present value costs
    """
    # Load emissions details
    (
        compensation_percent,
        energy_source_mix_details,
        emission_intensities_details,
        societal_costs_details,
    ) = load_emissions_details()

    # Load financing details
    social_discount_rate = load_financing_social_discount_rate()

    # Get delay and construction years from project details
    project_details = load_project_technical_details()

    # Get number_of_converters if DC
    if project_details.ac_dc == "DC":
        try:
            project_details_data = get_project_data_raw()
            if "project" not in project_details_data:
                raise KeyError(
                    "Missing 'project' key in project technical details"
                )
            if "number_of_converters" not in project_details_data["project"]:
                raise KeyError(
                    "Missing 'number_of_converters' key in project section of technical details"
                )
            number_of_converters = project_details_data["project"][
                "number_of_converters"
            ]
        except KeyError as e:
            raise KeyError(
                f"Missing required key in project technical details: {e}"
            )
    else:
        number_of_converters = 0

    # Calculate total energy losses
    loss_data = get_total_energy_losses()
    total_losses_mwh_per_year = loss_data["total_losses_mwh_per_year"]
    project_lifetime_from_losses = loss_data["project_lifetime"]

    # Calculate emissions across lifetime
    (
        yearly_emissions,
        total_emissions,
        avg_annual_emissions,
        avg_annual_costs,
        avg_annual_costs_by_pollutant,
        total_costs_by_pollutant,
        lifetime_cost,
        lifetime_cost_pv,
        total_costs_by_pollutant_pv,
    ) = calculate_lifetime_emissions(
        total_losses_mwh_per_year,
        compensation_percent,
        energy_source_mix_details,
        emission_intensities_details,
        societal_costs_details,
        project_details.project_lifetime,
        social_discount_rate,
        project_details.delay_years,
        project_details.construction_years,
    )

    # Calculate TEC for display
    total_energy_compensated_mwh = compensation_percent * total_losses_mwh_per_year

    # Print results
    print_emissions_results(
        compensation_percent,
        energy_source_mix_details,
        avg_annual_emissions,
        societal_costs_details,
        avg_annual_costs,
        avg_annual_costs_by_pollutant,
        total_emissions,
        total_costs_by_pollutant,
        lifetime_cost,
        lifetime_cost_pv,
        total_costs_by_pollutant_pv,
        total_losses_mwh_per_year,
        total_energy_compensated_mwh,
    )

    # ========================================================================
    # CSV OUTPUT - Write results to batch summary and detail CSV
    # ========================================================================

    # Initialize CSV output manager
    csv_manager = CTCCOutputManager()

    # Prepare results dictionary
    results = {
        "total_nominal": lifetime_cost,
        "total_pv": lifetime_cost_pv,
        "annual_cost": avg_annual_costs,
        "co2_emissions_kg": total_emissions["co2"],
        "co2_cost_nominal": total_costs_by_pollutant["co2"],
        "co2_cost_pv": total_costs_by_pollutant_pv["co2"],
        "sox_emissions_kg": total_emissions["sox"],
        "sox_cost_nominal": total_costs_by_pollutant["sox"],
        "sox_cost_pv": total_costs_by_pollutant_pv["sox"],
        "nox_emissions_kg": total_emissions["nox"],
        "nox_cost_nominal": total_costs_by_pollutant["nox"],
        "nox_cost_pv": total_costs_by_pollutant_pv["nox"],
    }

    # Write to CSV
    csv_manager.add_emissions_costs(results)
    csv_manager.write_batch_summary()


if __name__ == "__main__":
    main()
