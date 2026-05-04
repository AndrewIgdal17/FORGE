"""Standalone accuracy tests for facilitated_emissions.py.

Verifies the module against hand-calculated expected values.
Run: cd repos/ctcc/scripts && python test_facilitated_emissions.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from facilitated_emissions import calculate_facilitated_emissions

SOURCES = ["coal", "oil", "natural_gas", "solar", "wind", "hydro", "nuclear", "other"]

def _make_mix(solar_pct, gas_pct, solar_rate, gas_rate):
    """Helper: build a full 8-source mix dict with only solar and gas nonzero."""
    mix = {}
    for s in SOURCES:
        if s == "solar":
            mix[s] = {"percentage": solar_pct, "rate_of_change": solar_rate}
        elif s == "natural_gas":
            mix[s] = {"percentage": gas_pct, "rate_of_change": gas_rate}
        else:
            mix[s] = {"percentage": 0, "rate_of_change": 0.0}
    return mix

INTENSITIES = {
    "co2_intensity_kg_per_mwh": {s: (400 if s == "natural_gas" else 0) for s in SOURCES},
    "sox_intensity_kg_per_mwh": {s: 0 for s in SOURCES},
    "nox_intensity_kg_per_mwh": {s: 0 for s in SOURCES},
}
SOCIETAL = {"co2_cost_per_kg": 0.05, "sox_cost_per_kg": 0.0, "nox_cost_per_kg": 0.0}

TOL = 1e-4


def assert_close(actual, expected, label, tol=TOL):
    diff = abs(actual - expected)
    if diff > tol:
        print(f"  FAIL {label}: expected {expected:.10f}, got {actual:.10f}, diff={diff:.2e}")
        return False
    print(f"  OK   {label}: {actual:.6f} (expected {expected:.6f})")
    return True


def test_hand_calculated():
    """Test 1: 3-year case with hand-calculated expected values.

    Setup:
      - solar=60%, gas=40%; project solar grows +10%/yr; counterfactual frozen
      - E_delivered=1000 MWh, gas intensity=400 kg CO2/MWh, cost=$0.05/kg
      - lifetime=3, r_social=0, delay=0, construction=0

    Expected (from hand calculation using emissions.py evolution engine):
      - proj_nominal = proj_pv = 21326.419078 (no discounting)
      - cf_nominal = cf_pv = 24000.000000
      - displacement = 2673.580922
    """
    print("\n=== Test 1: Hand-calculated 3-year case ===")

    proj_mix = _make_mix(60, 40, 0.10, 0.0)
    cf_mix = _make_mix(60, 40, 0.0, 0.0)

    r = calculate_facilitated_emissions(
        energy_delivered_annual_mwh=1000.0,
        energy_source_mix_details=proj_mix,
        counterfactual_energy_source_mix_details=cf_mix,
        emission_intensities=INTENSITIES,
        societal_costs=SOCIETAL,
        project_lifetime=3,
        social_discount_rate=0.0,
        delay_years=0,
        construction_years=0,
    )

    ok = True
    ok &= assert_close(r.fac_emissions_project_nominal, 21326.419078, "proj_nominal", tol=0.01)
    ok &= assert_close(r.fac_emissions_project_pv, 21326.419078, "proj_pv", tol=0.01)
    ok &= assert_close(r.fac_emissions_noline_nominal, 24000.0, "cf_nominal")
    ok &= assert_close(r.fac_emissions_noline_pv, 24000.0, "cf_pv")
    ok &= assert_close(r.displacement_avoided_cost_pv, 2673.580922, "displacement_pv", tol=0.01)
    ok &= assert_close(r.displacement_avoided_cost_nominal, 2673.580922, "displacement_nom", tol=0.01)

    if r.displacement_avoided_cost_pv <= 0:
        print("  FAIL displacement should be positive (cleaner project)")
        ok = False

    return ok


def test_zero_displacement():
    """Test 2: identical project and counterfactual -> displacement exactly 0."""
    print("\n=== Test 2: Zero displacement (identical mixes) ===")

    mix = _make_mix(60, 40, 0.10, 0.0)

    r = calculate_facilitated_emissions(
        energy_delivered_annual_mwh=1000.0,
        energy_source_mix_details=mix,
        counterfactual_energy_source_mix_details=mix,
        emission_intensities=INTENSITIES,
        societal_costs=SOCIETAL,
        project_lifetime=5,
        social_discount_rate=0.03,
        delay_years=2,
        construction_years=3,
    )

    ok = True
    ok &= assert_close(r.displacement_avoided_cost_pv, 0.0, "displacement_pv")
    ok &= assert_close(r.displacement_avoided_cost_nominal, 0.0, "displacement_nom")
    ok &= assert_close(r.fac_emissions_project_pv, r.fac_emissions_noline_pv, "proj_pv == cf_pv")

    return ok


def test_discount_sanity():
    """Test 3: with positive discount rate, PV < nominal."""
    print("\n=== Test 3: Discount sanity (PV < nominal) ===")

    proj_mix = _make_mix(60, 40, 0.10, 0.0)
    cf_mix = _make_mix(60, 40, 0.0, 0.0)

    r = calculate_facilitated_emissions(
        energy_delivered_annual_mwh=1000.0,
        energy_source_mix_details=proj_mix,
        counterfactual_energy_source_mix_details=cf_mix,
        emission_intensities=INTENSITIES,
        societal_costs=SOCIETAL,
        project_lifetime=10,
        social_discount_rate=0.05,
        delay_years=3,
        construction_years=2,
    )

    ok = True
    if r.fac_emissions_project_pv >= r.fac_emissions_project_nominal:
        print(f"  FAIL proj PV ({r.fac_emissions_project_pv:.2f}) should be < nominal ({r.fac_emissions_project_nominal:.2f})")
        ok = False
    else:
        print(f"  OK   proj PV ({r.fac_emissions_project_pv:.2f}) < nominal ({r.fac_emissions_project_nominal:.2f})")

    if r.fac_emissions_noline_pv >= r.fac_emissions_noline_nominal:
        print(f"  FAIL cf PV ({r.fac_emissions_noline_pv:.2f}) should be < nominal ({r.fac_emissions_noline_nominal:.2f})")
        ok = False
    else:
        print(f"  OK   cf PV ({r.fac_emissions_noline_pv:.2f}) < nominal ({r.fac_emissions_noline_nominal:.2f})")

    if r.displacement_avoided_cost_pv <= 0:
        print(f"  FAIL displacement should be positive (cleaner project), got {r.displacement_avoided_cost_pv:.2f}")
        ok = False
    else:
        print(f"  OK   displacement positive: ${r.displacement_avoided_cost_pv:.2f}")

    return ok


def main():
    results = []
    results.append(("Hand-calculated", test_hand_calculated()))
    results.append(("Zero displacement", test_zero_displacement()))
    results.append(("Discount sanity", test_discount_sanity()))

    print("\n" + "=" * 50)
    all_pass = True
    for name, passed in results:
        status = "PASS" if passed else "FAIL"
        print(f"  {status}: {name}")
        if not passed:
            all_pass = False

    if all_pass:
        print("\nAll tests passed.")
        return 0
    else:
        print("\nSome tests FAILED.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
