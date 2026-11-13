"""Loss-compensation emissions.

A margin line splits compensated losses by the share of hours the sending
end is more congested. A dedicated line prices the resource's own rates at
the sending state's damage costs. Operating year tau's amount is placed at
calendar year t = t_cod + tau - 1 and discounted at the social rate.
"""

from __future__ import annotations

import logging
from typing import Any

from forge.scripts.calc.energy_losses import (
    get_total_energy_losses,
    load_project_technical_details,
)
from forge.scripts.utils.constants import HOURS_PER_YEAR
from forge.scripts.utils.smart_loaders import (
    get_project_data_raw,
    load_emissions_details,
)
from forge.scripts.utils.smart_output import SmartOutputManager
from forge.scripts.utils.streams import pv, undiscounted

logger = logging.getLogger(__name__)

_HOURS_REV_PATH = (
    "01_project_technical_details.market_measurements.hours_sending_more_congested"
)
_POLLUTANTS = ("co2e", "so2", "nox")


def place_operating_years(
    annual_values: list[float], t_cod: int, horizon: int
) -> list[float]:
    """Place operating year tau's amount at calendar year t = t_cod + tau - 1."""
    stream = [0.0] * horizon
    for tau, amount in enumerate(annual_values, start=1):
        t = t_cod + tau - 1
        stream[t - 1] = amount
    return stream


def _hours_sending_more_congested() -> float | None:
    """Measured reverse hours, or None when the count was not supplied."""
    block = get_project_data_raw().get("market_measurements") or {}
    if not isinstance(block, dict):
        return None
    value = block.get("hours_sending_more_congested")
    if value is None:
        return None
    return float(value)


def _rates_used(
    receiving: dict[str, Any],
    sending: dict[str, Any],
    sending_source: str,
    share_receiving: float | None,
) -> dict[str, Any]:
    sending_used = dict(sending)
    sending_used["source"] = sending_source
    return {
        "receiving": dict(receiving),
        "sending": sending_used,
        "share_receiving": None if sending_source == "dedicated" else share_receiving,
    }


def _availability(available: bool) -> dict[str, Any]:
    return {
        "emissions_comp": {
            "available": available,
            "missing_inputs": () if available else (_HOURS_REV_PATH,),
        }
    }


def _not_available(
    receiving: dict[str, Any],
    sending: dict[str, Any],
    sending_source: str,
) -> dict[str, Any]:
    """Margin line with no reverse-hour count. Identifiers stay filled."""
    return {
        "total_nominal": None,
        "total_pv": None,
        "annual_cost": None,
        "emissions_comp_annual_values": None,
        "streams": {"emissions_comp": None},
        "annual_kg": None,
        "damage_cost_per_kg": None,
        "rates_used": _rates_used(receiving, sending, sending_source, None),
        "availability": _availability(False),
    }


def calculate_loss_compensation(
    e_loss_mwh_per_year: float,
    compensation_fraction: float,
    *,
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
    share_receiving: float | None,
    sending_source: str,
    t_cod: int,
    horizon: int,
    social_discount_rate: float,
    receiving: dict[str, Any],
    sending: dict[str, Any],
) -> dict[str, Any]:
    """Price loss compensation from rates the caller already looked up.

    Margin dollars are ``E_comp`` times the hour-weighted sum of each end's
    rate bundle. Dedicated dollars are ``E_comp * eps_res * c_snd`` and do
    not use ``share_receiving``. A margin line with ``share_receiving is
    None`` is not available. ``annual_cost`` is the mean of the operating-year
    dollars. Present value uses ``place_operating_years`` and then ``streams.pv``.
    """
    if sending_source != "dedicated" and share_receiving is None:
        return _not_available(receiving, sending, sending_source)

    e_comp = compensation_fraction * e_loss_mwh_per_year
    dedicated = sending_source == "dedicated"
    weight_rcv = 0.0 if dedicated else float(share_receiving)
    weight_snd = 1.0 - weight_rcv
    n = len(snd_co2e)
    annual: list[float] = []
    mass_snd = {name: [] for name in _POLLUTANTS}
    mass_rcv = {name: [] for name in _POLLUTANTS}
    for i in range(n):
        snd_kg = {
            "co2e": e_comp * weight_snd * snd_co2e[i],
            "so2": e_comp * weight_snd * snd_so2,
            "nox": e_comp * weight_snd * snd_nox,
        }
        if dedicated:
            rcv_kg = {name: 0.0 for name in _POLLUTANTS}
            dollars = (
                snd_kg["co2e"] * c_co2e[i]
                + snd_kg["so2"] * c_so2_snd[i]
                + snd_kg["nox"] * c_nox_snd[i]
            )
        else:
            rcv_kg = {
                "co2e": e_comp * weight_rcv * rcv_co2e[i],
                "so2": e_comp * weight_rcv * rcv_so2,
                "nox": e_comp * weight_rcv * rcv_nox,
            }
            dollars = (
                snd_kg["co2e"] * c_co2e[i]
                + snd_kg["so2"] * c_so2_snd[i]
                + snd_kg["nox"] * c_nox_snd[i]
                + rcv_kg["co2e"] * c_co2e[i]
                + rcv_kg["so2"] * c_so2_rcv[i]
                + rcv_kg["nox"] * c_nox_rcv[i]
            )
        annual.append(dollars)
        for name in _POLLUTANTS:
            mass_snd[name].append(snd_kg[name])
            mass_rcv[name].append(rcv_kg[name])
    total_kg = {
        name: [mass_snd[name][i] + mass_rcv[name][i] for i in range(n)]
        for name in _POLLUTANTS
    }
    stream = place_operating_years(annual, t_cod, horizon)
    return {
        "total_nominal": undiscounted(stream),
        "total_pv": pv(stream, social_discount_rate),
        "annual_cost": (sum(annual) / n) if n else 0.0,
        "emissions_comp_annual_values": annual,
        "streams": {"emissions_comp": stream},
        "annual_kg": {
            "sending": mass_snd,
            "receiving": mass_rcv,
            "total": total_kg,
        },
        "damage_cost_per_kg": {
            "sending": {
                "co2e": list(c_co2e[:n]),
                "so2": list(c_so2_snd[:n]),
                "nox": list(c_nox_snd[:n]),
            },
            "receiving": {
                "co2e": list(c_co2e[:n]),
                "so2": list(c_so2_rcv[:n]),
                "nox": list(c_nox_rcv[:n]),
            },
        },
        "rates_used": _rates_used(receiving, sending, sending_source, share_receiving),
        "availability": _availability(True),
    }


