# Author: Andrew Igdal
# Date: 2025-10-27
# Description: This script calculates the O&M costs for a transmission line project.
#              It calculates O&M costs for conductors, converters, and structures.

import math
import yaml


def load_financing_details():
    """
    Load financing parameters and calculate real WACC using Fisher equation.

    Returns:
        tuple: (inflation_rate, base_year, wacc_nominal, wacc_real)
    """
    with open("../yamls/03_financing.yaml", "r") as file:
        financing_data = yaml.load(file, Loader=yaml.FullLoader)

    inflation_rate = financing_data["financial"]["inflation_rate"]
    base_year = financing_data["financial"]["base_year"]
    wacc_nominal = financing_data["financial"]["wacc_nominal"]

    # Use Fisher equation to convert nominal WACC to real WACC
    wacc_real = (1 + wacc_nominal) / (1 + inflation_rate) - 1

    return inflation_rate, base_year, wacc_nominal, wacc_real


def calculate_present_value(annual_cost, wacc_real, total_years, start_year=1):
    """
    Calculate the present value of annual payments over a given time period.

    Args:
        annual_cost (float): Annual cost amount
        wacc_real (float): Real weighted average cost of capital (discount rate)
        total_years (int): Number of years over which payments occur
        start_year (int): Year when payments begin (default: 1)

    Returns:
        float: Present value of the payment stream
    """
    n_full_years = math.floor(total_years)
    frac = total_years - n_full_years
    total_pv = 0
    for year in range(n_full_years):
        t = start_year + year
        total_pv += annual_cost / (1 + wacc_real) ** t

    if frac > 0:
        t_frac = start_year + n_full_years + frac
        total_pv += annual_cost * frac / (1 + wacc_real) ** t_frac

    return total_pv


def load_project_technical_details():
    """
    Load project technical details and construct category identifier.

    The category identifier follows the format:
    "construction_type/AC_or_DC/capacity_MW/conductor_type/converter_type"

    Returns:
        tuple: (category, delay_year, construction_years, project_lifetime, reconductoring)
    """
    with open("../yamls/01_project_technical_details.yaml", "r") as file:
        project_details = yaml.load(file, Loader=yaml.FullLoader)

    # Extract project specifications
    construction_type = project_details["project"]["construction_type"]
    ac_dc = project_details["project"]["ac_dc"]
    capacity_mw = project_details["project"]["capacity_mw"]
    conductor_type = project_details["project"]["conductor_type"]

    if ac_dc == "AC":
        converter_type = "NA"
    else:
        converter_type = project_details["project"]["converter_type"]

    line_utilization = project_details["project"]["line_utilization"]
    reconductoring = project_details["project"]["reconductoring"]

    delay_years = project_details["timeline"]["delay_years"]
    construction_years = project_details["timeline"]["construction_years"]
    project_lifetime = project_details["timeline"]["project_lifetime"]

    return (
        construction_type,
        ac_dc,
        capacity_mw,
        conductor_type,
        converter_type,
        line_utilization,
        reconductoring,
        delay_years,
        construction_years,
        project_lifetime,
    )


def load_physical_details():
    """
    Load physical project details and calculate total miles.

    Returns:
        float: Total miles of transmission line across all terrain types
    """
    with open("../yamls/02_project_physical_details.yaml", "r") as file:
        physical_details = yaml.load(file, Loader=yaml.FullLoader)

    # Sum miles across all terrain types to get total line length
    forested_miles = physical_details["terrain"]["terrain_miles"]["forested"]
    scrubbed_flat_miles = physical_details["terrain"]["terrain_miles"]["scrubbed_flat"]
    wetland_miles = physical_details["terrain"]["terrain_miles"]["wetland"]
    farmland_miles = physical_details["terrain"]["terrain_miles"]["farmland"]
    desert_barren_miles = physical_details["terrain"]["terrain_miles"]["desert_barren"]
    urban_miles = physical_details["terrain"]["terrain_miles"]["urban"]
    rolling_hills_miles = physical_details["terrain"]["terrain_miles"]["rolling_hills"]
    mountain_miles = physical_details["terrain"]["terrain_miles"]["mountain"]
    subsea_miles = physical_details["terrain"]["terrain_miles"]["subsea"]
    total_miles = (
        forested_miles
        + scrubbed_flat_miles
        + wetland_miles
        + farmland_miles
        + desert_barren_miles
        + urban_miles
        + rolling_hills_miles
        + mountain_miles
        + subsea_miles
    )
    return (
        total_miles,
        forested_miles,
        scrubbed_flat_miles,
        wetland_miles,
        farmland_miles,
        desert_barren_miles,
        urban_miles,
        rolling_hills_miles,
        mountain_miles,
        subsea_miles,
    )


def load_vegetation_management_om_costs(construction_type):
    """
    Load vegetation management O&M costs from YAML file.

    Args:
        construction_type: Type of construction (Overhead/Subsea)

    Returns:
        float: Variable vegetation management cost per mile per year
    """
    with open("../yamls/12_project_om_vegetation_management.yaml", "r") as file:
        vegetation_management_om_costs = yaml.load(file, Loader=yaml.FullLoader)[
            "vegetation_management_om_costs"
        ]

    return vegetation_management_om_costs[construction_type]


