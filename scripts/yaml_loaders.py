# Author: Andrew Igdal
# Date: 2025-01-XX
# Description: Centralized YAML loading utilities for transmission cost calculator.

from __future__ import annotations

import yaml
from typing import Dict, Any, Tuple, Optional
from path_config import YAMLS_DIR


def load_financing_details() -> Tuple[float, int, float, float]:
    """Load financing parameters and calculate real WACC using Fisher equation."""
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
        wacc_nominal = financial["wacc_nominal"]

        # Validate inflation_rate to prevent division by zero in Fisher equation
        if inflation_rate <= -1:
            raise ValueError(
                f"Invalid inflation_rate: {inflation_rate}. "
                f"Value must be > -1 to prevent division by zero in Fisher equation calculation. "
                f"An inflation_rate of {inflation_rate} would cause (1 + inflation_rate) to be <= 0."
            )

        wacc_real = (1 + wacc_nominal) / (1 + inflation_rate) - 1
        return inflation_rate, base_year, wacc_nominal, wacc_real
    except FileNotFoundError:
        raise FileNotFoundError(
            f"Financing YAML not found at {YAMLS_DIR / '03_financing.yaml'}"
        )
    except yaml.YAMLError as e:
        raise ValueError(f"Error parsing financing YAML: {e}")
    except KeyError as e:
        raise KeyError(f"Missing required key in financing YAML: {e}")


