# CTCC Testing Suite

Automated test suite for the Comprehensive Transmission Cost Calculator (CTCC).

## Quick Start

```bash
cd testing
../venv/bin/python3 run_tests.py --quick
```

## Files

- **`run_tests.py`** - Main test runner (executable script)
- **`run_tests.command`** - macOS launcher (double-clickable)
- **`TEST_PLAN.md`** - Complete manual test plan
- **`TESTING.md`** - Detailed testing guide

## Common Commands

```bash
# Quick smoke tests (2 tests, ~5 seconds)
../venv/bin/python3 run_tests.py --quick

# Critical tests only (P0 - 7 tests)
../venv/bin/python3 run_tests.py --priority P0

# All tests with report
../venv/bin/python3 run_tests.py --save-report

# Verbose output
../venv/bin/python3 run_tests.py --verbose
```

## Test Categories

### P0 (Critical) - 7 tests
- CLI mode combinations (YAML→CSV, JSON→CSV, JSON→JSON)
- Command-line flags (--norisk, custom scenario ID)
- YAML↔JSON conversion
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
- **../CLAUDE.md** - Developer documentation
- **../README.md** - User guide

## Requirements

- Python 3.8+
- Virtual environment with dependencies installed
- CTCC project properly set up

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
