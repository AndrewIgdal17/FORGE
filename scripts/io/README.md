# scripts/io/

Input/output and taxonomy modules.

YAML and JSON loaders read scenario inputs; the JSON output manager collects per-module results. `csv_output_manager` holds the batch-summary field schema used by forge.py. `taxonomy` and `taxonomy_adapters` map calculator outputs onto the canonical taxonomy used by the web app and BCR layer.
