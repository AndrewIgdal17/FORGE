"""Standalone accuracy tests for facilitated_emissions.py (single-trajectory model).

Verifies the module against hand-calculated expected values.
Run: cd repos/forge && python -m pytest scripts/tests/test_facilitated_emissions.py -v
"""

import sys

from forge.scripts.calc.facilitated_emissions import calculate_facilitated_emissions

SOURCES = ["coal", "oil", "natural_gas", "solar", "wind", "hydro", "nuclear", "other"]

def _make_grid_mix(solar_pct, gas_pct, rate_pre_cod, rate_post_cod):
    """Helper: build a grid_mix dict with only solar and gas nonzero.

    rate_pre_cod / rate_post_cod are (solar_rate, gas_rate) tuples applied
    uniformly across all fuels other than solar/gas (which stay at 0).
    """
    initial = {s: 0 for s in SOURCES}
    initial["solar"] = solar_pct
    initial["natural_gas"] = gas_pct

    def _rates(solar_rate, gas_rate):
        r = {s: 0.0 for s in SOURCES}
        r["solar"] = solar_rate
        r["natural_gas"] = gas_rate
        return r

    return {
        "initial": initial,
        "rate_pre_cod": _rates(*rate_pre_cod),
        "rate_post_cod": _rates(*rate_post_cod),
    }

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
      - solar=60%, gas=40%; rate_pre_cod frozen (no-line); rate_post_cod: solar
        grows +10%/yr (with-line)
      - delay=0, construction=0 -> T_COD=1yr, and rate_pre_cod=0 means the COD
        state equals the initial mix exactly, so this reduces to the same
        hand-calculated case as the pre-single-trajectory model.
      - E_delivered=1000 MWh, gas intensity=400 kg CO2/MWh, cost=$0.05/kg
        lifetime=3, r_social=0

    Expected (from hand calculation using fixed evolution engine, tau-1 exponent):
      - withline_nominal = withline_pv = 22651.965548 (no discounting)
      - noline_nominal = noline_pv = 24000.000000
      - displacement = 1348.034452
    """
    print("\n=== Test 1: Hand-calculated 3-year case ===")

    grid_mix = _make_grid_mix(60, 40, rate_pre_cod=(0.0, 0.0), rate_post_cod=(0.10, 0.0))

    r = calculate_facilitated_emissions(
        energy_delivered_annual_mwh=1000.0,
        grid_mix=grid_mix,
        emission_intensities=INTENSITIES,
        societal_costs=SOCIETAL,
        project_lifetime=3,
        social_discount_rate=0.0,
        delay_years=0,
        construction_years=0,
    )

    ok = True
    ok &= assert_close(r.fac_emissions_project_nominal, 22651.965548, "withline_nominal", tol=0.01)
    ok &= assert_close(r.fac_emissions_project_pv, 22651.965548, "withline_pv", tol=0.01)
    ok &= assert_close(r.fac_emissions_noline_nominal, 24000.0, "noline_nominal")
    ok &= assert_close(r.fac_emissions_noline_pv, 24000.0, "noline_pv")
    ok &= assert_close(r.displacement_avoided_benefit_pv, 1348.034452, "displacement_pv", tol=0.01)
    ok &= assert_close(r.displacement_avoided_benefit_nominal, 1348.034452, "displacement_nom", tol=0.01)

    if r.displacement_avoided_benefit_pv <= 0:
        print("  FAIL displacement should be positive (cleaner with-line trajectory)")
        ok = False

    return ok

def test_zero_displacement():
    """Test 2: identical rate_pre_cod/rate_post_cod -> displacement exactly 0.

    This is the identity-placeholder property required by Task 4a: when the
    line has no researched influence on the grid, with-line and without-line
    trajectories are identical regardless of the COD state they start from.
    """
    print("\n=== Test 2: Zero displacement (rate_pre_cod == rate_post_cod) ===")

    grid_mix = _make_grid_mix(60, 40, rate_pre_cod=(0.10, 0.0), rate_post_cod=(0.10, 0.0))

    r = calculate_facilitated_emissions(
        energy_delivered_annual_mwh=1000.0,
        grid_mix=grid_mix,
        emission_intensities=INTENSITIES,
        societal_costs=SOCIETAL,
        project_lifetime=5,
        social_discount_rate=0.03,
        delay_years=2,
        construction_years=3,
    )

    ok = True
    ok &= assert_close(r.displacement_avoided_benefit_pv, 0.0, "displacement_pv")
    ok &= assert_close(r.displacement_avoided_benefit_nominal, 0.0, "displacement_nom")
    ok &= assert_close(r.fac_emissions_project_pv, r.fac_emissions_noline_pv, "withline_pv == noline_pv")

    return ok

def test_discount_sanity():
    """Test 3: with positive discount rate, PV < nominal; displacement positive."""
    print("\n=== Test 3: Discount sanity (PV < nominal) ===")

    grid_mix = _make_grid_mix(60, 40, rate_pre_cod=(0.0, 0.0), rate_post_cod=(0.10, 0.0))

    r = calculate_facilitated_emissions(
        energy_delivered_annual_mwh=1000.0,
        grid_mix=grid_mix,
        emission_intensities=INTENSITIES,
        societal_costs=SOCIETAL,
        project_lifetime=10,
        social_discount_rate=0.05,
        delay_years=3,
        construction_years=2,
    )

    ok = True
    if r.fac_emissions_project_pv >= r.fac_emissions_project_nominal:
        print(f"  FAIL withline PV ({r.fac_emissions_project_pv:.2f}) should be < nominal ({r.fac_emissions_project_nominal:.2f})")
        ok = False
    else:
        print(f"  OK   withline PV ({r.fac_emissions_project_pv:.2f}) < nominal ({r.fac_emissions_project_nominal:.2f})")

    if r.fac_emissions_noline_pv >= r.fac_emissions_noline_nominal:
        print(f"  FAIL noline PV ({r.fac_emissions_noline_pv:.2f}) should be < nominal ({r.fac_emissions_noline_nominal:.2f})")
        ok = False
    else:
        print(f"  OK   noline PV ({r.fac_emissions_noline_pv:.2f}) < nominal ({r.fac_emissions_noline_nominal:.2f})")

    if r.displacement_avoided_benefit_pv <= 0:
        print(f"  FAIL displacement should be positive (cleaner with-line trajectory), got {r.displacement_avoided_benefit_pv:.2f}")
        ok = False
    else:
        print(f"  OK   displacement positive: ${r.displacement_avoided_benefit_pv:.2f}")

    return ok

def test_cod_handoff():
    """Test 4: with a nonzero rate_pre_cod, delay changes the COD starting point.

    A longer delay means more pre-COD evolution has already happened by COD,
    so the operational trajectories (which both start from the COD state)
    differ from the zero-delay case even though rate_pre_cod/rate_post_cod are
    unchanged. This is the behavior the single-trajectory redesign fixes.
    """
    print("\n=== Test 4: COD handoff changes results with delay ===")

    grid_mix = _make_grid_mix(60, 40, rate_pre_cod=(0.05, 0.0), rate_post_cod=(0.10, 0.0))

    common = dict(
        energy_delivered_annual_mwh=1000.0,
        grid_mix=grid_mix,
        emission_intensities=INTENSITIES,
        societal_costs=SOCIETAL,
        project_lifetime=5,
        social_discount_rate=0.0,
    )

    r_no_delay = calculate_facilitated_emissions(delay_years=0, construction_years=0, **common)
    r_delay = calculate_facilitated_emissions(delay_years=10, construction_years=2, **common)

    ok = True
    if abs(r_no_delay.fac_emissions_noline_pv - r_delay.fac_emissions_noline_pv) < 1e-6:
        print("  FAIL delay should change the COD starting point (noline PV unchanged)")
        ok = False
    else:
        print(
            f"  OK   noline PV differs with delay: "
            f"{r_no_delay.fac_emissions_noline_pv:.2f} (no delay) vs "
            f"{r_delay.fac_emissions_noline_pv:.2f} (12yr COD)"
        )

    return ok

def main():
    results = []
    results.append(("Hand-calculated", test_hand_calculated()))
    results.append(("Zero displacement", test_zero_displacement()))
    results.append(("Discount sanity", test_discount_sanity()))
    results.append(("COD handoff", test_cod_handoff()))

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
