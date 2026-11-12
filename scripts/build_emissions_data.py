"""Build forge/data/emissions from the raw files. Not imported by the calculator."""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import warnings
import zipfile
from pathlib import Path

import pandas as pd
import yaml
from openpyxl import load_workbook

KG_PER_LB = 0.45359237
DROP_EGRID = {"AKGD", "AKMS", "HIMS", "HIOA", "PRMS"}
STATES = (
    "AL", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", "ID", "IL", "IN", "IA",
    "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV",
    "NH", "NJ", "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC", "SD",
    "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY", "DC",
)
PAIRS = {
    "AL": "ALMS", "MS": "ALMS", "AZ": "AZNM", "NM": "AZNM", "CT": "CTRI", "RI": "CTRI",
    "ID": "IDMT", "MT": "IDMT", "NV": "NVUT", "UT": "NVUT", "NY": "NYVT", "VT": "NYVT",
    "OK": "OKTX", "TX": "OKTX", "OR": "ORWA", "WA": "ORWA", "MD": "MDDC", "DC": "MDDC",
}
SC_BORROW = "NC (borrowed for SC; EPA 2025 PM workbook has no SC NOx row)"
TITLES = {
    "cambium": "Cambium 2024 Mid-case, annual, GEA (NLR TP-6A40-93005), lrmer_co2e_c + lrmer_co2e_p",
    "egrid": "eGRID2023 rev2 (data year 2023), SRL23 SRSO2RTA/SRNOXRTA",
    "sc_ghg": "EPA 2023 SC-GHG Table A.5.1, SC-CO2, 2.0% near-term, 2020$",
    "bpt": "EPA 2024 BPT, EGU by state, 2025 analysis year, 2%, low mortality (PM) + short-term ozone, 2019$",
    "cpi_u": "BLS CUUR0000SA0 annual average; 2025 = 321.943",
}
CPI_YEARS = (2010, 2019, 2020, 2024, 2025)
_NO_DEFAULT_STYLE = "Workbook contains no default style, apply openpyxl's default"


def _read_excel(*args, **kwargs):
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message=_NO_DEFAULT_STYLE, category=UserWarning)
        return pd.read_excel(*args, **kwargs)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_pm_workbook(path: Path):
    raw = path.read_bytes()
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message=_NO_DEFAULT_STYLE, category=UserWarning)
        book = load_workbook(io.BytesIO(raw + b"\x00"), data_only=True)
    return book, hashlib.sha256(raw).hexdigest()


def _csv_cell(value: object) -> object:
    if isinstance(value, float):
        if value.is_integer():
            return int(value)
        return repr(value)
    return value


