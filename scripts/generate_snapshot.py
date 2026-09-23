"""Generate a ref_snapshot SQL INSERT from current YAML values.

Usage:
    cd repos/forge
    .venv/bin/python scripts/generate_snapshot.py > /tmp/snapshot_v1.sql

Then paste the output into the Supabase SQL Editor.
"""
import json
import yaml
from pathlib import Path

YAMLS_DIR = Path(__file__).parent.parent / "yamls"
SKIP = {"project_category_template"}

combined = {}
for yf in sorted(YAMLS_DIR.glob("*.yaml")):
    if yf.stem in SKIP:
        continue
    with yf.open() as f:
        combined[yf.stem] = yaml.safe_load(f)

json_str = json.dumps(combined).replace("'", "''")
print(
    f"INSERT INTO ref_snapshot (label, data) VALUES ("
    f"'v1.0 - Paper 1 defaults (June 2026)', "
    f"'{json_str}'::jsonb);"
)
