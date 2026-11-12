import csv
import hashlib
import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "scripts" / "data" / "raw"
EGRID = Path(os.environ.get(
    "FORGE_EGRID_XLSX",
    "/srv/forge/gis-data/egrid/2023-rev2/raw/egrid2023_data_rev2.xlsx",
))
SC_BORROW = "NC (borrowed for SC; EPA 2025 PM workbook has no SC NOx row)"
TITLES = {
    "cambium": "Cambium 2024 Mid-case, annual, GEA (NLR TP-6A40-93005), lrmer_co2e_c + lrmer_co2e_p",
    "egrid": "eGRID2023 rev2 (data year 2023), SRL23 SRSO2RTA/SRNOXRTA",
    "sc_ghg": "EPA 2023 SC-GHG Table A.5.1, SC-CO2, 2.0% near-term, 2020$",
    "bpt": "EPA 2024 BPT, EGU by state, 2025 analysis year, 2%, low mortality (PM) + short-term ozone, 2019$",
    "cpi_u": "BLS CUUR0000SA0 annual average; 2025 = 321.943",
}


def _series_report() -> Path:
    matches = sorted(RAW.glob("SeriesReport-*.xlsx"))
    assert len(matches) == 1, matches
    return matches[0]


def _bpt_index():
    from scripts.build_emissions_data import build_bpt

    rows = build_bpt(
        RAW / "BPT_PM_results_EGU_2025.xlsx",
        RAW / "BPT_O3MDA8_results_EGU_2025.xlsx",
    )
    assert len(rows) == 49
    return {
        state: {
            "so2": so2,
            "nox_pm": nox_pm,
            "nox_o3": nox_o3,
            "so2_source_row": so2_src,
            "nox_pm_source_row": pm_src,
            "nox_o3_source_row": o3_src,
        }
        for state, so2, nox_pm, nox_o3, so2_src, pm_src, o3_src in rows
    }


def test_social_cost_csv_is_the_vault_extract():
    raw = (RAW / "sc_co2_2pct_2020usd.csv").read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    assert digest == "c7f01ff8374c431f580492265018042d0508af41e4f6e62902707a8e31e8af35"


def test_build_sc_anchors():
    from scripts.build_emissions_data import build_sc

    rows = build_sc(RAW / "sc_co2_2pct_2020usd.csv")
    assert len(rows) == 61
    by_year = dict(rows)
    assert list(by_year) == list(range(2020, 2081))
    assert by_year[2020] == 193
    assert by_year[2025] == 212
    assert by_year[2030] == 230
    assert by_year[2050] == 308
    assert by_year[2080] == 407
    assert all(isinstance(year, int) and isinstance(value, int) for year, value in rows)


def test_build_cambium_midcase_gea_names():
    from scripts.build_emissions_data import build_cambium

    rows = build_cambium(RAW / "Cambium24_allScenarios_annual_gea.zip")
    assert len(rows) == 108
    by_key = {(gea, year): value for gea, year, value in rows}
    assert by_key[("CAISO", 2025)] == pytest.approx(310.6)
    assert by_key[("CAISO", 2030)] == pytest.approx(168.8)
    assert all(" " not in gea for gea, _, _ in rows)


def test_build_bpt_state_rows():
    table = _bpt_index()
    assert set(table) == {
        "AL", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", "ID", "IL", "IN", "IA",
        "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV",
        "NH", "NJ", "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC", "SD",
        "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY", "DC",
    }
    assert table["AL"]["so2_source_row"] == "ALMS"
    assert table["AL"]["so2"] == 95800
    assert table["TX"]["so2_source_row"] == "OKTX"
    assert table["TX"]["so2"] == 38800
    assert table["AL"]["nox_pm"] == 2120
    assert table["AL"]["nox_o3"] == 15500
    assert table["TX"]["nox_pm"] == 1520
    assert table["TX"]["nox_o3"] == 13200
    for state in ("DC",):
        assert table[state]["so2_source_row"] == "MDDC"
        assert table[state]["nox_pm_source_row"] == "MDDC"
        assert table[state]["nox_o3_source_row"] == "MDDC"
    for state in ("NY", "VT"):
        assert table[state]["so2_source_row"] == "NYVT"
        assert table[state]["nox_pm_source_row"] == "NYVT"
        assert table[state]["nox_o3_source_row"] == "NYVT"
        assert table[state]["nox_pm"] == 6680
        assert table[state]["nox_o3"] == 19500
    assert table["SC"]["nox_pm"] == 4090
    assert table["SC"]["nox_pm_source_row"] == SC_BORROW
    assert table["SC"]["so2"] == 43700
    assert table["SC"]["nox_o3"] == 12700
    for row in table.values():
        for key in ("so2_source_row", "nox_pm_source_row", "nox_o3_source_row"):
            assert row[key] not in {"TB", "TL"}
    borrowers = [
        state for state, row in table.items() if row["nox_pm_source_row"] == SC_BORROW
    ]
    assert borrowers == ["SC"]


