# Date: 2025-01-XX
# Description: Centralized YAML loading utilities for transmission cost calculator.

from __future__ import annotations

import logging
import yaml
from dataclasses import dataclass
from typing import Dict, Any, Tuple, Optional
from path_config import YAMLS_DIR
from run_context import get_run_context
from calculation_utils import normalize_capacity_mw
from financial_utils import calculate_real_wacc, get_wacc_nominal

logger = logging.getLogger(__name__)


@dataclass
class ProjectTechnicalDetails:
    """Project technical details returned from load_project_technical_details()."""

    construction_type: str
    ac_dc: str
    capacity_mw: int
    conductor_type: str
    converter_type: str
    line_utilization: float
    project_type: str  # "greenfield" | "reconductoring" | "rebuild"
    uses_existing_row: bool
    delay_years: float
    construction_years: int
    project_lifetime: int
    converter_loss_percentage: Optional[float]
    row_agreement_type: Optional[str] = (
        None  # permanent_easement_new | lease_license_existing | fee_simple | federal_hybrid; if None, inferred from project_type/uses_existing_row
    )


@dataclass
class CongestionCurtailmentParams:
    """Congestion and curtailment reduction parameters."""

    flow_factor: float
    constrained_hours: float
    average_exceedance: float
    average_congestion_price: float
    benefit_price_escalation_real: float = 0.0


@dataclass
class PhysicalDetailsDetailed:
    """Detailed physical project details with terrain breakdown."""

    total_miles: float
    forested_miles: float
    scrubbed_flat_miles: float
    wetland_miles: float
    farmland_miles: float
    desert_barren_miles: float
    urban_miles: float
    rolling_hills_miles: float
    mountain_miles: float
    subsea_miles: float


@dataclass
class CircuitAndResistanceDetails:
    """Circuit and resistance details for a project category."""

    voltage_kv: float
    conductors_per_phase: int
    number_of_phases: int
    number_of_circuits_poles: int
    AC_75_resistance: float
    DC_20_resistance: float
    material: str
    alpha_20: float


@dataclass
class FinancingDetails:
    """Financing parameters and WACC calculations."""

    inflation_rate: float
    base_year: int
    wacc_nominal: float
    wacc_real: float


def load_financing_details() -> FinancingDetails:
    """Load financing parameters and calculate real WACC using Fisher equation."""
    ctx = get_run_context()
    if ctx is not None:
        return ctx.financing
    try:
        with open(YAMLS_DIR / "03_financing.yaml", "r") as file:
            financing_data = yaml.safe_load(file)
        if not financing_data:
            raise ValueError("Financing YAML file is empty or invalid")
        if "financial" not in financing_data:
            raise KeyError("Missing 'financial' key in financing YAML file")
        financial = financing_data["financial"]
        if "inflation_rate" not in financial:
            raise KeyError("Missing 'inflation_rate' key in financing YAML file")
        if "base_year" not in financial:
            raise KeyError("Missing 'base_year' key in financing YAML file")
        if "wacc_nominal" not in financial:
            raise KeyError("Missing 'wacc_nominal' key in financing YAML file")
        inflation_rate = financial["inflation_rate"]
        base_year = financial["base_year"]
        wacc_nominal = get_wacc_nominal(financing_data)

        wacc_real = calculate_real_wacc(wacc_nominal, inflation_rate)
        return FinancingDetails(
            inflation_rate=inflation_rate,
            base_year=base_year,
            wacc_nominal=wacc_nominal,
            wacc_real=wacc_real,
        )
    except FileNotFoundError:
        raise FileNotFoundError(
            f"Financing YAML not found at {YAMLS_DIR / '03_financing.yaml'}"
        )
    except yaml.YAMLError as e:
        raise ValueError(f"Error parsing financing YAML: {e}")
    except KeyError as e:
        raise KeyError(f"Missing required key in financing YAML: {e}")


def normalize_construction_type(construction_type: str) -> str:
    """
    Normalize construction_type to match YAML category key format.
    Converts "Underground Direct-Buried" -> "Underground direct-buried"
    and "Underground Tunnel" -> "Underground tunnel" to match YAML keys.
    """
    # Map common variations to YAML format
    normalization_map = {
        "Underground Direct-Buried": "Underground direct-buried",
        "Underground Tunnel": "Underground tunnel",
        "Underground direct-buried": "Underground direct-buried",  # Already correct
        "Underground tunnel": "Underground tunnel",  # Already correct
        "Overhead": "Overhead",  # Already correct
        "Subsea": "Subsea",  # Already correct
    }

    normalized = normalization_map.get(construction_type, construction_type)
    return normalized


