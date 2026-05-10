# Author: Dane McFarlane
# Date: 2025-11-10
# Description: JSON-based data loading utilities for transmission cost calculator.
#              Parallel implementation to yaml_loaders.py that uses JSON input instead of YAML files.

import json
import logging
import os
from typing import Any, Dict, Optional
from financial_utils import calculate_real_wacc, get_wacc_nominal
from yaml_loaders import (
    ProjectTechnicalDetails,
    CongestionCurtailmentParams,
    PhysicalDetailsDetailed,
    CircuitAndResistanceDetails,
    FinancingDetails,
)


class JSONDataSource:
    """
    Singleton data source for JSON-based configuration.
    Stores the combined JSON data in memory for all loader functions to access.
    Automatically loads from CTCC_JSON_DATA_FILE environment variable if set.
    """

    _instance = None
    _json_data: Optional[Dict[str, Any]] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def set_data(self, json_data: Dict[str, Any]):
        """Set the JSON data source."""
        self._json_data = json_data

    def get_data(self, key: str) -> Dict[str, Any]:
        """Get data for a specific key."""
        # Auto-load from environment variable if data not set
        if self._json_data is None:
            self._load_from_env_file()

        if self._json_data is None:
            raise RuntimeError(
                "JSON data not set. Call set_data() first or set CTCC_JSON_DATA_FILE environment variable."
            )
        if key not in self._json_data:
            raise KeyError(f"Key '{key}' not found in JSON data.")
        return self._json_data[key]

    def _load_from_env_file(self):
        """Load JSON data from file specified in CTCC_JSON_DATA_FILE environment variable."""
        json_file_path = os.environ.get("CTCC_JSON_DATA_FILE")
        if json_file_path and os.path.exists(json_file_path):
            try:
                with open(json_file_path, "r") as f:
                    self._json_data = json.load(f)
            except Exception as e:
                raise RuntimeError(
                    f"Failed to load JSON data from {json_file_path}: {e}"
                )

    def clear(self):
        """Clear the JSON data."""
        self._json_data = None


# Global instance
_data_source = JSONDataSource()

logger = logging.getLogger(__name__)


