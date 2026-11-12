import csv

import pytest
from forge.emissions_data import (
    BASE_YEAR,
    calendar_year,
    cpi_u,
    criteria_damage_2025_usd_per_kg,
    data_releases,
    egrid_rates,
    lrmer_co2e,
    sc_co2_2025_usd_per_kg,
)
from forge.errors import InvalidInputs


def test_caiso_interpolates_and_holds():
    assert lrmer_co2e("CAISO", 2025) == pytest.approx(310.6)
    assert lrmer_co2e("CAISO", 2030) == pytest.approx(168.8)
    expected_2027 = 310.6 + (168.8 - 310.6) * 2 / 5
    assert lrmer_co2e("CAISO", 2027) == pytest.approx(expected_2027)
    assert lrmer_co2e("CAISO", 2055) == lrmer_co2e("CAISO", 2050)


def test_aznm_is_the_unrounded_product():
    assert egrid_rates("AZNM") == (0.103 * 0.45359237, 0.360 * 0.45359237)


def test_social_cost_2025_uses_the_cpi_table():
    assert sc_co2_2025_usd_per_kg(2025) == pytest.approx(212 * 321.943 / 258.811 / 1000)
    assert sc_co2_2025_usd_per_kg(2090) == sc_co2_2025_usd_per_kg(2080)


def test_criteria_damage_grows_through_2040_then_holds():
    first = criteria_damage_2025_usd_per_kg("AL", "nox", 2025)
    grown = criteria_damage_2025_usd_per_kg("AL", "nox", 2026)
    assert grown == pytest.approx(first * 1.02)
    assert criteria_damage_2025_usd_per_kg("AL", "nox", 2041) == pytest.approx(
        criteria_damage_2025_usd_per_kg("AL", "nox", 2040)
    )


def test_so2_damage_converts_short_tons_with_the_cpi_ratio():
    expected = 95800 / 907.185 * 321.943 / 255.657
    assert criteria_damage_2025_usd_per_kg("AL", "so2", 2025) == pytest.approx(expected)


def test_missing_region_names_the_field():
    with pytest.raises(InvalidInputs, match="No Cambium data for gea 'NOT_A_REGION'."):
        lrmer_co2e("NOT_A_REGION", 2025)


def test_cambium_year_before_2025_names_the_year_after_the_gea_exists():
    with pytest.raises(InvalidInputs, match="No Cambium data for year '2024'."):
        lrmer_co2e("CAISO", 2024)
    with pytest.raises(InvalidInputs, match="No Cambium data for gea 'NOT_A_REGION'."):
        lrmer_co2e("NOT_A_REGION", 2020)


def test_missing_keys_name_the_series():
    with pytest.raises(InvalidInputs, match="No eGRID data for subregion 'NOPE'."):
        egrid_rates("NOPE")
    with pytest.raises(InvalidInputs, match="No BPT data for state 'XX'."):
        criteria_damage_2025_usd_per_kg("XX", "so2", 2025)
    with pytest.raises(InvalidInputs, match="No SC-CO2 data for year '2019'."):
        sc_co2_2025_usd_per_kg(2019)
    with pytest.raises(InvalidInputs, match="No CPI-U data for year '2011'."):
        cpi_u(2011)


def test_cpi_anchors_and_cambium_row_count():
    from forge.data import get_emissions_path

    assert cpi_u(2024) == 313.689
    assert cpi_u(2025) == 321.943
    path = get_emissions_path() / "cambium_lrmer_co2e.csv"
    with path.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 108


def test_calendar_year_is_base_plus_operating_year_minus_one():
    assert BASE_YEAR == 2025
    assert calendar_year(1) == 2025
    assert calendar_year(26) == 2050


def test_data_releases_follow_edition_order():
    releases = data_releases()
    assert list(releases) == ["cambium", "egrid", "sc_ghg", "bpt", "cpi_u"]
    assert releases == {
        "cambium": (
            "Cambium 2024 Mid-case, annual, GEA (NLR TP-6A40-93005), "
            "lrmer_co2e_c + lrmer_co2e_p"
        ),
        "egrid": "eGRID2023 rev2 (data year 2023), SRL23 SRSO2RTA/SRNOXRTA",
        "sc_ghg": "EPA 2023 SC-GHG Table A.5.1, SC-CO2, 2.0% near-term, 2020$",
        "bpt": (
            "EPA 2024 BPT, EGU by state, 2025 analysis year, 2%, low mortality (PM) + "
            "short-term ozone, 2019$"
        ),
        "cpi_u": "BLS CUUR0000SA0 annual average; 2025 = 321.943",
    }
