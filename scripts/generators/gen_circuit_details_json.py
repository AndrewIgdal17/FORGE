"""Generate circuit_details.json from the YAML source for client-side lookup."""

import json
import yaml
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()
YAMLS_DIR = SCRIPT_DIR.parent.parent / "yamls"
OUTPUT_PATH = SCRIPT_DIR.parent.parent / "server" / "static" / "circuit_details.json"

FIELDS = [
    "conductor_specification",
    "voltage_kv",
    "conductors_per_phase",
    "number_of_phases",
    "number_of_circuits_poles",
    "AC_75_resistance",
    "DC_20_resistance",
]


def main():
    src = YAMLS_DIR / "21_project_category_circuit_and_resistance_detail.yaml"
    with open(src) as f:
        data = yaml.safe_load(f)

    categories = data["project_categories_circuit_and_resistance_details"]
    result = {}
    for key, entry in categories.items():
        result[key] = {field: entry[field] for field in FIELDS}

    with open(OUTPUT_PATH, "w") as f:
        json.dump(result, f, indent=2)

    print(f"Wrote {len(result)} entries to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
