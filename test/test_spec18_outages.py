import inspect
import json

import forge
import pytest
import yaml
from forge.data import get_yamls_path
from forge.scripts.calc.outage_costs import calculate_outage_costs
from forge.scripts.io.input_metadata import input_metadata_to_dict
from test.spec05_project import item, project_changes, run
from forge.scripts.io.taxonomy import TAXONOMY, get_excluded_taxonomy_ids

BASE_OUTAGE_PV = 857805241.5575649

SHARE = "07_outage_costs.outage.load_shed_fraction"
LOAD_SHED_HELP = (
    "Share of lost power shed as unserved energy and priced at the value of lost load. "
    "Default 0.05 for AC and DC lines alike (ENTSO-E 2021). "
    "The rest is redispatched at the route's congestion spread."
)


def _registry_leaf(dotted_path: str) -> dict:
    document = yaml.safe_load((get_yamls_path() / "defaults_registry.yaml").read_text())

    def walk(node):
        if isinstance(node, dict):
            if node.get("path") == dotted_path:
                return node
            for child in node.values():
                found = walk(child)
                if found is not None:
                    return found
        return None

    leaf = walk(document)
    assert leaf is not None, dotted_path
    return leaf


def test_two_outage_items_replace_one():
    assert "outage_eac" not in TAXONOMY
    for tid in ("outage_load_shed", "outage_redispatch"):
        assert TAXONOMY[tid].category == TAXONOMY["wildfire_eac"].category
        assert TAXONOMY[tid].subgroup == TAXONOMY["wildfire_eac"].subgroup
    assert set(get_excluded_taxonomy_ids(["outage"])) == {
        "outage_load_shed",
        "outage_redispatch",
    }


def test_split_keeps_the_total():
    r = run()
    parts = item(r, "outage_load_shed")["value_pv"] + item(r, "outage_redispatch")["value_pv"]
    assert parts == pytest.approx(BASE_OUTAGE_PV, rel=1e-12)
    assert r["costs"]["outage"]["pv_cost"] == pytest.approx(BASE_OUTAGE_PV, rel=1e-12)
    assert r["bcr"]["outage_pv"] == pytest.approx(BASE_OUTAGE_PV, rel=1e-12)


def test_one_share_for_every_line():
    assert "ac_dc" not in inspect.signature(calculate_outage_costs).parameters
    assert forge.get_defaults_template()["07_outage_costs"]["outage"]["load_shed_fraction"] == 0.05
    assert run()["costs"]["outage"]["load_shed_fraction"] == 0.05


def test_stored_auto_loads_as_005():
    resolved = forge.resolve_inputs(project_changes(**{SHARE: "auto"}))
    assert resolved["07_outage_costs"]["outage"]["load_shed_fraction"] == 0.05


def test_stored_number_is_kept():
    assert run(project_changes(**{SHARE: 0.2}))["costs"]["outage"]["load_shed_fraction"] == 0.2


def test_bundled_documents_with_auto_still_resolve():
    for path in forge.get_scenarios_path().glob("*.forge"):
        changes = forge.diff_changes(json.loads(path.read_text())["inputs"])
        assert changes.get(SHARE) == "auto"
        assert forge.validate_changes(changes) == [], path.name


def test_registry_and_help_name_entso_e():
    leaf = _registry_leaf("07_outage_costs.outage.load_shed_fraction")
    assert leaf["citation"] == "ENTSOE2021CBA"
    field = next(f for f in input_metadata_to_dict() if f["id"] == "out_load_shed_fraction")
    assert field["help_text"] == LOAD_SHED_HELP


def test_ac_and_dc_lines_shed_the_same_share():
    yaml_doc = {
        "outage": {
            "risk_growth_rate": 0.0,
            "load_shed_fraction": 0.05,
            "redispatch_cost_per_mwh": 0.0,
            "value_of_lost_load": {"tiers": [{"max_hours": ".inf", "value_per_mwh": 1.0}]},
            "outage_duration": 1.0,
            "outage_duration_multiplier": {"overhead": 1.0},
            "outage_rate": {"overhead": 0.0},
        }
    }
    terrain = {"forested": 1.0}
    common = dict(
        construction_type="overhead",
        terrain_miles=terrain,
        capacity_mw=100,
        project_lifetime=10,
        discount_rate=0.05,
        construction_years=1,
        line_utilization=1.0,
    )
    ac = calculate_outage_costs(yaml_doc, number_of_circuits_poles=1, **common)
    dc = calculate_outage_costs(yaml_doc, number_of_circuits_poles=2, **common)
    assert ac["load_shed_fraction"] == 0.05
    assert dc["load_shed_fraction"] == 0.05