def _write_csv(path: Path, header: list[str], rows: list[tuple]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(header)
        for row in rows:
            writer.writerow([_csv_cell(value) for value in row])


def build_cambium(zip_path: Path) -> list[tuple[str, int, float]]:
    with zipfile.ZipFile(zip_path) as archive:
        names = [name for name in archive.namelist() if name.endswith(".csv")]
        if len(names) != 1:
            raise SystemExit(f"Cambium zip members {names!r}; expected one CSV")
        frame = pd.read_csv(archive.open(names[0]), skiprows=5)
    needed = {"scenario", "gea", "lrmer_co2e_c", "lrmer_co2e_p"}
    if not needed <= set(frame.columns):
        raise SystemExit(f"Cambium columns {list(frame.columns)}")
    year_col = "t" if "t" in frame.columns else "year"
    if year_col not in frame.columns:
        raise SystemExit(f"Cambium has no year column in {list(frame.columns)}")
    mid = frame[frame["scenario"] == "MidCase"]
    rows = []
    for record in mid.itertuples(index=False):
        gea = str(getattr(record, "gea"))
        if " " in gea:
            raise SystemExit(f"Cambium gea {gea!r} contains a space; spec stores transgrp names")
        value = float(getattr(record, "lrmer_co2e_c")) + float(getattr(record, "lrmer_co2e_p"))
        rows.append((gea, int(getattr(record, year_col)), value))
    rows.sort()
    if len(rows) != 108:
        raise SystemExit(f"Cambium MidCase rows: {len(rows)}")
    return rows


def build_egrid(xlsx: Path) -> list[tuple[str, float, float]]:
    frame = _read_excel(xlsx, sheet_name="SRL23", header=1)
    rows = []
    for record in frame.itertuples(index=False):
        code = str(getattr(record, "SUBRGN"))
        if code in DROP_EGRID or code in {"nan", "None"}:
            continue
        rows.append((
            code,
            float(getattr(record, "SRSO2RTA")) * KG_PER_LB,
            float(getattr(record, "SRNOXRTA")) * KG_PER_LB,
        ))
    rows = [row for row in rows if row[0] not in DROP_EGRID]
    rows.sort()
    if len(rows) != 22:
        raise SystemExit(f"eGRID lower-48 rows: {len(rows)}")
    return rows


def build_sc(csv_path: Path) -> list[tuple[int, int]]:
    frame = pd.read_csv(csv_path)
    rows = [(int(year), int(value)) for year, value in frame.itertuples(index=False)]
    if [year for year, _ in rows] != list(range(2020, 2081)):
        raise SystemExit("SC-CO2 years are not 2020–2080")
    return rows


def _numeric_cell(table: dict[str, dict], sector: str, column: str):
    row = table.get(sector)
    if row is None:
        return None
    value = row.get(column)
    if value is None or value == "":
        return None
    return float(value)


def _pick(by_sector_pollutant: dict, state: str, pollutant: str):
    """Own USPS row first, then the paired sectorname. SC NOx is the one borrow."""
    own = by_sector_pollutant.get((state, pollutant))
    if own is not None:
        return state, own
    pair = PAIRS.get(state)
    paired = by_sector_pollutant.get((pair, pollutant)) if pair else None
    if paired is not None:
        return pair, paired
    if state == "SC" and pollutant == "nox_pm":
        borrowed = by_sector_pollutant.get(("NC", "nox_pm"))
        if borrowed is None:
            raise SystemExit("NC fine-particle NOx missing; cannot borrow for SC")
        return SC_BORROW, borrowed
    raise SystemExit(f"no {pollutant} row for {state}")


def _index_pollutant_rows(
    frame: pd.DataFrame, value_column: str, pollutant: str
) -> dict[tuple[str, str], float]:
    """One numeric cell per sector for this pollutant. Stop if a sector has two."""
    if "sectorname" not in frame.columns or value_column not in frame.columns:
        raise SystemExit(f"columns {list(frame.columns)}")
    label_col = next(
        (name for name in frame.columns if str(name).lower() in {"pollutant", "pollutantname"}),
        None,
    )
    found: dict[tuple[str, str], float] = {}
    for record in frame.to_dict(orient="records"):
        sector = record.get("sectorname")
        if not isinstance(sector, str) or sector in {"TB", "TL"}:
            continue
        if label_col is not None:
            label = str(record.get(label_col)).upper()
            if value_column == "SO2" and "SO2" not in label:
                continue
            if value_column == "NOx" and "NOX" not in label and "NOₓ" not in label:
                continue
        cell = record.get(value_column)
        if cell is None or cell == "" or (isinstance(cell, float) and pd.isna(cell)):
            continue
        key = (sector, pollutant)
        if key in found:
            raise SystemExit(f"two {pollutant} rows for {sector}")
        found[key] = float(cell)
    return found


def build_bpt(pm_path: Path, o3_path: Path) -> list[tuple]:
    raw = pm_path.read_bytes()
    pm = _read_excel(io.BytesIO(raw + b"\x00"), sheet_name="most_sectors_low_2")
    ozone = _read_excel(o3_path, sheet_name="most_sectors_short_2")
    so2_rows = _index_pollutant_rows(pm, "SO2", "so2")
    nox_pm_rows = _index_pollutant_rows(pm, "NOx", "nox_pm")
    nox_o3_rows = _index_pollutant_rows(ozone, "NOx", "nox_o3")
    out = []
    for state in STATES:
        so2_src, so2 = _pick(so2_rows, state, "so2")
        pm_src, nox_pm = _pick(nox_pm_rows, state, "nox_pm")
        o3_src, nox_o3 = _pick(nox_o3_rows, state, "nox_o3")
        out.append((state, so2, nox_pm, nox_o3, so2_src, pm_src, o3_src))
    return out


def _cpi_sheet(xlsx: Path) -> pd.DataFrame:
    """Find the Year row. A BLS SeriesReport puts it under a title block, not on row 1."""
    preview = _read_excel(xlsx, header=None)
    header_row = None
    for index, row in preview.iterrows():
        labels = set()
        for cell in row.tolist():
            if cell is None or (isinstance(cell, float) and pd.isna(cell)):
                continue
            labels.add(str(cell).strip().lower())
        if "year" in labels and ({"value", "annual", "cpi"} & labels):
            header_row = int(index)
            break
    if header_row is None:
        return _read_excel(xlsx)
    return _read_excel(xlsx, header=header_row)


def build_cpi(xlsx: Path) -> list[tuple[int, float]]:
    frame = _cpi_sheet(xlsx)
    columns = {str(name).lower(): name for name in frame.columns}
    if "year" not in columns or not ({"value", "annual", "cpi"} & set(columns)):
        raise SystemExit(f"CPI columns {list(frame.columns)}; expected year, period, value")
    year_col = columns["year"]
    period_col = columns.get("period")
    value_col = next(columns[name] for name in ("value", "annual", "cpi") if name in columns)
    rows = []
    for record in frame.to_dict(orient="records"):
        if period_col is not None and str(record.get(period_col)) not in {"M13", "13"}:
            continue
        year_cell = record[year_col]
        if year_cell is None or (isinstance(year_cell, float) and pd.isna(year_cell)):
            continue
        year = int(year_cell)
        rows.append((year, float(record[value_col])))
    found = {year: value for year, value in rows}
    missing = [year for year in CPI_YEARS if year not in found]
    if missing:
        raise SystemExit(
            "CPI SeriesReport has no M13 value for "
            + ", ".join(str(year) for year in missing)
            + "; add it from BLS CUUR0000SA0 and record the source in EDITIONS.yaml"
        )
    return [(year, found[year]) for year in CPI_YEARS]


def _edition(
    title: str,
    edition: str,
    raw_files: list[tuple[str, str]],
    transform: str,
    notes: str | None = None,
) -> dict:
    entry = {
        "title": title,
        "edition": edition,
        "raw_files": [{"name": name, "sha256": digest} for name, digest in raw_files],
        "transform": transform,
    }
    if notes is not None:
        entry["notes"] = notes
    return entry


def _one_series_report(raw_dir: Path) -> Path:
    matches = sorted(raw_dir.glob("SeriesReport-*.xlsx"))
    if len(matches) != 1:
        raise SystemExit(f"expected one SeriesReport xlsx in {raw_dir}, found {[path.name for path in matches]}")
    return matches[0]


def write_release(raw_dir: Path, out_dir: Path, cpi_out: Path, egrid_xlsx: Path | None) -> None:
    raw_dir = Path(raw_dir)
    out_dir = Path(out_dir)
    cpi_out = Path(cpi_out)
    cambium_zip = raw_dir / "Cambium24_allScenarios_annual_gea.zip"
    pm_path = raw_dir / "BPT_PM_results_EGU_2025.xlsx"
    o3_path = raw_dir / "BPT_O3MDA8_results_EGU_2025.xlsx"
    sc_path = raw_dir / "sc_co2_2pct_2020usd.csv"
    cpi_path = _one_series_report(raw_dir)

    _write_csv(
        out_dir / "cambium_lrmer_co2e.csv",
        ["gea", "year", "lrmer_co2e_kg_per_mwh"],
        build_cambium(cambium_zip),
    )
    _write_csv(
        out_dir / "sc_co2_2pct.csv",
        ["year", "sc_co2_2020usd_per_metric_ton"],
        build_sc(sc_path),
    )
    _write_csv(
        out_dir / "bpt_egu_state.csv",
        [
            "state",
            "so2_2019usd_per_short_ton",
            "nox_pm_2019usd_per_short_ton",
            "nox_o3_2019usd_per_short_ton",
            "so2_source_row",
            "nox_pm_source_row",
            "nox_o3_source_row",
        ],
        build_bpt(pm_path, o3_path),
    )
    _write_csv(cpi_out, ["year", "cpi_u"], build_cpi(cpi_path))

    egrid_files: list[tuple[str, str]] = []
    if egrid_xlsx is not None:
        egrid_path = Path(egrid_xlsx)
        _write_csv(
            out_dir / "egrid_criteria_rates.csv",
            ["subregion", "so2_kg_per_mwh", "nox_kg_per_mwh"],
            build_egrid(egrid_path),
        )
        egrid_files = [(egrid_path.name, sha256_file(egrid_path))]

    document = {
        "cambium": _edition(
            TITLES["cambium"],
            "Cambium 2024 Mid-case, annual, GEA (file id 69141; NLR TP-6A40-93005)",
            [(cambium_zip.name, sha256_file(cambium_zip))],
            "CSV member, skip 5 preamble lines. scenario == MidCase. "
            "lrmer_co2e_kg_per_mwh = lrmer_co2e_c + lrmer_co2e_p. Year column t.",
        ),
        "egrid": _edition(
            TITLES["egrid"],
            "eGRID2023 revision 2, released 12 June 2025, data year 2023",
            egrid_files,
            "Sheet SRL23, header row 2. SRSO2RTA and SRNOXRTA in lb/MWh, each times 0.45359237. "
            "Drop AKGD, AKMS, HIMS, HIOA, and PRMS. The workbook is not committed.",
        ),
        "sc_ghg": _edition(
            TITLES["sc_ghg"],
            "EPA 2023 SC-GHG Table A.5.1, SC-CO2, 2.0 percent near-term, 2020 dollars, extracted 2026-11-11",
            [(sc_path.name, sha256_file(sc_path))],
            "Rename emission_year to year. Integer 2020 dollars per metric ton for 2020 through 2080.",
        ),
        "bpt": _edition(
            TITLES["bpt"],
            "EPA 2024 BPT TSD, EGU state workbooks, 2025 analysis year, 2 percent",
            [
                (pm_path.name, sha256_file(pm_path)),
                (o3_path.name, sha256_file(o3_path)),
            ],
            "PM sheet most_sectors_low_2, opened from the unmodified bytes plus one trailing NUL in memory. "
            "Ozone sheet most_sectors_short_2. One numeric cell per pollutant. "
            "Own USPS sectorname, else the paired sectorname. "
            "South Carolina fine-particle NOx borrows North Carolina.",
            notes=SC_BORROW,
        ),
        "cpi_u": _edition(
            TITLES["cpi_u"],
            "BLS CUUR0000SA0 annual average, SeriesReport generated 2026-11-09",
            [(cpi_path.name, sha256_file(cpi_path))],
            "Header row containing Year and Annual. Annual column (BLS period M13), "
            "years 2010, 2019, 2020, 2024, and 2025. Written only to forge/data/cpi_u.csv.",
        ),
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "EDITIONS.yaml").write_text(
        yaml.safe_dump(document, sort_keys=False),
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Write the vendored emissions tables.")
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--cpi-out", type=Path, required=True)
    parser.add_argument("--egrid-xlsx", type=Path, default=None)
    args = parser.parse_args(argv)
    write_release(args.raw_dir, args.out_dir, args.cpi_out, args.egrid_xlsx)


if __name__ == "__main__":
    main()
