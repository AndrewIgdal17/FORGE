#!/bin/bash

# Run CTCC in JSON input → CSV output mode

cd "$(dirname "$0")"

echo "Starting CTCC: JSON → CSV mode..."
echo ""

# Run ctcc.py with JSON input flag
./venv/bin/python3 ctcc.py -j

echo ""
echo "CTCC execution complete."
echo "Input: combined_data.json (auto-generated from YAML)"
echo "CSV files saved to: outputs/"
