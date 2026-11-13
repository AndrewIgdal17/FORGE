import logging
import pathlib

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
from test.spec05_project import item, measured, project_changes

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


_SEND = "01_project_technical_details.terminals.sending"
_RECV = "01_project_technical_details.terminals.receiving"
_EXCEEDANCE = (
    "17_congestion_reductions.greenfield_congestion_reductions"
    ".constraints.average_exceedance"
)
_POLLUTANTS = ("co2e", "so2", "nox")
_NULL_PUBLISHED = (
    "congestion_benefit_pv",
    "conductor_loss_pv",
    "emissions_comp_cost_pv",
    "displacement_avoided_benefit_pv",
    "benefits_remedial_pv",
)


def _null_measurements():
    return measured(
        congestion_spread_per_mwh=None,
        hours_receiving_more_congested=None,
        hours_sending_more_congested=None,
        receiving_energy_value_per_mwh=None,
    )


def _run(changes: dict) -> dict:
    return forge.run_calculation(forge.resolve_inputs(changes))


def _margin_terminals() -> dict:
    return {
        f"{_SEND}.gea": "MISO_North",
        f"{_SEND}.egrid_subregion": "MROW",
        f"{_SEND}.state": "MN",
        f"{_RECV}.gea": "MISO_Central",
        f"{_RECV}.egrid_subregion": "SRMW",
        f"{_RECV}.state": "MO",
    }


def _end(gea: str, subregion: str, state: str, year: int) -> tuple[dict, dict]:
    so2, nox = egrid_rates(subregion)
    eps = {"co2e": lrmer_co2e(gea, year), "so2": so2, "nox": nox}
    cost = {
        "co2e": sc_co2_2025_usd_per_kg(year),
        "so2": criteria_damage_2025_usd_per_kg(state, "so2", year),
        "nox": criteria_damage_2025_usd_per_kg(state, "nox", year),
    }
    return eps, cost


def _margin_avoided_run(hours_forward: float, hours_reverse: float, utilization: float) -> dict:
    changes = project_changes(**{
        **_margin_terminals(),
        "01_project_technical_details.project.sending_source": "margin",
        "01_project_technical_details.timeline.project_lifetime": 1,
        "01_project_technical_details.project.line_utilization": utilization,
        _EXCEEDANCE: 100,
        **measured(
            congestion_spread_per_mwh=5,
            hours_receiving_more_congested=hours_forward,
            hours_sending_more_congested=hours_reverse,
            receiving_energy_value_per_mwh=30,
        ),
    })
    return _run(changes)


@pytest.fixture(scope="module")
def null_margin_ac():
    """Margin greenfield AC with every market measurement null."""
    changes = project_changes(**{
        "01_project_technical_details.project.ac_dc": "AC",
        "01_project_technical_details.project.capacity_mw": 1792,
        "01_project_technical_details.project.converter_type": "NA",
        "01_project_technical_details.project.number_of_converters": 0,
        "01_project_technical_details.project.sending_source": "margin",
        "01_project_technical_details.project.project_type": "greenfield",
        **_null_measurements(),
    })
    return _run(changes)


def test_acceptance_1_null_measurements_margin_ac(null_margin_ac):
    results = null_margin_ac
    congestion = item(results, "congestion_benefit")
    assert congestion["available"] is False
    assert congestion["value_pv"] is None
    assert congestion["value_nominal"] is None
    assert congestion["value_annual"] is None
    assert congestion["value_pv_wacc"] is None
    assert SPREAD in congestion["missing_inputs"]
    benefit = results["benefits"]["congestion"]
    assert benefit["congestion_benefit_pv"] is None
    assert benefit["congestion_benefit_nominal"] is None
    assert benefit["congestion_benefit_annual"] is None
    assert benefit["congestion_benefit_pv_wacc"] is None
    assert results["bcr"]["omitted"]["bcr_societal"] == [
        "avoided_emissions_benefit",
        "congestion_benefit",
        "emissions_comp",
        "line_loss_conductor",
    ]
    converter = item(results, "line_loss_converter")
    assert converter["available"] is True
    assert converter["value_pv"] == 0.0
    assert results["costs"]["line_loss"]["total_pv"] is None
    assert isinstance(results["bcr"]["bcr_societal"], float)
    avoided = results["benefits"]["avoided_emissions"]
    assert avoided["net_binding_hours"] is None
    assert isinstance(avoided["relief_mw"], (int, float))
    assert avoided["rates_used"]["sending"]["source"] == "margin"
    assert avoided["rates_used"]["receiving"]["gea"]
    avoided_item = item(results, "avoided_emissions_benefit")
    assert avoided_item["available"] is False
    assert HFWD in avoided_item["missing_inputs"]
    assert HREV in avoided_item["missing_inputs"]


