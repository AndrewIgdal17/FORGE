import pytest
from forge.scripts.utils import streams as s
from forge.scripts.utils.financial_utils import fisher_real


def test_growing_counts_from_year_one():
    st = s.growing(100.0, 0.02, t0=6, n=3, horizon=10)
    assert st[:5] == [0.0] * 5
    assert st[5] == pytest.approx(100.0 * 1.02**5)
    assert st[7] == pytest.approx(100.0 * 1.02**7)
    assert st[8:] == [0.0, 0.0]


def test_pv_discounts_year_t_by_t():
    assert s.pv([0.0, 0.0, 100.0], 0.02) == pytest.approx(100.0 / 1.02**3)


def test_pv_operator_matches_sum_when_g_ne_r():
    st = s.growing(50.0, 0.01, t0=4, n=40, horizon=43)
    assert s.pv_operator(50.0, 0.01, 0.02, 4, 40) == pytest.approx(s.pv(st, 0.02), rel=1e-9)


def test_pv_operator_matches_sum_when_g_eq_r():
    st = s.growing(50.0, 0.02, t0=4, n=40, horizon=43)
    assert s.pv_operator(50.0, 0.02, 0.02, 4, 40) == pytest.approx(s.pv(st, 0.02), rel=1e-9)


def test_weighted_escalates_each_year_on_the_calendar():
    st = s.weighted(1000.0, [0.2, 0.3, 0.5], t_start=3, horizon=6, escalation=0.01)
    assert st[0:2] == [0.0, 0.0]
    assert st[2] == pytest.approx(0.2 * 1000.0 * 1.01**2)
    assert st[4] == pytest.approx(0.5 * 1000.0 * 1.01**4)
    assert st[5] == 0.0


def test_level_and_undiscounted():
    assert s.undiscounted(s.level(10.0, 1, 3, 5)) == pytest.approx(30.0)
    assert s.level(10.0, 1, 0, 5) == [0.0] * 5


def test_add_requires_equal_lengths():
    assert s.add([1.0, 2.0], [3.0, 4.0]) == [4.0, 6.0]
    with pytest.raises(ValueError):
        s.add([1.0], [1.0, 2.0])


def test_fisher_real():
    assert fisher_real(0.04, 0.03) == pytest.approx(1.04 / 1.03 - 1)
    assert fisher_real(0.075, 0.03) == pytest.approx(1.075 / 1.03 - 1)
