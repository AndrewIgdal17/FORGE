"""Loss-compensation emissions.

Line losses that generators make up are priced at the receiving-end
emission rates and damage costs. Operating year tau's amount is placed at
calendar year t = t_cod + tau - 1 and discounted at the social rate.
"""

from __future__ import annotations

import logging

from forge.scripts.calc.energy_losses import (
    get_total_energy_losses,
    load_project_technical_details,
)
from forge.scripts.utils.smart_loaders import load_emissions_details
from forge.scripts.utils.smart_output import SmartOutputManager
from forge.scripts.utils.streams import pv, undiscounted

logger = logging.getLogger(__name__)


def place_operating_years(
    annual_values: list[float], t_cod: int, horizon: int
) -> list[float]:
    """Place operating year tau's amount at calendar year t = t_cod + tau - 1."""
    stream = [0.0] * horizon
    for tau, amount in enumerate(annual_values, start=1):
        t = t_cod + tau - 1
        stream[t - 1] = amount
    return stream


def calculate_loss_compensation(
    e_loss_mwh_per_year: float,
    compensation_fraction: float,
    *,
    co2e_kg_per_mwh: list[float],
    so2_kg_per_mwh: float,
    nox_kg_per_mwh: float,
    c_co2e_usd_per_kg: list[float],
    c_so2_usd_per_kg: list[float],
    c_nox_usd_per_kg: list[float],
    t_cod: int,
    horizon: int,
    social_discount_rate: float,
    receiving: dict[str, str],
) -> dict:
    """Price loss-compensation emissions from rates the caller already looked up.

    ``annual_cost`` is the mean of the operating-year dollars. Present value
    uses ``place_operating_years`` and then ``streams.pv``.
    """
    e_comp = compensation_fraction * e_loss_mwh_per_year
    annual: list[float] = []
    annual_kg_co2e: list[float] = []
    for i, eps_co2e in enumerate(co2e_kg_per_mwh):
        annual.append(
            e_comp
            * (
                eps_co2e * c_co2e_usd_per_kg[i]
                + so2_kg_per_mwh * c_so2_usd_per_kg[i]
                + nox_kg_per_mwh * c_nox_usd_per_kg[i]
            )
        )
        annual_kg_co2e.append(e_comp * eps_co2e)
    n = len(annual)
    stream = place_operating_years(annual, t_cod, horizon)
    return {
        "total_nominal": undiscounted(stream),
        "total_pv": pv(stream, social_discount_rate),
        "annual_cost": (sum(annual) / n) if n else 0.0,
        "emissions_comp_annual_values": annual,
        "streams": {"emissions_comp": stream},
        "annual_kg": {
            "co2e": annual_kg_co2e,
            "so2": [e_comp * so2_kg_per_mwh] * n,
            "nox": [e_comp * nox_kg_per_mwh] * n,
        },
        "damage_cost_per_kg": {
            "co2e": list(c_co2e_usd_per_kg[:n]),
            "so2": list(c_so2_usd_per_kg[:n]),
            "nox": list(c_nox_usd_per_kg[:n]),
        },
        "rates_used": {
            "gea": receiving["gea"],
            "egrid_subregion": receiving["egrid_subregion"],
            "state": receiving["state"],
        },
    }


def main() -> None:
    """Price loss-compensation emissions from the receiving-end schedules."""
    from forge.emissions_data import (
        calendar_year,
        criteria_damage_2025_usd_per_kg,
        egrid_rates,
        lrmer_co2e,
        sc_co2_2025_usd_per_kg,
    )
    from forge.scripts.utils.run_context import get_run_context

    ctx = get_run_context()
    if ctx is None:
        raise RuntimeError(
            f"{__name__} requires a RunContext. Run via forge.py or set up "
            "RunContext in your test fixture."
        )

    total_losses_mwh_per_year = get_total_energy_losses()["total_losses_mwh_per_year"]
    compensation_fraction = load_emissions_details()
    details = load_project_technical_details()
    lifetime = int(details.project_lifetime)
    years = [calendar_year(ctx.t_cod + tau - 1) for tau in range(1, lifetime + 1)]
    co2e = [lrmer_co2e(details.receiving_gea, year) for year in years]
    so2, nox = egrid_rates(details.receiving_egrid_subregion)
    c_co2e = [sc_co2_2025_usd_per_kg(year) for year in years]
    c_so2 = [
        criteria_damage_2025_usd_per_kg(details.receiving_state, "so2", year)
        for year in years
    ]
    c_nox = [
        criteria_damage_2025_usd_per_kg(details.receiving_state, "nox", year)
        for year in years
    ]
    results = calculate_loss_compensation(
        total_losses_mwh_per_year,
        compensation_fraction,
        co2e_kg_per_mwh=co2e,
        so2_kg_per_mwh=so2,
        nox_kg_per_mwh=nox,
        c_co2e_usd_per_kg=c_co2e,
        c_so2_usd_per_kg=c_so2,
        c_nox_usd_per_kg=c_nox,
        t_cod=ctx.t_cod,
        horizon=ctx.horizon,
        social_discount_rate=ctx.social_discount_rate,
        receiving={
            "gea": details.receiving_gea,
            "egrid_subregion": details.receiving_egrid_subregion,
            "state": details.receiving_state,
        },
    )

    logger.info("Loss-compensation emissions PV: $%s", f"{results['total_pv']:,.2f}")
    output = SmartOutputManager()
    output.add_emissions_comp_costs(results)
    output.write_batch_summary()
