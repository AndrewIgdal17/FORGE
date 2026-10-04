"""CLI entry-point test.

The bundled defaults have capacity_mw: 0, so `forge` with no arguments
raises InvalidInputs and exits 1.  This proves the CLI entry point, argument
parsing, and error handling work.  Full calculations are covered by
test_golden.py through the Python API.
"""

import subprocess
import sys


def test_cli_exits_1_on_default_inputs():
    """Running `forge` with no args exits 1 because capacity_mw is 0."""
    result = subprocess.run(
        [sys.executable, "-m", "forge"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 1
    assert "Invalid inputs" in result.stdout or "InvalidInputs" in result.stdout
