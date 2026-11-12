"""Avoided-emissions benefit.

Delivered energy is priced at the receiving rate minus the sending rate.
Operating year tau's amount is placed at calendar year t = t_cod + tau - 1
and discounted at the social rate.
"""

from __future__ import annotations

import logging
from typing import Any

from forge.scripts.calc.emissions import place_operating_years
from forge.scripts.calc.energy_losses import load_project_technical_details
from forge.scripts.utils.smart_output import SmartOutputManager
from forge.scripts.utils.streams import pv, undiscounted

logger = logging.getLogger(__name__)


def calculate_avoided_emissions(
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
    """Price avoided emissions at both terminals."""
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

    details = load_project_technical_details()
    lifetime = int(details.project_lifetime)
    years = [calendar_year(ctx.t_cod + tau - 1) for tau in range(1, lifetime + 1)]
    rcv_co2e = [lrmer_co2e(details.receiving_gea, year) for year in years]
    snd_co2e = [lrmer_co2e(details.sending_gea, year) for year in years]
    rcv_so2, rcv_nox = egrid_rates(details.receiving_egrid_subregion)
    snd_so2, snd_nox = egrid_rates(details.sending_egrid_subregion)
    if details.sending_source == "dedicated":
        # A dedicated rate of 0 is a real rate. Do not fall back to the margin.
        snd_co2e = [float(details.emission_rate_co2e)] * len(years)
        snd_so2 = float(details.emission_rate_so2)
        snd_nox = float(details.emission_rate_nox)
    c_co2e = [sc_co2_2025_usd_per_kg(year) for year in years]
    c_so2_rcv = [
        criteria_damage_2025_usd_per_kg(details.receiving_state, "so2", year)
        for year in years
    ]
    c_nox_rcv = [
        criteria_damage_2025_usd_per_kg(details.receiving_state, "nox", year)
        for year in years
    ]
    c_so2_snd = [
        criteria_damage_2025_usd_per_kg(details.sending_state, "so2", year)
        for year in years
    ]
    c_nox_snd = [
        criteria_damage_2025_usd_per_kg(details.sending_state, "nox", year)
        for year in years
    ]
    output = SmartOutputManager()
    delivered = output.require_upstream(
        "benefits", "congestion", "energy_delivered_annual_mwh_yr"
    )
    results = calculate_avoided_emissions(
        delivered,
        sending_source=details.sending_source,
        rcv_co2e=rcv_co2e,
        snd_co2e=snd_co2e,
        rcv_so2=rcv_so2,
        rcv_nox=rcv_nox,
        snd_so2=snd_so2,
        snd_nox=snd_nox,
        c_co2e=c_co2e,
        c_so2_rcv=c_so2_rcv,
        c_nox_rcv=c_nox_rcv,
        c_so2_snd=c_so2_snd,
        c_nox_snd=c_nox_snd,
        t_cod=ctx.t_cod,
        horizon=ctx.horizon,
        social_discount_rate=ctx.social_discount_rate,
        rates_used={
            "receiving": {
                "gea": details.receiving_gea,
                "egrid_subregion": details.receiving_egrid_subregion,
                "state": details.receiving_state,
            },
            "sending": {
                "gea": details.sending_gea,
                "egrid_subregion": details.sending_egrid_subregion,
                "state": details.sending_state,
            },
        },
    )
    logger.info(
        "Avoided emissions PV: $%s",
        f"{results['avoided_emissions_pv']:,.2f}",
    )
    output.add_avoided_emissions(results)
    output.write_batch_summary()
