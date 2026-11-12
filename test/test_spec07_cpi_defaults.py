"""Template dollar defaults come from one CPI table, or from one inflation deflator."""

import csv
import re
from pathlib import Path

import numpy as np
import pytest
import yaml

from forge.data import get_cpi_path, get_defaults_template

ROOT = Path(__file__).resolve().parents[1]
BANNED_FACTORS = (
    "1.4762",
    "1.2438",
    "1.2591",
    "1.0262",
    "0.9728",
    "1.5525",
    "321.900",
    "313.685",
)
FACTOR = re.compile(
    r"(?:(?<![A-Za-z])[x×*/÷]\s*(\d+\.\d+)|(\d+\.\d+)\s*[x×*/÷](?![A-Za-z]))"
)
CONTEXT = re.compile(r"CPI|deflat|20\d\d\$", re.IGNORECASE)
_INDEX = re.compile(r"\[(\d+)\]")

HABITAT = (
    "09_environmental_mitigation.environmental_mitigation"
    ".habitat_credit_cost_per_credit"
)
HABITAT_CLASSES = (
    "forested",
    "scrubbed_flat",
    "desert_barren",
    "rolling_hills",
    "mountain",
)
SURVEY_VALUES = (35685, 21326, 13340, 10435, 13581)
SURVEY_RESULTS = (36624, 21887, 13691, 10710, 13938)
FIT_HOURS = (1, 2, 4, 8, 16)
FIT_AT = (32, 64, 168, 720)
FIT_RESULTS = (20631, 36286, 88522, 367324)
RENTS = (
    (8.08, 7.84, 0.78),
    (15.65, 15.19, 1.52),
    (30.60, 29.71, 2.97),
    (46.12, 44.78, 4.48),
    (63.53, 61.68, 6.17),
    (91.76, 89.09, 8.91),
    (128.31, 124.57, 12.46),
    (177.97, 172.79, 17.28),
    (440.10, 427.28, 42.73),
    (1351.76, 1312.39, 131.24),
    (2703.51, 2624.77, 262.48),
    (6758.78, 6561.92, 656.19),
    (13517.55, 13123.83, 1312.38),
    (20276.33, 19685.76, 1968.58),
    (27035.10, 26247.67, 2624.77),
)
ACQUISITION = (
    299, 579, 1132, 1706, 2350, 3394, 4746, 6583, 16279,
    50000, 100000, 250000, 500000, 750000, 1000000,
)
ROUNDED_FORMULA = "V(t) = 32210/t + 3339 + 492t"


def _lookup(root, path):
    current = root
    for part in path.split("."):
        name, *indexes = _INDEX.split(part)
        indexes = [piece for piece in indexes if piece != ""]
        current = current[name]
        for raw in indexes:
            current = current[int(raw)]
    return current


def _leaves(node):
    if isinstance(node, dict) and "path" in node:
        yield node
        return
    if isinstance(node, dict):
        for child in node.values():
            yield from _leaves(child)


def _registry_leaves():
    document = yaml.safe_load(
        (ROOT / "forge" / "yamls" / "defaults_registry.yaml").read_text()
    )
    return list(_leaves(document))


def _leaf(path):
    matches = [leaf for leaf in _registry_leaves() if leaf.get("path") == path]
    assert len(matches) == 1, path
    return matches[0]


def _cpi():
    path = get_cpi_path()
    assert path.name == "cpi_u.csv"
    assert path.parent.name == "data"
    with path.open(newline="") as handle:
        return {int(row["year"]): float(row["cpi_u"]) for row in csv.DictReader(handle)}


def _round_to(value, step):
    """`round_to` is the unit: 1 is the nearest dollar, 0.01 the nearest cent."""
    if step == 1:
        return round(value)
    decimals = 0
    probe = step
    while probe < 1:
        probe *= 10
        decimals += 1
    return round(value, decimals)


def _voll(index):
    return f"07_outage_costs.outage.value_of_lost_load.tiers[{index}].value_per_mwh"


def _rent(zone):
    return f"11_project_row_details.right_of_way.zone_{zone}.rent_cost"


def _hold(zone):
    return f"11_project_row_details.right_of_way.zone_{zone}.hold_cost"


def _acquisition(zone):
    return f"11_project_row_details.right_of_way.zone_{zone}.acquisition_cost"


def _survey_paths():
    return [_voll(index) for index in range(5)]


