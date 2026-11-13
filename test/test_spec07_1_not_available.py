import logging

import pytest
import forge
from forge.emissions_data import (
    calendar_year,
    criteria_damage_2025_usd_per_kg,
    egrid_rates,
    lrmer_co2e,
    sc_co2_2025_usd_per_kg,
)
from forge.errors import InvalidInputs, UnknownInputPath
from forge.scripts.calc.bcr_calculator import compute_all_bcrs, print_bcr_summary
from forge.scripts.calc.bcr_trajectory import compute_trajectory
from forge.scripts.io.taxonomy_adapters import TaxonomyResult
from test.spec05_project import measured, project_changes

SPREAD = "01_project_technical_details.market_measurements.congestion_spread_per_mwh"
HFWD = "01_project_technical_details.market_measurements.hours_receiving_more_congested"
HREV = "01_project_technical_details.market_measurements.hours_sending_more_congested"
VREC = "01_project_technical_details.market_measurements.receiving_energy_value_per_mwh"

def _changes(**measures):
    block = {
        "congestion_spread_per_mwh": None,
        "hours_receiving_more_congested": None,
        "hours_sending_more_congested": None,
        "receiving_energy_value_per_mwh": None,
    }
    block.update(measures)
    return {
        "01_project_technical_details.market_measurements.congestion_spread_per_mwh": block["congestion_spread_per_mwh"],
        "01_project_technical_details.market_measurements.hours_receiving_more_congested": block["hours_receiving_more_congested"],
        "01_project_technical_details.market_measurements.hours_sending_more_congested": block["hours_sending_more_congested"],
        "01_project_technical_details.market_measurements.receiving_energy_value_per_mwh": block["receiving_energy_value_per_mwh"],
    }

CASES = [
    {"hours_receiving_more_congested": 8761, "hours_sending_more_congested": 0, "congestion_spread_per_mwh": 1, "receiving_energy_value_per_mwh": 30},
    {"congestion_spread_per_mwh": 1.5, "receiving_energy_value_per_mwh": 30},
    {"congestion_spread_per_mwh": 1.5, "hours_receiving_more_congested": 0, "hours_sending_more_congested": 0, "receiving_energy_value_per_mwh": 30},
    {"congestion_spread_per_mwh": 0, "hours_receiving_more_congested": 10, "hours_sending_more_congested": 0, "receiving_energy_value_per_mwh": 30},
    {"congestion_spread_per_mwh": -1, "hours_receiving_more_congested": 0, "hours_sending_more_congested": 0, "receiving_energy_value_per_mwh": 30},
    {"congestion_spread_per_mwh": 1, "hours_receiving_more_congested": 9000, "hours_sending_more_congested": 0, "receiving_energy_value_per_mwh": 30},
    {"congestion_spread_per_mwh": 1, "hours_receiving_more_congested": 10.5, "hours_sending_more_congested": 0, "receiving_energy_value_per_mwh": 30},
    {"congestion_spread_per_mwh": 1, "hours_receiving_more_congested": 10, "hours_sending_more_congested": 0},
]

def test_acceptance_9_measurement_rules_are_invalid_inputs():
    for measures in CASES:
        with pytest.raises(InvalidInputs) as resolved:
            forge.resolve_inputs(_changes(**measures))
        assert not isinstance(resolved.value, UnknownInputPath)
        document = forge.get_defaults_template()
        acres = document["02_project_physical_details"]["terrain"]["protected_area_acres"]
        for key in acres:
            acres[key] = 0.0
        document["01_project_technical_details"]["market_measurements"].update(measures)
        with pytest.raises(InvalidInputs) as calculated:
            forge.run_calculation(document)
        assert "market_measurements" in str(calculated.value)
    missing = forge.missing_required_inputs({})
    assert not any("market_measurements" in item["path"] for item in missing)


def test_acceptance_14_results_schema_is_2():
    info = forge.calculator_info()
    assert info["results_schema"] == 2


