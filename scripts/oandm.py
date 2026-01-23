# Author: Andrew Igdal
# Date: 2025-10-27
# Description: This script calculates the O&M costs for a transmission line project.
#              It calculates O&M costs for conductors, converters, and structures.

from __future__ import annotations

# Standard library imports
import yaml
import sys
import os
from typing import Dict, Tuple

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from smart_output import CTCCOutputManager

# Local utility imports
from yaml_loaders import (
    load_financing_details,
    load_project_technical_details,
    load_physical_details_detailed,
    load_circuit_and_resistance_details,
)
from financial_utils import calculate_present_value, calculate_cod_year
from calculation_utils import build_category_string
from path_config import YAMLS_DIR


def load_vegetation_management_om_costs(construction_type: str) -> Dict[str, float]:
    """
    Load vegetation management O&M costs from YAML file.

    Args:
        construction_type: Type of construction (Overhead/Subsea)

    Returns:
        float: Variable vegetation management cost per mile per year
    """
    try:
        with open(YAMLS_DIR / "12_project_om_vegetation_management.yaml", "r") as file:
            data = yaml.safe_load(file)
        if not data:
            raise ValueError("Vegetation management O&M YAML file is empty or invalid")
        if "vegetation_management_om_costs" not in data:
            raise KeyError("Missing 'vegetation_management_om_costs' key in YAML file")
        vegetation_management_om_costs = data["vegetation_management_om_costs"]
        if construction_type not in vegetation_management_om_costs:
            raise KeyError(
                f"Construction type '{construction_type}' not found in vegetation management O&M YAML"
            )
        return vegetation_management_om_costs[construction_type]
    except FileNotFoundError:
        raise FileNotFoundError(
            f"Vegetation management O&M YAML not found at {YAMLS_DIR / '12_project_om_vegetation_management.yaml'}"
        )
    except yaml.YAMLError as e:
        raise ValueError(f"Error parsing vegetation management O&M YAML: {e}")
    except KeyError as e:
        raise KeyError(f"Missing required key in vegetation management O&M YAML: {e}")


def load_conductor_om_costs(
    construction_type: str,
    ac_dc: str,
    capacity_mw: int,
    conductor_type: str,
    converter_type: str,
) -> float:
    """
    Load conductor O&M costs from YAML file.

    Args:
        construction_type: Type of construction (Overhead/Subsea)
        ac_dc: AC or DC designation
        capacity_mw: Capacity in megawatts
        conductor_type: Type of conductor
        converter_type: Type of converter

    Returns:
        float: Variable conductor cost per mile per year
    """
    try:
        with open(YAMLS_DIR / "13_category_om_conductors.yaml", "r") as file:
            data = yaml.safe_load(file)
        if not data:
            raise ValueError("Conductor O&M YAML file is empty or invalid")
        if "project_categories_om_conductors" not in data:
            raise KeyError(
                "Missing 'project_categories_om_conductors' key in YAML file"
            )
        conductor_om_costs = data["project_categories_om_conductors"]

        category = build_category_string(construction_type, ac_dc, capacity_mw, conductor_type, converter_type)

        if category not in conductor_om_costs:
            raise KeyError(f"Category '{category}' not found in conductor O&M YAML")
        if "variable_cost_per_mile_year" not in conductor_om_costs[category]:
            raise KeyError(
                f"Missing 'variable_cost_per_mile_year' key for category '{category}' in conductor O&M YAML"
            )

        variable_conductor_cost_per_mile_year = conductor_om_costs[category][
            "variable_cost_per_mile_year"
        ]

        return variable_conductor_cost_per_mile_year
    except FileNotFoundError:
        raise FileNotFoundError(
            f"Conductor O&M YAML not found at {YAMLS_DIR / '13_category_om_conductors.yaml'}"
        )
    except yaml.YAMLError as e:
        raise ValueError(f"Error parsing conductor O&M YAML: {e}")
    except KeyError as e:
        raise KeyError(f"Missing required key in conductor O&M YAML: {e}")