def _fitted_results(cpi):
    hours = np.array(FIT_HOURS, dtype=float)
    values = np.array(SURVEY_VALUES, dtype=float)
    design = np.column_stack((1.0 / hours, np.ones_like(hours), hours))
    coeff, *_ = np.linalg.lstsq(design, values, rcond=None)
    ratio = cpi[2025] / cpi[2024]
    converted = []
    for hour in FIT_AT:
        raw = coeff[0] / hour + coeff[1] + coeff[2] * hour
        converted.append(_round_to(raw * ratio, 1))
    return converted


def _entries():
    path = ROOT / "forge" / "data" / "converted_defaults.yaml"
    assert path.is_file(), "forge/data/converted_defaults.yaml is missing"
    document = yaml.safe_load(path.read_text())
    rows = document["entries"]
    paths = [row["path"] for row in rows]
    assert len(paths) == len(set(paths))
    return {row["path"]: row for row in rows}


def _require_source(entry):
    assert isinstance(entry["source"], str) and entry["source"].strip()


def scan_text(text: str) -> list[str]:
    hits = []
    for token in BANNED_FACTORS:
        if token in text:
            hits.append(token)
    for line_no, line in enumerate(text.splitlines(), start=1):
        if CONTEXT.search(line) is None:
            continue
        for match in FACTOR.finditer(line):
            number = float(match.group(1) or match.group(2))
            if 0.9 <= number <= 1.6:
                hits.append(f"line {line_no}: {match.group(0)}")
    return hits


def _scanned_files():
    yamls = sorted((ROOT / "forge" / "yamls").glob("*.yaml"))
    scripts = sorted(path for path in (ROOT / "forge" / "scripts").rglob("*.py"))
    return yamls + scripts


def test_habitat_credits_use_the_2010_cpi_ratio():
    cpi = _cpi()
    template = get_defaults_template()
    expected = _round_to(31683 * cpi[2025] / cpi[2010], 1)
    assert expected == 46778
    for name in HABITAT_CLASSES:
        path = f"{HABITAT}.{name}"
        assert _lookup(template, path) == expected
        entry = _entries()[path]
        assert entry["source_value"] == 31683
        assert entry["source_basis"] == "cpi:2010"
        assert entry["round_to"] == 1
        assert "derived_from" not in entry
        _require_source(entry)
        assert _leaf(path)["dollar_year"] == 2010


def test_survey_voll_uses_the_2024_cpi_ratio():
    cpi = _cpi()
    template = get_defaults_template()
    ratio = cpi[2025] / cpi[2024]
    for index, (source, result) in enumerate(zip(SURVEY_VALUES, SURVEY_RESULTS)):
        path = _voll(index)
        assert _lookup(template, path) == result
        assert _lookup(template, path) == _round_to(source * ratio, 1)
        entry = _entries()[path]
        assert entry["source_value"] == source
        assert entry["source_basis"] == "cpi:2024"
        assert entry["round_to"] == 1
        assert "derived_from" not in entry
        _require_source(entry)
        assert _leaf(path)["dollar_year"] == 2024


def test_long_voll_tiers_follow_the_survey_fit():
    cpi = _cpi()
    template = get_defaults_template()
    fitted = _fitted_results(cpi)
    assert fitted == list(FIT_RESULTS)
    survey_paths = _survey_paths()
    for offset, value in enumerate(fitted):
        path = _voll(offset + 5)
        assert _lookup(template, path) == value
        entry = _entries()[path]
        assert "source_value" not in entry
        assert entry["derived_from"] == survey_paths
        assert entry["source_basis"] == "cpi:2024"
        assert entry["round_to"] == 1
        for key in ("a0", "a1", "a2", "coefficients"):
            assert key not in entry
        _require_source(entry)
        assert _leaf(path)["dollar_year"] == 2024
    assert _lookup(template, _voll(9)) == _lookup(template, _voll(8))
    tier_nine = _entries()[_voll(9)]
    assert tier_nine["derived_from"] == survey_paths
    assert "source_value" not in tier_nine
    registry_text = (ROOT / "forge" / "yamls" / "defaults_registry.yaml").read_text()
    converted_text = (ROOT / "forge" / "data" / "converted_defaults.yaml").read_text()
    assert ROUNDED_FORMULA not in registry_text
    assert "32210" not in registry_text
    assert "32210" not in converted_text


