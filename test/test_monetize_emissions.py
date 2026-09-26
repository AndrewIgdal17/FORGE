"""Tests for shared emissions monetization function."""


def test_monetize_annual_emissions_basic():
    from scripts.calc.emissions import monetize_annual_emissions

    emissions = {"co2": 1000.0, "sox": 50.0, "nox": 30.0}
    societal_costs = {
        "co2": {"base_cost_per_kg": 0.05, "growth_rate": 0.02},
        "sox": {"base_cost_per_kg": 3.00, "growth_rate": 0.01},
        "nox": {"base_cost_per_kg": 2.00, "growth_rate": 0.01},
    }
    # year_idx=0: cost = 1000*0.05 + 50*3.00 + 30*2.00 = 50+150+60 = 260
    result = monetize_annual_emissions(emissions, societal_costs, year_idx=0)
    assert abs(result - 260.0) < 0.01


def test_monetize_with_growth():
    from scripts.calc.emissions import monetize_annual_emissions

    emissions = {"co2": 1000.0}
    societal_costs = {"co2": {"base_cost_per_kg": 0.05, "growth_rate": 0.10}}
    # year_idx=5: cost = 1000 * 0.05 * (1.1)^5 = 50 * 1.61051 = 80.5255
    result = monetize_annual_emissions(emissions, societal_costs, year_idx=5)
    assert abs(result - 80.5255) < 0.01


def test_monetize_accepts_yaml_flat_keys():
    from scripts.calc.emissions import monetize_annual_emissions

    emissions = {"co2": 1000.0, "sox": 50.0, "nox": 30.0}
    societal_costs = {
        "co2_cost_per_kg": 0.05,
        "co2_cost_annual_growth": 0.02,
        "sox_cost_per_kg": 3.00,
        "sox_cost_annual_growth": 0.01,
        "nox_cost_per_kg": 2.00,
        "nox_cost_annual_growth": 0.01,
    }
    result = monetize_annual_emissions(emissions, societal_costs, year_idx=0)
    assert abs(result - 260.0) < 0.01


def test_monetize_skips_pollutant_without_cost():
    from scripts.calc.emissions import monetize_annual_emissions

    emissions = {"co2": 1000.0, "unknown": 999.0}
    societal_costs = {"co2": {"base_cost_per_kg": 0.05, "growth_rate": 0.0}}
    result = monetize_annual_emissions(emissions, societal_costs, year_idx=0)
    assert abs(result - 50.0) < 0.01