def load_converter_om_costs(
    construction_type: str,
    ac_dc: str,
    capacity_mw: int,
    conductor_type: str,
    converter_type: str,
) -> float:
    """
    Load converter O&M costs from YAML file.

    Args:
        construction_type: Type of construction (Overhead/Subsea)
        ac_dc: AC or DC designation
        capacity_mw: Capacity in megawatts
        conductor_type: Type of conductor
        converter_type: Type of converter

    Returns:
        float: Variable converter cost per mile per year (0 for AC projects)
    """
    try:
        with open(YAMLS_DIR / "15_category_om_converters.yaml", "r") as file:
            data = yaml.safe_load(file)
        if not data:
            raise ValueError("Converter O&M YAML file is empty or invalid")
        if "project_categories_om_converters" not in data:
            raise KeyError(
                "Missing 'project_categories_om_converters' key in YAML file"
            )
        converter_om_costs = data["project_categories_om_converters"]

        if ac_dc == "AC":
            print("AC Project detected. No converter O&M costs needed.")
            return 0
        else:
            from calculation_utils import build_category_string
            category = build_category_string(construction_type, ac_dc, capacity_mw, conductor_type, converter_type)

            if category not in converter_om_costs:
                raise KeyError(f"Category '{category}' not found in converter O&M YAML")
            if "converter_om_cost_per_mile_year" not in converter_om_costs[category]:
                raise KeyError(
                    f"Missing 'converter_om_cost_per_mile_year' key for category '{category}' in converter O&M YAML"
                )

            variable_converter_cost_per_mile_year = converter_om_costs[category][
                "converter_om_cost_per_mile_year"
            ]

            return variable_converter_cost_per_mile_year
    except FileNotFoundError:
        raise FileNotFoundError(
            f"Converter O&M YAML not found at {YAMLS_DIR / '15_category_om_converters.yaml'}"
        )
    except yaml.YAMLError as e:
        raise ValueError(f"Error parsing converter O&M YAML: {e}")
    except KeyError as e:
        raise KeyError(f"Missing required key in converter O&M YAML: {e}")