def test_pm_workbook_one_byte_read_does_not_rewrite_the_file():
    from scripts.build_emissions_data import read_pm_workbook

    path = RAW / "BPT_PM_results_EGU_2025.xlsx"
    before = path.read_bytes()
    book, digest = read_pm_workbook(path)
    assert path.read_bytes() == before
    assert digest == hashlib.sha256(before).hexdigest()
    assert "most_sectors_low_2" in book.sheetnames


def test_build_cpi_annual_values():
    from scripts.build_emissions_data import build_cpi

    source = (ROOT / "scripts" / "build_emissions_data.py").read_text()
    assert "218.056" not in source
    rows = build_cpi(_series_report())
    assert [year for year, _ in rows] == [2010, 2019, 2020, 2024, 2025]
    by_year = dict(rows)
    assert by_year[2010] == pytest.approx(218.056)
    assert by_year[2019] == pytest.approx(255.657)
    assert by_year[2020] == pytest.approx(258.811)
    assert by_year[2024] == pytest.approx(313.689)
    assert by_year[2025] == pytest.approx(321.943)


def test_build_cpi_raises_when_2010_is_absent(tmp_path):
    from openpyxl import Workbook

    from scripts.build_emissions_data import build_cpi

    book = Workbook()
    sheet = book.active
    sheet.append(["Year", "Period", "Value"])
    for year, value in ((2019, 255.657), (2020, 258.811), (2024, 313.689), (2025, 321.943)):
        sheet.append([year, "M13", value])
    path = tmp_path / "SeriesReport-missing-2010.xlsx"
    book.save(path)
    with pytest.raises(SystemExit, match="2010"):
        build_cpi(path)