def load_project_technical_details() -> (
    Tuple[str, str, int, str, str, float, bool, float, int, int, Optional[float]]
):
    """Load project technical details - returns all project specs."""
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
            "reconductoring",
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
        construction_type = project_data["construction_type"]
        ac_dc = project_data["ac_dc"]
        capacity_mw = project_data["capacity_mw"]
        conductor_type = project_data["conductor_type"]
        converter_type = "NA" if ac_dc == "AC" else project_data["converter_type"]
        converter_loss_percentage = (
            None
            if ac_dc == "AC"
            else project_data.get("converter_loss_percentage", None)
        )
        return (
            construction_type,
            ac_dc,
            capacity_mw,
            conductor_type,
            converter_type,
            project_data["line_utilization"],
            project_data["reconductoring"],
            timeline_data["delay_years"],
            timeline_data["construction_years"],
            timeline_data["project_lifetime"],
            converter_loss_percentage,
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
) -> Tuple[float, int, int, int, float, float]:
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
        ]
        for key in required_keys:
            if key not in circuit_resistance_details[category]:
                raise KeyError(
                    f"Missing '{key}' key for category '{category}' in circuit and resistance details YAML"
                )
        return (
            circuit_resistance_details[category]["voltage_kv"],
            circuit_resistance_details[category]["conductors_per_phase"],
            circuit_resistance_details[category]["number_of_phases"],
            circuit_resistance_details[category]["number_of_circuits_poles"],
            circuit_resistance_details[category]["AC_75_resistance"],
            circuit_resistance_details[category]["DC_20_resistance"],
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


def load_row_widths(category: str) -> float:
    """Load ROW width for specified category."""
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
    """Load ROW details from YAML."""
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


def load_emissions_details() -> (
    Tuple[float, Dict[str, Any], Dict[str, Any], Dict[str, Any]]
):
    """Load emissions reductions details from YAML."""
    try:
        with open(YAMLS_DIR / "16_emissions_reductions.yaml", "r") as file:
            data = yaml.safe_load(file)
        if not data:
            raise ValueError("Emissions reductions YAML file is empty or invalid")
        if "emissions_reductions" not in data:
            raise KeyError("Missing 'emissions_reductions' key in YAML file")
        emissions_reductions_data = data["emissions_reductions"]
        required_keys = [
            "compensation_percent",
            "energy_source_mix",
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
            emissions_reductions_data["energy_source_mix"],
            emissions_reductions_data["emission_intensities"],
            emissions_reductions_data["societal_costs_per_kg"],
        )
    except FileNotFoundError:
        raise FileNotFoundError(
            f"Emissions reductions YAML not found at {YAMLS_DIR / '16_emissions_reductions.yaml'}"
        )
    except yaml.YAMLError as e:
        raise ValueError(f"Error parsing emissions reductions YAML: {e}")
    except KeyError as e:
        raise KeyError(f"Missing required key in emissions reductions YAML: {e}")


def load_congestion_reductions() -> (
    Tuple[float, float, float, float, float, float, float, float]
):
    """Load congestion reduction parameters from YAML."""
    try:
        # Check if this is a reconductoring project
        with open(YAMLS_DIR / "01_project_technical_details.yaml", "r") as project_file:
            project_data = yaml.safe_load(project_file)
        reconductoring = project_data.get("project", {}).get("reconductoring", False) if project_data else False
        
        with open(YAMLS_DIR / "17_congestion_reductions.yaml", "r") as file:
            data = yaml.safe_load(file)
        if not data:
            raise ValueError("Congestion reductions YAML file is empty or invalid")
        
        # Load from appropriate section
        if reconductoring:
            if "reconductoring_congestion_reductions" not in data:
                raise KeyError(
                    "Missing 'reconductoring_congestion_reductions' key in YAML file"
                )
            congestion_reductions_data = data["reconductoring_congestion_reductions"]
            flow_factor = 0.0  # flow_factor not used for reconductoring
        else:
            if "greenfield_congestion_reductions" not in data:
                raise KeyError(
                    "Missing 'greenfield_congestion_reductions' key in YAML file"
                )
            congestion_reductions_data = data["greenfield_congestion_reductions"]
            flow_factor = congestion_reductions_data["constraints"]["flow_factor"]
        
        if "constraints" not in congestion_reductions_data:
            raise KeyError(
                f"Missing 'constraints' key in {'reconductoring' if reconductoring else 'greenfield'}_congestion_reductions section"
            )
        if "costs" not in congestion_reductions_data:
            raise KeyError(
                f"Missing 'costs' key in {'reconductoring' if reconductoring else 'greenfield'}_congestion_reductions section"
            )
        constraints = congestion_reductions_data["constraints"]
        costs = congestion_reductions_data["costs"]
        required_constraint_keys = [
            "binding_hours",
            "average_exceedance",
            "near_binding_hours",
            "near_average_exceedance",
            "near_binding_relief_factor",
            "saturation_factor",
        ]
        for key in required_constraint_keys:
            if key not in constraints:
                raise KeyError(
                    f"Missing '{key}' key in constraints section of congestion reductions YAML"
                )
        if "average_congestion_price" not in costs:
            raise KeyError(
                "Missing 'average_congestion_price' key in costs section of congestion reductions YAML"
            )
        result = (
            flow_factor,
            constraints["binding_hours"],
            constraints["average_exceedance"],
            constraints["near_binding_hours"],
            constraints["near_average_exceedance"],
            constraints["near_binding_relief_factor"],
            constraints["saturation_factor"],
            costs["average_congestion_price"],
        )
        return result
    except FileNotFoundError:
        raise FileNotFoundError(
            f"Congestion reductions YAML not found at {YAMLS_DIR / '17_congestion_reductions.yaml'}"
        )
    except yaml.YAMLError as e:
        raise ValueError(f"Error parsing congestion reductions YAML: {e}")
    except KeyError as e:
        raise KeyError(f"Missing required key in congestion reductions YAML: {e}")


def load_curtailment_reductions() -> Tuple[float, float, float, float]:
    """Load curtailment reductions parameters from YAML."""
    try:
        with open(YAMLS_DIR / "18_curtailment_reductions.yaml", "r") as f:
            data = yaml.safe_load(f)
        if not data:
            raise ValueError("Curtailment reductions YAML file is empty or invalid")
        if "curtailment_reductions" not in data:
            raise KeyError("Missing 'curtailment_reductions' key in YAML file")
        curtailment_reductions_data = data["curtailment_reductions"]
        return (
            float(curtailment_reductions_data.get("curtailment_hours_total", 0)),
            float(curtailment_reductions_data.get("average_curtailment_mw", 0)),
            float(curtailment_reductions_data.get("average_curtailment_price", 0)),
            float(curtailment_reductions_data.get("curtailment_saturation_factor", 0)),
        )
    except FileNotFoundError:
        raise FileNotFoundError(
            f"Curtailment reductions YAML not found at {YAMLS_DIR / '18_curtailment_reductions.yaml'}"
        )
    except yaml.YAMLError as e:
        raise ValueError(f"Error parsing curtailment reductions YAML: {e}")
    except KeyError as e:
        raise KeyError(f"Missing required key in curtailment reductions YAML: {e}")
    except (ValueError, TypeError) as e:
        raise ValueError(f"Error converting curtailment reduction values to float: {e}")


def load_contingencies() -> Dict[str, float]:
    """Load contingencies from financing YAML."""
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


def load_physical_details_detailed() -> (
    Tuple[float, float, float, float, float, float, float, float, float, float]
):
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
        return (
            sum(v if v is not None else 0 for v in terrain.values()),  # total_miles
            safe_get("forested"),
            safe_get("scrubbed_flat"),
            safe_get("wetland"),
            safe_get("farmland"),
            safe_get("desert_barren"),
            safe_get("urban"),
            safe_get("rolling_hills"),
            safe_get("mountain"),
            safe_get("subsea"),
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


def load_primary_bcr_config() -> Dict[str, Dict[str, bool]]:
    """
    Load Primary BCR configuration from YAML file.
    
    Returns:
        Dictionary with module enable/disable flags grouped by category.
        If file doesn't exist, returns default (all enabled).
        
    Structure:
        {
            "operational": {"oandm": True, "insurance": True, "delay_costs": True},
            "risk": {"wildfire": True, "outages": True},
            "energy": {"line_losses": True, "emissions": True},
            "benefits": {"congestion": True, "curtailment": True}
        }
    """
    # Default configuration (all modules enabled)
    default_config = {
        "operational": {
            "oandm": True,
            "insurance": True,
            "delay_costs": True,
        },
        "risk": {
            "wildfire": True,
            "outages": True,
        },
        "energy": {
            "line_losses": True,
            "emissions": True,
        },
        "benefits": {
            "congestion": True,
            "curtailment": True,
        },
    }
    
    config_path = YAMLS_DIR / "22_primary_bcr_config.yaml"
    
    # If file doesn't exist, return default
    if not config_path.exists():
        return default_config
    
    try:
        with open(config_path, "r") as file:
            config_data = yaml.safe_load(file)
        
        if not config_data:
            # Empty file, return default
            return default_config
        
        if "primary_bcr_config" not in config_data:
            # Missing top-level key, return default
            return default_config
        
        config = config_data["primary_bcr_config"]
        
        # Merge with defaults to handle missing keys
        result = {}
        for category in ["operational", "risk", "energy", "benefits"]:
            result[category] = {}
            category_config = config.get(category, {})
            # Use defaults for each module if not specified
            for module, default_value in default_config[category].items():
                result[category][module] = category_config.get(module, default_value)
        
        return result
        
    except yaml.YAMLError as e:
        # Invalid YAML, return default with warning
        import warnings
        warnings.warn(
            f"Error parsing Primary BCR config YAML: {e}. Using default (all modules enabled)."
        )
        return default_config
    except Exception as e:
        # Any other error, return default with warning
        import warnings
        warnings.warn(
            f"Error loading Primary BCR config: {e}. Using default (all modules enabled)."
        )
        return default_config