def load_structure_om_costs(
    construction_type: str,
    forested_miles: float,
    scrubbed_flat_miles: float,
    wetland_miles: float,
    farmland_miles: float,
    desert_barren_miles: float,
    urban_miles: float,
    rolling_hills_miles: float,
    mountain_miles: float,
    subsea_miles: float,
) -> Tuple[float, float, Dict[str, int], float]:
    """
    Load structure O&M costs from YAML file and calculate total costs.

    Args:
        construction_type: Type of construction (Overhead/Subsea)
        forested_miles: Miles of forested terrain
        scrubbed_flat_miles: Miles of scrubbed flat terrain
        wetland_miles: Miles of wetland terrain
        farmland_miles: Miles of farmland terrain
        desert_barren_miles: Miles of desert/barren terrain
        urban_miles: Miles of urban terrain
        rolling_hills_miles: Miles of rolling hills terrain
        mountain_miles: Miles of mountain terrain
        subsea_miles: Miles of subsea terrain

    Returns:
        tuple: (variable_structure_cost_per_mile_year, variable_structure_cost_per_year, structure_dict)
    """

    # Initialize vegetation
    total_vegetation_management_cost_per_year = 0

    try:
        with open(YAMLS_DIR / "14_category_om_structures.yaml", "r") as file:
            data = yaml.safe_load(file)
        if not data:
            raise ValueError("Structure O&M YAML file is empty or invalid")
        if "project_categories_om_structures" not in data:
            raise KeyError(
                "Missing 'project_categories_om_structures' key in YAML file"
            )
        structure_om_costs = data["project_categories_om_structures"]

        category = construction_type
        if category not in structure_om_costs:
            raise KeyError(
                f"Construction type '{category}' not found in structure O&M YAML"
            )
    except FileNotFoundError:
        raise FileNotFoundError(
            f"Structure O&M YAML not found at {YAMLS_DIR / '14_category_om_structures.yaml'}"
        )
    except yaml.YAMLError as e:
        raise ValueError(f"Error parsing structure O&M YAML: {e}")
    except KeyError as e:
        raise KeyError(f"Missing required key in structure O&M YAML: {e}")

    # Continue with rest of function using structure_om_costs
    structure_dict = {}

    if construction_type == "Overhead":
        structures_per_mile_forested = structure_om_costs[category][
            "structures_per_mile_forested"
        ]
        structures_per_mile_scrubbed_flat = structure_om_costs[category][
            "structures_per_mile_scrubbed_flat"
        ]
        structures_per_mile_wetland = structure_om_costs[category][
            "structures_per_mile_wetland"
        ]
        structures_per_mile_farmland = structure_om_costs[category][
            "structures_per_mile_farmland"
        ]
        structures_per_mile_desert_barren = structure_om_costs[category][
            "structures_per_mile_desert_barren"
        ]
        structures_per_mile_urban = structure_om_costs[category][
            "structures_per_mile_urban"
        ]
        structures_per_mile_rolling_hills = structure_om_costs[category][
            "structures_per_mile_rolling_hills"
        ]
        structures_per_mile_mountain = structure_om_costs[category][
            "structures_per_mile_mountain"
        ]

        forested_structures = forested_miles * structures_per_mile_forested
        scrubbed_flat_structures = (
            scrubbed_flat_miles * structures_per_mile_scrubbed_flat
        )
        wetland_structures = wetland_miles * structures_per_mile_wetland
        farmland_structures = farmland_miles * structures_per_mile_farmland
        desert_barren_structures = (
            desert_barren_miles * structures_per_mile_desert_barren
        )
        urban_structures = urban_miles * structures_per_mile_urban
        rolling_hills_structures = (
            rolling_hills_miles * structures_per_mile_rolling_hills
        )
        mountain_structures = mountain_miles * structures_per_mile_mountain
        subsea_structures = 0  # No structures for subsea terrain

        total_structures = (
            forested_structures
            + scrubbed_flat_structures
            + wetland_structures
            + farmland_structures
            + desert_barren_structures
            + urban_structures
            + rolling_hills_structures
            + mountain_structures
            + subsea_structures
        )

        variable_structure_cost_per_year = (
            structure_om_costs[category]["cost_per_structure_per_year"]
            * total_structures
        )
        variable_structure_cost_per_mile_year = 0

        # Store structure info for printing
        structure_dict = {
            "total": total_structures,
            "forested": forested_structures,
            "scrubbed_flat": scrubbed_flat_structures,
            "wetland": wetland_structures,
            "farmland": farmland_structures,
            "desert_barren": desert_barren_structures,
            "urban": urban_structures,
            "rolling_hills": rolling_hills_structures,
            "mountain": mountain_structures,
            "subsea": subsea_structures,
        }

        vegetation_management_cost_per_mile_year = load_vegetation_management_om_costs(
            construction_type
        )

        # should be multiplying the different veg amangement for each terrain type by the miles of that terrain type
        forested_vegetation_management_cost_per_year = (
            forested_miles * vegetation_management_cost_per_mile_year["forested"]
        )
        scrubbed_flat_vegetation_management_cost_per_year = (
            scrubbed_flat_miles
            * vegetation_management_cost_per_mile_year["scrubbed_flat"]
        )
        wetland_vegetation_management_cost_per_year = (
            wetland_miles * vegetation_management_cost_per_mile_year["wetland"]
        )
        farmland_vegetation_management_cost_per_year = (
            farmland_miles * vegetation_management_cost_per_mile_year["farmland"]
        )
        desert_barren_vegetation_management_cost_per_year = (
            desert_barren_miles
            * vegetation_management_cost_per_mile_year["desert_barren"]
        )
        urban_vegetation_management_cost_per_year = (
            urban_miles * vegetation_management_cost_per_mile_year["urban"]
        )
        rolling_hills_vegetation_management_cost_per_year = (
            rolling_hills_miles
            * vegetation_management_cost_per_mile_year["rolling_hills"]
        )
        mountain_vegetation_management_cost_per_year = (
            mountain_miles * vegetation_management_cost_per_mile_year["mountain"]
        )
        subsea_vegetation_management_cost_per_year = (
            subsea_miles * vegetation_management_cost_per_mile_year["subsea"]
        )

        total_vegetation_management_cost_per_year = (
            forested_vegetation_management_cost_per_year
            + scrubbed_flat_vegetation_management_cost_per_year
            + wetland_vegetation_management_cost_per_year
            + farmland_vegetation_management_cost_per_year
            + desert_barren_vegetation_management_cost_per_year
            + urban_vegetation_management_cost_per_year
            + rolling_hills_vegetation_management_cost_per_year
            + mountain_vegetation_management_cost_per_year
            + subsea_vegetation_management_cost_per_year
        )

        variable_structure_cost_per_year += total_vegetation_management_cost_per_year

    else:
        variable_structure_cost_per_year = 0
        variable_structure_cost_per_mile_year = structure_om_costs[category][
            "variable_cost_per_mile_year"
        ]

    return (
        variable_structure_cost_per_mile_year,
        variable_structure_cost_per_year,
        structure_dict,
        total_vegetation_management_cost_per_year,
    )