def _load_energy_source_mix_from_combined_json(
    emissions_reductions: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Canonical mix from key 18_energy_source_mix; legacy fallback from
    emissions_reductions.energy_source_mix when 18 is absent.
    """
    jd = _data_source._json_data
    if jd:
        block18 = jd.get("18_energy_source_mix")
        if isinstance(block18, dict) and "energy_source_mix" in block18:
            return block18["energy_source_mix"]
    if "energy_source_mix" in emissions_reductions:
        logger.warning(
            "Using legacy energy_source_mix under 16_emissions_reductions; "
            "prefer top-level 18_energy_source_mix in combined JSON"
        )
        return emissions_reductions["energy_source_mix"]
    raise KeyError(
        "energy_source_mix missing: add 18_energy_source_mix to combined JSON "
        "or legacy energy_source_mix under 16_emissions_reductions.emissions_reductions"
    )


def set_json_data(combined_json: Dict[str, Any]):
    """
    Set the combined JSON data for all loader functions.

    Args:
        combined_json: Dictionary containing all configuration data
                      (e.g., loaded from final_combined.json)
    """
    _data_source.set_data(combined_json)


def clear_json_data():
    """Clear the JSON data source."""
    _data_source.clear()


def load_financing_details() -> FinancingDetails:
    """Load financing parameters and calculate real WACC using Fisher equation."""
    financing_data = _data_source.get_data("03_financing")
    inflation_rate = financing_data["financial"]["inflation_rate"]
    base_year = financing_data["financial"]["base_year"]
    wacc_nominal = get_wacc_nominal(financing_data)
    wacc_real = calculate_real_wacc(wacc_nominal, inflation_rate)
    return FinancingDetails(
        inflation_rate=inflation_rate,
        base_year=base_year,
        wacc_nominal=wacc_nominal,
        wacc_real=wacc_real,
    )


def load_project_technical_details() -> ProjectTechnicalDetails:
    """Load project technical details - returns all project specs."""
    from calculation_utils import normalize_capacity_mw
    from yaml_loaders import normalize_construction_type

    project_details = _data_source.get_data("01_project_technical_details")
    pd = project_details["project"]
    tl = project_details["timeline"]
    construction_type = normalize_construction_type(pd["construction_type"])
    ac_dc = pd["ac_dc"]
    capacity_mw_raw = pd["capacity_mw"]
    capacity_mw = normalize_capacity_mw(capacity_mw_raw)
    conductor_type = pd["conductor_type"]
    from calculation_utils import get_converter_type

    converter_type = get_converter_type(ac_dc, pd["converter_type"])
    converter_loss_percentage = (
        None if ac_dc == "AC" else pd.get("converter_loss_percentage", None)
    )
    uses_existing_row = pd.get("uses_existing_row", False)
    reconductoring = pd["reconductoring"]
    row_agreement_type = pd.get("row_agreement_type")
    if row_agreement_type is None:
        row_agreement_type = (
            "lease_license_existing"
            if (reconductoring or uses_existing_row)
            else "permanent_easement_new"
        )
    return ProjectTechnicalDetails(
        construction_type=construction_type,
        ac_dc=ac_dc,
        capacity_mw=capacity_mw,
        conductor_type=conductor_type,
        converter_type=converter_type,
        line_utilization=pd["line_utilization"],
        reconductoring=reconductoring,
        uses_existing_row=uses_existing_row,
        delay_years=tl["delay_years"],
        construction_years=tl["construction_years"],
        project_lifetime=tl["project_lifetime"],
        converter_loss_percentage=converter_loss_percentage,
        row_agreement_type=row_agreement_type,
    )


def load_physical_details():
    """Load physical project details - return total miles only."""
    physical_details = _data_source.get_data("02_project_physical_details")
    return sum(physical_details["terrain"]["terrain_miles"].values())


def load_circuit_and_resistance_details(category: str) -> CircuitAndResistanceDetails:
    """Load circuit and resistance details for specified category."""
    data = _data_source.get_data("21_project_category_circuit_and_resistance_detail")
    crd = data["project_categories_circuit_and_resistance_details"]
    return CircuitAndResistanceDetails(
        voltage_kv=crd[category]["voltage_kv"],
        conductors_per_phase=crd[category]["conductors_per_phase"],
        number_of_phases=crd[category]["number_of_phases"],
        number_of_circuits_poles=crd[category]["number_of_circuits_poles"],
        AC_75_resistance=crd[category]["AC_75_resistance"],
        DC_20_resistance=crd[category]["DC_20_resistance"],
    )


def load_row_widths(category):
    """Load ROW width for specified category."""
    row_widths = _data_source.get_data("20_project_category_row_widths")
    return row_widths["project_categories_row_widths"][category]["row_width_feet"]


def load_row_details():
    """Load ROW details from JSON."""
    return _data_source.get_data("11_project_row_details")


def load_delay_costs():
    """Load delay costs from JSON."""
    return _data_source.get_data("05_delays")


def load_emissions_details():
    """Load emissions reductions details from JSON; mix merged from 18_energy_source_mix."""
    data = _data_source.get_data("16_emissions_reductions")
    erd = data["emissions_reductions"]
    mix = _load_energy_source_mix_from_combined_json(erd)
    return (
        erd["compensation_percent"],
        mix,
        erd["emission_intensities"],
        erd["societal_costs_per_kg"],
    )


def load_congestion_curtailment_reductions() -> CongestionCurtailmentParams:
    """
    Load congestion and curtailment reduction parameters from merged JSON.

    Returns:
        CongestionCurtailmentParams: Dataclass containing all congestion and curtailment parameters
    """
    data = _data_source.get_data("17_congestion_curtailment_reductions")

    # Check if this is a reconductoring project
    project_data = _data_source.get_data("01_project_technical_details")
    reconductoring = project_data["project"].get("reconductoring", False)

    # Load from appropriate section
    if reconductoring:
        reductions_data = data["reconductoring_congestion_curtailment_reductions"]
        # flow_factor is not used for reconductoring (capacity relief = capacity - old_capacity)
        flow_factor = 0.0
    else:
        reductions_data = data["greenfield_congestion_curtailment_reductions"]
        flow_factor = reductions_data["congestion"]["constraints"]["flow_factor"]

    congestion_data = reductions_data["congestion"]
    curtailment_data = reductions_data["curtailment"]

    # Get average_congestion_price - handle missing costs key
    if "costs" in congestion_data:
        average_congestion_price = congestion_data["costs"]["average_congestion_price"]
        # Get residual_exceedance_value (can be None or string "null" from JSON/front-end)
        residual_exceedance_value = congestion_data["costs"].get(
            "residual_exceedance_value"
        )
        if residual_exceedance_value is not None:
            if isinstance(residual_exceedance_value, str) and residual_exceedance_value.strip().lower() in ("null", ""):
                residual_exceedance_value = None
            else:
                try:
                    residual_exceedance_value = float(residual_exceedance_value)
                except (TypeError, ValueError):
                    residual_exceedance_value = None
    else:
        # Fallback: try to get from greenfield section or use default
        average_congestion_price = (
            data.get("greenfield_congestion_curtailment_reductions", {})
            .get("congestion", {})
            .get("costs", {})
            .get("average_congestion_price", 30)
        )
        residual_exceedance_value = None

    return CongestionCurtailmentParams(
        flow_factor=float(flow_factor),
        binding_hours=float(congestion_data["constraints"]["binding_hours"]),
        average_exceedance=float(congestion_data["constraints"]["average_exceedance"]),
        near_binding_hours=float(congestion_data["constraints"]["near_binding_hours"]),
        near_average_exceedance=float(
            congestion_data["constraints"]["near_average_exceedance"]
        ),
        average_congestion_price=float(average_congestion_price),
        residual_exceedance_value=residual_exceedance_value,
        curtailment_hours_total=float(
            curtailment_data.get("curtailment_hours_total", 0)
        ),
        average_curtailment_mw=float(curtailment_data.get("average_curtailment_mw", 0)),
        average_curtailment_price=float(
            curtailment_data.get("average_curtailment_price", 0)
        ),
    )


def load_contingencies():
    """Load contingencies from financing JSON."""
    financing_data = _data_source.get_data("03_financing")
    return financing_data["financial"]["contingencies"]


def load_financing_social_discount_rate():
    """Load social discount rate from financing JSON."""
    financing_data = _data_source.get_data("03_financing")
    return financing_data["financial"]["social_discount_rate"]


def load_physical_details_detailed() -> PhysicalDetailsDetailed:
    """Load physical project details - return detailed terrain breakdown."""
    physical_details = _data_source.get_data("02_project_physical_details")
    terrain = physical_details["terrain"]["terrain_miles"]
    return PhysicalDetailsDetailed(
        total_miles=sum(terrain.values()),
        forested_miles=terrain.get("forested", 0),
        scrubbed_flat_miles=terrain.get("scrubbed_flat", 0),
        wetland_miles=terrain.get("wetland", 0),
        farmland_miles=terrain.get("farmland", 0),
        desert_barren_miles=terrain.get("desert_barren", 0),
        urban_miles=terrain.get("urban", 0),
        rolling_hills_miles=terrain.get("rolling_hills", 0),
        mountain_miles=terrain.get("mountain", 0),
        subsea_miles=terrain.get("subsea", 0),
    )


def load_environmental_mitigation():
    """Load environmental mitigation parameters from JSON."""
    return _data_source.get_data("09_environmental_mitigation")


def load_cost_timing_patterns():
    """Load cost timing patterns for AFUDC calculations."""
    return _data_source.get_data("19_cost_timing_patterns")


def load_afudc_config():
    """Load AFUDC configuration from financing JSON."""
    fin = _data_source.get_data("03_financing")
    afudc_cfg = fin["financial"].get("afudc", {})
    return (
        afudc_cfg.get("apply_afudc", False),
        afudc_cfg.get("delay_period_active_work", False),
    )


def load_insurance_details():
    """Load insurance parameters from JSON."""
    return _data_source.get_data("04_insurance")


def load_wildfire_costs():
    """Load wildfire cost parameters from JSON."""
    return _data_source.get_data("06_wildfire_costs")


def load_outage_costs():
    """Load outage cost parameters from JSON."""
    return _data_source.get_data("07_outage_costs")


def load_terrain_data():
    """Load terrain data including terrain miles and multipliers from JSON."""
    physical_details = _data_source.get_data("02_project_physical_details")
    return physical_details["terrain"]

