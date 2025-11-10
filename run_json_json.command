#!/bin/bash

# Run CTCC in JSON input → JSON output mode (full JSON mode)

cd "$(dirname "$0")"

echo "Starting CTCC: JSON → JSON mode..."
echo ""

# Run ctcc.py with JSON input and JSON output flags
./venv/bin/python3 ctcc.py -j -o

echo ""
echo "CTCC execution complete."
echo "Input: combined_data.json (auto-generated from YAML)"
echo "Output: outputs/ctcc_results_[scenario_id].json"
