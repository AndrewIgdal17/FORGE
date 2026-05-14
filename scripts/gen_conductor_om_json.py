"""Generate conductor_om.json from the YAML source for client-side lookup."""

import json
import yaml
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()
YAMLS_DIR = SCRIPT_DIR.parent / "yamls"
OUTPUT_PATH = SCRIPT_DIR.parent / "server" / "static" / "conductor_om.json"


def main():
    src = YAMLS_DIR / "13_category_om_conductors.yaml"
    with open(src) as f:
        data = yaml.safe_load(f)

    categories = data["project_categories_om_conductors"]
    result = {}
    for key, entry in categories.items():
        result[key] = {"variable_cost_per_mile_year": entry["variable_cost_per_mile_year"]}

    with open(OUTPUT_PATH, "w") as f:
        json.dump(result, f, indent=2)

    print(f"Wrote {len(result)} entries to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
