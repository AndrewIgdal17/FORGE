# Date: 2025-10-27
# Description: This script calculates the O&M costs for a transmission line project.
#              It calculates O&M costs for conductors, converters, and structures.

from __future__ import annotations

# Standard library imports
import yaml
from typing import Dict

from forge.scripts.utils.smart_output import SmartOutputManager

# Local utility imports
from forge.scripts.io.yaml_loaders import (
    load_financing_details,
    load_project_technical_details,
    load_physical_details_detailed,
)
from forge.scripts.utils.financial_utils import calculate_cod_year, calculate_growing_annuity_pv, calculate_nominal_growing_series
from forge.scripts.utils.path_config import YAMLS_DIR
from forge.scripts.utils.constants import CONSTRUCTION_TYPE_OVERHEAD
from forge.scripts.utils.run_context import get_run_context, add_derived

# All four O&M rate tables (12-15) read through the scenario-aware YAMLS_DIR.
# API-mode scenario customizations to conductor/structure/converter rates
# now take effect the same way vegetation management customizations do.

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

def load_converter_om_costs(
    ac_dc: str,
    converter_type: str,
    construction_type: str,
    capacity_mw: int,
    conductor_type: str,
) -> float:
    """
    Calculate annual converter O&M as r_om,conv × K_converter × ξ_DC.

    K_converter is post-contingency, post-soft-cost total converter CAPEX
    (includes N_conv) from ctx.build_costs. ξ_DC = 1 for DC projects
    (ac_dc == "DC"), else 0 for AC projects.

    Returns:
        float: Total annual converter O&M cost ($/year), NOT per-mile.
    """
    ctx = get_run_context()
    if ctx is None or ctx.build_costs is None:
        raise RuntimeError(
            f"{__name__} requires a RunContext. Run via forge.py or set up "
            "RunContext in your test fixture."
        )
    converter_capex = ctx.build_costs.converter_cost_with_contingencies

    # Appendix §4: ξ_DC gates converter O&M by project type (not upstream CAPEX value)
    xi_dc = 1.0 if ac_dc == "DC" else 0.0

    # Load converter O&M rate by technology type
    try:
        with open(YAMLS_DIR / "15_category_om_converters.yaml", "r") as file:
            data = yaml.safe_load(file)
        if not data or "converter_om_rate" not in data:
            raise ValueError("Missing 'converter_om_rate' key in converter O&M YAML")
        rates = data["converter_om_rate"]
        if converter_type not in rates:
            if xi_dc == 0.0:
                om_rate = 0.0
            else:
                raise KeyError(
                    f"Converter type '{converter_type}' not found in converter_om_rate. "
                    f"Available: {list(rates.keys())}"
                )
        else:
            om_rate = rates[converter_type]
    except FileNotFoundError:
        raise FileNotFoundError(
            f"Converter O&M YAML not found at {YAMLS_DIR / '15_category_om_converters.yaml'}"
        )

    return converter_capex * om_rate * xi_dc

def load_nonoverhead_line_om(
    construction_type: str,
    ac_dc: str,
    capacity_mw: int,
    conductor_type: str,
    converter_type: str,
) -> float:
    """
    Compute total annual line O&M for non-overhead construction types as % of line CAPEX.

    K_line = C_adj,cont,conductor + C_adj,cont,structure (post-contingency,
    post-soft-cost CAPEX from ctx.build_costs; excludes converter stations).
    Rates from 14_category_om_structures.yaml: UG 0.15%, tunnel 0.4%, subsea 2.5%.

    Returns:
        float: Total annual line O&M cost ($/year).
    """
    # Load O&M rate for this construction type
    try:
        with open(YAMLS_DIR / "14_category_om_structures.yaml", "r") as file:
            data = yaml.safe_load(file)
        if not data or "project_categories_om_structures" not in data:
            raise ValueError("Missing 'project_categories_om_structures' in structure O&M YAML")
        entry = data["project_categories_om_structures"].get(construction_type)
        if entry is None:
            raise KeyError(f"Construction type '{construction_type}' not found in structure O&M YAML")
        if "om_pct_of_line_capex" not in entry:
            raise KeyError(
                f"Construction type '{construction_type}' missing 'om_pct_of_line_capex' — "
                "expected non-overhead type"
            )
        om_rate = entry["om_pct_of_line_capex"]
    except FileNotFoundError:
        raise FileNotFoundError(
            f"Structure O&M YAML not found at {YAMLS_DIR / '14_category_om_structures.yaml'}"
        )

    ctx = get_run_context()
    if ctx is None or ctx.build_costs is None:
        raise RuntimeError(
            f"{__name__} requires a RunContext. Run via forge.py or set up "
            "RunContext in your test fixture."
        )
    line_capex = (
        ctx.build_costs.conductor_cost_with_contingencies
        + ctx.build_costs.structure_cost_with_contingencies
    )

    return line_capex * om_rate

