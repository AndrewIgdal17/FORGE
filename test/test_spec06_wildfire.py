"""Wildfire ignition multipliers for direct-buried and tunnel construction."""
import pytest

import forge
from test.spec05_project import project_changes, run

CT = "01_project_technical_details.project.construction_type"
COND = "01_project_technical_details.project.conductor_type"


def _ign(ct, cond):
    r = run(project_changes(**{CT: ct, COND: cond}))
    return r["costs"]["wildfire"]["EAL"]


def test_direct_buried_and_tunnel_take_one_hundredth():
    oh = _ign("Overhead", "Standard Aluminum Conductor")
    db = _ign("Underground Direct-Buried", "Underground Copper Conductor")
    tu = _ign("Underground Tunnel", "Underground Copper Conductor")
    assert db == pytest.approx(0.01 * oh) and tu == pytest.approx(0.01 * oh)


def test_generic_underground_key_is_gone():
    m = forge.get_defaults_template()["06_wildfire_costs"]["wildfire"]["ignition_rate_multiplier"]
    assert set(m) == {"overhead", "underground_direct_buried", "underground_tunnel"}
    assert forge.validate_changes({"06_wildfire_costs.wildfire.ignition_rate_multiplier.underground": 0.5})
