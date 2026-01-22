# Author: Claude Code
# Date: 2025-11-10
# Description: JSON-based data loading utilities for transmission cost calculator.
#              Parallel implementation to yaml_loaders.py that uses JSON input instead of YAML files.

import os
import json
from typing import Dict, Any, Optional


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


def load_financing_details():
    """Load financing parameters and calculate real WACC using Fisher equation."""
    financing_data = _data_source.get_data("03_financing")
    inflation_rate = financing_data["financial"]["inflation_rate"]
    base_year = financing_data["financial"]["base_year"]
    wacc_nominal = financing_data["financial"]["wacc_nominal"]
    wacc_real = (1 + wacc_nominal) / (1 + inflation_rate) - 1
    return inflation_rate, base_year, wacc_nominal, wacc_real


def load_project_technical_details():
    """Load project technical details - returns all project specs."""
    from calculation_utils import normalize_capacity_mw
    
    project_details = _data_source.get_data("01_project_technical_details")
    pd = project_details["project"]
    tl = project_details["timeline"]
    construction_type = pd["construction_type"]
    ac_dc = pd["ac_dc"]
    capacity_mw_raw = pd["capacity_mw"]
    capacity_mw = normalize_capacity_mw(capacity_mw_raw)
    conductor_type = pd["conductor_type"]
    converter_type = "NA" if ac_dc == "AC" else pd["converter_type"]
    converter_loss_percentage = (
        None if ac_dc == "AC" else pd.get("converter_loss_percentage", None)
    )
    uses_existing_row = pd.get("uses_existing_row", False)
    return (
        construction_type,
        ac_dc,
        capacity_mw,
        conductor_type,
        converter_type,
        pd["line_utilization"],
        pd["reconductoring"],
        uses_existing_row,
        tl["delay_years"],
        tl["construction_years"],
        tl["project_lifetime"],
        converter_loss_percentage,
    )


def load_physical_details():
    """Load physical project details - return total miles only."""
    physical_details = _data_source.get_data("02_project_physical_details")
    return sum(physical_details["terrain"]["terrain_miles"].values())


