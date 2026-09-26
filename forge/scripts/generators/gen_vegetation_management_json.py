"""Generate vegetation_management.json from the YAML source for client-side lookup."""

import json
import os
import yaml
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()
YAMLS_DIR = SCRIPT_DIR.parent.parent / "yamls"
OUTPUT_PATH = Path(os.environ.get(
    "FORGE_STATIC_DIR",
    str(SCRIPT_DIR.parent.parent.parent / "server" / "static"),
)) / "vegetation_management.json"


def main():
    src = YAMLS_DIR / "12_project_om_vegetation_management.yaml"
    with open(src) as f:
        data = yaml.safe_load(f)

    categories = data["vegetation_management_om_costs"]
    result = {}
    for key, entry in categories.items():
        result[key] = entry

    with open(OUTPUT_PATH, "w") as f:
        json.dump(result, f, indent=2)

    print(f"Wrote {len(result)} entries to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