def load_conductor_om_costs(
    construction_type, ac_dc, capacity_mw, conductor_type, converter_type
):
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
    with open("../yamls/13_category_om_conductors.yaml", "r") as file:
        conductor_om_costs = yaml.load(file, Loader=yaml.FullLoader)[
            "project_categories_om_conductors"
        ]

    category = (
        f"{construction_type}/{ac_dc}/{capacity_mw}MW/{conductor_type}/{converter_type}"
    )

    variable_conductor_cost_per_mile_year = conductor_om_costs[category][
        "variable_cost_per_mile_year"
    ]

    return variable_conductor_cost_per_mile_year


def load_converter_om_costs(
    construction_type, ac_dc, capacity_mw, conductor_type, converter_type
):
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
    with open("../yamls/15_category_om_converters.yaml", "r") as file:
        converter_om_costs = yaml.load(file, Loader=yaml.FullLoader)[
            "project_categories_om_converters"
        ]

    if ac_dc == "AC":
        print("AC Project detected. No converter O&M costs needed.")
        return 0
    else:
        category = f"{construction_type}/{ac_dc}/{capacity_mw}MW/{conductor_type}/{converter_type}"

        variable_converter_cost_per_mile_year = converter_om_costs[category][
            "converter_om_cost_per_mile_year"
        ]

        return variable_converter_cost_per_mile_year


def load_structure_om_costs(
    construction_type,
    forested_miles,
    scrubbed_flat_miles,
    wetland_miles,
    farmland_miles,
    desert_barren_miles,
    urban_miles,
    rolling_hills_miles,
    mountain_miles,
    subsea_miles,
):
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
    with open("../yamls/14_category_om_structures.yaml", "r") as file:
        structure_om_costs = yaml.load(file, Loader=yaml.FullLoader)[
            "project_categories_om_structures"
        ]

    category = construction_type
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


def main():
    (
        construction_type,
        ac_dc,
        capacity_mw,
        conductor_type,
        converter_type,
        line_utilization,
        reconductoring,
        delay_years,
        construction_years,
        project_lifetime,
    ) = load_project_technical_details()
    (
        total_miles,
        forested_miles,
        scrubbed_flat_miles,
        wetland_miles,
        farmland_miles,
        desert_barren_miles,
        urban_miles,
        rolling_hills_miles,
        mountain_miles,
        subsea_miles,
    ) = load_physical_details()
    inflation_rate, base_year, wacc_nominal, wacc_real = load_financing_details()
    variable_conductor_cost_per_mile_year = load_conductor_om_costs(
        construction_type, ac_dc, capacity_mw, conductor_type, converter_type
    )
    variable_converter_cost_per_mile_year = load_converter_om_costs(
        construction_type, ac_dc, capacity_mw, conductor_type, converter_type
    )

    (
        variable_structure_cost_per_mile_year,
        variable_structure_cost_per_year,
        structure_dict,
        total_vegetation_management_cost_per_year,
    ) = load_structure_om_costs(
        construction_type,
        forested_miles,
        scrubbed_flat_miles,
        wetland_miles,
        farmland_miles,
        desert_barren_miles,
        urban_miles,
        rolling_hills_miles,
        mountain_miles,
        subsea_miles,
    )

    # Calculate annual costs
    total_conductor_cost_per_year = variable_conductor_cost_per_mile_year * total_miles
    total_converter_cost_per_year = variable_converter_cost_per_mile_year * total_miles

    # Calculate lifetime costs (undiscounted)
    total_structure_cost_lifetime = variable_structure_cost_per_year * project_lifetime
    total_conductor_cost_lifetime = total_conductor_cost_per_year * project_lifetime
    total_converter_cost_lifetime = total_converter_cost_per_year * project_lifetime
    total_vegetation_management_cost_lifetime = (
        total_vegetation_management_cost_per_year * project_lifetime
    )

    # Calculate present values
    pv_conductor = calculate_present_value(
        total_conductor_cost_per_year, wacc_real, project_lifetime, start_year=1
    )
    pv_converter = calculate_present_value(
        total_converter_cost_per_year, wacc_real, project_lifetime, start_year=1
    )
    pv_structure = calculate_present_value(
        variable_structure_cost_per_year, wacc_real, project_lifetime, start_year=1
    )
    pv_vegetation_management = calculate_present_value(
        total_vegetation_management_cost_per_year,
        wacc_real,
        project_lifetime,
        start_year=1,
    )
    pv_total = pv_conductor + pv_converter + pv_structure + pv_vegetation_management

    # Print results
    print("\n" + "=" * 80)
    print("O&M COST ANALYSIS")
    print("=" * 80)

    print("\n--- Project Overview ---")
    print(f"Construction Type: {construction_type}")
    print(f"Total Line Length: {total_miles:.2f} miles")
    print(f"Project Lifetime: {project_lifetime} years")

    # Print structure information for overhead projects
    if construction_type == "Overhead" and structure_dict:
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
    if construction_type == "Overhead":
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
    print(f"Real WACC: {wacc_real:.4f}")
    print(f"PV Conductor:  ${pv_conductor:,.2f}")
    print(f"PV Converter:  ${pv_converter:,.2f}")
    print(f"PV Structure:  ${pv_structure:,.2f}")
    print(f"PV Vegetation Management:  ${pv_vegetation_management:,.2f}")
    print(f"{'─' * 40}")
    print(f"PV Total:      ${pv_total:,.2f}")
    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
