"""Loss-compensation dollars from terminal emission rates."""

import pytest

from forge.scripts.calc.emissions import calculate_loss_compensation


def test_one_operating_year_in_2026_matches_the_hand_formula():
    e_loss, fraction = 1000.0, 1.0
    eps_co2e, eps_so2, eps_nox = 400.0, 0.05, 0.20
    c_co2e, c_so2, c_nox = 0.25, 10.0, 20.0
    e_comp = fraction * e_loss
    expected = e_comp * (eps_co2e * c_co2e + eps_so2 * c_so2 + eps_nox * c_nox)
    out = calculate_loss_compensation(
        e_loss, fraction,
        co2e_kg_per_mwh=[eps_co2e], so2_kg_per_mwh=eps_so2, nox_kg_per_mwh=eps_nox,
        c_co2e_usd_per_kg=[c_co2e], c_so2_usd_per_kg=[c_so2], c_nox_usd_per_kg=[c_nox],
        t_cod=2, horizon=2, social_discount_rate=0.02,
        receiving={"gea": "CAISO", "egrid_subregion": "CAMX", "state": "CA"},
    )
    assert out["emissions_comp_annual_values"] == pytest.approx([expected])
    assert out["streams"]["emissions_comp"] == pytest.approx([0.0, expected])
    assert out["total_pv"] == pytest.approx(expected / (1.02 ** 2))
    assert out["annual_kg"]["co2e"] == pytest.approx([e_comp * eps_co2e])
    assert "total_pv_wacc" not in out
