"""Generate converter_details.json from the YAML source for client-side lookup."""

import json
import os
import yaml
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()
YAMLS_DIR = SCRIPT_DIR.parent.parent / "yamls"
OUTPUT_PATH = Path(os.environ.get(
    "FORGE_STATIC_DIR",
    str(SCRIPT_DIR.parent.parent.parent / "server" / "static"),
)) / "converter_details.json"


def main():
    src = YAMLS_DIR / "15_category_om_converters.yaml"
    with open(src) as f:
        data = yaml.safe_load(f)

    categories = data["project_categories_om_converters"]
    result = {}
    for key, entry in categories.items():
        result[key] = {"converter_om_cost_per_mile_year": entry["converter_om_cost_per_mile_year"]}

    with open(OUTPUT_PATH, "w") as f:
        json.dump(result, f, indent=2)

    print(f"Wrote {len(result)} entries to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
