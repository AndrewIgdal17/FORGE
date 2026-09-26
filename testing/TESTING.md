# FORGE Testing Guide

## Quick Start

From the FORGE root directory:

```bash
cd testing
../venv/bin/python3 run_tests.py
```

Or double-click (macOS):
```
testing/run_tests.command
```

## Test Runner Usage

### Basic Commands

All commands should be run from the `testing/` directory:

```bash
cd testing

# Run all tests
../venv/bin/python3 run_tests.py

# Run quick smoke tests (fastest)
../venv/bin/python3 run_tests.py --quick

# Run only P0 (Critical) tests
../venv/bin/python3 run_tests.py --priority P0

# Run P0 and P1 tests
../venv/bin/python3 run_tests.py --priority P1

# Show verbose output
../venv/bin/python3 run_tests.py --verbose

# Save test results to JSON (saves to testing/test_results.json)
../venv/bin/python3 run_tests.py --save-report
```

### Test Priority Levels

- **P0 (Critical)**: Core functionality - CLI modes, API endpoints, calculation modules
- **P1 (High)**: Financial calculations, BCR metrics, error handling
- **P2 (Medium)**: Edge cases, performance, documentation

## Current Test Coverage

### Implemented Tests (`run_tests.py`)

#### P0 Tests (Critical)
- ✅ **1.1.1** - YAML→JSON Mode
- ⏭️ **1.1.2** - JSON→CSV Mode (skipped; calculator is YAML-in, JSON-out)
- ✅ **1.1.3** - YAML→JSON Mode (custom ID)
- ✅ **1.2.6** - Custom Scenario ID (`FORGE_SCENARIO_ID`)
- ✅ **5.1.1** - YAML→JSON Converter
- ✅ **5.2.1** - Round-trip Comparison

#### P1 Tests (High Priority)
- ✅ **6.3.1** - BCR Calculation
- ✅ **7.1.3** - Invalid JSON Handling

#### P2 Tests (Medium Priority)
- ✅ **9.1.1** - CLI Performance

### Pytest suite

From the repo root:

```bash
python -m pytest test/ -v
```

15 tests across `test_capacity_value.py`, `test_build_costs.py`, and `test_bcr_incremental_comparison.py`.

Additional suites:

```bash
python -m pytest scripts/tests/ -v
python -m pytest testing/test_api_validation.py -v
```

`scripts/tests/` holds `test_facilitated_emissions.py` and `validate_tier2_batch1.py`. `testing/test_api_validation.py` checks that invalid `/api/forge/calculate` payloads return 422.

### Test Output

The test runner provides colored output:
- ✅ **Green**: Test passed
- ❌ **Red**: Test failed
- ⚠️ **Yellow**: Test warning
- ⏭️ **Gray**: Test skipped

### Example Output

```
======================================================================
FORGE TEST SUITE
======================================================================

Started: 2025-11-17 08:41:17
Priority: P0
Verbose: False

======================================================================
P0 TESTS - CRITICAL
======================================================================

  [1.1.1] YAML→JSON mode: ✅ PASS (2.50s)
  [1.1.2] JSON→CSV mode: ⏭️ SKIP (0.00s)
    → Calculator is YAML-in, JSON-out; API converts JSON at boundary
  [1.1.3] YAML→JSON mode (custom ID): ✅ PASS (1.56s)
    → Output size: 8.4 KB
  [1.2.6] Custom scenario ID: ✅ PASS (1.78s)
  [5.1.1] YAML→JSON converter: ✅ PASS (0.45s)
  [5.2.1] Round-trip test: ✅ PASS (4.89s)

======================================================================
TEST SUMMARY
======================================================================

Total Tests:    6
Passed:         5
Failed:         0
Warnings:       0
Skipped:        1

Total Time:     15.61s

Success Rate:   100.0%

======================================================================
✅ ALL TESTS PASSED
```

## Test Reports

When using `--save-report`, test results are saved to `test_results.json`:

```json
{
  "timestamp": "2025-11-17T08:41:32.123456",
  "total_tests": 10,
  "passed": 9,
  "failed": 1,
  "warnings": 0,
  "skipped": 0,
  "total_duration": 25.43,
  "results": [
    {
      "test_id": "1.1.1",
      "name": "YAML→JSON mode",
      "status": "pass",
      "duration": 2.50,
      "message": ""
    },
    ...
  ]
}
```

## Adding New Tests

To add a new test to the runner:

1. Create a test method in the `TestRunner` class:

```python
def test_X_Y_Z_my_new_test(self):
    """Test X.Y.Z: Description"""
    test_id = "X.Y.Z"
    start_time = time.time()

    # Run your test
    cmd = [str(self.venv_python), "-m", "forge", "--some-flag"]
    success, stdout, stderr = self.run_command(cmd, timeout=180)

    duration = time.time() - start_time

    # Validate results
    if not success:
        self.add_result(test_id, "Test Name", "fail", duration,
                       f"Error: {stderr[:200]}")
        return False

    # Add more validation...

    self.add_result(test_id, "Test Name", "pass", duration)
    return True
```

2. Add the test to the appropriate suite (P0, P1, P2):

```python
def run_p0_tests(self):
    tests = [
        # ... existing tests
        ("X.Y.Z: My New Test", self.test_X_Y_Z_my_new_test),
    ]

    for name, test_func in tests:
        try:
            test_func()
        except Exception as e:
            self.log(f"{Colors.FAIL}Exception in {name}: {e}{Colors.ENDC}")
```

## Continuous Integration

The test runner returns appropriate exit codes:
- `0` - All tests passed
- `1` - Some tests failed
- `130` - Tests interrupted (Ctrl+C)

This makes it suitable for CI/CD pipelines:

```bash
# In CI pipeline
venv/bin/python3 run_tests.py --priority P0 --save-report
EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
    echo "Tests failed!"
    exit 1
fi
```

## Troubleshooting

### Tests Timeout
Increase timeout in test method:
```python
success, stdout, stderr = self.run_command(cmd, timeout=300)  # 5 minutes
```

### False Failures
Run with verbose mode to see detailed output:
```bash
venv/bin/python3 run_tests.py --verbose
```

### Cleanup Issues
Temporary test files are automatically cleaned up. Manual cleanup:
```bash
rm -f test_combined.json invalid_test.json
rm -f outputs/forge_results_test_*.json
```

### Python Path Issues
Always use the virtual environment Python:
```bash
venv/bin/python3 run_tests.py
```

## Test Plan Reference

See `TEST_PLAN.md` for the complete manual test plan covering all features.

## Future Test Additions

Tests to be implemented:
- Individual calculation module tests (2.1.x)
- Smart loader tests (3.1.x)
- API endpoint tests (4.2.x - requires server)
- Financial calculation validation (6.1.x, 6.2.x)
- Edge case tests (7.2.x)
- Module integration tests (2.2.x)

## Performance Targets

- Quick tests: < 5 seconds
- P0 tests: < 30 seconds
- All tests: < 60 seconds
- Single calculation: < 30 seconds

## Contact

For test failures or questions, refer to:
- `TEST_PLAN.md` - Comprehensive test plan
- `README.md` - User guide
