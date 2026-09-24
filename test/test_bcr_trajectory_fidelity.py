"""Per-ratio BCR fidelity check: trajectory final-year vs bcr_calculator."""
import pytest

from scripts.calc.bcr_trajectory import _assert_per_ratio_fidelity


def test_ratio_fidelity_passes_when_core_ratios_match():
    final = {
        "bcr_societal": 1.25,
        "bcr_utility": 1.0,
        "bcr_ratepayer": 0.8,
    }
    bcr = {
        "bcr_societal": 1.25,
        "bcr_utility": 1.0,
        "bcr_ratepayer": 0.8,
    }
    _assert_per_ratio_fidelity(final, bcr)


def test_ratio_fidelity_fails_on_core_mismatch():
    final = {"bcr_societal": 1.0}
    bcr = {"bcr_societal": 2.0}
    with pytest.raises(AssertionError, match="bcr_societal"):
        _assert_per_ratio_fidelity(final, bcr)


def test_ratio_fidelity_skips_near_zero_calculator_value():
    final = {"bcr_societal": 999.0}
    bcr = {"bcr_societal": 0.0}
    _assert_per_ratio_fidelity(final, bcr)


def test_ratio_fidelity_uses_calculator_exclusion_keys():
    """Naive same-key lookup would skip this; the check must use bcr_excluding_*."""
    final = {"bcr_excl_wildfire": 1.0}
    bcr = {
        "bcr_excl_wildfire": 1.0,
        "bcr_excluding_wildfire_risk": 2.0,
    }
    with pytest.raises(AssertionError, match="bcr_excl_wildfire"):
        _assert_per_ratio_fidelity(final, bcr)


def test_ratio_fidelity_maps_all_exclusion_variants():
    final = {
        "bcr_excl_avoided_emissions": 1.10,
        "bcr_excl_emissions_costs": 1.20,
        "bcr_excl_all_emissions": 1.30,
        "bcr_excl_outage": 1.40,
        "bcr_excl_wildfire": 1.50,
        "bcr_excl_wf_out": 1.60,
    }
    bcr = {
        "bcr_excluding_avoided_emissions": 1.10,
        "bcr_excluding_emissions": 1.20,
        "bcr_excluding_avoided_emissions_and_emissions": 1.30,
        "bcr_excluding_outage_risk": 1.40,
        "bcr_excluding_wildfire_risk": 1.50,
        "bcr_excluding_wildfire_risk_and_outage_risk": 1.60,
    }
    _assert_per_ratio_fidelity(final, bcr)


def test_ratio_fidelity_reads_traj_bcr_excl_wf_out_alias():
    """Trajectory stores outage+wildfire as bcr_excl_wf_out, not taxonomy id."""
    final = {
        "bcr_excl_wf_out": 1.5,
        "bcr_excl_outage_wildfire": 99.0,
    }
    bcr = {"bcr_excluding_wildfire_risk_and_outage_risk": 1.5}
    _assert_per_ratio_fidelity(final, bcr)


def test_ratio_fidelity_treats_none_traj_as_zero():
    final = {"bcr_societal": None}
    bcr = {"bcr_societal": 1.5}
    with pytest.raises(AssertionError, match="bcr_societal"):
        _assert_per_ratio_fidelity(final, bcr)