def load_project_technical_details() -> ProjectTechnicalDetails:
    """Load project technical details - returns all project specs."""
    ctx = get_run_context()
    if ctx is not None:
        return ctx.project_details
    try:
        with open(YAMLS_DIR / "01_project_technical_details.yaml", "r") as file:
            project_details = yaml.safe_load(file)
        if not project_details:
            raise ValueError("Project technical details YAML file is empty or invalid")
        if "project" not in project_details:
            raise KeyError(
                "Missing 'project' key in project technical details YAML file"
            )
        if "timeline" not in project_details:
            raise KeyError(
                "Missing 'timeline' key in project technical details YAML file"
            )
        project_data = project_details["project"]
        timeline_data = project_details["timeline"]
        required_project_keys = [
            "construction_type",
            "ac_dc",
            "capacity_mw",
            "conductor_type",
            "line_utilization",
            "project_type",
        ]
        for key in required_project_keys:
            if key not in project_data:
                raise KeyError(
                    f"Missing '{key}' key in project section of technical details YAML"
                )
        required_timeline_keys = [
            "delay_years",
            "construction_years",
            "project_lifetime",
        ]
        for key in required_timeline_keys:
            if key not in timeline_data:
                raise KeyError(
                    f"Missing '{key}' key in timeline section of technical details YAML"
                )
        construction_type = normalize_construction_type(
            project_data["construction_type"]
        )
        ac_dc = project_data["ac_dc"]
        capacity_mw_raw = project_data["capacity_mw"]
        capacity_mw = normalize_capacity_mw(capacity_mw_raw)
        conductor_type = project_data["conductor_type"]
        from calculation_utils import get_converter_type

        converter_type = get_converter_type(ac_dc, project_data["converter_type"])
        converter_loss_percentage = (
            None
            if ac_dc == "AC"
            else project_data.get("converter_loss_percentage", None)
        )
        uses_existing_row = project_data.get("uses_existing_row", False)
        project_type = project_data["project_type"]
        if project_type not in ("greenfield", "reconductoring", "rebuild"):
            raise ValueError(
                f"Invalid project_type '{project_type}'. Must be one of: greenfield, reconductoring, rebuild"
            )
        row_agreement_type = project_data.get("row_agreement_type")
        if row_agreement_type is None:
            row_agreement_type = (
                "lease_license_existing"
                if (project_type in ("reconductoring", "rebuild") or uses_existing_row)
                else "permanent_easement_new"
            )
        return ProjectTechnicalDetails(
            construction_type=construction_type,
            ac_dc=ac_dc,
            capacity_mw=capacity_mw,
            conductor_type=conductor_type,
            converter_type=converter_type,
            line_utilization=project_data["line_utilization"],
            project_type=project_type,
            uses_existing_row=uses_existing_row,
            delay_years=timeline_data["delay_years"],
            construction_years=timeline_data["construction_years"],
            project_lifetime=timeline_data["project_lifetime"],
            converter_loss_percentage=converter_loss_percentage,
            row_agreement_type=row_agreement_type,
        )
    except FileNotFoundError:
        raise FileNotFoundError(
            f"Project technical details YAML not found at {YAMLS_DIR / '01_project_technical_details.yaml'}"
        )
    except yaml.YAMLError as e:
        raise ValueError(f"Error parsing project technical details YAML: {e}")
    except KeyError as e:
        raise KeyError(f"Missing required key in project technical details YAML: {e}")


