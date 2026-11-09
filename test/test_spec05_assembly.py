import pytest

from forge.scripts.calc.bcr_calculator import compute_all_bcrs
from forge.scripts.io.taxonomy import TAXONOMY_ITEMS
from forge.scripts.io.taxonomy_adapters import (
    TaxonomyResult,
    taxonomy_results_to_flat_keys,
    taxonomy_results_to_json_list,
)

_SOCIAL = ("wildfire_eac", "outage_eac", "emissions_comp", "avoided_emissions_benefit")


def _r(i, pv, wacc):  # value_nominal irrelevant here
    return TaxonomyResult(i, value_pv=pv, value_nominal=0.0, value_pv_wacc=wacc)


def test_utility_and_ratepayer_use_wacc_values_societal_uses_social():
    rs = [_r("congestion_benefit", 300.0, 200.0), _r("oandm", 50.0, 40.0),
          _r("insurance", 10.0, 8.0), _r("row_rent", 0.0, 0.0),
          _r("line_loss_conductor", 20.0, 15.0), _r("line_loss_converter", 0.0, 0.0),
          _r("base_delay", 5.0, 4.0), TaxonomyResult("capital_recovery", value_pv=None,
          value_nominal=0.0, value_pv_wacc=100.0), _r("build_conductor", 90.0, 70.0)]
    b = compute_all_bcrs(rs)
    assert b["bcr_ratepayer"] == pytest.approx(200.0 / (100.0 + 40.0 + 8.0 + 0.0 + 15.0 + 0.0))
    assert b["bcr_utility"] == pytest.approx((100.0 + 40.0 + 8.0) / (100.0 + 40.0 + 8.0 + 4.0))
    assert b["total_costs_pv"] == pytest.approx(50 + 10 + 20 + 5 + 90)


def test_json_and_flat_keys_carry_both_values():
    rs = [TaxonomyResult("oandm", value_pv=50.0, value_nominal=0.0, value_pv_wacc=40.0, stream=[1.0]),
          TaxonomyResult("capital_recovery", value_pv=None, value_nominal=0.0, value_pv_wacc=100.0)]
    j = {x["taxonomy_id"]: x for x in taxonomy_results_to_json_list(rs)}
    assert j["oandm"]["value_pv_wacc"] == 40.0 and j["oandm"]["stream"] == [1.0]
    f = taxonomy_results_to_flat_keys(rs)
    assert f["oandm_pv_wacc"] == 40.0 and f["capital_recovery_pv"] == 100.0


def test_discount_rate_metadata():
    rate = {t.id: t.discount_rate for t in TAXONOMY_ITEMS}
    for i in _SOCIAL:
        assert rate[i] == "social"
    assert rate["capital_recovery"] == "wacc_real"
    assert rate["oandm"] == "per_perspective"
    for i, item_rate in rate.items():
        if i in _SOCIAL or i == "capital_recovery":
            continue
        assert item_rate == "per_perspective"