def load_circuit_and_resistance_details(category):
    """Load circuit and resistance details for specified category."""
    data = _data_source.get_data("21_project_category_circuit_and_resistance_detail")
    crd = data["project_categories_circuit_and_resistance_details"]
    return (
        crd[category]["voltage_kv"],
        crd[category]["conductors_per_phase"],
        crd[category]["number_of_phases"],
        crd[category]["number_of_circuits_poles"],
        crd[category]["AC_75_resistance"],
        crd[category]["DC_20_resistance"],
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
    """Load emissions reductions details from JSON."""
    data = _data_source.get_data("16_emissions_reductions")
    erd = data["emissions_reductions"]
    return (
        erd["compensation_percent"],
        erd["energy_source_mix"],
        erd["emission_intensities"],
        erd["societal_costs_per_kg"],
    )


def load_congestion_curtailment_reductions():
    """
    Load congestion and curtailment reduction parameters from merged JSON.

    Returns:
        Tuple of 13 values:
        - flow_factor (float, 0.0 for reconductoring)
        - binding_hours (float)
        - average_exceedance (float)
        - near_binding_hours (float)
        - near_average_exceedance (float)
        - near_binding_relief_factor (float)
        - saturation_factor (float)
        - average_congestion_price (float)
        - residual_exceedance_value (float | None, None if null in JSON)
        - curtailment_hours_total (float)
        - average_curtailment_mw (float)
        - average_curtailment_price (float)
        - curtailment_saturation_factor (float)
    """
    # #region agent log
    import json, os

    try:
        log_path = "/Users/ai17/Documents/UT Austin/Research/Webber Energy Group/Comprehensive Transmission Cost Calculator/Python Version/.cursor/debug.log"
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        with open(log_path, "a") as f:
            f.write(
                json.dumps(
                    {
                        "id": "log_load_congestion_curtailment_entry",
                        "timestamp": int(__import__("time").time() * 1000),
                        "location": "json_loaders.py:164",
                        "message": "load_congestion_curtailment_reductions entry",
                        "data": {},
                        "sessionId": "debug-session",
                        "runId": "run1",
                        "hypothesisId": "A",
                    }
                )
                + "\n"
            )
    except Exception as e:
        pass
    # #endregion
    data = _data_source.get_data("17_congestion_curtailment_reductions")

    # Check if this is a reconductoring project
    project_data = _data_source.get_data("01_project_technical_details")
    reconductoring = project_data["project"].get("reconductoring", False)

    # #region agent log
    try:
        log_path = "/Users/ai17/Documents/UT Austin/Research/Webber Energy Group/Comprehensive Transmission Cost Calculator/Python Version/.cursor/debug.log"
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        with open(log_path, "a") as f:
            f.write(
                json.dumps(
                    {
                        "id": "log_reconductoring_flag",
                        "timestamp": int(__import__("time").time() * 1000),
                        "location": "json_loaders.py:164",
                        "message": "reconductoring flag check",
                        "data": {
                            "reconductoring": reconductoring,
                            "type": str(type(reconductoring)),
                            "project_data_keys": list(project_data.keys()),
                        },
                        "sessionId": "debug-session",
                        "runId": "run1",
                        "hypothesisId": "A",
                    }
                )
                + "\n"
            )
    except Exception as e:
        pass
    # #endregion

    # Load from appropriate section
    if reconductoring:
        # #region agent log
        try:
            log_path = "/Users/ai17/Documents/UT Austin/Research/Webber Energy Group/Comprehensive Transmission Cost Calculator/Python Version/.cursor/debug.log"
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
            with open(log_path, "a") as f:
                f.write(
                    json.dumps(
                        {
                            "id": "log_reconductoring_branch",
                            "timestamp": int(__import__("time").time() * 1000),
                            "location": "json_loaders.py:167",
                            "message": "entering reconductoring branch",
                            "data": {"data_keys": list(data.keys())},
                            "sessionId": "debug-session",
                            "runId": "run1",
                            "hypothesisId": "B",
                        }
                    )
                    + "\n"
                )
        except Exception as e:
            pass
        # #endregion
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
        # Get residual_exceedance_value (can be None)
        residual_exceedance_value = congestion_data["costs"].get(
            "residual_exceedance_value"
        )
        if residual_exceedance_value is not None:
            residual_exceedance_value = float(residual_exceedance_value)
    else:
        # Fallback: try to get from greenfield section or use default
        average_congestion_price = (
            data.get("greenfield_congestion_curtailment_reductions", {})
            .get("congestion", {})
            .get("costs", {})
            .get("average_congestion_price", 30)
        )
        residual_exceedance_value = None

    result = (
        float(flow_factor),
        float(congestion_data["constraints"]["binding_hours"]),
        float(congestion_data["constraints"]["average_exceedance"]),
        float(congestion_data["constraints"]["near_binding_hours"]),
        float(congestion_data["constraints"]["near_average_exceedance"]),
        float(congestion_data["constraints"]["near_binding_relief_factor"]),
        float(congestion_data["constraints"]["saturation_factor"]),
        float(average_congestion_price),
        residual_exceedance_value,
        float(curtailment_data.get("curtailment_hours_total", 0)),
        float(curtailment_data.get("average_curtailment_mw", 0)),
        float(curtailment_data.get("average_curtailment_price", 0)),
        float(curtailment_data.get("curtailment_saturation_factor", 0)),
    )
    # #region agent log
    try:
        log_path = "/Users/ai17/Documents/UT Austin/Research/Webber Energy Group/Comprehensive Transmission Cost Calculator/Python Version/.cursor/debug.log"
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        with open(log_path, "a") as f:
            f.write(
                json.dumps(
                    {
                        "id": "log_load_congestion_curtailment_exit",
                        "timestamp": int(__import__("time").time() * 1000),
                        "location": "json_loaders.py:184",
                        "message": "load_congestion_curtailment_reductions exit",
                        "data": {
                            "flow_factor": result[0],
                            "binding_hours": result[1],
                            "average_exceedance": result[2],
                            "saturation_factor": result[6],
                            "congestion_price": result[7],
                        },
                        "sessionId": "debug-session",
                        "runId": "run1",
                        "hypothesisId": "C",
                    }
                )
                + "\n"
            )
    except Exception as e:
        pass
    # #endregion
    return result


def load_contingencies():
    """Load contingencies from financing JSON."""
    financing_data = _data_source.get_data("03_financing")
    return financing_data["financial"]["contingencies"]


def load_financing_social_discount_rate():
    """Load social discount rate from financing JSON."""
    financing_data = _data_source.get_data("03_financing")
    return financing_data["financial"]["social_discount_rate"]


def load_physical_details_detailed():
    """Load physical project details - return detailed terrain breakdown."""
    physical_details = _data_source.get_data("02_project_physical_details")
    terrain = physical_details["terrain"]["terrain_miles"]
    return (
        sum(terrain.values()),  # total_miles
        terrain.get("forested", 0),
        terrain.get("scrubbed_flat", 0),
        terrain.get("wetland", 0),
        terrain.get("farmland", 0),
        terrain.get("desert_barren", 0),
        terrain.get("urban", 0),
        terrain.get("rolling_hills", 0),
        terrain.get("mountain", 0),
        terrain.get("subsea", 0),
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