def load_physical_details() -> float:
    """Load physical project details - return total miles only."""
    ctx = get_run_context()
    if ctx is not None:
        return ctx.total_miles
    try:
        with open(YAMLS_DIR / "02_project_physical_details.yaml", "r") as file:
            physical_details = yaml.safe_load(file)
        if not physical_details:
            raise ValueError("Physical details YAML file is empty or invalid")
        if "terrain" not in physical_details:
            raise KeyError("Missing 'terrain' key in physical details YAML file")
        if "terrain_miles" not in physical_details["terrain"]:
            raise KeyError(
                "Missing 'terrain_miles' key in terrain section of physical details YAML"
            )
        terrain_miles = physical_details["terrain"]["terrain_miles"]
        # Handle None values by treating them as 0
        return sum(v if v is not None else 0 for v in terrain_miles.values())
    except FileNotFoundError:
        raise FileNotFoundError(
            f"Physical details YAML not found at {YAMLS_DIR / '02_project_physical_details.yaml'}"
        )
    except yaml.YAMLError as e:
        raise ValueError(f"Error parsing physical details YAML: {e}")
    except KeyError as e:
        raise KeyError(f"Missing required key in physical details YAML: {e}")


def load_circuit_and_resistance_details(
    category: str,
) -> CircuitAndResistanceDetails:
    """Load circuit and resistance details for specified category."""
    try:
        with open(
            YAMLS_DIR / "21_project_category_circuit_and_resistance_detail.yaml", "r"
        ) as file:
            data = yaml.safe_load(file)
        if not data:
            raise ValueError(
                "Circuit and resistance details YAML file is empty or invalid"
            )
        if "project_categories_circuit_and_resistance_details" not in data:
            raise KeyError(
                "Missing 'project_categories_circuit_and_resistance_details' key in YAML file"
            )
        circuit_resistance_details = data[
            "project_categories_circuit_and_resistance_details"
        ]
        if category not in circuit_resistance_details:
            raise KeyError(
                f"Category '{category}' not found in circuit and resistance details YAML"
            )
        required_keys = [
            "voltage_kv",
            "conductors_per_phase",
            "number_of_phases",
            "number_of_circuits_poles",
            "AC_75_resistance",
            "DC_20_resistance",
            "material",
            "alpha_20",
        ]
        for key in required_keys:
            if key not in circuit_resistance_details[category]:
                raise KeyError(
                    f"Missing '{key}' key for category '{category}' in circuit and resistance details YAML"
                )
        return CircuitAndResistanceDetails(
            voltage_kv=circuit_resistance_details[category]["voltage_kv"],
            conductors_per_phase=circuit_resistance_details[category][
                "conductors_per_phase"
            ],
            number_of_phases=circuit_resistance_details[category]["number_of_phases"],
            number_of_circuits_poles=circuit_resistance_details[category][
                "number_of_circuits_poles"
            ],
            AC_75_resistance=circuit_resistance_details[category]["AC_75_resistance"],
            DC_20_resistance=circuit_resistance_details[category]["DC_20_resistance"],
            material=circuit_resistance_details[category]["material"],
            alpha_20=circuit_resistance_details[category]["alpha_20"],
        )
    except FileNotFoundError:
        raise FileNotFoundError(
            f"Circuit and resistance details YAML not found at {YAMLS_DIR / '21_project_category_circuit_and_resistance_detail.yaml'}"
        )
    except yaml.YAMLError as e:
        raise ValueError(f"Error parsing circuit and resistance details YAML: {e}")
    except KeyError as e:
        raise KeyError(
            f"Missing required key in circuit and resistance details YAML: {e}"
        )


def load_corona_kw_per_mile(voltage_kv: float) -> float:
    """Look up annual-average AC overhead corona loss (kW/mile) for a voltage class."""
    try:
        with open(YAMLS_DIR / "22_corona_losses.yaml", "r") as file:
            data = yaml.safe_load(file)
        tiers = data["corona"]["voltage_class_tiers"]
    except (FileNotFoundError, KeyError, TypeError) as e:
        raise ValueError(f"Cannot load corona loss parameters: {e}")
    for tier in tiers:
        max_kv = float("inf") if tier["max_kv"] in (".inf", None) else tier["max_kv"]
        if voltage_kv <= max_kv:
            return tier["kw_per_mile"]
    return tiers[-1]["kw_per_mile"]


