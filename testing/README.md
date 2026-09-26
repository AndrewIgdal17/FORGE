# FORGE Testing Suite

Automated test suite for the Framework for Open Reproducible Grid Economics (FORGE).

## Quick Start

```bash
cd testing
../venv/bin/python3 run_tests.py --quick
```

## Files

- **`run_tests.py`** - Main test runner (executable script)
- **`run_tests.command`** - macOS launcher (double-clickable)
- **`test_api_validation.py`** - FastAPI payload validation (422 on invalid modes)
- **`TEST_PLAN.md`** - Complete manual test plan
- **`TESTING.md`** - Detailed testing guide

## Common Commands

```bash
# Quick smoke tests (2 tests, ~5 seconds)
../venv/bin/python3 run_tests.py --quick

# Critical tests only (P0 - 6 tests)
../venv/bin/python3 run_tests.py --priority P0

# All tests with report
../venv/bin/python3 run_tests.py --save-report

# Verbose output
../venv/bin/python3 run_tests.py --verbose
```

## Other test suites

```bash
# pytest (from repo root): 15 tests in test/
# test_capacity_value, test_build_costs, test_bcr_incremental_comparison
python -m pytest test/ -v

# Script-level checks
python -m pytest forge/scripts/tests/ -v   # test_facilitated_emissions, validate_tier2_batch1

# API payload validation
python -m pytest testing/test_api_validation.py -v
```

## Test Categories

### P0 (Critical) - 6 tests
- CLI YAML→JSON calculation
- Custom scenario ID (`FORGE_SCENARIO_ID`)
- YAML→JSON conversion
- Round-trip data integrity

### P1 (High) - 2 tests
- BCR calculation validation
- Error handling

### P2 (Medium) - 1 test
- Performance benchmarks

## Output

Tests produce color-coded output:
- ✅ **Green** - Pass
- ❌ **Red** - Fail
- ⚠️ **Yellow** - Warning
- ⏭️ **Gray** - Skip

## Test Reports

Use `--save-report` to generate `test_results.json` with:
- Timestamp
- Pass/fail counts
- Execution times
- Detailed results per test

## Documentation

- **TESTING.md** - Complete testing guide with examples
- **TEST_PLAN.md** - Full manual test plan (all test categories)
- **../README.md** - User guide

## Requirements

- Python 3.8+
- Virtual environment with dependencies installed
- FORGE project properly set up

## Exit Codes

- `0` - All tests passed
- `1` - Some tests failed
- `130` - Tests interrupted (Ctrl+C)

## CI/CD Integration

The test runner is designed for automated testing:

```bash
cd testing
../venv/bin/python3 run_tests.py --priority P0 --save-report
EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
    echo "Tests failed!"
    cat test_results.json
    exit 1
fi
```

## Support

For issues or questions:
1. Check TESTING.md for detailed usage
2. Review TEST_PLAN.md for test descriptions
3. Run with `--verbose` for debugging
4. Check test_results.json for failure details
