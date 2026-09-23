#!/bin/bash

# Run FORGE in YAML input → CSV output mode (traditional mode)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Determine Python binary
PYTHON_BIN="${PYTHON_BIN:-python3}"
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  if command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
  else
    echo "Python interpreter not found. Install Python 3 or export PYTHON_BIN." >&2
    exit 1
  fi
fi

# Create virtual environment if it doesn't exist
if [[ ! -d "venv" ]]; then
  echo "Creating virtual environment at venv"
  "$PYTHON_BIN" -m venv venv
fi

# Activate virtual environment
# shellcheck disable=SC1091
source "venv/bin/activate"
VENV_PYTHON="$(command -v python)"

if [[ -z "$VENV_PYTHON" ]]; then
  echo "Failed to locate python inside venv" >&2
  exit 1
fi

# Install/update dependencies
if [[ -f "requirements.txt" ]]; then
  echo "Installing/updating dependencies..."
  "$VENV_PYTHON" -m pip install --upgrade pip >/dev/null 2>&1 || true
  "$VENV_PYTHON" -m pip install -r requirements.txt
else
  echo "requirements.txt not found; skipping dependency installation."
fi

echo ""
echo "Starting FORGE: YAML → CSV mode..."
echo ""

# Run forge.py (default mode is YAML → CSV, no flags needed)
"$VENV_PYTHON" forge.py

echo ""
echo "FORGE execution complete."
echo "CSV files saved to: outputs/"
