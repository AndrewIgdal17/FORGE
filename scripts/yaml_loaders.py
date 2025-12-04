# Author: Andrew Igdal
# Date: 2025-01-XX
# Description: Centralized YAML loading utilities for transmission cost calculator.

import yaml


def load_financing_details():
    """Load financing parameters and calculate real WACC using Fisher equation."""
    with open("../yamls/03_financing.yaml", "r") as file:
        financing_data = yaml.load(file, Loader=yaml.FullLoader)
    inflation_rate = financing_data["financial"]["inflation_rate"]
    base_year = financing_data["financial"]["base_year"]
    wacc_nominal = financing_data["financial"]["wacc_nominal"]
    wacc_real = (1 + wacc_nominal) / (1 + inflation_rate) - 1
    return inflation_rate, base_year, wacc_nominal, wacc_real


def load_project_technical_details():
    """Load project technical details - returns all project specs."""
    with open("../yamls/01_project_technical_details.yaml", "r") as file:
        project_details = yaml.load(file, Loader=yaml.FullLoader)
    pd = project_details["project"]
    tl = project_details["timeline"]
    construction_type = pd["construction_type"]
    ac_dc = pd["ac_dc"]
    capacity_mw = pd["capacity_mw"]
    conductor_type = pd["conductor_type"]
    converter_type = "NA" if ac_dc == "AC" else pd["converter_type"]
    return (
        construction_type,
        ac_dc,
        capacity_mw,
        conductor_type,
        converter_type,
        pd["line_utilization"],
        pd["reconductoring"],
        tl["delay_years"],
        tl["construction_years"],
        tl["project_lifetime"],
    )


def load_physical_details():
    """Load physical project details - return total miles only."""
    with open("../yamls/02_project_physical_details.yaml", "r") as file:
        terrain_miles = yaml.load(file, Loader=yaml.FullLoader)["terrain"][
            "terrain_miles"
        ]
        # Handle None values by treating them as 0
        return sum(v if v is not None else 0 for v in terrain_miles.values())


def load_circuit_and_resistance_details(category):
    """Load circuit and resistance details for specified category."""
    with open(
        "../yamls/21_project_category_circuit_and_resistance_detail.yaml", "r"
    ) as file:
        crd = yaml.load(file, Loader=yaml.FullLoader)[
            "project_categories_circuit_and_resistance_details"
        ]
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
    with open("../yamls/20_project_category_row_widths.yaml", "r") as file:
        row_widths = yaml.load(file, Loader=yaml.FullLoader)
    return row_widths["project_categories_row_widths"][category]["row_width_feet"]


def load_row_details():
    """Load ROW details from YAML."""
    with open("../yamls/11_project_row_details.yaml", "r") as file:
        return yaml.load(file, Loader=yaml.FullLoader)


def load_delay_costs():
    """Load delay costs from YAML."""
    with open("../yamls/05_delays.yaml", "r") as file:
        return yaml.load(file, Loader=yaml.FullLoader)


def load_emissions_details():
    """Load emissions reductions details from YAML."""
    with open("../yamls/16_emissions_reductions.yaml", "r") as file:
        erd = yaml.safe_load(file)["emissions_reductions"]
    return (
        erd["compensation_percent"],
        erd["energy_source_mix"],
        erd["emission_intensities"],
        erd["societal_costs_per_kg"],
    )


def load_congestion_reductions():
    """Load congestion reduction parameters from YAML."""
    with open("../yamls/17_congestion_reductions.yaml", "r") as file:
        cr = yaml.load(file, Loader=yaml.FullLoader)["greenfield_congestion_reductions"]
    return (
        cr["constraints"]["flow_factor"],
        cr["constraints"]["binding_hours"],
        cr["constraints"]["average_exceedance"],
        cr["constraints"]["near_binding_hours"],
        cr["constraints"]["near_average_exceedance"],
        cr["constraints"]["near_binding_relief_factor"],
        cr["constraints"]["saturation_factor"],
        cr["costs"]["average_congestion_price"],
    )


def load_curtailment_reductions():
    """Load curtailment reductions parameters from YAML."""
    with open("../yamls/18_curtailment_reductions.yaml", "r") as f:
        y = yaml.load(f, Loader=yaml.FullLoader)["curtailment_reductions"]
    return (
        float(y.get("curtailment_hours_total", 0)),
        float(y.get("average_curtailment_mw", 0)),
        float(y.get("average_curtailment_price", 0)),
        float(y.get("curtailment_saturation_factor", 0)),
    )


def load_contingencies():
    """Load contingencies from financing YAML."""
    with open("../yamls/03_financing.yaml", "r") as file:
        return yaml.load(file, Loader=yaml.FullLoader)["financial"]["contingencies"]


def load_financing_social_discount_rate():
    """Load social discount rate from financing YAML."""
    with open("../yamls/03_financing.yaml", "r") as file:
        financing_data = yaml.safe_load(file)
    return financing_data["financial"]["social_discount_rate"]


def load_physical_details_detailed():
    """Load physical project details - return detailed terrain breakdown."""
    with open("../yamls/02_project_physical_details.yaml", "r") as file:
        physical_details = yaml.load(file, Loader=yaml.FullLoader)
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


def load_environmental_mitigation():
    """Load environmental mitigation parameters from YAML."""
    with open("../yamls/09_environmental_mitigation.yaml", "r") as file:
        return yaml.load(file, Loader=yaml.FullLoader)


def load_cost_timing_patterns():
    """Load cost timing patterns for AFUDC calculations."""
    with open("../yamls/19_cost_timing_patterns.yaml", "r") as file:
        return yaml.load(file, Loader=yaml.FullLoader)


def load_afudc_config():
    """Load AFUDC configuration from financing YAML."""
    with open("../yamls/03_financing.yaml", "r") as file:
        fin = yaml.load(file, Loader=yaml.FullLoader)
    afudc_cfg = fin["financial"].get("afudc", {})
    return (
        afudc_cfg.get("apply_afudc", False),
        afudc_cfg.get("delay_period_active_work", False),
    )


def load_insurance_details():
    """Load insurance parameters from YAML."""
    with open("../yamls/04_insurance.yaml", "r") as file:
        return yaml.load(file, Loader=yaml.FullLoader)


def load_wildfire_costs():
    """Load wildfire cost parameters from YAML."""
    with open("../yamls/06_wildfire_costs.yaml", "r") as file:
        return yaml.load(file, Loader=yaml.FullLoader)


def load_outage_costs():
    """Load outage cost parameters from YAML."""
    with open("../yamls/07_outage_costs.yaml", "r") as file:
        return yaml.load(file, Loader=yaml.FullLoader)