def _terminal(details: Any, end: str) -> dict[str, Any]:
    return {
        "gea": getattr(details, f"{end}_gea"),
        "egrid_subregion": getattr(details, f"{end}_egrid_subregion"),
        "state": getattr(details, f"{end}_state"),
    }


def _criteria(state: str, pollutant: str, years: list[int]) -> list[float]:
    from forge.emissions_data import criteria_damage_2025_usd_per_kg

    return [
        criteria_damage_2025_usd_per_kg(state, pollutant, year) for year in years
    ]


def main() -> None:
    """Price loss-compensation emissions for a margin or dedicated line."""
    from forge.emissions_data import (
        calendar_year,
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
    receiving = _terminal(details, "receiving")
    sending = _terminal(details, "sending")
    dedicated = details.sending_source == "dedicated"
    # A dedicated resource does not use a sending Cambium or eGRID series.
    # The sending state is still required for criteria damage.
    if dedicated:
        share = None
        snd_co2e = [float(details.emission_rate_co2e)] * len(years)
        snd_so2 = float(details.emission_rate_so2)
        snd_nox = float(details.emission_rate_nox)
        rcv_co2e = [0.0] * len(years)
        rcv_so2 = 0.0
        rcv_nox = 0.0
    else:
        hours_rev = _hours_sending_more_congested()
        share = None if hours_rev is None else hours_rev / HOURS_PER_YEAR
        if share is None:
            snd_co2e = []
            rcv_co2e = []
            snd_so2 = snd_nox = rcv_so2 = rcv_nox = 0.0
        else:
            snd_co2e = [lrmer_co2e(details.sending_gea, year) for year in years]
            rcv_co2e = [lrmer_co2e(details.receiving_gea, year) for year in years]
            snd_so2, snd_nox = egrid_rates(details.sending_egrid_subregion)
            rcv_so2, rcv_nox = egrid_rates(details.receiving_egrid_subregion)
    if dedicated or share is not None:
        c_co2e = [sc_co2_2025_usd_per_kg(year) for year in years]
        c_so2_snd = _criteria(details.sending_state, "so2", years)
        c_nox_snd = _criteria(details.sending_state, "nox", years)
        c_so2_rcv = _criteria(details.receiving_state, "so2", years)
        c_nox_rcv = _criteria(details.receiving_state, "nox", years)
    else:
        c_co2e = c_so2_snd = c_nox_snd = c_so2_rcv = c_nox_rcv = []
    results = calculate_loss_compensation(
        total_losses_mwh_per_year,
        compensation_fraction,
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
        share_receiving=share,
        sending_source=details.sending_source,
        t_cod=ctx.t_cod,
        horizon=ctx.horizon,
        social_discount_rate=ctx.social_discount_rate,
        receiving=receiving,
        sending=sending,
    )

    if results["total_pv"] is None:
        logger.info("Loss-compensation emissions: not available")
    else:
        logger.info(
            "Loss-compensation emissions PV: $%s",
            f"{results['total_pv']:,.2f}",
        )
    output = SmartOutputManager()
    output.add_emissions_comp_costs(results)
    output.write_batch_summary()