def test_not_available_item_keeps_null_dollars():
    from forge.scripts.io.taxonomy_adapters import adapt_all_results
    congestion = {
        "availability": {
            "congestion_benefit": {
                "available": False,
                "missing_inputs": (
                    "01_project_technical_details.market_measurements.congestion_spread_per_mwh",
                ),
            }
        },
        "congestion_benefit_pv": None,
        "congestion_benefit_nominal": None,
        "congestion_benefit_annual": None,
        "congestion_benefit_pv_wacc": None,
        "delivered_benefit_pv": 0.0,
        "delivered_benefit_nominal": 0.0,
        "delivered_benefit_annual": 0.0,
        "delivered_benefit_pv_wacc": 0.0,
        "streams": {
            "congestion_benefit": None,
            "delivered_energy_benefit": [0.0],
        },
    }
    items = adapt_all_results({"benefits": {"congestion": congestion}, "costs": {}})
    benefit = next(item for item in items if item.taxonomy_id == "congestion_benefit")
    assert benefit.available is False
    assert benefit.value_pv is None
    assert benefit.value_nominal is None


# Spec table: trajectory key -> bcr.omitted source. Nine ratios and nine NPVs.
TRAJECTORY_OMITTED = {
    "bcr_societal": "bcr_societal",
    "npv_societal": "net_benefit_pv",
    "bcr_utility": "bcr_utility",
    "npv_utility": "net_benefit_utility_pv",
    "bcr_ratepayer": "bcr_ratepayer",
    "npv_ratepayer": "net_benefit_ratepayer_pv",
    "bcr_excl_avoided_emissions": "bcr_excluding_avoided_emissions",
    "npv_excl_avoided_emissions": "net_benefit_excluding_avoided_emissions_pv",
    "bcr_excl_emissions_costs": "bcr_excluding_emissions",
    "npv_excl_emissions_costs": "net_benefit_excluding_emissions_pv",
    "bcr_excl_all_emissions": "bcr_excluding_avoided_emissions_and_emissions",
    "npv_excl_all_emissions": "net_benefit_excluding_avoided_emissions_and_emissions_pv",
    "bcr_excl_outage": "bcr_excluding_outage_risk",
    "npv_excl_outage": "net_benefit_excluding_outage_risk_pv",
    "bcr_excl_wildfire": "bcr_excluding_wildfire_risk",
    "npv_excl_wildfire": "net_benefit_excluding_wildfire_risk_pv",
    "bcr_excl_wf_out": "bcr_excluding_wildfire_risk_and_outage_risk",
    "npv_excl_wf_out": "net_benefit_excluding_wildfire_risk_and_outage_risk_pv",
}

CUMULATIVE_TO_BCR = {
    "cum_C_hard": "hard_costs_pv",
    "cum_C_soft": "soft_costs_pv",
    "cum_C_risk": "risk_costs_pv",
    "cum_C_emissions": "emissions_costs_pv",
    "cum_C_total": "total_costs_pv",
    "cum_B_remedial": "benefits_remedial_pv",
    "cum_B_enabling": "benefits_enabling_pv",
    "cum_B_avoided_emissions": "benefits_avoided_emissions_pv",
    "cum_B_total": "total_benefits_pv",
}


def _partial_items():
    """Avoided emissions and congestion are not available. Converter is an available 0."""
    unavailable = ("avoided_emissions_benefit", "congestion_benefit")
    items = [
        TaxonomyResult(
            taxonomy_id,
            value_pv=None,
            value_nominal=None,
            value_pv_wacc=None,
            stream=None,
            available=False,
        )
        for taxonomy_id in unavailable
    ]
    items.append(
        TaxonomyResult(
            "line_loss_converter",
            value_pv=0.0,
            value_nominal=0.0,
            value_pv_wacc=0.0,
            stream=[0.0, 0.0, 0.0],
            available=True,
        )
    )
    return items


@pytest.fixture
def partial_items():
    return _partial_items()


@pytest.fixture
def bcr(partial_items):
    return compute_all_bcrs(partial_items)


def test_acceptance_11_exclusion_and_perspective_sums(bcr):
    assert "avoided_emissions_benefit" not in bcr["omitted"]["bcr_excluding_avoided_emissions"]
    assert bcr["omitted"]["bcr_excluding_avoided_emissions"] == ["congestion_benefit"]
    assert bcr["omitted"]["bcr_societal"] == [
        "avoided_emissions_benefit",
        "congestion_benefit",
    ]
    assert bcr["omitted"]["bcr_utility"] == []
    assert "energy_losses_pv" not in bcr["omitted"]
    assert bcr["energy_losses_pv"] == 0.0
    assert bcr["benefits_remedial_pv"] is None
    assert bcr["bcr_ratepayer"] is None or isinstance(bcr["bcr_ratepayer"], float)
    assert bcr["bcr_ratepayer"] is None
    assert bcr["bcr_utility"] is not None