def test_acceptance_2_nulls_are_not_zero(null_margin_ac):
    results = null_margin_ac
    congestion = results["benefits"]["congestion"]
    for key in (
        "congestion_benefit_annual",
        "congestion_benefit_nominal",
        "congestion_benefit_pv",
        "congestion_benefit_pv_wacc",
    ):
        assert congestion[key] is None
    assert congestion["streams"]["congestion_benefit"] is None

    line_loss = results["costs"]["line_loss"]
    for key in (
        "line_annual_cost",
        "line_nominal_total",
        "line_cost_pv",
        "line_cost_pv_wacc",
        "annual_cost",
        "total_nominal",
        "total_pv",
        "total_pv_wacc",
    ):
        assert line_loss[key] is None
    assert line_loss["streams"]["line_loss_conductor"] is None

    emissions = results["costs"]["emissions"]
    for key in (
        "total_nominal",
        "total_pv",
        "annual_cost",
        "emissions_comp_annual_values",
        "annual_kg",
        "damage_cost_per_kg",
    ):
        assert emissions[key] is None
    assert emissions["streams"]["emissions_comp"] is None

    avoided = results["benefits"]["avoided_emissions"]
    for key in (
        "avoided_emissions_pv",
        "avoided_emissions_nominal",
        "avoided_emissions_annual_values",
        "annual_kg_avoided",
    ):
        assert avoided[key] is None
    assert avoided["streams"]["avoided_emissions_benefit"] is None

    for taxonomy_id in (
        "congestion_benefit",
        "line_loss_conductor",
        "emissions_comp",
        "avoided_emissions_benefit",
    ):
        row = item(results, taxonomy_id)
        assert row["value_pv"] is None
        assert row["value_nominal"] is None
        assert row["value_pv_wacc"] is None
        assert row["stream"] is None

    for key in _NULL_PUBLISHED:
        assert results["bcr"][key] is None
        assert results["csv_equivalent"][key] is None
    for key in ("displacement_avoided_benefit_pv", "benefits_remedial_pv"):
        assert results["summary"][key] is None
    assert results["bcr"]["benefits_remedial_pv"] is None


def test_acceptance_3_measured_zero():
    changes = project_changes(**{
        **_margin_terminals(),
        "01_project_technical_details.project.sending_source": "margin",
        "01_project_technical_details.timeline.project_lifetime": 1,
        **measured(
            congestion_spread_per_mwh=0,
            hours_receiving_more_congested=0,
            hours_sending_more_congested=0,
            receiving_energy_value_per_mwh=30,
        ),
    })
    resolved = forge.resolve_inputs(changes)
    results = forge.run_calculation(resolved)
    congestion = item(results, "congestion_benefit")
    assert congestion["available"] is True
    assert congestion["value_pv"] == pytest.approx(0.0)
    avoided_item = item(results, "avoided_emissions_benefit")
    assert avoided_item["available"] is True
    assert avoided_item["value_pv"] == pytest.approx(0.0)
    avoided = results["benefits"]["avoided_emissions"]
    assert avoided["avoided_emissions_annual_values"] == pytest.approx([0.0])
    for pollutant in _POLLUTANTS:
        assert avoided["annual_kg_avoided"][pollutant] == pytest.approx([0.0])

    year = calendar_year(results["derived_parameters"]["t_cod"])
    eps_snd, c_snd = _end("MISO_North", "MROW", "MN", year)
    fraction = resolved["16_emissions_reductions"]["emissions_reductions"]["compensation_percent"]
    e_comp = fraction * results["costs"]["line_loss"]["total_loss_mwh_yr"]
    assert e_comp != 0
    expected = e_comp * sum(eps_snd[name] * c_snd[name] for name in _POLLUTANTS)
    emissions = results["costs"]["emissions"]
    assert emissions["availability"]["emissions_comp"]["available"] is True
    assert emissions["emissions_comp_annual_values"] == pytest.approx([expected])
    for omitted in results["bcr"]["omitted"].values():
        assert omitted == []


