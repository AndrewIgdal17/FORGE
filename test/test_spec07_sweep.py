"""The grid-mix model is gone from the calculator package."""

from pathlib import Path

BANNED = ("grid_mix", "energy_source_mix", "emission_intensities", "societal_costs_per_kg")


def test_grid_mix_strings_are_gone():
    root = Path("forge")
    for path in root.rglob("*"):
        if "data/archive" in path.as_posix() or not path.is_file():
            continue
        text = path.read_text(errors="ignore")
        for token in BANNED:
            assert token not in text, f"{token} in {path}"
