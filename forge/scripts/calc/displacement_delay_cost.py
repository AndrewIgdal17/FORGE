"""Displacement delay emissions cost module.

Computes the foregone emissions displacement benefit during the delay period:
every year a project sits in delay is a year where dirty generation runs
instead of being displaced by the project's cleaner generation mix. This
module values that foregone displacement at year-specific social cost of
carbon (SCC) and discounts it to present value at the social discount rate.

Single-trajectory model (see design doc
2026-07-07__single-trajectory-grid-mix-redesign.md): both the without-line
and with-line (hypothetical) trajectories start from the same initial grid
mix at year 0. Without-line evolves at rate_pre_cod; with-line evolves at
rate_post_cod (hypothetically, as if the line's influence started at year 0).
At COD, the with-line trajectory resets to the without-line state — that
handoff is implemented in facilitated_emissions.py via compute_cod_state().

Reuses the evolution engine and emissions-by-year functions from emissions.py
(the same engine used by facilitated_emissions.py).

Methodology note: enabling_resources_displacement_emissions_method.md.
Appendix: sec:app-displacement-delay.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, Any

from forge.scripts.utils.smart_output import SmartOutputManager
from forge.scripts.calc.emissions import calculate_energy_mix_by_year, calculate_emissions_by_year, build_mix_input
from forge.scripts.utils.smart_loaders import (
    load_emissions_details,
    load_grid_mix,
    load_financing_social_discount_rate,
)
from forge.scripts.calc.energy_losses import load_project_technical_details

logger = logging.getLogger(__name__)


@dataclass
class DisplacementDelayCostResults:
    """Results from the displacement delay cost calculation."""
    displacement_delay_cost_pv: float = 0.0
    displacement_delay_cost_nominal: float = 0.0
    pv_by_pollutant: Dict[str, float] = field(default_factory=dict)

def calculate_displacement_delay_cost(
    energy_delivered_annual_mwh: float,
    grid_mix: Dict[str, Any],
    emission_intensities: Dict[str, Any],
    societal_costs: Dict[str, float],
    delay_years: int,
    social_discount_rate: float,
) -> DisplacementDelayCostResults:
    """Compute the PV cost of foregone emissions displacement during delay.

    Both trajectories start from the same initial grid mix at year 0:
    without-line evolves at rate_pre_cod, with-line (hypothetical) evolves at
    rate_post_cod. For each delay year t (1-indexed), evolves both to year t,
    computes the emissions difference (the displacement that WOULD have
    occurred had the project been operational), values it at year-t SCC, and
    discounts to PV at the social discount rate.
    """
    pollutants = ["co2", "sox", "nox"]

    if delay_years is None or delay_years <= 0 or energy_delivered_annual_mwh <= 0:
        return DisplacementDelayCostResults(
            pv_by_pollutant={p: 0.0 for p in pollutants}
        )

    delay_years_int = int(delay_years)

    noline_input = build_mix_input(grid_mix["initial"], grid_mix["rate_pre_cod"])
    withline_input = build_mix_input(grid_mix["initial"], grid_mix["rate_post_cod"])

    noline_mix_by_year = calculate_energy_mix_by_year(noline_input, delay_years_int)
    withline_mix_by_year = calculate_energy_mix_by_year(withline_input, delay_years_int)

    total_nominal = 0.0
    total_pv = 0.0
    pv_by_pollutant = {p: 0.0 for p in pollutants}

    for t in range(delay_years_int):
        noline_emissions = calculate_emissions_by_year(
            energy_delivered_annual_mwh, noline_mix_by_year[t], emission_intensities
        )
        withline_emissions = calculate_emissions_by_year(
            energy_delivered_annual_mwh, withline_mix_by_year[t], emission_intensities
        )

        year_cost = 0.0
        discount_factor = (1 + social_discount_rate) ** (t + 1)
        for pollutant in pollutants:
            emissions_diff_kg = (
                noline_emissions[pollutant] - withline_emissions[pollutant]
            )
            base_cost = societal_costs.get(f"{pollutant}_cost_per_kg", 0.0)
            growth = societal_costs.get(f"{pollutant}_cost_annual_growth", 0.0)
            cost_per_kg = base_cost * (1 + growth) ** t
            pollutant_cost = emissions_diff_kg * cost_per_kg
            year_cost += pollutant_cost
            pv_by_pollutant[pollutant] += pollutant_cost / discount_factor

        total_nominal += year_cost
        total_pv += year_cost / discount_factor

    return DisplacementDelayCostResults(
        displacement_delay_cost_pv=total_pv,
        displacement_delay_cost_nominal=total_nominal,
        pv_by_pollutant=pv_by_pollutant,
    )

def print_displacement_delay_cost_results(
    results: DisplacementDelayCostResults,
    energy_delivered_annual_mwh: float,
    delay_years: float,
) -> None:
    """Print displacement delay cost results."""
    logger.info("=" * 60)
    logger.info("DISPLACEMENT DELAY EMISSIONS COST")
    logger.info("=" * 60)
    logger.info(f"Delay years: {delay_years}")
    logger.info(f"Scope: E_delivered_annual = {energy_delivered_annual_mwh:,.2f} MWh/yr")
    logger.info("")
    logger.info(f"  Nominal: ${results.displacement_delay_cost_nominal:,.2f}")
    logger.info(f"  PV:      ${results.displacement_delay_cost_pv:,.2f}")
    for p, v in results.pv_by_pollutant.items():
        logger.info(f"    {p.upper()} PV: ${v:,.2f}")
    logger.info("")

def main() -> None:
    """Entry point for the displacement delay cost pipeline step."""
    (
        _compensation_percent,
        emission_intensities,
        societal_costs,
    ) = load_emissions_details()

    grid_mix = load_grid_mix()

    social_discount_rate = load_financing_social_discount_rate()
    project_details = load_project_technical_details()

    output_manager = SmartOutputManager()
    actual_manager = getattr(output_manager, '_manager', output_manager)
    energy_delivered_annual_mwh = 0.0

    if hasattr(actual_manager, 'require_upstream'):
        try:
            energy_delivered_annual_mwh = actual_manager.require_upstream(
                "benefits", "congestion", "energy_delivered_annual_mwh_yr"
            )
        except KeyError as exc:
            logger.warning(f"⚠️  {exc}")
    elif hasattr(actual_manager, 'benefits'):
        cc_results = actual_manager.benefits.get("congestion", {})
        energy_delivered_annual_mwh = cc_results.get("energy_delivered_annual_mwh_yr", 0.0)


    if project_details.delay_years <= 0:
        logger.info("ℹ️  delay_years is 0 — no displacement delay period, cost is zero.")
    elif energy_delivered_annual_mwh <= 0:
        logger.warning("⚠️  E_delivered_annual is 0 or missing — displacement delay cost is zero.")

    results = calculate_displacement_delay_cost(
        energy_delivered_annual_mwh=energy_delivered_annual_mwh,
        grid_mix=grid_mix,
        emission_intensities=emission_intensities,
        societal_costs=societal_costs,
        delay_years=project_details.delay_years,
        social_discount_rate=social_discount_rate,
    )

    print_displacement_delay_cost_results(
        results, energy_delivered_annual_mwh, project_details.delay_years
    )

    output_results = {
        "displacement_delay_cost_pv": results.displacement_delay_cost_pv,
        "displacement_delay_cost_nominal": results.displacement_delay_cost_nominal,
        "co2_pv": results.pv_by_pollutant.get("co2", 0.0),
        "sox_pv": results.pv_by_pollutant.get("sox", 0.0),
        "nox_pv": results.pv_by_pollutant.get("nox", 0.0),
        "energy_delivered_annual_mwh": energy_delivered_annual_mwh,
    }
    output_manager.add_displacement_delay_cost(output_results)
    output_manager.write_batch_summary()