def load_row_widths(category: str) -> float:
    """Load ROW width for specified category."""
    ctx = get_run_context()
    if ctx is not None and category == ctx.category_string:
        return ctx.row_width_feet
    try:
        with open(YAMLS_DIR / "20_project_category_row_widths.yaml", "r") as file:
            row_widths = yaml.safe_load(file)
        if not row_widths:
            raise ValueError("ROW widths YAML file is empty or invalid")
        if "project_categories_row_widths" not in row_widths:
            raise KeyError(
                "Missing 'project_categories_row_widths' key in ROW widths YAML file"
            )
        if category not in row_widths["project_categories_row_widths"]:
            raise KeyError(f"Category '{category}' not found in ROW widths YAML")
        if (
            "row_width_feet"
            not in row_widths["project_categories_row_widths"][category]
        ):
            raise KeyError(
                f"Missing 'row_width_feet' key for category '{category}' in ROW widths YAML"
            )
        return row_widths["project_categories_row_widths"][category]["row_width_feet"]
    except FileNotFoundError:
        raise FileNotFoundError(
            f"ROW widths YAML not found at {YAMLS_DIR / '20_project_category_row_widths.yaml'}"
        )
    except yaml.YAMLError as e:
        raise ValueError(f"Error parsing ROW widths YAML: {e}")
    except KeyError as e:
        raise KeyError(f"Missing required key in ROW widths YAML: {e}")


def load_row_details() -> Dict[str, Any]:
    """Load ROW details from YAML.

    Returned dict includes the top-level ``row_rent_escalation_real`` key
    (real annual escalation applied to ROW rent/holding cost, decimal,
    default 0.0 for backward compatibility) alongside ``right_of_way``.
    Callers should read it via ``data.get("row_rent_escalation_real", 0.0)``.
    """
    try:
        with open(YAMLS_DIR / "11_project_row_details.yaml", "r") as file:
            row_details = yaml.safe_load(file)
        if not row_details:
            raise ValueError("ROW details YAML file is empty or invalid")
        return row_details
    except FileNotFoundError:
        raise FileNotFoundError(
            f"ROW details YAML not found at {YAMLS_DIR / '11_project_row_details.yaml'}"
        )
    except yaml.YAMLError as e:
        raise ValueError(f"Error parsing ROW details YAML: {e}")


def load_delay_costs() -> Dict[str, Any]:
    """Load delay costs from YAML."""
    try:
        with open(YAMLS_DIR / "05_delays.yaml", "r") as file:
            delay_costs = yaml.safe_load(file)
        if not delay_costs:
            raise ValueError("Delay costs YAML file is empty or invalid")
        return delay_costs
    except FileNotFoundError:
        raise FileNotFoundError(
            f"Delay costs YAML not found at {YAMLS_DIR / '05_delays.yaml'}"
        )
    except yaml.YAMLError as e:
        raise ValueError(f"Error parsing delay costs YAML: {e}")


def load_grid_mix() -> Dict[str, Any]:
    """Load the single-trajectory grid mix from 18_energy_source_mix.yaml.

    Returns a dict with keys 'initial', 'rate_pre_cod', 'rate_post_cod', each mapping
    source name -> value ('initial' values are percentages 0-100; rate values are
    fractional annual growth/decline rates). No backward compatibility: old
    'energy_source_mix' / 'counterfactual_energy_source_mix' keys are not recognized.
    """
    path18 = YAMLS_DIR / "18_energy_source_mix.yaml"
    if not path18.is_file():
        raise FileNotFoundError(f"Energy source mix YAML not found at {path18}")
    with open(path18, "r", encoding="utf-8") as file:
        data = yaml.safe_load(file)
    if not data or "grid_mix" not in data:
        raise KeyError("Missing 'grid_mix' key in 18_energy_source_mix.yaml")
    grid_mix = data["grid_mix"]
    required_keys = ["initial", "rate_pre_cod", "rate_post_cod"]
    for key in required_keys:
        if key not in grid_mix:
            raise KeyError(
                f"Missing '{key}' key in grid_mix section of 18_energy_source_mix.yaml"
            )
    return grid_mix