def test_energy_losses_keep_available_zero_when_conductor_is_unavailable():
    bcr = compute_all_bcrs([
        TaxonomyResult(
            "line_loss_conductor",
            value_pv=None,
            value_nominal=None,
            value_pv_wacc=None,
            available=False,
        ),
        TaxonomyResult(
            "line_loss_converter",
            value_pv=0.0,
            value_nominal=0.0,
            value_pv_wacc=0.0,
            available=True,
        ),
    ])
    assert bcr["energy_losses_pv"] == 0.0
    assert bcr["conductor_loss_pv"] is None
    assert bcr["converter_loss_pv"] == 0.0
    assert "energy_losses_pv" not in bcr["omitted"]


def _trajectory_inputs():
    return {
        "01_project_technical_details": {
            "timeline": {
                "delay_years": 1,
                "construction_years": 1,
                "project_lifetime": 1,
            }
        }
    }


def test_acceptance_12_trajectory_omitted_matches_bcr(bcr, partial_items):
    assert len(TRAJECTORY_OMITTED) == 18
    results = {
        "bcr": bcr,
        "taxonomy_results": partial_items,
        "derived_parameters": {
            "social_discount_rate": 0.0,
            "wacc_real": 0.0,
        },
    }
    trajectory = compute_trajectory(results, _trajectory_inputs())
    assert isinstance(trajectory, list)
    assert trajectory
    assert results["trajectory_omitted"] == {
        key: bcr["omitted"][source] for key, source in TRAJECTORY_OMITTED.items()
    }
    final = trajectory[-1]
    for traj_key, bcr_key in CUMULATIVE_TO_BCR.items():
        actual = final[traj_key]
        expected = bcr[bcr_key]
        if actual is not None and expected is not None:
            assert actual == pytest.approx(expected, abs=0.01)
    assert all(row["pv_B_remedial"] is None for row in trajectory)


def test_print_bcr_summary_prints_not_available_for_none(caplog):
    with caplog.at_level(logging.INFO, logger="forge.scripts.calc.bcr_calculator"):
        print_bcr_summary({
            "total_benefits_pv": None,
            "total_costs_pv": None,
            "bcr_societal": None,
            "bcr_utility": None,
            "bcr_ratepayer": None,
            "net_benefit_pv": None,
        })
    messages = [record.message for record in caplog.records]
    benefits = next(message for message in messages if message.startswith("  Total Benefits:"))
    societal = next(message for message in messages if "Societal BCR:" in message)
    net = next(message for message in messages if message.startswith("  Net Benefit (PV):"))
    assert "not available" in benefits and "$" not in benefits
    assert "not available" in societal and "0.000" not in societal
    assert "not available" in net and "$" not in net


OLD = [
    "17_congestion_reductions.greenfield_congestion_reductions.prices.average_congestion_price",
    "17_congestion_reductions.incremental_congestion_reductions.prices.average_congestion_price",
    "01_project_technical_details.project.value_of_load_per_mwh",
]


def test_acceptance_10_removed_paths_and_absent_block():
    for path in OLD:
        with pytest.raises(UnknownInputPath):
            forge.resolve_inputs({path: 1})
    listed = forge.missing_required_inputs({})
    assert not any("market_measurements" in item["path"] for item in listed)
    document = forge.get_defaults_template()
    # resolve_inputs still rejects a bare template for acres, capacity, flow,
    # and terminals. Fill those, then drop the measurement block.
    acres = document["02_project_physical_details"]["terrain"]["protected_area_acres"]
    for key in acres:
        acres[key] = 0.0
    document["01_project_technical_details"]["project"]["capacity_mw"] = 500
    document["17_congestion_reductions"]["greenfield_congestion_reductions"]["constraints"]["flow_factor"] = 0.0
    for end in ("sending", "receiving"):
        document["01_project_technical_details"]["terminals"][end] = {
            "gea": "CAISO",
            "egrid_subregion": "AZNM",
            "state": "AZ",
        }
    document["01_project_technical_details"].pop("market_measurements", None)
    changes = forge.diff_changes(document)
    resolved = forge.resolve_inputs(changes)
    block = resolved["01_project_technical_details"]["market_measurements"]
    assert block == {
        "congestion_spread_per_mwh": None,
        "hours_receiving_more_congested": None,
        "hours_sending_more_congested": None,
        "receiving_energy_value_per_mwh": None,
    }


