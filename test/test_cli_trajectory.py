"""CLI JSON output must include BCR trajectory (parity with the API path)."""
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from forge import write_final_json_output


def _aggregator_with_bcr():
    aggregator = MagicMock()
    aggregator.get_json_results.return_value = {
        "scenario_id": "test_traj",
        "costs": {},
        "benefits": {},
        "bcr": {"total_costs_pv": 1.0, "total_benefits_pv": 2.0},
    }
    return aggregator


def test_cli_json_output_includes_trajectory(tmp_path):
    sentinel = [{"year": 1, "cumulative_npv": 0.0}]
    aggregator = _aggregator_with_bcr()

    with patch(
        "scripts.calc.bcr_trajectory.compute_trajectory",
        return_value=sentinel,
    ) as mock_traj:
        output_file = write_final_json_output(
            aggregator,
            bcr_results={"total_costs_pv": 1.0, "total_benefits_pv": 2.0},
            scenario_id="test_traj",
            output_dir=str(tmp_path),
        )

    data = json.loads(Path(output_file).read_text())
    assert "trajectory" in data
    assert data["trajectory"] == sentinel
    mock_traj.assert_called_once()
    results_arg, combined_data = mock_traj.call_args.args
    assert isinstance(combined_data, dict)
    assert combined_data, "combined_data must be built from YAML files on disk"


def test_cli_json_omits_trajectory_when_no_bcr(tmp_path):
    aggregator = MagicMock()
    aggregator.get_json_results.return_value = {
        "scenario_id": "test_no_bcr",
        "costs": {},
        "benefits": {},
        "bcr": {},
    }

    with patch("scripts.calc.bcr_trajectory.compute_trajectory") as mock_traj:
        output_file = write_final_json_output(
            aggregator,
            bcr_results=None,
            scenario_id="test_no_bcr",
            output_dir=str(tmp_path),
        )

    data = json.loads(Path(output_file).read_text())
    assert "trajectory" not in data
    mock_traj.assert_not_called()


def test_cli_json_survives_trajectory_failure(tmp_path):
    aggregator = _aggregator_with_bcr()

    with patch(
        "scripts.calc.bcr_trajectory.compute_trajectory",
        side_effect=RuntimeError("trajectory boom"),
    ):
        output_file = write_final_json_output(
            aggregator,
            bcr_results={"total_costs_pv": 1.0},
            scenario_id="test_traj_fail",
            output_dir=str(tmp_path),
            simple=True,
        )

    data = json.loads(Path(output_file).read_text())
    assert "trajectory" not in data
    assert data["scenario_id"] == "test_traj"


def test_cli_builds_combined_data_from_yamls_dir(tmp_path):
    yaml_dir = tmp_path / "yamls"
    yaml_dir.mkdir()
    (yaml_dir / "01_project_technical_details.yaml").write_text("timeline: {}\n")
    (yaml_dir / "03_financing.yaml").write_text("financial: {wacc: 0.07}\n")

    aggregator = _aggregator_with_bcr()
    captured = {}

    def fake_compute(results, combined_data):
        captured["combined"] = combined_data
        return [{"year": 1}]

    with patch("scripts.utils.path_config.YAMLS_DIR", yaml_dir), patch(
        "scripts.calc.bcr_trajectory.compute_trajectory",
        side_effect=fake_compute,
    ):
        output_file = write_final_json_output(
            aggregator,
            bcr_results={"total_costs_pv": 1.0},
            scenario_id="test_yaml_load",
            output_dir=str(tmp_path / "out"),
        )

    combined = captured["combined"]
    assert combined["01_project_technical_details"] == {"timeline": {}}
    assert combined["03_financing"] == {"financial": {"wacc": 0.07}}
    data = json.loads(Path(output_file).read_text())
    assert data["trajectory"] == [{"year": 1}]
