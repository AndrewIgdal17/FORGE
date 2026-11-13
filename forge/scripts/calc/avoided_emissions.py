"""Avoided-emissions benefit.

A margin line prices ``relief_mw * (H_fwd - H_rev)`` at the receiving rate
minus the sending rate. A dedicated line keeps the delivered-energy formula
and the resource's own rates. Operating year tau's amount is placed at
calendar year t = t_cod + tau - 1 and discounted at the social rate.
"""

from __future__ import annotations

import logging
from typing import Any

from forge.scripts.calc.emissions import place_operating_years
from forge.scripts.calc.energy_losses import load_project_technical_details
from forge.scripts.utils.smart_output import SmartOutputManager
from forge.scripts.utils.streams import pv, undiscounted

logger = logging.getLogger(__name__)

_HFWD = (
    "01_project_technical_details.market_measurements.hours_receiving_more_congested"
)
_HREV = (
    "01_project_technical_details.market_measurements.hours_sending_more_congested"
)


def _with_source(rates_used: dict, sending_source: str) -> dict[str, Any]:
    used: dict[str, Any] = {
        key: (dict(value) if isinstance(value, dict) else value)
        for key, value in rates_used.items()
    }
    sending = dict(used.get("sending", {}))
    sending["source"] = sending_source
    used["sending"] = sending
    return used


def _availability(available: bool) -> dict[str, Any]:
    return {
        "avoided_emissions_benefit": {
            "available": available,
            "missing_inputs": () if available else (_HFWD, _HREV),
        }
    }


def _terminal(details: Any, end: str) -> dict[str, Any]:
    return {
        "gea": getattr(details, f"{end}_gea"),
        "egrid_subregion": getattr(details, f"{end}_egrid_subregion"),
        "state": getattr(details, f"{end}_state"),
    }


def _measurement(name: str) -> float | None:
    from forge.scripts.utils.smart_loaders import get_project_data_raw

    block = get_project_data_raw().get("market_measurements") or {}
    if not isinstance(block, dict):
        return None
    value = block.get(name)
    if value is None:
        return None
    return float(value)


def resolve_rate_series(
    details: Any,
    years: list[int],
    *,
    hours_forward: float | None,
    hours_reverse: float | None,
) -> dict[str, Any]:
    """Look up the series the formula prices.

    A dedicated line uses the resource's rates at the sending end and does
    not read a sending Cambium or eGRID series. A present terminal is still
    returned on ``rates_used``. A margin line with either hour count missing
    does not look up rates; the caller reports the component not available.
    """
    from forge.emissions_data import (
        criteria_damage_2025_usd_per_kg,
        egrid_rates,
        lrmer_co2e,
        sc_co2_2025_usd_per_kg,
    )

    dedicated = details.sending_source == "dedicated"
    receiving = _terminal(details, "receiving")
    sending = _terminal(details, "sending")
    missing = (not dedicated) and (hours_forward is None or hours_reverse is None)
    if dedicated:
        # Resource rates first. A missing sending GEA is not a Cambium lookup.
        snd_co2e = [float(details.emission_rate_co2e)] * len(years)
        snd_so2 = float(details.emission_rate_so2)
        snd_nox = float(details.emission_rate_nox)
        rcv_co2e = [lrmer_co2e(details.receiving_gea, year) for year in years]
        rcv_so2, rcv_nox = egrid_rates(details.receiving_egrid_subregion)
        priced = True
    elif missing:
        snd_co2e = []
        rcv_co2e = []
        snd_so2 = snd_nox = rcv_so2 = rcv_nox = 0.0
        priced = False
    else:
        rcv_co2e = [lrmer_co2e(details.receiving_gea, year) for year in years]
        snd_co2e = [lrmer_co2e(details.sending_gea, year) for year in years]
        rcv_so2, rcv_nox = egrid_rates(details.receiving_egrid_subregion)
        snd_so2, snd_nox = egrid_rates(details.sending_egrid_subregion)
        priced = True
    if priced:
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
    else:
        c_co2e = []
        c_so2_rcv = []
        c_nox_rcv = []
        c_so2_snd = []
        c_nox_snd = []
    return {
        "rcv_co2e": rcv_co2e,
        "snd_co2e": snd_co2e,
        "rcv_so2": rcv_so2,
        "rcv_nox": rcv_nox,
        "snd_so2": snd_so2,
        "snd_nox": snd_nox,
        "c_co2e": c_co2e,
        "c_so2_rcv": c_so2_rcv,
        "c_nox_rcv": c_nox_rcv,
        "c_so2_snd": c_so2_snd,
        "c_nox_snd": c_nox_snd,
        "receiving": receiving,
        "sending": sending,
    }