def test_calculate_summary_does_not_add_none():
    from forge.scripts.io.json_output_manager import JSONOutputManager

    manager = JSONOutputManager.__new__(JSONOutputManager)
    manager.costs = {
        "line_loss": {"total_pv": None, "total_nominal": None},
        "emissions": {"total_pv": 0, "total_nominal": 0},
    }
    manager.summary = {}
    manager.calculate_summary()
    assert manager.summary["total_energy_emissions_pv"] is None
    assert manager.summary["total_energy_emissions_nominal"] is None
    assert manager.summary["total_capital_pv"] == 0


def test_acceptance_6_margin_loss_split():
    """One operating year, split 0.9 sending / 0.1 receiving at loaded rates."""
    send = "01_project_technical_details.terminals.sending"
    recv = "01_project_technical_details.terminals.receiving"
    changes = project_changes(**{
        f"{send}.gea": "MISO_North",
        f"{send}.egrid_subregion": "MROW",
        f"{send}.state": "MN",
        f"{recv}.gea": "MISO_Central",
        f"{recv}.egrid_subregion": "SRMW",
        f"{recv}.state": "MO",
        "01_project_technical_details.project.sending_source": "margin",
        "01_project_technical_details.timeline.project_lifetime": 1,
        **measured(
            congestion_spread_per_mwh=5.0,
            hours_receiving_more_congested=2000,
            hours_sending_more_congested=876,
            receiving_energy_value_per_mwh=30,
        ),
    })
    resolved = forge.resolve_inputs(changes)
    results = forge.run_calculation(resolved)
    emissions = results["costs"]["emissions"]
    assert emissions["rates_used"]["share_receiving"] == 0.1

    year = calendar_year(results["derived_parameters"]["t_cod"])
    eps_snd_co2e = lrmer_co2e("MISO_North", year)
    eps_rcv_co2e = lrmer_co2e("MISO_Central", year)
    eps_snd_so2, eps_snd_nox = egrid_rates("MROW")
    eps_rcv_so2, eps_rcv_nox = egrid_rates("SRMW")
    c_co2e = sc_co2_2025_usd_per_kg(year)
    c_so2_snd = criteria_damage_2025_usd_per_kg("MN", "so2", year)
    c_nox_snd = criteria_damage_2025_usd_per_kg("MN", "nox", year)
    c_so2_rcv = criteria_damage_2025_usd_per_kg("MO", "so2", year)
    c_nox_rcv = criteria_damage_2025_usd_per_kg("MO", "nox", year)
    snd_bundle = (
        eps_snd_co2e * c_co2e
        + eps_snd_so2 * c_so2_snd
        + eps_snd_nox * c_nox_snd
    )
    rcv_bundle = (
        eps_rcv_co2e * c_co2e
        + eps_rcv_so2 * c_so2_rcv
        + eps_rcv_nox * c_nox_rcv
    )
    fraction = resolved["16_emissions_reductions"]["emissions_reductions"]["compensation_percent"]
    e_comp = fraction * results["costs"]["line_loss"]["total_loss_mwh_yr"]
    assert e_comp != 0
    expected = e_comp * (0.9 * snd_bundle + 0.1 * rcv_bundle)
    assert emissions["emissions_comp_annual_values"] == pytest.approx([expected])
    eps_snd = {"co2e": eps_snd_co2e, "so2": eps_snd_so2, "nox": eps_snd_nox}
    eps_rcv = {"co2e": eps_rcv_co2e, "so2": eps_rcv_so2, "nox": eps_rcv_nox}
    for pollutant in ("co2e", "so2", "nox"):
        assert emissions["annual_kg"]["sending"][pollutant][0] == pytest.approx(
            e_comp * 0.9 * eps_snd[pollutant]
        )
        assert emissions["annual_kg"]["receiving"][pollutant][0] == pytest.approx(
            e_comp * 0.1 * eps_rcv[pollutant]
        )
