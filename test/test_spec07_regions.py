"""Terminal region dropdowns. Optional until a later task requires them."""
import csv

import yaml

from forge.contract import validate_changes
from forge.data import get_defaults_template, get_emissions_path, get_yamls_path
from forge.scripts.io.input_metadata import input_metadata_to_dict
from forge.scripts.io.region_codes import EGRID_SUBREGIONS, GEA_NAMES, STATES
from forge.scripts.io.yaml_loaders import load_project_technical_details
from forge.scripts.utils.run_context import RunState, reset_run_state, set_run_state

emissions = get_emissions_path()

_ENDS = ("sending", "receiving")
_KEYS = ("gea", "egrid_subregion", "state")
_LABELS = {
    ("sending", "gea"): "Sending terminal GEA region",
    ("sending", "egrid_subregion"): "Sending terminal eGRID subregion",
    ("sending", "state"): "Sending terminal state",
    ("receiving", "gea"): "Receiving terminal GEA region",
    ("receiving", "egrid_subregion"): "Receiving terminal eGRID subregion",
    ("receiving", "state"): "Receiving terminal state",
}
_FIELDS = (
    "sending_gea",
    "sending_egrid_subregion",
    "sending_state",
    "receiving_gea",
    "receiving_egrid_subregion",
    "receiving_state",
)


def _path(end: str, key: str) -> str:
    return f"01_project_technical_details.terminals.{end}.{key}"


def test_dropdowns_match_the_data_files():
    gea = {row["gea"] for row in csv.DictReader(open(emissions / "cambium_lrmer_co2e.csv"))}
    sub = {row["subregion"] for row in csv.DictReader(open(emissions / "egrid_criteria_rates.csv"))}
    assert set(GEA_NAMES) == gea
    assert list(EGRID_SUBREGIONS) == [
        "AZNM", "CAMX", "ERCT", "FRCC", "MROE", "MROW", "NEWE", "NWPP",
        "NYCW", "NYLI", "NYUP", "RFCE", "RFCM", "RFCW", "RMPA", "SPNO",
        "SPSO", "SRMV", "SRMW", "SRSO", "SRTV", "SRVC",
    ]
    assert set(EGRID_SUBREGIONS) == sub
    assert "AK" not in STATES and "HI" not in STATES and "DC" in STATES
    assert len(STATES) == 49


def test_a_region_string_must_be_in_the_list():
    errors = validate_changes({
        "01_project_technical_details.terminals.receiving.gea": "MISO Central",
    })
    assert errors[0]["message"].startswith("'MISO Central' is not one of the allowed options")


def test_terminal_paths_are_null_and_not_required():
    template = get_defaults_template()["01_project_technical_details"]["terminals"]
    by_path = {
        f"{field['yaml_section']}.{field['field_path']}": field
        for field in input_metadata_to_dict()
    }
    options = {
        "gea": list(GEA_NAMES),
        "egrid_subregion": list(EGRID_SUBREGIONS),
        "state": list(STATES),
    }
    for end in _ENDS:
        for key in _KEYS:
            assert template[end][key] is None
            field = by_path[_path(end, key)]
            assert field["label"] == _LABELS[(end, key)]
            assert field["input_type"] == "dropdown"
            assert field["taxonomy_id"] == "project_technology"
            assert field["input_tab"] == "routing"
            assert field["sub_tab"] == "terminals"
            assert field["required_when"] is None
            assert list(field["validation"]["options"]) == options[key]


def test_registry_leaves_are_route_analysis():
    document = yaml.safe_load((get_yamls_path() / "defaults_registry.yaml").read_text())
    leaves = {}

    def walk(node):
        if isinstance(node, dict) and "path" in node and isinstance(node["path"], str):
            leaves[node["path"]] = node
            return
        if isinstance(node, dict):
            for child in node.values():
                walk(child)

    walk(document)
    for end in _ENDS:
        for key in _KEYS:
            entry = leaves[_path(end, key)]
            assert entry["unit"] == "region code"
            assert entry["source"] == "Route analysis. No default."
            assert entry["basis"] == "Derived"
            assert entry["citation"] is None
            assert entry["yaml_file"] == "01_project_technical_details.yaml"


def _load(section: dict):
    state = RunState(
        inputs={"01_project_technical_details": section},
        scenario_id="test-terminal-regions",
    )
    token = set_run_state(state)
    try:
        return load_project_technical_details()
    finally:
        reset_run_state(token)


def _section(terminals):
    section = {
        "project": {
            "construction_type": "Overhead",
            "ac_dc": "AC",
            "capacity_mw": 500,
            "conductor_type": "Standard Aluminum Conductor",
            "converter_type": "NA",
            "line_utilization": 0.7,
            "project_type": "greenfield",
        },
        "timeline": {
            "construction_years": 1,
            "delay_years": 0,
            "project_lifetime": 40,
        },
    }
    if terminals is not None:
        section["terminals"] = terminals
    return section


def test_missing_terminals_block_stays_none():
    details = _load(_section(None))
    assert [getattr(details, name) for name in _FIELDS] == [None] * 6


def test_loader_reads_terminal_regions():
    details = _load(_section({
        "sending": {"gea": "GEA_SEND", "egrid_subregion": "SUB_SEND", "state": "TX"},
        "receiving": {"gea": "GEA_RECV", "egrid_subregion": "SUB_RECV", "state": "NM"},
    }))
    assert details.sending_gea == "GEA_SEND"
    assert details.sending_egrid_subregion == "SUB_SEND"
    assert details.sending_state == "TX"
    assert details.receiving_gea == "GEA_RECV"
    assert details.receiving_egrid_subregion == "SUB_RECV"
    assert details.receiving_state == "NM"
