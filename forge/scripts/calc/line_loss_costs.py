# Date: 2025-10-27
# Description: This script uses the energy_losses script to calculate the line losses for
# a reconductoring project and its original state. Then it calculates each years
# lossbenefit = (Lbase(t) - L reconductoring(t)) * price_per_mwh
#

from __future__ import annotations

import logging

from dataclasses import dataclass

from forge.scripts.utils.smart_output import SmartOutputManager

# Standard library imports
import yaml

# Local utility imports
from forge.scripts.calc.energy_losses import net_energy_losses
from forge.scripts.utils.streams import growing, pv, undiscounted
from forge.scripts.utils.calculation_utils import to_percent
from forge.scripts.utils.smart_loaders import (
    load_financing_details,
    load_project_technical_details as load_project_technical_details_centralized,
    get_project_data_raw,
    load_congestion_reductions,
)
from forge.scripts.utils.run_context import get_run_context

logger = logging.getLogger(__name__)

_ENERGY_PATH = (
    "01_project_technical_details.market_measurements.receiving_energy_value_per_mwh"
)


@dataclass
class LineLossProjectDetails:
    """Project details specific to line loss cost calculations."""

    construction_type: str
    ac_dc: str
    capacity_mw: int
    conductor_type: str
    number_of_converters: int
    converter_type: str
    line_utilization_percent: float
    value_of_load: float | None
    wacc_real: float
    benefit_price_escalation_real: float
    project_type: str  # "greenfield" | "reconductoring" | "rebuild"
    delay_years: float
    construction_years: int
    project_lifetime: int

def load_project_details() -> LineLossProjectDetails:
    """
    Load project technical details with line_loss_costs specific fields.

    This function loads comprehensive project details from the technical details YAML file,
    including the standard project specifications used for line loss cost calculations.

    Args:
        None (reads from YAML file)

    Returns:
        LineLossProjectDetails: Dataclass containing all project details for line loss calculations
            - construction_type: Type of construction (e.g., "Overhead", "Underground")
            - ac_dc: "AC" or "DC" designation
            - capacity_mw: Line capacity in MW
            - conductor_type: Type of conductor used
            - number_of_converters: Number of converter stations (DC projects only, else 0)
            - converter_type: Converter type (for DC projects) or "NA" for AC
            - line_utilization_percent: Line utilization as decimal (0-1)
            - value_of_load: Value of load in $/MWh
            - wacc_real: Real WACC for present value of thermal line loss cost (market-tracked)
            - benefit_price_escalation_real: Real annual escalation rate applied to v_load
              for welfare consistency with the benefit-of-delivered-energy valuation (g_benefit)
            - project_type: "greenfield" | "reconductoring" | "rebuild"
            - delay_years: Number of years of project delay
            - construction_years: Number of years of construction
            - project_lifetime: Project operational lifetime in years

    Raises:
        FileNotFoundError: When project technical details YAML is not found
        ValueError: When YAML file is empty or invalid
        KeyError: When required keys are missing from the YAML structure
    """
    try:
        # Load from centralized loader (returns ProjectTechnicalDetails dataclass)
        from forge.scripts.io.yaml_loaders import ProjectTechnicalDetails

        project_details_obj: ProjectTechnicalDetails = (
            load_project_technical_details_centralized()
        )

        # Extract values from dataclass
        construction_type = project_details_obj.construction_type
        ac_dc = project_details_obj.ac_dc
        capacity_mw = project_details_obj.capacity_mw
        conductor_type = project_details_obj.conductor_type
        converter_type = project_details_obj.converter_type
        line_utilization_percent = project_details_obj.line_utilization
        project_type = project_details_obj.project_type
        delay_years = project_details_obj.delay_years
        construction_years = project_details_obj.construction_years
        project_lifetime = project_details_obj.project_lifetime
        _converter_loss_percentage = project_details_obj.converter_loss_percentage

        # Get additional fields not in centralized loader
        project_details = get_project_data_raw()
        if not project_details:
            raise ValueError("Project technical details file is empty or invalid")
        if "project" not in project_details:
            raise KeyError("Missing 'project' key in project technical details")
        project = project_details["project"]

        measurements = project_details.get("market_measurements") or {}
        if not isinstance(measurements, dict):
            measurements = {}
        raw_energy_value = measurements.get("receiving_energy_value_per_mwh")
        value_of_load = None if raw_energy_value is None else float(raw_energy_value)
        financing = load_financing_details()
        wacc_real = financing.wacc_real
        congestion_params = load_congestion_reductions()
        benefit_price_escalation_real = congestion_params.benefit_price_escalation_real

        ctx = get_run_context()
        if ctx is None:
            raise RuntimeError(
                f"{__name__} requires a RunContext. Run via forge.py or set up "
                "RunContext in your test fixture."
            )
        number_of_converters = ctx.number_of_converters
    except FileNotFoundError:
        raise FileNotFoundError(f"Project technical details not found")
    except yaml.YAMLError as e:
        raise ValueError(f"Error parsing project technical details: {e}")
    except KeyError as e:
        raise KeyError(f"Missing required key in project technical details: {e}")

    return LineLossProjectDetails(
        construction_type=construction_type,
        ac_dc=ac_dc,
        capacity_mw=capacity_mw,
        conductor_type=conductor_type,
        number_of_converters=number_of_converters,
        converter_type=converter_type,
        line_utilization_percent=line_utilization_percent,
        value_of_load=value_of_load,
        wacc_real=wacc_real,
        benefit_price_escalation_real=benefit_price_escalation_real,
        project_type=project_type,
        delay_years=delay_years,
        construction_years=construction_years,
        project_lifetime=project_lifetime,
    )

