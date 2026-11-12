"""Avoided-emissions benefit.

The with-line and no-line grid-mix paths, their monetization, and the
no-line minus with-line difference are today's arithmetic, moved unchanged.
Operating year tau's amount is placed at
calendar year t = t_cod + tau - 1 and discounted at the social rate.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from forge.scripts.calc.emissions import (
    build_mix_input,
    calculate_emissions_by_year,
    calculate_energy_mix_by_year,
    compute_cod_state,
    monetize_annual_emissions,
    place_operating_years,
)
from forge.scripts.calc.energy_losses import load_project_technical_details
from forge.scripts.utils.financial_utils import calculate_cod_year
from forge.scripts.utils.smart_loaders import (
    load_emissions_details,
    load_grid_mix,
)
from forge.scripts.utils.smart_output import SmartOutputManager
from forge.scripts.utils.streams import pv, undiscounted

logger = logging.getLogger(__name__)


def _compute_instance_costs(
    energy_delivered_annual_mwh: float,
    mix_by_year: List[Dict[str, float]],
    emission_intensities: Dict[str, Any],
    societal_costs: Dict[str, float],
    social_discount_rate: float,
    start_year: float,
) -> tuple:
    """Compute nominal + PV emissions cost for one instance over all years.

    Returns (total_nominal, total_pv, pv_by_pollutant, annual_values).
    annual_values is the nominal (undiscounted) cost for each year, in order,
    length = len(mix_by_year) = project_lifetime.
    """
    pollutants = ["co2", "sox", "nox"]
    total_nominal = 0.0
    total_pv = 0.0
    pv_by_pollutant = {p: 0.0 for p in pollutants}
    annual_values = []

    for year_idx, energy_mix in enumerate(mix_by_year):
        emissions = calculate_emissions_by_year(
            energy_delivered_annual_mwh, energy_mix, emission_intensities
        )
        year_cost = monetize_annual_emissions(emissions, societal_costs, year_idx)
        total_nominal += year_cost
        annual_values.append(year_cost)

        year_number = year_idx + 1
        discount_year = start_year + year_number - 1
        year_pv = year_cost / ((1 + social_discount_rate) ** discount_year)
        total_pv += year_pv

        for pollutant, emissions_kg in emissions.items():
            pollutant_cost = monetize_annual_emissions(
                {pollutant: emissions_kg}, societal_costs, year_idx
            )
            pollutant_pv = pollutant_cost / (
                (1 + social_discount_rate) ** discount_year
            )
            pv_by_pollutant[pollutant] += pollutant_pv

    return total_nominal, total_pv, pv_by_pollutant, annual_values


def calculate_avoided_emissions(
    energy_delivered_annual_mwh: float,
    grid_mix: Dict[str, Any],
    emission_intensities: Dict[str, Any],
    societal_costs: Dict[str, float],
    project_lifetime: int,
    social_discount_rate: float,
    delay_years: float,
    construction_years: int,
    t_cod: int,
    horizon: int,
) -> dict[str, Any]:
    """No-line minus with-line social cost of delivered energy.

    Both operational trajectories start from the grid state at COD. Without-line
    continues at rate_pre_cod. With-line evolves at rate_post_cod. The benefit
    in each operating year is the no-line monetized cost minus the with-line cost.
    """
    start_year = calculate_cod_year(delay_years, construction_years)

    cod_state_pct = compute_cod_state(grid_mix, delay_years, construction_years)
    withline_ops_input = build_mix_input(cod_state_pct, grid_mix["rate_post_cod"])
    noline_ops_input = build_mix_input(cod_state_pct, grid_mix["rate_pre_cod"])

    proj_mix = calculate_energy_mix_by_year(withline_ops_input, project_lifetime)
    noline_mix = calculate_energy_mix_by_year(noline_ops_input, project_lifetime)

    _proj_nom, _proj_pv, _proj_by_poll, proj_annual_values = _compute_instance_costs(
        energy_delivered_annual_mwh, proj_mix, emission_intensities,
        societal_costs, social_discount_rate, start_year,
    )
    _noline_nom, _noline_pv, _noline_by_poll, noline_annual_values = _compute_instance_costs(
        energy_delivered_annual_mwh, noline_mix, emission_intensities,
        societal_costs, social_discount_rate, start_year,
    )

    annual_values = [
        noline_annual_values[i] - proj_annual_values[i]
        for i in range(len(noline_annual_values))
    ]
    stream = place_operating_years(annual_values, t_cod, horizon)
    return {
        "avoided_emissions_pv": pv(stream, social_discount_rate),
        "avoided_emissions_nominal": undiscounted(stream),
        "avoided_emissions_annual_values": annual_values,
        "streams": {"avoided_emissions_benefit": stream},
    }


def calculate_avoided_benefit(
    e_deliv_mwh_per_year: float,
    *,
    sending_source: str,
    rcv_co2e: list[float],
    snd_co2e: list[float],
    rcv_so2: float,
    rcv_nox: float,
    snd_so2: float,
    snd_nox: float,
    c_co2e: list[float],
    c_so2_rcv: list[float],
    c_nox_rcv: list[float],
    c_so2_snd: list[float],
    c_nox_snd: list[float],
    t_cod: int,
    horizon: int,
    social_discount_rate: float,
    rates_used: dict,
) -> dict[str, Any]:
    """Price delivered energy at the receiving rate minus the sending rate.

    CO2e dollars are that mass times the year's social cost. SO2 and NOx
    dollars use each terminal's own damage price, ``E * (eps * c)`` at that
    end, not the mass difference times one price. ``E_deliv == 0`` still
    returns this dict; the benefit stream is zeros of length ``horizon``.
    """
    annual: list[float] = []
    kg: dict[str, list[float]] = {"co2e": [], "so2": [], "nox": []}
    for i, eps_rcv in enumerate(rcv_co2e):
        q_co2e = e_deliv_mwh_per_year * (eps_rcv - snd_co2e[i])
        q_so2 = e_deliv_mwh_per_year * (rcv_so2 - snd_so2)
        q_nox = e_deliv_mwh_per_year * (rcv_nox - snd_nox)
        dollars = (
            q_co2e * c_co2e[i]
            + e_deliv_mwh_per_year * (rcv_so2 * c_so2_rcv[i] - snd_so2 * c_so2_snd[i])
            + e_deliv_mwh_per_year * (rcv_nox * c_nox_rcv[i] - snd_nox * c_nox_snd[i])
        )
        annual.append(dollars)
        kg["co2e"].append(q_co2e)
        kg["so2"].append(q_so2)
        kg["nox"].append(q_nox)
    stream = place_operating_years(annual, t_cod, horizon)
    used: dict[str, Any] = {
        key: (dict(value) if isinstance(value, dict) else value)
        for key, value in rates_used.items()
    }
    sending = dict(used.get("sending", {}))
    sending["source"] = sending_source
    used["sending"] = sending
    return {
        "avoided_emissions_pv": pv(stream, social_discount_rate),
        "avoided_emissions_nominal": undiscounted(stream),
        "avoided_emissions_annual_values": annual,
        "streams": {"avoided_emissions_benefit": stream},
        "annual_kg_avoided": kg,
        "rates_used": used,
    }


def main() -> None:
    """Entry point for the avoided-emissions pipeline step."""
    from forge.scripts.utils.run_context import get_run_context

    ctx = get_run_context()
    if ctx is None:
        raise RuntimeError(
            f"{__name__} requires a RunContext. Run via forge.py or set up "
            "RunContext in your test fixture."
        )

    (
        _compensation_percent,
        emission_intensities,
        societal_costs,
    ) = load_emissions_details()

    grid_mix = load_grid_mix()
    social_discount_rate = ctx.social_discount_rate
    project_details = load_project_technical_details()

    output_manager = SmartOutputManager()
    actual_manager = getattr(output_manager, "_manager", output_manager)
    energy_delivered_annual_mwh = 0.0

    if hasattr(actual_manager, "require_upstream"):
        try:
            energy_delivered_annual_mwh = actual_manager.require_upstream(
                "benefits", "congestion", "energy_delivered_annual_mwh_yr"
            )
        except KeyError as exc:
            logger.warning(f"⚠️  {exc}")
    elif hasattr(actual_manager, "benefits"):
        cc_results = actual_manager.benefits.get("congestion", {})
        energy_delivered_annual_mwh = cc_results.get("energy_delivered_annual_mwh_yr", 0.0)

    if energy_delivered_annual_mwh <= 0:
        logger.warning("⚠️  E_delivered_annual is 0 or missing — skipping avoided emissions.")
        return

    results = calculate_avoided_emissions(
        energy_delivered_annual_mwh=energy_delivered_annual_mwh,
        grid_mix=grid_mix,
        emission_intensities=emission_intensities,
        societal_costs=societal_costs,
        project_lifetime=project_details.project_lifetime,
        social_discount_rate=social_discount_rate,
        delay_years=project_details.delay_years,
        construction_years=project_details.construction_years,
        t_cod=ctx.t_cod,
        horizon=ctx.horizon,
    )

    logger.info("=" * 60)
    logger.info("AVOIDED EMISSIONS BENEFIT")
    logger.info("=" * 60)
    logger.info(f"Scope: E_delivered_annual = {energy_delivered_annual_mwh:,.2f} MWh/yr")
    logger.info(f"  Nominal: ${results['avoided_emissions_nominal']:,.2f}")
    logger.info(f"  PV:      ${results['avoided_emissions_pv']:,.2f}")
    logger.info("")

    output_manager.add_avoided_emissions(results)
    output_manager.write_batch_summary()
