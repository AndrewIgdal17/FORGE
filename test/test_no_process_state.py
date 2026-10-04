"""After a call, no process-wide state has changed."""
import json
import os
import subprocess
import sys

import forge


def _runnable_inputs() -> dict:
    """Return a complete case-study input dict.

    ``get_defaults_template()`` has ``capacity_mw`` of 0 and is not a runnable
    project, so these checks use a bundled scenario the same way the golden
    tests do.
    """
    forge_file = forge.get_scenarios_path() / "TBC_Delay4.forge"
    with open(forge_file) as handle:
        document = json.load(handle)
    return forge.resolve_inputs(forge.diff_changes(document["inputs"]))


def test_no_env_leak():
    env_before = dict(os.environ)
    forge.run_calculation(_runnable_inputs(), scenario_id="leak_test")
    env_after = dict(os.environ)
    assert env_before == env_after


def test_stdout_stderr_unchanged():
    out_before = sys.stdout
    err_before = sys.stderr
    forge.run_calculation(_runnable_inputs(), scenario_id="stream_test")
    assert sys.stdout is out_before
    assert sys.stderr is err_before


def test_caller_dict_unchanged():
    inputs = _runnable_inputs()
    original = forge.canonical_dumps(inputs)
    forge.run_calculation(inputs, scenario_id="immutable_test")
    assert forge.canonical_dumps(inputs) == original


def test_no_banned_patterns_in_calc_code():
    """No file under forge/scripts/calc, io, or utils mentions os.environ, YAMLS_DIR, or bare print(."""
    from pathlib import Path

    scripts_dir = Path(forge.__file__).parent / "scripts"
    banned = ["os.environ", "YAMLS_DIR", "print("]
    violations = []
    for pattern in banned:
        result = subprocess.run(
            [
                "grep", "-rnI", "--exclude-dir=__pycache__",
                pattern,
                str(scripts_dir / "calc"),
                str(scripts_dir / "io"),
                str(scripts_dir / "utils"),
            ],
            capture_output=True, text=True,
        )
        if result.stdout.strip():
            violations.append(f"Pattern '{pattern}' found:\n{result.stdout[:500]}")
    assert not violations, "\n".join(violations)
