# Date: 2025-11-10
# Description: JSON-based data loading utilities for transmission cost calculator.
#              Parallel implementation to yaml_loaders.py that uses JSON input instead of YAML files.

import json
import logging
import os
from typing import Any, Dict, Optional
from forge.scripts.utils.financial_utils import calculate_real_wacc, get_wacc_nominal
from .yaml_loaders import (
    ProjectTechnicalDetails,
    CongestionParams,
    PhysicalDetailsDetailed,
    CircuitAndResistanceDetails,
    FinancingDetails,
)


class JSONDataSource:
    """
    Singleton data source for JSON-based configuration.
    Stores the combined JSON data in memory for all loader functions to access.
    Automatically loads from FORGE_JSON_DATA_FILE environment variable if set.
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
                "JSON data not set. Call set_data() first or set FORGE_JSON_DATA_FILE environment variable."
            )
        if key not in self._json_data:
            raise KeyError(f"Key '{key}' not found in JSON data.")
        return self._json_data[key]

    def _load_from_env_file(self):
        """Load JSON data from file specified in FORGE_JSON_DATA_FILE environment variable."""
        json_file_path = os.environ.get("FORGE_JSON_DATA_FILE")
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


def load_grid_mix() -> Dict[str, Any]:
    """Load the single-trajectory grid mix from the '18_energy_source_mix' JSON block.

    Returns a dict with keys 'initial', 'rate_pre_cod', 'rate_post_cod'. No backward
    compatibility: old 'energy_source_mix' / 'counterfactual_energy_source_mix' keys
    are not recognized.
    """
    block18 = _data_source.get_data("18_energy_source_mix")
    if not isinstance(block18, dict) or "grid_mix" not in block18:
        raise KeyError("Missing 'grid_mix' key in 18_energy_source_mix JSON block")
    grid_mix = block18["grid_mix"]
    for key in ("initial", "rate_pre_cod", "rate_post_cod"):
        if key not in grid_mix:
            raise KeyError(f"Missing '{key}' key in grid_mix section of 18_energy_source_mix")
    return grid_mix


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
    from forge.scripts.utils.calculation_utils import normalize_capacity_mw
    from .yaml_loaders import normalize_construction_type

    project_details = _data_source.get_data("01_project_technical_details")
    pd = project_details["project"]
    tl = project_details["timeline"]
    construction_type = normalize_construction_type(pd["construction_type"])
    ac_dc = pd["ac_dc"]
    capacity_mw_raw = pd["capacity_mw"]
    capacity_mw = normalize_capacity_mw(capacity_mw_raw)
    conductor_type = pd["conductor_type"]
    from forge.scripts.utils.calculation_utils import get_converter_type

    converter_type = get_converter_type(ac_dc, pd["converter_type"])
    converter_loss_percentage = (
        None if ac_dc == "AC" else pd.get("converter_loss_percentage", None)
    )
    uses_existing_row = pd.get("uses_existing_row", False)
    project_type = pd["project_type"]
    if project_type not in ("greenfield", "reconductoring", "rebuild"):
        raise ValueError(
            f"Invalid project_type '{project_type}'. Must be one of: greenfield, reconductoring, rebuild"
        )
    row_agreement_type = pd.get("row_agreement_type")
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
        line_utilization=pd["line_utilization"],
        project_type=project_type,
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
    """Load emissions reductions details from JSON (compensation, intensities, societal costs).

    Grid mix is loaded separately via load_grid_mix().
    """
    data = _data_source.get_data("16_emissions_reductions")
    erd = data["emissions_reductions"]
    return (
        erd["compensation_percent"],
        erd["emission_intensities"],
        erd["societal_costs_per_kg"],
    )


def load_congestion_reductions() -> CongestionParams:
    """
    Load congestion reduction parameters from merged JSON.

    Returns:
        CongestionParams: Dataclass containing congestion parameters
    """
    data = _data_source.get_data("17_congestion_reductions")

    project_data = _data_source.get_data("01_project_technical_details")
    project_type = project_data["project"]["project_type"]
    use_incremental = project_type in ("reconductoring", "rebuild")

    # Load from appropriate section
    if use_incremental:
        reductions_data = data["incremental_congestion_reductions"]
        constraints = reductions_data["constraints"]
        prices = reductions_data["prices"]
        flow_factor = 0.0
    else:
        reductions_data = data["greenfield_congestion_reductions"]
        constraints = reductions_data["constraints"]
        prices = reductions_data["prices"]
        flow_factor = constraints["flow_factor"]

    # Backward compat: ignore fields from the removed separately-modeled curtailment stream
    constraints.pop("congestion_fraction", None)
    prices.pop("average_curtailment_price", None)

    return CongestionParams(
        flow_factor=float(flow_factor),
        constrained_hours=float(constraints["constrained_hours"]),
        average_exceedance=float(constraints["average_exceedance"]),
        average_congestion_price=float(prices["average_congestion_price"]),
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