def load_emissions_details() -> Tuple[float, Dict[str, Any], Dict[str, Any]]:
    """Load emissions reductions details from YAML (compensation, intensities, societal costs).

    Grid mix is loaded separately via load_grid_mix() — callers that need the mix
    (facilitated_emissions.py, displacement_delay_cost.py, emissions.py) load it and
    derive the COD-state trajectory themselves.
    """
    path16 = YAMLS_DIR / "16_emissions_reductions.yaml"
    if not path16.is_file():
        raise FileNotFoundError(f"Emissions reductions YAML not found at {path16}")
    try:
        with open(path16, "r", encoding="utf-8") as file:
            data = yaml.safe_load(file)
        if not data:
            raise ValueError("Emissions reductions YAML file is empty or invalid")
        if "emissions_reductions" not in data:
            raise KeyError("Missing 'emissions_reductions' key in YAML file")
        emissions_reductions_data = data["emissions_reductions"]
        required_keys = [
            "compensation_percent",
            "emission_intensities",
            "societal_costs_per_kg",
        ]
        for key in required_keys:
            if key not in emissions_reductions_data:
                raise KeyError(
                    f"Missing '{key}' key in emissions_reductions section of YAML"
                )
        return (
            emissions_reductions_data["compensation_percent"],
            emissions_reductions_data["emission_intensities"],
            emissions_reductions_data["societal_costs_per_kg"],
        )
    except yaml.YAMLError as e:
        raise ValueError(f"Error parsing emissions reductions YAML: {e}")
    except KeyError as e:
        raise KeyError(f"Missing required key in emissions reductions YAML: {e}")


def load_congestion_curtailment_reductions() -> CongestionCurtailmentParams:
    """
    Load congestion and curtailment reduction parameters from merged YAML file.

    Returns:
        CongestionCurtailmentParams: Dataclass containing all congestion and curtailment parameters
    """
    try:
        with open(YAMLS_DIR / "01_project_technical_details.yaml", "r") as project_file:
            project_data = yaml.safe_load(project_file)
    except FileNotFoundError:
        raise FileNotFoundError(
            f"Project technical details YAML not found at {YAMLS_DIR / '01_project_technical_details.yaml'}"
        )
    except yaml.YAMLError as e:
        raise ValueError(f"Error parsing project technical details YAML: {e}")

    if not project_data or "project" not in project_data:
        raise KeyError(
            "Missing 'project' key in project technical details YAML file"
        )
    if "project_type" not in project_data["project"]:
        raise KeyError(
            "Missing 'project_type' key in project section of technical details YAML"
        )
    project_type = project_data["project"]["project_type"]
    use_incremental = project_type in ("reconductoring", "rebuild")

    try:
        with open(YAMLS_DIR / "17_congestion_curtailment_reductions.yaml", "r") as file:
            data = yaml.safe_load(file)
        if not data:
            raise ValueError(
                "Congestion/curtailment reductions YAML file is empty or invalid"
            )

        # Load from appropriate section
        if use_incremental:
            if "incremental_congestion_curtailment_reductions" not in data:
                raise KeyError(
                    "Missing 'incremental_congestion_curtailment_reductions' key in YAML file"
                )
            reductions_data = data["incremental_congestion_curtailment_reductions"]
            constraints = reductions_data["constraints"]
            prices = reductions_data["prices"]
            constraints.pop("congestion_fraction", None)
            prices.pop("average_curtailment_price", None)
            flow_factor = 0.0
            constrained_hours = float(constraints["constrained_hours"])
            average_exceedance = float(constraints["average_exceedance"])
            average_congestion_price = float(prices["average_congestion_price"])
        else:
            if "greenfield_congestion_curtailment_reductions" not in data:
                raise KeyError(
                    "Missing 'greenfield_congestion_curtailment_reductions' key in YAML file"
                )
            reductions_data = data["greenfield_congestion_curtailment_reductions"]
            constraints = reductions_data["constraints"]
            prices = reductions_data["prices"]
            constraints.pop("congestion_fraction", None)
            prices.pop("average_curtailment_price", None)
            flow_factor = constraints["flow_factor"]
            constrained_hours = float(constraints["constrained_hours"])
            average_exceedance = float(constraints["average_exceedance"])
            average_congestion_price = float(prices["average_congestion_price"])

        return CongestionCurtailmentParams(
            flow_factor=float(flow_factor),
            constrained_hours=constrained_hours,
            average_exceedance=average_exceedance,
            average_congestion_price=average_congestion_price,
            benefit_price_escalation_real=float(
                data.get("benefit_price_escalation_real", 0.0)
            ),
        )
    except FileNotFoundError:
        raise FileNotFoundError(
            f"Congestion/curtailment reductions YAML not found at {YAMLS_DIR / '17_congestion_curtailment_reductions.yaml'}"
        )
    except yaml.YAMLError as e:
        raise ValueError(f"Error parsing congestion/curtailment reductions YAML: {e}")
    except KeyError as e:
        raise KeyError(
            f"Missing required key in congestion/curtailment reductions YAML: {e}"
        )
    except (ValueError, TypeError) as e:
        raise ValueError(
            f"Error converting congestion/curtailment reduction values to float: {e}"
        )


