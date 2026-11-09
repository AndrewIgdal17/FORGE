import pytest, forge
from forge.errors import InvalidInputs
from test.spec05_project import project_changes, run

ESC = "03_financing.financial.construction_cost_escalation_nominal"
DELAY = "01_project_technical_details.timeline.delay_years"
BASE = "01_project_technical_details.timeline.baseline_delay_years"

def test_real_escalation_is_derived_by_fisher():
    r = run(project_changes(**{ESC: 0.04, "03_financing.financial.inflation_rate": 0.03}))
    assert r["derived_parameters"]["construction_escalation_real"] == pytest.approx(1.04 / 1.03 - 1)

def test_old_escalation_key_is_unknown():
    errs = forge.validate_changes({"03_financing.financial.construction_cost_escalation_rate": 0.04})
    assert errs and "unknown input path" in errs[0]["message"]

def test_non_whole_delay_fails_validation_and_bootstrap():
    errs = forge.validate_changes({DELAY: 2.5})
    assert errs[0]["path"] == DELAY and "is not a whole number" in errs[0]["message"]
    with pytest.raises(InvalidInputs, match="delay_years"):
        run(project_changes(**{DELAY: 2.5}))

def test_baseline_cannot_exceed_delay():
    with pytest.raises(InvalidInputs, match=r"baseline_delay_years \(3\) must not exceed delay_years \(2\)\."):
        run(project_changes(**{DELAY: 2, BASE: 3}))

def test_timeline_context_and_weights():
    r = run(project_changes(**{DELAY: 2, "01_project_technical_details.timeline.construction_years": 3,
                               "01_project_technical_details.timeline.project_lifetime": 40}))
    d = r["derived_parameters"]
    assert d["t_cod"] == 6 and d["horizon"] == 45
    assert sum(d["construction_spending_weights"]) == pytest.approx(1.0, abs=1e-12)
    assert len(d["construction_spending_weights"]) == 3
