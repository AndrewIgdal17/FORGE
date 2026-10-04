"""Calculator must produce no stdout/stderr when no logging is configured."""
import json

import forge


def test_run_calculation_is_silent(capsys):
    """With no logging configured, run_calculation produces no output.

    The defaults template has capacity_mw 0, so bootstrap raises before any
    module runs. A bundled case study is the smallest input that completes
    the pipeline and would emit the module print calls.
    """
    forge_file = forge.get_scenarios_path() / "SunZia_Delay2.forge"
    with open(forge_file) as f:
        document = json.load(f)
    inputs = forge.resolve_inputs(forge.diff_changes(document["inputs"]))
    forge.run_calculation(inputs, scenario_id="silent_test")
    captured = capsys.readouterr()
    assert captured.out == "", f"Unexpected stdout: {captured.out[:200]}"
    assert captured.err == "", f"Unexpected stderr: {captured.err[:200]}"