def load_contingencies() -> Dict[str, float]:
    """Load contingencies from financing YAML."""
    ctx = get_run_context()
    if ctx is not None:
        return ctx.contingencies
    try:
        with open(YAMLS_DIR / "03_financing.yaml", "r") as file:
            financing_data = yaml.safe_load(file)
        if not financing_data:
            raise ValueError("Financing YAML file is empty or invalid")
        if "financial" not in financing_data:
            raise KeyError("Missing 'financial' key in financing YAML file")
        if "contingencies" not in financing_data["financial"]:
            raise KeyError(
                "Missing 'contingencies' key in financial section of financing YAML"
            )
        return financing_data["financial"]["contingencies"]
    except FileNotFoundError:
        raise FileNotFoundError(
            f"Financing YAML not found at {YAMLS_DIR / '03_financing.yaml'}"
        )
    except yaml.YAMLError as e:
        raise ValueError(f"Error parsing financing YAML: {e}")
    except KeyError as e:
        raise KeyError(f"Missing required key in financing YAML: {e}")


def load_financing_social_discount_rate() -> float:
    """Load social discount rate from financing YAML."""
    try:
        with open(YAMLS_DIR / "03_financing.yaml", "r") as file:
            financing_data = yaml.safe_load(file)
        if not financing_data:
            raise ValueError("Financing YAML file is empty or invalid")
        if "financial" not in financing_data:
            raise KeyError("Missing 'financial' key in financing YAML file")
        if "social_discount_rate" not in financing_data["financial"]:
            raise KeyError(
                "Missing 'social_discount_rate' key in financial section of financing YAML"
            )
        return financing_data["financial"]["social_discount_rate"]
    except FileNotFoundError:
        raise FileNotFoundError(
            f"Financing YAML not found at {YAMLS_DIR / '03_financing.yaml'}"
        )
    except yaml.YAMLError as e:
        raise ValueError(f"Error parsing financing YAML: {e}")
    except KeyError as e:
        raise KeyError(f"Missing required key in financing YAML: {e}")


def load_physical_details_detailed() -> PhysicalDetailsDetailed:
    """Load physical project details - return detailed terrain breakdown."""
    try:
        with open(YAMLS_DIR / "02_project_physical_details.yaml", "r") as file:
            physical_details = yaml.safe_load(file)
        if not physical_details:
            raise ValueError("Physical details YAML file is empty or invalid")
        if "terrain" not in physical_details:
            raise KeyError("Missing 'terrain' key in physical details YAML file")
        if "terrain_miles" not in physical_details["terrain"]:
            raise KeyError(
                "Missing 'terrain_miles' key in terrain section of physical details YAML"
            )
        terrain = physical_details["terrain"]["terrain_miles"]
        # Handle None values
        safe_get = lambda k: terrain.get(k, 0) if terrain.get(k) is not None else 0
        return PhysicalDetailsDetailed(
            total_miles=sum(v if v is not None else 0 for v in terrain.values()),
            forested_miles=safe_get("forested"),
            scrubbed_flat_miles=safe_get("scrubbed_flat"),
            wetland_miles=safe_get("wetland"),
            farmland_miles=safe_get("farmland"),
            desert_barren_miles=safe_get("desert_barren"),
            urban_miles=safe_get("urban"),
            rolling_hills_miles=safe_get("rolling_hills"),
            mountain_miles=safe_get("mountain"),
            subsea_miles=safe_get("subsea"),
        )
    except FileNotFoundError:
        raise FileNotFoundError(
            f"Physical details YAML not found at {YAMLS_DIR / '02_project_physical_details.yaml'}"
        )
    except yaml.YAMLError as e:
        raise ValueError(f"Error parsing physical details YAML: {e}")
    except KeyError as e:
        raise KeyError(f"Missing required key in physical details YAML: {e}")


