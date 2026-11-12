"""Load bundled Cambium, eGRID, social-cost, BPT, and CPI-U tables."""
from __future__ import annotations

import csv
from functools import lru_cache

import yaml

from forge.data import get_cpi_path, get_emissions_path
from forge.errors import InvalidInputs

BASE_YEAR = 2025
_HOLD_CAMBIUM_YEAR = 2050
_HOLD_SC_YEAR = 2080
_HOLD_CRITERIA_YEAR = 2040
_KG_PER_SHORT_TON = 907.185
_CRITERIA_GROWTH = 1.02
_RELEASE_KEYS = ("cambium", "egrid", "sc_ghg", "bpt", "cpi_u")


def calendar_year(operating_year: int) -> int:
    """Map operating year t to a calendar year: 2025 + t - 1."""
    return BASE_YEAR + operating_year - 1


def _missing(series: str, field: str, value: object) -> InvalidInputs:
    return InvalidInputs(f"No {series} data for {field} '{value}'.")


@lru_cache(maxsize=1)
def _read_csv(name: str) -> tuple[dict[str, str], ...]:
    path = get_emissions_path() / name
    with path.open(newline="") as handle:
        return tuple(dict(row) for row in csv.DictReader(handle))


@lru_cache(maxsize=1)
def _cambium() -> dict[str, dict[int, float]]:
    table: dict[str, dict[int, float]] = {}
    for row in _read_csv("cambium_lrmer_co2e.csv"):
        series = table.setdefault(row["gea"], {})
        series[int(row["year"])] = float(row["lrmer_co2e_kg_per_mwh"])
    return table


@lru_cache(maxsize=1)
def _egrid() -> dict[str, tuple[float, float]]:
    return {
        row["subregion"]: (
            float(row["so2_kg_per_mwh"]),
            float(row["nox_kg_per_mwh"]),
        )
        for row in _read_csv("egrid_criteria_rates.csv")
    }


@lru_cache(maxsize=1)
def _sc_co2() -> dict[int, float]:
    return {
        int(row["year"]): float(row["sc_co2_2020usd_per_metric_ton"])
        for row in _read_csv("sc_co2_2pct.csv")
    }


@lru_cache(maxsize=1)
def _bpt() -> dict[str, tuple[float, float, float]]:
    return {
        row["state"]: (
            float(row["so2_2019usd_per_short_ton"]),
            float(row["nox_pm_2019usd_per_short_ton"]),
            float(row["nox_o3_2019usd_per_short_ton"]),
        )
        for row in _read_csv("bpt_egu_state.csv")
    }


@lru_cache(maxsize=1)
def _cpi() -> dict[int, float]:
    table: dict[int, float] = {}
    with get_cpi_path().open(newline="") as handle:
        for row in csv.DictReader(handle):
            table[int(row["year"])] = float(row["cpi_u"])
    return table


@lru_cache(maxsize=1)
def _editions() -> dict:
    path = get_emissions_path() / "EDITIONS.yaml"
    with path.open() as handle:
        loaded = yaml.safe_load(handle)
    if not isinstance(loaded, dict):
        raise InvalidInputs("EDITIONS.yaml did not contain a mapping.")
    return loaded


def lrmer_co2e(gea: str, year: int) -> float:
    series = _cambium().get(gea)
    if series is None:
        raise _missing("Cambium", "gea", gea)
    if year < BASE_YEAR:
        raise _missing("Cambium", "year", year)
    if year > _HOLD_CAMBIUM_YEAR:
        year = _HOLD_CAMBIUM_YEAR
    if year in series:
        return series[year]
    lower_years = [published for published in series if published < year]
    upper_years = [published for published in series if published > year]
    if not lower_years or not upper_years:
        raise _missing("Cambium", "year", year)
    lower = max(lower_years)
    upper = min(upper_years)
    weight = (year - lower) / (upper - lower)
    return series[lower] + (series[upper] - series[lower]) * weight


def egrid_rates(subregion: str) -> tuple[float, float]:
    rates = _egrid().get(subregion)
    if rates is None:
        raise _missing("eGRID", "subregion", subregion)
    return rates


def sc_co2_2025_usd_per_kg(year: int) -> float:
    lookup = min(year, _HOLD_SC_YEAR)
    value = _sc_co2().get(lookup)
    if value is None:
        raise _missing("SC-CO2", "year", year)
    return value * cpi_u(2025) / cpi_u(2020) / 1000


def criteria_damage_2025_usd_per_kg(state: str, pollutant: str, year: int) -> float:
    row = _bpt().get(state)
    if row is None:
        raise _missing("BPT", "state", state)
    so2, nox_pm, nox_o3 = row
    if pollutant == "so2":
        raw = so2
    elif pollutant == "nox":
        raw = nox_pm + nox_o3
    else:
        raise _missing("BPT", "pollutant", pollutant)
    per_kg = raw / _KG_PER_SHORT_TON * cpi_u(2025) / cpi_u(2019)
    elapsed = min(year, _HOLD_CRITERIA_YEAR) - BASE_YEAR
    return per_kg * (_CRITERIA_GROWTH ** elapsed)


def cpi_u(year: int) -> float:
    value = _cpi().get(year)
    if value is None:
        raise _missing("CPI-U", "year", year)
    return value


def data_releases() -> dict[str, str]:
    document = _editions()
    return {key: str(document[key]["title"]) for key in _RELEASE_KEYS}