def test_acceptance_4_margin_avoided_hours():
    forward = _margin_avoided_run(3000, 1000, 0.67)
    other = _margin_avoided_run(3000, 1000, 0.2)
    assert forward["derived_parameters"]["relief_mw"] == 100
    assert forward["derived_parameters"]["energy_delivered_annual_mwh_yr"] != (
        other["derived_parameters"]["energy_delivered_annual_mwh_yr"]
    )
    avoided = forward["benefits"]["avoided_emissions"]
    assert avoided["relief_mw"] == 100
    assert avoided["net_binding_hours"] == 2000
    factor = 100 * 2000
    year = calendar_year(forward["derived_parameters"]["t_cod"])
    eps_snd, c_snd = _end("MISO_North", "MROW", "MN", year)
    eps_rcv, c_rcv = _end("MISO_Central", "SRMW", "MO", year)
    for pollutant in _POLLUTANTS:
        assert avoided["annual_kg_avoided"][pollutant] == pytest.approx(
            [factor * (eps_rcv[pollutant] - eps_snd[pollutant])]
        )
    dollars = factor * sum(
        eps_rcv[name] * c_rcv[name] - eps_snd[name] * c_snd[name]
        for name in _POLLUTANTS
    )
    assert avoided["avoided_emissions_annual_values"] == pytest.approx([dollars])
    assert other["benefits"]["avoided_emissions"] == avoided


def test_acceptance_5_reverse_hours_negate_check_4():
    forward = _margin_avoided_run(3000, 1000, 0.67)
    reverse = _margin_avoided_run(1000, 3000, 0.67)
    forward_avoided = forward["benefits"]["avoided_emissions"]
    reverse_avoided = reverse["benefits"]["avoided_emissions"]
    assert reverse_avoided["net_binding_hours"] == -2000
    assert item(reverse, "avoided_emissions_benefit")["available"] is True
    for pollutant in _POLLUTANTS:
        assert reverse_avoided["annual_kg_avoided"][pollutant] == pytest.approx(
            [-value for value in forward_avoided["annual_kg_avoided"][pollutant]]
        )
    assert reverse_avoided["avoided_emissions_annual_values"] == pytest.approx(
        [-value for value in forward_avoided["avoided_emissions_annual_values"]]
    )
    assert reverse_avoided["avoided_emissions_pv"] == pytest.approx(
        -forward_avoided["avoided_emissions_pv"]
    )
    assert reverse_avoided["avoided_emissions_nominal"] == pytest.approx(
        -forward_avoided["avoided_emissions_nominal"]
    )


def _dedicated_null(**measures):
    block = {
        "congestion_spread_per_mwh": None,
        "hours_receiving_more_congested": None,
        "hours_sending_more_congested": None,
        "receiving_energy_value_per_mwh": None,
    }
    block.update(measures)
    rate = "01_project_technical_details.project.dedicated_resource.emission_rate_kg_per_mwh"
    return project_changes(**{
        "01_project_technical_details.project.sending_source": "dedicated",
        "01_project_technical_details.project.dedicated_resource.contract_price_per_mwh": 0.0,
        f"{rate}.co2e": 0.0,
        f"{rate}.so2": 0.0,
        f"{rate}.nox": 0.0,
        "01_project_technical_details.timeline.project_lifetime": 1,
        **measured(**block),
    })


def test_acceptance_7_dedicated_null_measurements():
    results = _run(_dedicated_null())
    emissions = results["costs"]["emissions"]
    assert emissions["availability"]["emissions_comp"]["available"] is True
    assert emissions["emissions_comp_annual_values"] == pytest.approx([0.0])
    congestion = item(results, "congestion_benefit")
    assert congestion["available"] is True
    assert congestion["value_pv"] == pytest.approx(0.0)
    e_deliv = results["derived_parameters"]["energy_delivered_annual_mwh_yr"]
    assert e_deliv > 0
    year = calendar_year(results["derived_parameters"]["t_cod"])
    eps_rcv, c_rcv = _end("WestConnect_South", "AZNM", "AZ", year)
    expected = e_deliv * sum(eps_rcv[name] * c_rcv[name] for name in _POLLUTANTS)
    avoided = results["benefits"]["avoided_emissions"]
    assert item(results, "avoided_emissions_benefit")["available"] is True
    assert avoided["energy_delivered_annual_mwh_yr"] == e_deliv
    assert avoided["avoided_emissions_annual_values"] == pytest.approx([expected])

    second = _run(_dedicated_null(receiving_energy_value_per_mwh=None))
    assert item(second, "delivered_energy_benefit")["available"] is False
    assert item(second, "line_loss_conductor")["available"] is False
    used = results["benefits"]["avoided_emissions"]["rates_used"]
    assert used["sending"]["source"] == "dedicated"
    assert used["receiving"]["gea"] == "WestConnect_South"
    assert used["sending"]["gea"] == "WestConnect_South"