def load_environmental_mitigation() -> Dict[str, Any]:
    """Load environmental mitigation parameters from YAML."""
    try:
        with open(YAMLS_DIR / "09_environmental_mitigation.yaml", "r") as file:
            env_mitigation = yaml.safe_load(file)
        if not env_mitigation:
            raise ValueError("Environmental mitigation YAML file is empty or invalid")
        return env_mitigation
    except FileNotFoundError:
        raise FileNotFoundError(
            f"Environmental mitigation YAML not found at {YAMLS_DIR / '09_environmental_mitigation.yaml'}"
        )
    except yaml.YAMLError as e:
        raise ValueError(f"Error parsing environmental mitigation YAML: {e}")


def load_cost_timing_patterns() -> Dict[str, Any]:
    """Load cost timing patterns for AFUDC calculations."""
    try:
        with open(YAMLS_DIR / "19_cost_timing_patterns.yaml", "r") as file:
            cost_timing = yaml.safe_load(file)
        if not cost_timing:
            raise ValueError("Cost timing patterns YAML file is empty or invalid")
        return cost_timing
    except FileNotFoundError:
        raise FileNotFoundError(
            f"Cost timing patterns YAML not found at {YAMLS_DIR / '19_cost_timing_patterns.yaml'}"
        )
    except yaml.YAMLError as e:
        raise ValueError(f"Error parsing cost timing patterns YAML: {e}")


def load_afudc_config() -> Tuple[bool, bool]:
    """Load AFUDC configuration from financing YAML."""
    try:
        with open(YAMLS_DIR / "03_financing.yaml", "r") as file:
            financing_data = yaml.safe_load(file)
        if not financing_data:
            raise ValueError("Financing YAML file is empty or invalid")
        if "financial" not in financing_data:
            raise KeyError("Missing 'financial' key in financing YAML file")
        afudc_cfg = financing_data["financial"].get("afudc", {})
        return (
            afudc_cfg.get("apply_afudc", False),
            afudc_cfg.get("delay_period_active_work", False),
        )
    except FileNotFoundError:
        raise FileNotFoundError(
            f"Financing YAML not found at {YAMLS_DIR / '03_financing.yaml'}"
        )
    except yaml.YAMLError as e:
        raise ValueError(f"Error parsing financing YAML: {e}")
    except KeyError as e:
        raise KeyError(f"Missing required key in financing YAML: {e}")


def load_insurance_details() -> Dict[str, Any]:
    """Load insurance parameters from YAML."""
    try:
        with open(YAMLS_DIR / "04_insurance.yaml", "r") as file:
            insurance_data = yaml.safe_load(file)
        if not insurance_data:
            raise ValueError("Insurance YAML file is empty or invalid")
        return insurance_data
    except FileNotFoundError:
        raise FileNotFoundError(
            f"Insurance YAML not found at {YAMLS_DIR / '04_insurance.yaml'}"
        )
    except yaml.YAMLError as e:
        raise ValueError(f"Error parsing insurance YAML: {e}")


def load_wildfire_costs() -> Dict[str, Any]:
    """Load wildfire cost parameters from YAML."""
    try:
        with open(YAMLS_DIR / "06_wildfire_costs.yaml", "r") as file:
            wildfire_data = yaml.safe_load(file)
        if not wildfire_data:
            raise ValueError("Wildfire costs YAML file is empty or invalid")
        return wildfire_data
    except FileNotFoundError:
        raise FileNotFoundError(
            f"Wildfire costs YAML not found at {YAMLS_DIR / '06_wildfire_costs.yaml'}"
        )
    except yaml.YAMLError as e:
        raise ValueError(f"Error parsing wildfire costs YAML: {e}")


def load_outage_costs() -> Dict[str, Any]:
    """Load outage cost parameters from YAML."""
    try:
        with open(YAMLS_DIR / "07_outage_costs.yaml", "r") as file:
            outage_data = yaml.safe_load(file)
        if not outage_data:
            raise ValueError("Outage costs YAML file is empty or invalid")
        return outage_data
    except FileNotFoundError:
        raise FileNotFoundError(
            f"Outage costs YAML not found at {YAMLS_DIR / '07_outage_costs.yaml'}"
        )
    except yaml.YAMLError as e:
        raise ValueError(f"Error parsing outage costs YAML: {e}")

