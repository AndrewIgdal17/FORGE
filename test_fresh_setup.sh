#!/bin/bash
# Test script to simulate fresh clone scenario
# This tests that venv setup works automatically

set -e

echo "=========================================="
echo "Testing Fresh Clone Scenario"
echo "=========================================="
echo ""

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Backup existing venvs if they exist
echo "Step 1: Backing up existing virtual environments..."
if [ -d "venv" ]; then
    echo "  Backing up venv/ to venv.backup/"
    mv venv venv.backup
fi

if [ -d "server/.venv" ]; then
    echo "  Backing up server/.venv/ to server/.venv.backup/"
    mv server/.venv server/.venv.backup
fi

echo "  Backup complete"
echo ""

# Test 1: Run JSON→JSON command
echo "=========================================="
echo "Test 1: CLI Command (run_json_json.command)"
echo "=========================================="
echo "This should auto-create venv/ and install dependencies"
echo ""
./run_json_json.command

if [ $? -eq 0 ]; then
    echo "✓ Test 1 PASSED: CLI command worked with auto venv setup"
else
    echo "✗ Test 1 FAILED: CLI command failed"
    exit 1
fi
echo ""

# Clean up venv for next test
echo "Removing venv/ for next test..."
rm -rf venv
echo ""

# Test 2: Start API server (which should auto-setup both venvs)
echo "=========================================="
echo "Test 2: API Server Auto-Setup"
echo "=========================================="
echo "This should auto-create both server/.venv/ and venv/"
echo ""

# Start server in background
cd server
./run_calc_server.command &
SERVER_PID=$!
cd ..

# Wait for server to start
echo "Waiting for server to start..."
sleep 5

# Test API call
echo "Testing API calculation endpoint..."
curl -X POST http://localhost:8000/api/ctcc/calculate \
  -H "Content-Type: application/json" \
  -d @- << 'EOF' > /tmp/api_test_response.json
{
  "input_mode": "json",
  "output_mode": "json",
  "scenario_id": "test_fresh_setup"
}
EOF

# Check if calculation succeeded
if grep -q '"success": true' /tmp/api_test_response.json; then
    echo "✓ Test 2 PASSED: API calculation worked with auto venv setup"
else
    echo "✗ Test 2 FAILED: API calculation failed"
    cat /tmp/api_test_response.json
    kill $SERVER_PID 2>/dev/null || true
    exit 1
fi

# Stop server
echo "Stopping server..."
kill $SERVER_PID 2>/dev/null || true
sleep 2

echo ""
echo "=========================================="
echo "All Tests Passed!"
echo "=========================================="
echo ""
echo "Cleanup: Restoring original virtual environments..."

# Restore backups
if [ -d "venv.backup" ]; then
    rm -rf venv
    mv venv.backup venv
    echo "  Restored venv/"
fi

if [ -d "server/.venv.backup" ]; then
    rm -rf server/.venv
    mv server/.venv.backup server/.venv
    echo "  Restored server/.venv/"
fi

rm -f /tmp/api_test_response.json

echo ""
echo "✓ Fresh clone scenario test completed successfully!"
echo "  Both CLI commands and API server will auto-setup venvs on fresh clone."
