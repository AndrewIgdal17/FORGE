"""ROW and environmental mitigation streams; ROW holding enters the totals."""
import pytest

from forge.scripts.io.taxonomy import TAXONOMY
from test.spec05_project import item, project_changes, run

COST_IDS = {tid for tid, entry in TAXONOMY.items() if entry.side == "cost"}


def test_holding_enters_total_costs():
    r = run(project_changes(**{"01_project_technical_details.timeline.delay_years": 3}))
    hold = item(r, "row_holding")
    h = hold["stream"][0]
    assert h > 0 and hold["stream"][3:] == [0.0] * (len(hold["stream"]) - 3)
    assert hold["value_pv"] == pytest.approx(sum(h / 1.02**t for t in (1, 2, 3)))
    total = sum(i["value_pv"] for i in r["taxonomy_results"] if i["taxonomy_id"] in COST_IDS)
    assert r["bcr"]["total_costs_pv"] == pytest.approx(total)


def test_no_delay_gives_empty_holding_stream():
    r = run(project_changes(**{"01_project_technical_details.timeline.delay_years": 0}))
    assert all(v == 0.0 for v in item(r, "row_holding")["stream"])


def test_acquisition_and_mitigation_follow_weights_without_escalation():   # F2
    r = run(project_changes(**{"01_project_technical_details.timeline.delay_years": 2,
                               "01_project_technical_details.timeline.construction_years": 4}))
    w = r["derived_parameters"]["construction_spending_weights"]
    for tid, total_key in (("row_acquisition", ("row", "acquisition_nominal")),
                           ("env_mitigation", ("environmental", "total_nominal"))):
        st = item(r, tid)["stream"]; total = r["costs"][total_key[0]][total_key[1]]
        assert st[2:6] == pytest.approx([x * total for x in w])
