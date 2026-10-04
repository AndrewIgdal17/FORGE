"""Tests for JSONOutputManager.require_upstream / require_upstream_dict."""
import pytest
from forge.scripts.io.json_output_manager import JSONOutputManager


@pytest.fixture
def mgr(monkeypatch):
    """Construct a manager without a calculation run.

    load_technical_details reads the active run. These tests only exercise
    require_upstream, so the loader is stubbed.
    """
    monkeypatch.setattr(
        JSONOutputManager,
        "load_technical_details",
        lambda self: {"capacity_mw": 1},
    )
    return JSONOutputManager(scenario_id="test")


def test_require_upstream_returns_value_when_present(mgr):
    mgr.costs["build"] = {"total_afudc": 1234.56, "total_pv": 5000.0}
    assert mgr.require_upstream("costs", "build", "total_afudc") == 1234.56


def test_require_upstream_returns_zero_when_field_is_zero(mgr):
    mgr.costs["build"] = {"total_afudc": 0.0, "total_pv": 5000.0}
    assert mgr.require_upstream("costs", "build", "total_afudc") == 0.0


def test_require_upstream_raises_when_module_missing(mgr):
    with pytest.raises(KeyError, match="build.*has not run"):
        mgr.require_upstream("costs", "build", "total_afudc")


def test_require_upstream_raises_when_field_missing(mgr):
    mgr.costs["build"] = {"total_pv": 5000.0}
    with pytest.raises(KeyError, match="total_afudc.*not found"):
        mgr.require_upstream("costs", "build", "total_afudc")


def test_require_upstream_works_for_benefits(mgr):
    mgr.benefits["congestion"] = {"energy_delivered_annual_mwh_yr": 42000.0}
    assert mgr.require_upstream("benefits", "congestion", "energy_delivered_annual_mwh_yr") == 42000.0


def test_require_upstream_dict_returns_full_dict(mgr):
    mgr.benefits["congestion"] = {"energy_delivered_annual_mwh_yr": 42000.0, "pv": 100.0}
    d = mgr.require_upstream_dict("benefits", "congestion")
    assert d["energy_delivered_annual_mwh_yr"] == 42000.0


def test_require_upstream_dict_raises_when_missing(mgr):
    with pytest.raises(KeyError, match="congestion.*has not run"):
        mgr.require_upstream_dict("benefits", "congestion")