def test_blm_rents_deflate_by_the_template_inflation_rate():
    template = get_defaults_template()
    inflation = _lookup(template, "03_financing.financial.inflation_rate")
    assert inflation == 0.03
    for zone, (source, rent, hold) in enumerate(RENTS, start=1):
        unrounded = source / (1 + inflation)
        assert _lookup(template, _rent(zone)) == pytest.approx(rent)
        assert _lookup(template, _hold(zone)) == pytest.approx(hold)
        assert _lookup(template, _rent(zone)) == pytest.approx(_round_to(unrounded, 0.01))
        assert _lookup(template, _hold(zone)) == pytest.approx(round(0.1 * unrounded, 2))
    entries = _entries()
    for zone, (source, _rent_result, _hold_result) in enumerate(RENTS, start=1):
        rent_entry = entries[_rent(zone)]
        hold_entry = entries[_hold(zone)]
        assert rent_entry["source_value"] == pytest.approx(source)
        assert rent_entry["source_basis"] == "inflation_deflate:2026"
        assert rent_entry["round_to"] == pytest.approx(0.01)
        assert "derived_from" not in rent_entry
        _require_source(rent_entry)
        assert hold_entry["source_basis"] == "inflation_deflate:2026"
        assert hold_entry["round_to"] == pytest.approx(0.01)
        assert hold_entry["derived_from"] == [_rent(zone)]
        assert "source_value" not in hold_entry
        _require_source(hold_entry)
        assert _leaf(_rent(zone)).get("dollar_year") is None
        assert _leaf(_hold(zone)).get("dollar_year") is None


def test_acquisition_costs_stay_out_of_the_conversion_registry():
    template = get_defaults_template()
    entries = _entries()
    for zone, cost in enumerate(ACQUISITION, start=1):
        path = _acquisition(zone)
        assert _lookup(template, path) == cost
        assert path not in entries
        leaf = _leaf(path)
        assert leaf["source"] == "BLM zone value, not converted"
        assert leaf.get("dollar_year") is None


def test_dollar_year_other_than_2025_or_null_is_converted():
    entries = _entries()
    for leaf in _registry_leaves():
        year = leaf.get("dollar_year", None)
        if year not in (2025, None):
            assert leaf["path"] in entries


def test_converted_paths_are_only_the_habitat_voll_and_blm_leaves():
    expected = [f"{HABITAT}.{name}" for name in HABITAT_CLASSES]
    expected += [_voll(index) for index in range(10)]
    for zone in range(1, 16):
        expected.append(_rent(zone))
        expected.append(_hold(zone))
    assert set(_entries()) == set(expected)


def test_blm_comments_name_the_cy2026_source_and_the_deflator():
    text = (ROOT / "forge" / "yamls" / "11_project_row_details.yaml").read_text()
    assert text.count("inflation_deflate:2026") == 31
    assert text.count("CY2026 source value") == 31
    for source, _rent_result, _hold_result in RENTS:
        assert text.count(f"CY2026 source value {source:.2f}") == 2


def test_templates_and_scripts_do_not_embed_cpi_factors():
    offenders = []
    for path in _scanned_files():
        hits = scan_text(path.read_text())
        if hits:
            offenders.append(f"{path.relative_to(ROOT)}: {hits}")
    assert offenders == []


def test_factor_scan_rejects_a_planted_multiplier(tmp_path):
    planted = tmp_path / "plant.yaml"
    planted.write_text("# ×1.4762\n")
    hits = scan_text(planted.read_text())
    assert any("1.4762" in hit for hit in hits)


def test_bare_inflation_rate_is_not_a_cpi_factor():
    assert scan_text("inflation_rate: 0.03\nused = 1.03\n") == []
    assert scan_text("CPI ×0.89\n") == []
    assert scan_text("CPI ×1.61\n") == []
    assert scan_text("CPI ×0.9\n")
    assert scan_text("CPI ×1.6\n")
    assert scan_text("deflated ×1.03 from 2026$\n")


def test_converted_defaults_are_package_data():
    text = (ROOT / "pyproject.toml").read_text()
    assert "data/converted_defaults.yaml" in text
    assert not (ROOT / "forge" / "data" / "emissions" / "converted_defaults.yaml").exists()
    assert not (ROOT / "forge" / "data" / "emissions" / "cpi_u.csv").exists()
