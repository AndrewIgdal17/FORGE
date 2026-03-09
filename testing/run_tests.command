#!/bin/bash
# Convenience launcher for CTCC test suite
# Double-click this file on macOS to run tests

# Change to testing directory
cd "$(dirname "$0")"

echo "=================================="
echo "CTCC Test Suite"
echo "=================================="
echo ""

# Run tests with all priority levels
../venv/bin/python3 run_tests.py --priority all --save-report

echo ""
echo "Press Enter to close..."
read