def test_acceptance_8_energy_value_only():
    changes = project_changes(**{
        f"{_SEND}.gea": "CAISO",
        f"{_SEND}.egrid_subregion": "CAMX",
        f"{_SEND}.state": "CA",
        f"{_RECV}.gea": "ERCOT",
        f"{_RECV}.egrid_subregion": "ERCT",
        f"{_RECV}.state": "TX",
        "01_project_technical_details.project.sending_source": "margin",
        **measured(
            congestion_spread_per_mwh=None,
            hours_receiving_more_congested=None,
            hours_sending_more_congested=None,
            receiving_energy_value_per_mwh=30,
        ),
    })
    results = _run(changes)
    conductor = item(results, "line_loss_conductor")
    delivered = item(results, "delivered_energy_benefit")
    assert conductor["available"] is True
    assert isinstance(conductor["value_pv"], float)
    assert delivered["available"] is True
    assert delivered["value_pv"] == pytest.approx(0.0)
    assert item(results, "congestion_benefit")["available"] is False
    assert item(results, "avoided_emissions_benefit")["available"] is False
    assert item(results, "emissions_comp")["available"] is False


def run_margin_all_null(*, delay_years: int, baseline_delay_years: int) -> dict:
    """Margin AC, four null measurements, acres 0, MN/MO terminals."""
    changes = project_changes(**{
        "01_project_technical_details.project.ac_dc": "AC",
        "01_project_technical_details.project.capacity_mw": 1792,
        "01_project_technical_details.project.converter_type": "NA",
        "01_project_technical_details.project.number_of_converters": 0,
        "01_project_technical_details.project.sending_source": "margin",
        "01_project_technical_details.project.project_type": "greenfield",
        "01_project_technical_details.timeline.delay_years": delay_years,
        "01_project_technical_details.timeline.baseline_delay_years": baseline_delay_years,
        **_margin_terminals(),
        **_null_measurements(),
    })
    return {"results": _run(changes)}


def test_acceptance_13_delay_null_measurements():
    entered = run_margin_all_null(delay_years=4, baseline_delay_years=0)
    block = entered["results"]["delay_comparison"]
    assert block["delay_cost_cong"] is None
    assert block["delay_cost_avoid"] is None
    assert block["delay_cost_forgone"] is None
    assert block["omitted"]["delay_cost_forgone"] == [
        "avoided_emissions_benefit",
        "congestion_benefit",
    ]
    assert isinstance(block["delta_nb_delay"], float)
    assert "congestion_benefit" in block["omitted"]["delta_nb_delay"]

    same = run_margin_all_null(delay_years=0, baseline_delay_years=0)
    same_block = same["results"]["delay_comparison"]
    assert same_block["delay_cost_cong"] is None
    assert same_block["delta_nb_delay"] == 0.0
    assert same_block["omitted"]["delta_nb_delay"] == same["results"]["bcr"]["omitted"]["net_benefit_pv"]


ROOT = pathlib.Path(__file__).resolve().parents[1]
SURFACES = [
    ROOT / "forge/scenarios",
    ROOT / "forge/yamls",
    ROOT / "forge/scripts/io/input_metadata.py",
    ROOT / "forge/scripts/io/yaml_loaders.py",
    ROOT / "forge/scripts/runners",
    ROOT / "test/spec05_project.py",
]


def test_acceptance_15_bundled_inputs_round_trip_without_old_paths():
    forbidden = ("average_congestion_price", "value_of_load_per_mwh")
    for surface in SURFACES:
        paths = [surface] if surface.is_file() else surface.rglob("*")
        for path in paths:
            if path.suffix not in {".py", ".yaml", ".forge"}:
                continue
            text = path.read_text()
            if path.suffix == ".forge":
                inputs = text.split('"results"', 1)[0]
                assert not any(token in inputs for token in forbidden)
            else:
                assert not any(token in text for token in forbidden)
    # round-trip is the existing test_each_case_study_round_trips_through_changes
