"""CLI entry-point test.

The bundled defaults leave the required inputs empty, so `forge` with no
arguments raises InvalidInputs and exits 1.  This proves the CLI entry point,
argument parsing, and error handling work.  Full calculations are covered by
test_golden.py through the Python API.
"""

import subprocess
import sys


def test_cli_exits_1_on_default_inputs():
    """Running `forge` with no args exits 1 because required inputs are empty."""
    result = subprocess.run(
        [sys.executable, "-m", "forge"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 1
    assert "Invalid inputs" in result.stdout or "InvalidInputs" in result.stdout
