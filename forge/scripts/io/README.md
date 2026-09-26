# forge/scripts/io/

Input/output and taxonomy modules.

- `yaml_loaders.py` — YAML scenario input loaders (dataclasses + parse helpers).
- `json_loaders.py` — JSON-input parallel to `yaml_loaders` (web-app/API path).
- `json_output_manager.py` — Collects per-module results in memory as JSON.
- `csv_output_manager.py` — Holds the field-name schema (`BATCH_SUMMARY_FIELDS`) only; not an active output path.
- `taxonomy.py` — 34-item taxonomy (23 cost/benefit/transfer/reporting items + 11 utility entries), 9 BCR definitions (3 core + 6 exclusion), and excludable groups.
- `taxonomy_adapters.py` — Maps raw module output dicts onto taxonomy items.
- `input_metadata.py` — Per-field form metadata that bridges taxonomy items to web-app controls.
