import pytest

import forge
from forge.scripts.utils.financial_utils import capitalize_yearly_spending


def test_mid_year_compounding_to_cod():
    y = [0.0, 0.0, 100.0, 200.0, 0.0, 0.0]          # build in years 3–4, COD = 5
    v = capitalize_yearly_spending(y, t_cod=5, afudc_rate=0.05, apply_afudc=True)
    assert v == pytest.approx(100.0 * 1.05**1.5 + 200.0 * 1.05**0.5)


def test_afudc_off_adds_undiscounted_spending():
    y = [0.0, 0.0, 100.0, 200.0, 0.0, 0.0]
    assert capitalize_yearly_spending(y, 5, 0.05, False) == pytest.approx(300.0)


def test_one_construction_year():
    assert capitalize_yearly_spending([100.0, 0.0], 2, 0.05, True) == pytest.approx(100.0 * 1.05**0.5)


def test_operating_year_spending_is_an_error():
    with pytest.raises(ValueError):
        capitalize_yearly_spending([0.0, 0.0, 5.0], 2, 0.05, True)


def test_timing_inputs_are_gone():
    for p in ("19_cost_timing_patterns.cost_timing_patterns.build_costs.during_delay",
              "03_financing.financial.afudc.delay_period_active_work"):
        assert forge.validate_changes({p: 0.0})[0]["message"].startswith("unknown input path")