def main() -> None:
    project_details = load_project_technical_details()
    physical_details = load_physical_details_detailed()
    financing = load_financing_details()
    # Converter O&M (applies to both overhead and non-overhead DC projects)
    total_converter_cost_per_year = load_converter_om_costs(
        project_details.ac_dc,
        project_details.converter_type,
        project_details.construction_type,
        project_details.capacity_mw,
        project_details.conductor_type,
    )

    if project_details.construction_type == CONSTRUCTION_TYPE_OVERHEAD:
        # Overhead: base O&M rate (flat $/mile) + vegetation management (terrain-specific)
        try:
            with open(YAMLS_DIR / "14_category_om_structures.yaml", "r") as file:
                struct_data = yaml.safe_load(file)
            oh_entry = struct_data["project_categories_om_structures"]["Overhead"]
            base_om_per_mile_year = oh_entry["base_om_per_mile_year"]
        except (FileNotFoundError, KeyError, TypeError) as e:
            raise ValueError(f"Cannot load overhead base O&M rate: {e}")

        om_real_escalation_rate = struct_data["om_real_escalation_rate"]

        base_om_per_year = base_om_per_mile_year * physical_details.total_miles

        # Vegetation management (terrain-specific, from YAML 12)
        vegetation_costs = load_vegetation_management_om_costs(project_details.construction_type)
        total_vegetation_management_cost_per_year = (
            physical_details.forested_miles * vegetation_costs.get("forested", 0)
            + physical_details.scrubbed_flat_miles * vegetation_costs.get("scrubbed_flat", 0)
            + physical_details.wetland_miles * vegetation_costs.get("wetland", 0)
            + physical_details.farmland_miles * vegetation_costs.get("farmland", 0)
            + physical_details.desert_barren_miles * vegetation_costs.get("desert_barren", 0)
            + physical_details.urban_miles * vegetation_costs.get("urban", 0)
            + physical_details.rolling_hills_miles * vegetation_costs.get("rolling_hills", 0)
            + physical_details.mountain_miles * vegetation_costs.get("mountain", 0)
            + physical_details.subsea_miles * vegetation_costs.get("subsea", 0)
        )

        total_line_om_per_year = base_om_per_year + total_vegetation_management_cost_per_year

        # Legacy fields (zeroed — no longer decomposed into conductor/structure)
        total_conductor_cost_per_year = 0.0
        variable_conductor_cost_per_mile_year = 0.0
        variable_structure_cost_per_mile_year = 0.0
        variable_structure_cost_per_year = 0.0
        structure_dict = {}
    else:
        # Non-overhead: total line O&M as % of line CAPEX
        total_line_om_per_year = load_nonoverhead_line_om(
            project_details.construction_type,
            project_details.ac_dc,
            project_details.capacity_mw,
            project_details.conductor_type,
            project_details.converter_type,
        )
        total_conductor_cost_per_year = 0.0
        variable_conductor_cost_per_mile_year = 0.0
        variable_structure_cost_per_mile_year = 0.0
        variable_structure_cost_per_year = 0.0
        total_vegetation_management_cost_per_year = 0.0
        structure_dict = {}

        with open(YAMLS_DIR / "14_category_om_structures.yaml", "r") as file:
            struct_data = yaml.safe_load(file)
        om_real_escalation_rate = struct_data["om_real_escalation_rate"]

    # Calculate lifetime costs (nominal, with real escalation)
    total_structure_cost_lifetime = calculate_nominal_growing_series(
        variable_structure_cost_per_year, om_real_escalation_rate, project_details.project_lifetime,
    )
    total_conductor_cost_lifetime = calculate_nominal_growing_series(
        total_conductor_cost_per_year, om_real_escalation_rate, project_details.project_lifetime,
    )
    total_converter_cost_lifetime = calculate_nominal_growing_series(
        total_converter_cost_per_year, om_real_escalation_rate, project_details.project_lifetime,
    )
    total_vegetation_management_cost_lifetime = calculate_nominal_growing_series(
        total_vegetation_management_cost_per_year, om_real_escalation_rate, project_details.project_lifetime,
    )

    # Calculate present values
    # O&M costs start at first year of operation (COD)
    oandm_start_year = calculate_cod_year(project_details.delay_years, project_details.construction_years)

    if project_details.construction_type == CONSTRUCTION_TYPE_OVERHEAD:
        pv_conductor = 0.0
        pv_structure = 0.0
        pv_vegetation_management = calculate_growing_annuity_pv(
            annual_amount=total_vegetation_management_cost_per_year,
            growth_rate=om_real_escalation_rate,
            discount_rate=financing.wacc_real,
            project_lifetime=project_details.project_lifetime,
            delay_years=project_details.delay_years,
            construction_years=project_details.construction_years,
        )
        pv_line_om = calculate_growing_annuity_pv(
            annual_amount=total_line_om_per_year,
            growth_rate=om_real_escalation_rate,
            discount_rate=financing.wacc_real,
            project_lifetime=project_details.project_lifetime,
            delay_years=project_details.delay_years,
            construction_years=project_details.construction_years,
        )
    else:
        pv_line_om = calculate_growing_annuity_pv(
            annual_amount=total_line_om_per_year,
            growth_rate=om_real_escalation_rate,
            discount_rate=financing.wacc_real,
            project_lifetime=project_details.project_lifetime,
            delay_years=project_details.delay_years,
            construction_years=project_details.construction_years,
        )
        pv_conductor = 0.0
        pv_structure = 0.0
        pv_vegetation_management = 0.0

    pv_converter = calculate_growing_annuity_pv(
        annual_amount=total_converter_cost_per_year,
        growth_rate=om_real_escalation_rate,
        discount_rate=financing.wacc_real,
        project_lifetime=project_details.project_lifetime,
        delay_years=project_details.delay_years,
        construction_years=project_details.construction_years,
    )
    pv_total = pv_line_om + pv_converter

    _total_annual_oandm = total_line_om_per_year + total_converter_cost_per_year
    _total_nominal_oandm = calculate_nominal_growing_series(
        _total_annual_oandm, om_real_escalation_rate, project_details.project_lifetime,
    )
    add_derived({
        "total_structures": structure_dict.get("total", 0) if structure_dict else 0,
        "veg_mgmt_cost_per_year": total_vegetation_management_cost_per_year,
        "total_annual_oandm": _total_annual_oandm,
        "line_om_annual": total_line_om_per_year,
    })

    # Print results
    print("\n" + "=" * 80)
    print("O&M COST ANALYSIS")
    print("=" * 80)

    print("\n--- Project Overview ---")
    print(f"Construction Type: {project_details.construction_type}")
    print(f"Total Line Length: {physical_details.total_miles:.2f} miles")
    print(f"Project Lifetime: {project_details.project_lifetime} years")

    # Print structure information for overhead projects
    if project_details.construction_type == CONSTRUCTION_TYPE_OVERHEAD and structure_dict:
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
    print(f"Converter:  ${total_converter_cost_per_year:,.2f} (total $/year; % of station CAPEX)")
    if project_details.construction_type == CONSTRUCTION_TYPE_OVERHEAD:
        print(f"Structure:  ${variable_structure_cost_per_year:,.2f} (total per year)")
    else:
        print(f"Structure:  ${variable_structure_cost_per_mile_year:,.2f}")

    print("\n--- Annual Total Costs ---")
    print(f"Conductor:  ${total_conductor_cost_per_year:,.2f}")
    print(f"Converter:  ${total_converter_cost_per_year:,.2f}")
    print(f"Structure:  ${variable_structure_cost_per_year:,.2f}")
    print(f"Vegetation Management:  ${total_vegetation_management_cost_per_year:,.2f}")
    print(f"{'─' * 40}")
    print(f"Total:      ${_total_annual_oandm:,.2f}")

    print("\n--- Lifetime Total Costs (Undiscounted) ---")
    print(f"Conductor:  ${total_conductor_cost_lifetime:,.2f}")
    print(f"Converter:  ${total_converter_cost_lifetime:,.2f}")
    print(f"Structure:  ${total_structure_cost_lifetime:,.2f}")
    print(f"Vegetation Management:  ${total_vegetation_management_cost_lifetime:,.2f}")
    print(f"{'─' * 40}")
    print(f"Total:      ${_total_nominal_oandm:,.2f}")

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
    csv_manager = SmartOutputManager()

    results = {
        "total_annual": _total_annual_oandm,
        "total_nominal": _total_nominal_oandm,
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
        "line_om_annual": total_line_om_per_year,
        "line_om_pv": pv_line_om,
    }

    # Write to CSV
    csv_manager.add_oandm_costs(results)
    csv_manager.write_batch_summary()

if __name__ == "__main__":
    main()