def calculate_avoided_emissions(
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
    relief_mw: float | None = None,
    hours_forward: float | None = None,
    hours_reverse: float | None = None,
    e_deliv_mwh_per_year: float | None = None,
) -> dict[str, Any]:
    """Price avoided emissions from terminal rates and each end's damage price.

    Margin mass is ``relief_mw * (H_fwd - H_rev) * (eps_rcv - eps_snd)``.
    Dollars use each end's own state price and the national CO2e cost. The
    margin case does not read delivered energy. ``H_fwd < H_rev`` is negative
    and available. A missing hour count is not available: dollar and mass
    keys are null, ``net_binding_hours`` is null, and ``rates_used`` stays
    filled. Dedicated keeps delivered energy in place of that factor and the
    resource rates already supplied by the caller.
    """
    dedicated = sending_source == "dedicated"
    if not dedicated and (hours_forward is None or hours_reverse is None):
        return {
            "avoided_emissions_pv": None,
            "avoided_emissions_nominal": None,
            "avoided_emissions_annual_values": None,
            "streams": {"avoided_emissions_benefit": None},
            "annual_kg_avoided": None,
            "rates_used": _with_source(rates_used, sending_source),
            "net_binding_hours": None,
            "relief_mw": relief_mw,
            "availability": _availability(False),
        }

    if dedicated:
        factor = float(e_deliv_mwh_per_year)
        net_binding_hours = None
    else:
        net_binding_hours = float(hours_forward) - float(hours_reverse)
        factor = float(relief_mw) * net_binding_hours

    annual: list[float] = []
    kg: dict[str, list[float]] = {"co2e": [], "so2": [], "nox": []}
    for i, eps_rcv in enumerate(rcv_co2e):
        q_co2e = factor * (eps_rcv - snd_co2e[i])
        q_so2 = factor * (rcv_so2 - snd_so2)
        q_nox = factor * (rcv_nox - snd_nox)
        dollars = (
            q_co2e * c_co2e[i]
            + factor * (rcv_so2 * c_so2_rcv[i] - snd_so2 * c_so2_snd[i])
            + factor * (rcv_nox * c_nox_rcv[i] - snd_nox * c_nox_snd[i])
        )
        annual.append(dollars)
        kg["co2e"].append(q_co2e)
        kg["so2"].append(q_so2)
        kg["nox"].append(q_nox)
    stream = place_operating_years(annual, t_cod, horizon)
    result: dict[str, Any] = {
        "avoided_emissions_pv": pv(stream, social_discount_rate),
        "avoided_emissions_nominal": undiscounted(stream),
        "avoided_emissions_annual_values": annual,
        "streams": {"avoided_emissions_benefit": stream},
        "annual_kg_avoided": kg,
        "rates_used": _with_source(rates_used, sending_source),
        "net_binding_hours": net_binding_hours,
        "availability": _availability(True),
    }
    if dedicated:
        result["energy_delivered_annual_mwh_yr"] = factor
    else:
        result["relief_mw"] = float(relief_mw)
    return result


def main() -> None:
    """Price avoided emissions for a margin or dedicated line."""
    from forge.emissions_data import calendar_year
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
    dedicated = details.sending_source == "dedicated"
    if dedicated:
        hours_forward = None
        hours_reverse = None
    else:
        hours_forward = _measurement("hours_receiving_more_congested")
        hours_reverse = _measurement("hours_sending_more_congested")
    series = resolve_rate_series(
        details,
        years,
        hours_forward=hours_forward,
        hours_reverse=hours_reverse,
    )
    output = SmartOutputManager()
    if dedicated:
        delivered = output.require_upstream(
            "benefits", "congestion", "energy_delivered_annual_mwh_yr"
        )
        relief = None
    else:
        delivered = None
        relief = ctx.derived_parameters["relief_mw"]
    results = calculate_avoided_emissions(
        sending_source=details.sending_source,
        relief_mw=relief,
        hours_forward=hours_forward,
        hours_reverse=hours_reverse,
        e_deliv_mwh_per_year=delivered,
        rcv_co2e=series["rcv_co2e"],
        snd_co2e=series["snd_co2e"],
        rcv_so2=series["rcv_so2"],
        rcv_nox=series["rcv_nox"],
        snd_so2=series["snd_so2"],
        snd_nox=series["snd_nox"],
        c_co2e=series["c_co2e"],
        c_so2_rcv=series["c_so2_rcv"],
        c_nox_rcv=series["c_nox_rcv"],
        c_so2_snd=series["c_so2_snd"],
        c_nox_snd=series["c_nox_snd"],
        t_cod=ctx.t_cod,
        horizon=ctx.horizon,
        social_discount_rate=ctx.social_discount_rate,
        rates_used={
            "receiving": series["receiving"],
            "sending": series["sending"],
        },
    )
    if results["avoided_emissions_pv"] is None:
        logger.info("Avoided emissions: not available")
    else:
        logger.info(
            "Avoided emissions PV: $%s",
            f"{results['avoided_emissions_pv']:,.2f}",
        )
    output.add_avoided_emissions(results)
    output.write_batch_summary()
