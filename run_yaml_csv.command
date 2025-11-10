#!/bin/bash

# Run CTCC in YAML input → CSV output mode (traditional mode)

cd "$(dirname "$0")"

echo "Starting CTCC: YAML → CSV mode..."
echo ""

# Run ctcc.py (default mode is YAML → CSV, no flags needed)
./venv/bin/python3 ctcc.py

echo ""
echo "CTCC execution complete."
echo "CSV files saved to: outputs/"