def _component_money(
    annual: float | None,
    growth: float,
    lifetime: int,
    social_discount_rate: float,
    wacc_real: float,
    t_cod: int,
    horizon: int,
) -> dict:
    """One loss component. A null annual is not available."""
    if annual is None:
        return {
            "annual": None,
            "stream": None,
            "nominal": None,
            "pv": None,
            "pv_wacc": None,
        }
    stream = growing(annual, growth, t_cod, lifetime, horizon)
    return {
        "annual": annual,
        "stream": stream,
        "nominal": undiscounted(stream),
        "pv": pv(stream, social_discount_rate),
        "pv_wacc": pv(stream, wacc_real),
    }


def _priced_losses(
    line_mwh: float,
    converter_mwh: float,
    price: float | None,
    growth: float,
    lifetime: int,
    social_discount_rate: float,
    wacc_real: float,
    t_cod: int,
    horizon: int,
    converter_applies: bool = True,
) -> dict:
    """Conductor and converter dollars from the receiving-end energy value.

    Conductor dollars are not available when that value is null. Converter
    dollars are not available only when it is null and converter MWh is above
    0; a line with no converter loss is 0 and available. The four totals are
    null when either component is not available.
    """
    if price is None:
        line_annual = None
        converter_annual = (
            None if converter_applies and converter_mwh != 0 else 0.0
        )
    else:
        line_annual = line_mwh * price
        converter_annual = converter_mwh * price
    line = _component_money(
        line_annual, growth, lifetime, social_discount_rate, wacc_real, t_cod, horizon
    )
    converter = _component_money(
        converter_annual, growth, lifetime, social_discount_rate, wacc_real, t_cod, horizon
    )
    line_available = line["annual"] is not None
    converter_available = converter["annual"] is not None
    if line_available and converter_available:
        annual_cost = line["annual"] + converter["annual"]
        total_nominal = line["nominal"] + converter["nominal"]
        total_pv = line["pv"] + converter["pv"]
        total_pv_wacc = line["pv_wacc"] + converter["pv_wacc"]
    else:
        annual_cost = None
        total_nominal = None
        total_pv = None
        total_pv_wacc = None
    return {
        "annual_cost": annual_cost,
        "line_annual_cost": line["annual"],
        "converter_annual_cost": converter["annual"],
        "streams": {
            "line_loss_conductor": line["stream"],
            "line_loss_converter": converter["stream"],
        },
        "line_nominal_total": line["nominal"],
        "converter_nominal_total": converter["nominal"],
        "total_nominal": total_nominal,
        "line_cost_pv": line["pv"],
        "line_cost_pv_wacc": line["pv_wacc"],
        "converter_cost_pv": converter["pv"],
        "converter_cost_pv_wacc": converter["pv_wacc"],
        "total_pv": total_pv,
        "total_pv_wacc": total_pv_wacc,
        "availability": {
            "line_loss_conductor": {
                "available": line_available,
                "missing_inputs": () if line_available else (_ENERGY_PATH,),
            },
            "line_loss_converter": {
                "available": converter_available,
                "missing_inputs": () if converter_available else (_ENERGY_PATH,),
                "applies": converter_applies,
            },
        },
    }


def main() -> None:
    """Line loss costs: gross for greenfield, net change for reconductoring/rebuild."""

    project_details = load_project_details()
    losses = net_energy_losses()
    g_benefit = project_details.benefit_price_escalation_real
    ctx = get_run_context()
    if ctx is None:
        raise RuntimeError(
            f"{__name__} requires a RunContext. Run via forge.py or set up "
            "RunContext in your test fixture."
        )

    logger.info("=" * 70)
    logger.info("LINE LOSS COST CALCULATOR")
    logger.info("=" * 70)
    logger.info(f"Project type: {project_details.project_type}")
    logger.info(
        f"Line utilization: {to_percent(project_details.line_utilization_percent):.1f}%"
    )
    if losses["replaced"]:
        logger.info(
            "Net line MWh/yr: %.2f (new %.2f − old %.2f)",
            losses["line_mwh"],
            losses["line_mwh_new"],
            losses["line_mwh_old"],
        )
        logger.info(
            "Net converter MWh/yr: %.2f (new %.2f − old %.2f)",
            losses["converter_mwh"],
            losses["converter_mwh_new"],
            losses["converter_mwh_old"],
        )
    else:
        logger.info("Greenfield gross line MWh/yr: %.2f", losses["line_mwh"])
    logger.info("")

    loss_values = _priced_losses(
        losses["line_mwh"],
        losses["converter_mwh"],
        project_details.value_of_load,
        g_benefit,
        int(project_details.project_lifetime),
        ctx.social_discount_rate,
        project_details.wacc_real,
        ctx.t_cod,
        ctx.horizon,
        converter_applies=losses["converters_apply"],
    )

    results: dict = {
        "total_afudc": 0,
        "line_loss_mwh_yr": losses["line_mwh"],
        "converter_loss_mwh_yr": losses["converter_mwh"],
        "total_loss_mwh_yr": losses["total_mwh"],
        **loss_values,
    }
    if losses["replaced"]:
        results.update(
            {
                "line_loss_mwh_yr_new": losses["line_mwh_new"],
                "line_loss_mwh_yr_old": losses["line_mwh_old"],
                "converter_loss_mwh_yr_new": losses["converter_mwh_new"],
                "converter_loss_mwh_yr_old": losses["converter_mwh_old"],
                "total_loss_mwh_yr_new": losses["line_mwh_new"] + losses["converter_mwh_new"],
                "total_loss_mwh_yr_old": losses["line_mwh_old"] + losses["converter_mwh_old"],
            }
        )

    csv_manager = SmartOutputManager()
    csv_manager.add_line_loss_costs(results)
    csv_manager.write_batch_summary()
