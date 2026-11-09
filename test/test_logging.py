"""Calculator must produce no stdout/stderr when no logging is configured."""
import json

import forge


def test_run_calculation_is_silent(capsys):
    """With no logging configured, run_calculation produces no output.

    The defaults template leaves required inputs empty, so bootstrap raises
    before any module runs. A bundled case study is the smallest input that
    completes the pipeline and would emit the module print calls.
    """
    forge_file = forge.get_scenarios_path() / "SunZia_Delay2.forge"
    with open(forge_file) as f:
        document = json.load(f)
    changes = forge.diff_changes(document["inputs"])
    changes.update({
        "02_project_physical_details.terrain.protected_area_acres.forested": 0.0,
        "02_project_physical_details.terrain.protected_area_acres.scrubbed_flat": 0.0,
        "02_project_physical_details.terrain.protected_area_acres.desert_barren": 0.0,
        "02_project_physical_details.terrain.protected_area_acres.rolling_hills": 0.0,
        "02_project_physical_details.terrain.protected_area_acres.mountain": 0.0,
    })
    inputs = forge.resolve_inputs(changes)
    forge.run_calculation(inputs, scenario_id="silent_test")
    captured = capsys.readouterr()
    assert captured.out == "", f"Unexpected stdout: {captured.out[:200]}"
    assert captured.err == "", f"Unexpected stderr: {captured.err[:200]}"
