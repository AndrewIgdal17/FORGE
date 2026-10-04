"""CLI JSON output writes the results dict, including trajectory when present."""
import json
from pathlib import Path

from forge import write_final_json_output


def test_cli_json_output_includes_trajectory(tmp_path):
    results = {
        "scenario_id": "test_traj",
        "costs": {},
        "benefits": {},
        "bcr": {"total_costs_pv": 1.0},
        "trajectory": [{"year": 1, "cumulative_npv": 0.0}],
    }
    output_file = write_final_json_output(results, "test_traj", str(tmp_path))
    data = json.loads(Path(output_file).read_text())
    assert data["trajectory"] == [{"year": 1, "cumulative_npv": 0.0}]


def test_cli_json_writes_valid_file(tmp_path):
    results = {"scenario_id": "plain", "costs": {}, "benefits": {}}
    output_file = write_final_json_output(results, "plain", str(tmp_path))
    data = json.loads(Path(output_file).read_text())
    assert data["scenario_id"] == "plain"
    assert output_file.endswith("forge_results_plain.json")
