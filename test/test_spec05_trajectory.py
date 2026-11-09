"""Trajectory rows are the taxonomy streams, discounted per perspective."""
import pytest

from forge.scripts.calc.bcr_calculator import compute_all_bcrs
from forge.scripts.io.taxonomy_adapters import TaxonomyResult

from test.spec05_project import item, project_changes, run


@pytest.mark.parametrize("delay", [0, 4])
def test_trajectory_final_row_matches_ratios(delay):
    r = run(project_changes(**{"01_project_technical_details.timeline.delay_years": delay}))
    last = r["trajectory"][-1]
    for k in ("bcr_societal", "bcr_utility", "bcr_ratepayer"):
        assert last[k] == pytest.approx(r["bcr"][k], rel=1e-6)


def test_missing_wacc_value_raises():
    rs = [TaxonomyResult("oandm", value_pv=1.0, value_nominal=0.0, value_pv_wacc=None)]
    with pytest.raises(ValueError, match="oandm has no WACC present value"):
        compute_all_bcrs(rs)


def test_a1_societal_values_ignore_wacc():                            # spec test 1
    a = run(project_changes(**{"03_financing.financial.wacc_nominal": 0.075}))
    b = run(project_changes(**{"03_financing.financial.wacc_nominal": 0.10}))
    for i in a["taxonomy_results"]:
        if i["value_pv"] is not None:
            assert item(b, i["taxonomy_id"])["value_pv"] == pytest.approx(i["value_pv"])
    for k in ("total_costs_pv", "total_benefits_pv", "net_benefit_pv", "bcr_societal"):
        assert b["bcr"][k] == pytest.approx(a["bcr"][k])
    for k in (k for k in a["bcr"] if k.startswith("bcr_excluding_")):
        assert b["bcr"][k] == pytest.approx(a["bcr"][k])
    assert b["bcr"]["bcr_ratepayer"] != pytest.approx(a["bcr"]["bcr_ratepayer"])