def main() -> None:
    project_details = load_project_technical_details()
    physical_details = load_physical_details_detailed()
    financing = load_financing_details()
    variable_conductor_cost_per_mile_year = load_conductor_om_costs(
        project_details.construction_type, project_details.ac_dc, project_details.capacity_mw, project_details.conductor_type, project_details.converter_type
    )
    variable_converter_cost_per_mile_year = load_converter_om_costs(
        project_details.construction_type, project_details.ac_dc, project_details.capacity_mw, project_details.conductor_type, project_details.converter_type
    )

    (
        variable_structure_cost_per_mile_year,
        variable_structure_cost_per_year,
        structure_dict,
        total_vegetation_management_cost_per_year,
    ) = load_structure_om_costs(
        project_details.construction_type,
        physical_details.forested_miles,
        physical_details.scrubbed_flat_miles,
        physical_details.wetland_miles,
        physical_details.farmland_miles,
        physical_details.desert_barren_miles,
        physical_details.urban_miles,
        physical_details.rolling_hills_miles,
        physical_details.mountain_miles,
        physical_details.subsea_miles,
    )

    # Calculate annual costs
    total_conductor_cost_per_year = variable_conductor_cost_per_mile_year * physical_details.total_miles
    total_converter_cost_per_year = variable_converter_cost_per_mile_year * physical_details.total_miles

    # Calculate lifetime costs (undiscounted)
    total_structure_cost_lifetime = variable_structure_cost_per_year * project_details.project_lifetime
    total_conductor_cost_lifetime = total_conductor_cost_per_year * project_details.project_lifetime
    total_converter_cost_lifetime = total_converter_cost_per_year * project_details.project_lifetime
    total_vegetation_management_cost_lifetime = (
        total_vegetation_management_cost_per_year * project_details.project_lifetime
    )

    # Calculate present values
    # O&M costs start at first year of operation (COD)
    oandm_start_year = calculate_cod_year(project_details.delay_years, project_details.construction_years)
    pv_conductor = calculate_present_value(
        total_conductor_cost_per_year,
        financing.wacc_real,
        project_details.project_lifetime,
        start_year=oandm_start_year,
    )
    pv_converter = calculate_present_value(
        total_converter_cost_per_year,
        financing.wacc_real,
        project_details.project_lifetime,
        start_year=oandm_start_year,
    )
    pv_structure = calculate_present_value(
        variable_structure_cost_per_year,
        financing.wacc_real,
        project_details.project_lifetime,
        start_year=oandm_start_year,
    )
    pv_vegetation_management = calculate_present_value(
        total_vegetation_management_cost_per_year,
        financing.wacc_real,
        project_details.project_lifetime,
        start_year=oandm_start_year,
    )
    pv_total = pv_conductor + pv_converter + pv_structure + pv_vegetation_management

    # Print results
    print("\n" + "=" * 80)
    print("O&M COST ANALYSIS")
    print("=" * 80)

    print("\n--- Project Overview ---")
    print(f"Construction Type: {project_details.construction_type}")
    print(f"Total Line Length: {physical_details.total_miles:.2f} miles")
    print(f"Project Lifetime: {project_details.project_lifetime} years")

    # Print structure information for overhead projects
    if project_details.construction_type == "Overhead" and structure_dict:
        print("\n--- Structure Information ---")
        print(f"Total Structures: {int(structure_dict['total'])}")
        print("\nStructures by Terrain Type:")
        terrain_names = {
            "forested": "Forested",
            "scrubbed_flat": "Scrubbed Flat",
            "wetland": "Wetland",
            "farmland": "Farmland",
            "desert_barren": "Desert/Barren",
            "urban": "Urban",
            "rolling_hills": "Rolling Hills",
            "mountain": "Mountain",
            "subsea": "Subsea",
        }
        for key, label in terrain_names.items():
            structures = int(structure_dict[key])
            if structures > 0 or key in [
                "forested",
                "scrubbed_flat",
            ]:  # Show at least common terrains
                print(f"  {label:20s}: {structures:6d}")

    print("\n--- Unit Costs (per mile per year) ---")
    print(f"Conductor:  ${variable_conductor_cost_per_mile_year:,.2f}")
    print(f"Converter:  ${variable_converter_cost_per_mile_year:,.2f}")
    if project_details.construction_type == "Overhead":
        print(f"Structure:  ${variable_structure_cost_per_year:,.2f} (total per year)")
    else:
        print(f"Structure:  ${variable_structure_cost_per_mile_year:,.2f}")

    print("\n--- Annual Total Costs ---")
    print(f"Conductor:  ${total_conductor_cost_per_year:,.2f}")
    print(f"Converter:  ${total_converter_cost_per_year:,.2f}")
    print(f"Structure:  ${variable_structure_cost_per_year:,.2f}")
    print(f"Vegetation Management:  ${total_vegetation_management_cost_per_year:,.2f}")
    print(f"{'─' * 40}")
    print(
        f"Total:      ${total_conductor_cost_per_year + total_converter_cost_per_year + variable_structure_cost_per_year + total_vegetation_management_cost_per_year:,.2f}"
    )

    print("\n--- Lifetime Total Costs (Undiscounted) ---")
    print(f"Conductor:  ${total_conductor_cost_lifetime:,.2f}")
    print(f"Converter:  ${total_converter_cost_lifetime:,.2f}")
    print(f"Structure:  ${total_structure_cost_lifetime:,.2f}")
    print(f"Vegetation Management:  ${total_vegetation_management_cost_lifetime:,.2f}")
    print(f"{'─' * 40}")
    print(
        f"Total:      ${total_conductor_cost_lifetime + total_converter_cost_lifetime + total_structure_cost_lifetime + total_vegetation_management_cost_lifetime:,.2f}"
    )

    print("\n--- Present Value Calculations ---")
    print(f"Real WACC: {financing.wacc_real:.4f}")
    print(f"PV Conductor:  ${pv_conductor:,.2f}")
    print(f"PV Converter:  ${pv_converter:,.2f}")
    print(f"PV Structure:  ${pv_structure:,.2f}")
    print(f"PV Vegetation Management:  ${pv_vegetation_management:,.2f}")
    print(f"{'─' * 40}")
    print(f"PV Total:      ${pv_total:,.2f}")
    print("\n" + "=" * 80)

    # ========================================================================
    # CSV OUTPUT - Write results to batch summary and detail CSV
    # ========================================================================

    # Initialize CSV output manager
    csv_manager = CTCCOutputManager()

    # Calculate total annual cost
    total_annual = (
        total_conductor_cost_per_year
        + total_converter_cost_per_year
        + variable_structure_cost_per_year
        + total_vegetation_management_cost_per_year
    )

    # Calculate total nominal cost
    total_nominal = (
        total_conductor_cost_lifetime
        + total_converter_cost_lifetime
        + total_structure_cost_lifetime
        + total_vegetation_management_cost_lifetime
    )

    # Prepare results dictionary
    results = {
        "total_annual": total_annual,
        "total_nominal": total_nominal,
        "total_pv": pv_total,
        "conductor_annual": total_conductor_cost_per_year,
        "conductor_nominal": total_conductor_cost_lifetime,
        "conductor_pv": pv_conductor,
        "converter_annual": total_converter_cost_per_year,
        "converter_nominal": total_converter_cost_lifetime,
        "converter_pv": pv_converter,
        "structure_annual": variable_structure_cost_per_year,
        "structure_nominal": total_structure_cost_lifetime,
        "structure_pv": pv_structure,
        "vegetation_annual": total_vegetation_management_cost_per_year,
        "vegetation_nominal": total_vegetation_management_cost_lifetime,
        "vegetation_pv": pv_vegetation_management,
    }

    # Write to CSV
    csv_manager.add_oandm_costs(results)
    csv_manager.write_batch_summary()


if __name__ == "__main__":
    main()
