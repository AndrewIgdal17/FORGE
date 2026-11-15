"""Spec 11: costs the method switches off do not apply; one state per result."""
import json
import pathlib

import pytest

from test.spec05_project import item, measured, project_changes, run
from test.spec11_scenarios import SCENARIOS, numbers, scenario_changes

STATES = {"measured", "not_available", "does_not_apply"}
PROJECT = "01_project_technical_details.project."
_ROUTELESS = measured(
    congestion_spread_per_mwh=None,
    hours_receiving_more_congested=None,
    hours_sending_more_congested=None,
    receiving_energy_value_per_mwh=None,
)


def _consistent(entry: dict) -> None:
    assert entry["state"] in STATES
    assert (entry["state"] == "not_available") == (entry["available"] is False)
    assert (entry["state"] == "does_not_apply") == (entry["applies"] is False)


# --- Task 1: state -----------------------------------------------------------


def test_every_result_has_one_consistent_state():
    for changes in (project_changes(), project_changes(**_ROUTELESS)):
        r = run(changes)
        for entry in r["taxonomy_results"]:
            _consistent(entry)
        for entry in r["availability"].values():
            _consistent(entry)


def test_state_values_for_known_items():
    routeless = run(project_changes(**_ROUTELESS))
    assert item(routeless, "congestion_benefit")["state"] == "not_available"
    sunzia = run()
    assert item(sunzia, "delivered_energy_benefit")["state"] == "does_not_apply"
    assert item(sunzia, "build_conductor")["state"] == "measured"
