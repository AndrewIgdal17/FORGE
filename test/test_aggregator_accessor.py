"""Tests for JSONOutputManager.require_upstream / require_upstream_dict."""
import pytest
from scripts.io.json_output_manager import JSONOutputManager


def test_require_upstream_returns_value_when_present():
    mgr = JSONOutputManager(scenario_id="test")
    mgr.costs["build"] = {"total_afudc": 1234.56, "total_pv": 5000.0}
    assert mgr.require_upstream("costs", "build", "total_afudc") == 1234.56


def test_require_upstream_returns_zero_when_field_is_zero():
    mgr = JSONOutputManager(scenario_id="test")
    mgr.costs["build"] = {"total_afudc": 0.0, "total_pv": 5000.0}
    assert mgr.require_upstream("costs", "build", "total_afudc") == 0.0


def test_require_upstream_raises_when_module_missing():
    mgr = JSONOutputManager(scenario_id="test")
    with pytest.raises(KeyError, match="build.*has not run"):
        mgr.require_upstream("costs", "build", "total_afudc")


def test_require_upstream_raises_when_field_missing():
    mgr = JSONOutputManager(scenario_id="test")
    mgr.costs["build"] = {"total_pv": 5000.0}
    with pytest.raises(KeyError, match="total_afudc.*not found"):
        mgr.require_upstream("costs", "build", "total_afudc")


def test_require_upstream_works_for_benefits():
    mgr = JSONOutputManager(scenario_id="test")
    mgr.benefits["congestion"] = {"energy_delivered_annual_mwh_yr": 42000.0}
    assert mgr.require_upstream("benefits", "congestion", "energy_delivered_annual_mwh_yr") == 42000.0


def test_require_upstream_dict_returns_full_dict():
    mgr = JSONOutputManager(scenario_id="test")
    mgr.benefits["congestion"] = {"energy_delivered_annual_mwh_yr": 42000.0, "pv": 100.0}
    d = mgr.require_upstream_dict("benefits", "congestion")
    assert d["energy_delivered_annual_mwh_yr"] == 42000.0


def test_require_upstream_dict_raises_when_missing():
    mgr = JSONOutputManager(scenario_id="test")
    with pytest.raises(KeyError, match="congestion.*has not run"):
        mgr.require_upstream_dict("benefits", "congestion")
