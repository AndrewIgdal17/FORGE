from test.spec05_project import item, project_changes, run
from forge.scripts.io.taxonomy import TAXONOMY, get_excluded_taxonomy_ids

import pytest

BASE_OUTAGE_PV = 13388107507.986546


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