def test_write_release_editions_and_csv_format(tmp_path):
    import yaml

    from scripts.build_emissions_data import build_cambium, write_release

    out = tmp_path / "emissions"
    cpi_out = tmp_path / "cpi_u.csv"
    egrid = EGRID if EGRID.is_file() else None
    write_release(RAW, out, cpi_out, egrid)

    assert not (out / "cpi_u.csv").exists()
    doc = yaml.safe_load((out / "EDITIONS.yaml").read_text())
    assert list(doc) == ["cambium", "egrid", "sc_ghg", "bpt", "cpi_u"]
    for key, title in TITLES.items():
        assert doc[key]["title"] == title
        assert doc[key]["edition"]
        assert isinstance(doc[key]["raw_files"], list)
        assert doc[key]["transform"]
    assert doc["bpt"]["notes"] == SC_BORROW
    sc_files = {item["name"]: item["sha256"] for item in doc["sc_ghg"]["raw_files"]}
    assert sc_files["sc_co2_2pct_2020usd.csv"] == (
        "c7f01ff8374c431f580492265018042d0508af41e4f6e62902707a8e31e8af35"
    )
    pm_path = RAW / "BPT_PM_results_EGU_2025.xlsx"
    bpt_files = {item["name"]: item["sha256"] for item in doc["bpt"]["raw_files"]}
    assert bpt_files["BPT_PM_results_EGU_2025.xlsx"] == hashlib.sha256(pm_path.read_bytes()).hexdigest()
    assert bpt_files["BPT_O3MDA8_results_EGU_2025.xlsx"] == hashlib.sha256(
        (RAW / "BPT_O3MDA8_results_EGU_2025.xlsx").read_bytes()
    ).hexdigest()

    cambium_text = (out / "cambium_lrmer_co2e.csv").read_text()
    assert "\r" not in cambium_text
    cambium_rows = list(csv.DictReader(cambium_text.splitlines()))
    assert list(cambium_rows[0]) == ["gea", "year", "lrmer_co2e_kg_per_mwh"]
    built = {(gea, year): value for gea, year, value in build_cambium(RAW / "Cambium24_allScenarios_annual_gea.zip")}
    caiso = next(row for row in cambium_rows if row["gea"] == "CAISO" and row["year"] == "2025")
    assert caiso["lrmer_co2e_kg_per_mwh"] == repr(built[("CAISO", 2025)])

    sc_text = (out / "sc_co2_2pct.csv").read_text()
    assert "\r" not in sc_text
    sc_rows = list(csv.DictReader(sc_text.splitlines()))
    assert list(sc_rows[0]) == ["year", "sc_co2_2020usd_per_metric_ton"]
    assert sc_rows[0]["year"] == "2020"
    assert sc_rows[0]["sc_co2_2020usd_per_metric_ton"] == "193"
    assert len(sc_rows) == 61

    bpt_text = (out / "bpt_egu_state.csv").read_text()
    assert "\r" not in bpt_text
    bpt_rows = list(csv.DictReader(bpt_text.splitlines()))
    assert list(bpt_rows[0]) == [
        "state",
        "so2_2019usd_per_short_ton",
        "nox_pm_2019usd_per_short_ton",
        "nox_o3_2019usd_per_short_ton",
        "so2_source_row",
        "nox_pm_source_row",
        "nox_o3_source_row",
    ]
    sc_bpt = next(row for row in bpt_rows if row["state"] == "SC")
    assert sc_bpt["nox_pm_2019usd_per_short_ton"] == "4090"
    assert sc_bpt["nox_pm_source_row"] == SC_BORROW
    assert len(bpt_rows) == 49

    cpi_text = cpi_out.read_text()
    assert "\r" not in cpi_text
    cpi_rows = list(csv.DictReader(cpi_text.splitlines()))
    assert list(cpi_rows[0]) == ["year", "cpi_u"]
    assert [row["year"] for row in cpi_rows] == ["2010", "2019", "2020", "2024", "2025"]
    assert cpi_rows[-1]["cpi_u"] == "321.943"

    if egrid is None:
        assert not (out / "egrid_criteria_rates.csv").exists()
    else:
        egrid_text = (out / "egrid_criteria_rates.csv").read_text()
        assert "\r" not in egrid_text
        egrid_rows = list(csv.DictReader(egrid_text.splitlines()))
        assert list(egrid_rows[0]) == ["subregion", "so2_kg_per_mwh", "nox_kg_per_mwh"]
        assert len(egrid_rows) == 22
        recorded = {item["name"]: item["sha256"] for item in doc["egrid"]["raw_files"]}
        assert recorded[egrid.name] == hashlib.sha256(egrid.read_bytes()).hexdigest()


def test_vendored_tables_exist_without_a_second_cpi_path():
    emissions = ROOT / "forge" / "data" / "emissions"
    assert (emissions / "cambium_lrmer_co2e.csv").is_file()
    assert (emissions / "egrid_criteria_rates.csv").is_file()
    assert (emissions / "sc_co2_2pct.csv").is_file()
    assert (emissions / "bpt_egu_state.csv").is_file()
    assert (emissions / "EDITIONS.yaml").is_file()
    assert (ROOT / "forge" / "data" / "cpi_u.csv").is_file()
    assert not (emissions / "cpi_u.csv").exists()
    import yaml

    doc = yaml.safe_load((emissions / "EDITIONS.yaml").read_text())
    for key, title in TITLES.items():
        assert doc[key]["title"] == title
    assert SC_BORROW in doc["bpt"]["notes"]


@pytest.mark.skipif(not EGRID.is_file(), reason="eGRID workbook not on this machine")
def test_egrid_aznm_unrounded():
    from scripts.build_emissions_data import build_egrid

    rows = {sub: (so2, nox) for sub, so2, nox in build_egrid(EGRID)}
    assert len(rows) == 22
    assert rows["AZNM"] == (0.103 * 0.45359237, 0.360 * 0.45359237)
    for dropped in ("AKGD", "AKMS", "HIMS", "HIOA", "PRMS"):
        assert dropped not in rows
