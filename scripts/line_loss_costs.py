# Author: Andrew Igdal
# Date: 2025-10-27
# Description: This script uses the energy_losses script to calculate the line losses for
# a reconductoring project and its original state. Then it calculates each years
# lossbenefit = (Lbase(t) - L reconductoring(t)) * price_per_mwh
#

from __future__ import annotations

import sys
import os
from typing import Tuple, Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from smart_output import CTCCOutputManager

# Standard library imports
import yaml

# Local utility imports
from energy_losses import (
    load_physical_details,
    load_circuit_and_resistance_details,
    calculate_phase_current,
    full_load_adjusted,
    calculate_line_losses,
)
from financial_utils import calculate_present_value
from smart_loaders import (
    load_financing_social_discount_rate,
    load_project_technical_details as load_project_technical_details_centralized,
    get_project_data_raw,
)


def load_project_details() -> Tuple[
    str,
    str,
    int,
    str,
    int,
    str,
    float,
    float,
    float,
    bool,
    int,
    float,
    int,
    Optional[int],
    Optional[str],
]:
    """
    Load project technical details with line_loss_costs specific fields.

    This function loads comprehensive project details from the technical details YAML file,
    including both standard project specifications and optional fields used for line loss
    cost calculations (such as greenfield comparison parameters).

    Args:
        None (reads from YAML file)

    Returns:
        tuple: A 15-element tuple containing:
            - construction_type: Type of construction (e.g., "Overhead", "Subsea")
            - ac_dc: "AC" or "DC" designation
            - capacity_mw: Line capacity in MW
            - conductor_type: Type of conductor used
            - number_of_converters: Number of converter stations (DC projects only, else 0)
            - converter_type: Converter type (for DC projects) or "NA" for AC
            - line_utilization_percent: Line utilization as decimal (0-1)
            - baseline_electricity_price: Baseline electricity price in $/MWh
            - social_discount_rate: Social discount rate for present value calculations
            - reconductoring: True if reconductoring project, False for greenfield
            - delay_years: Number of years of project delay
            - construction_years: Number of years of construction
            - project_lifetime: Project operational lifetime in years
            - greenfield_comparison_capacity_mw: Optional comparison capacity for greenfield projects
            - greenfield_comparison_conductor_type: Optional comparison conductor type for greenfield projects

    Raises:
        FileNotFoundError: When project technical details YAML is not found
        ValueError: When YAML file is empty or invalid
        KeyError: When required keys are missing from the YAML structure

    Note:
        The last two tuple elements (greenfield_comparison_*) are optional and may be None
        if not specified in the YAML file. These are used for comparing different greenfield
        configurations in line loss cost calculations.
    """
    try:
        # Load from centralized loader
        # Returns: (construction_type, ac_dc, capacity_mw, conductor_type, converter_type,
        #           line_utilization, reconductoring, delay_years, construction_years,
        #           project_lifetime, converter_loss_percentage)
        (
            construction_type,
            ac_dc,
            capacity_mw,
            conductor_type,
            converter_type,
            line_utilization_percent,
            reconductoring,
            uses_existing_row,  # Added: 12th value from updated loader
            delay_years,
            construction_years,
            project_lifetime,
            _converter_loss_percentage,
        ) = load_project_technical_details_centralized()

        # Get additional fields not in centralized loader
        project_details = get_project_data_raw()
        if not project_details:
            raise ValueError("Project technical details file is empty or invalid")
        if "project" not in project_details:
            raise KeyError(
                "Missing 'project' key in project technical details"
            )
        project = project_details["project"]

        baseline_electricity_price = project.get(
            "baseline_electricity_price_per_mwh", 0
        )
        social_discount_rate = load_financing_social_discount_rate()

        # Get number_of_converters if DC
        if ac_dc == "DC":
            number_of_converters = project.get("number_of_converters", 0)
        else:
            number_of_converters = 0

        # Get greenfield comparison fields (optional, only for greenfield projects)
        greenfield_comparison_capacity_mw = project.get(
            "greenfield_comparison_capacity_mw", None
        )
        greenfield_comparison_conductor_type = project.get(
            "greenfield_comparison_conductor_type", None
        )
    except FileNotFoundError:
        raise FileNotFoundError(
            f"Project technical details not found"
        )
    except yaml.YAMLError as e:
        raise ValueError(f"Error parsing project technical details: {e}")
    except KeyError as e:
        raise KeyError(f"Missing required key in project technical details: {e}")

    return (
        construction_type,
        ac_dc,
        capacity_mw,
        conductor_type,
        number_of_converters,
        converter_type,
        line_utilization_percent,
        baseline_electricity_price,
        social_discount_rate,
        reconductoring,
        delay_years,
        construction_years,
        project_lifetime,
        greenfield_comparison_capacity_mw,
        greenfield_comparison_conductor_type,
    )


def calculate_configuration_losses(
    construction_type: str,
    ac_dc: str,
    capacity_mw: int,
    conductor_type: str,
    converter_type: str,
    line_utilization_percent: float,
    project_lifetime: int,
    voltage_kv_override: Optional[float] = None,
) -> Tuple[float, float]:
    """
    Calculate line losses for a given configuration.

    Args:
        construction_type: Construction type (Overhead, Underground, etc.)
        ac_dc: "AC" or "DC"
        capacity_mw: Capacity in MW (numeric)
        conductor_type: Type of conductor
        converter_type: Converter type (for DC) or "NA" for AC
        line_utilization_percent: Line utilization as decimal (0-1)
        project_lifetime: Project lifetime in years
        voltage_kv_override: Optional voltage override (if None, looks up from category)

    Returns:
        tuple: (losses_mwh_per_year, lifetime_losses_mwh)
    """
    # Build category string for lookup
    category = (
        f"{construction_type}/{ac_dc}/{capacity_mw}MW/{conductor_type}/{converter_type}"
    )

    # Load physical details (line length)
    line_length = load_physical_details()

    # Load circuit and resistance details
    (
        voltage_kv_lookup,
        conductors_per_phase,
        number_of_phases,
        number_of_circuits_poles,
        AC_75_resistance,
        DC_20_resistance,
    ) = load_circuit_and_resistance_details(category)

    # Use override voltage if provided, otherwise use lookup voltage
    voltage_kv = (
        voltage_kv_override if voltage_kv_override is not None else voltage_kv_lookup
    )

    # Convert capacity_mw to string for calculate_phase_current
    capacity_mw_str = f"{capacity_mw}MW"

    # Calculate phase current and full load adjustment
    phase_current = calculate_phase_current(
        capacity_mw_str, voltage_kv, number_of_phases, number_of_circuits_poles, ac_dc
    )
    full_load_adj = full_load_adjusted(line_utilization_percent)

    # Calculate line losses
    (
        losses_mwh_per_year,
        lifetime_losses_mwh,
        losses_mw_per_mile,
        resistance_per_mile,
        line_loss_per_mile_percent,
        total_line_loss_mw,
        total_line_loss_percent,
    ) = calculate_line_losses(
        phase_current,
        full_load_adj,
        AC_75_resistance,
        DC_20_resistance,
        ac_dc,
        number_of_circuits_poles,
        conductors_per_phase,
        number_of_phases,
        line_length,
        project_lifetime,
        capacity_mw,
        line_utilization_percent,
    )

    return losses_mwh_per_year, lifetime_losses_mwh


def calculate_present_value(
    annual_cost: float, discount_rate: float, total_years: float, start_year: int = 1
) -> float:
    """
    Calculate present value of annual payments.

    Args:
        annual_cost: Annual cost amount
        discount_rate: Discount rate (social discount rate for emissions)
        total_years: Number of years over which payments occur
        start_year: Year when payments begin

    Returns:
        Present value of the payment stream
    """
    import math

    n_full_years = math.floor(total_years)
    frac = total_years - n_full_years
    total_pv = 0

    for year in range(n_full_years):
        t = start_year + year
        total_pv += annual_cost / (1 + discount_rate) ** t

    if frac > 0:
        t_frac = start_year + n_full_years + frac
        total_pv += annual_cost * frac / (1 + discount_rate) ** t_frac

    return total_pv


def main() -> None:
    """Main function to calculate line loss costs for reconductoring projects."""

    (
        construction_type,
        ac_dc,
        capacity_mw,
        conductor_type,
        number_of_converters,
        converter_type,
        line_utilization_percent,
        baseline_electricity_price,
        social_discount_rate,
        reconductoring,
        delay_years,
        construction_years,
        project_lifetime,
        greenfield_comparison_capacity_mw,
        greenfield_comparison_conductor_type,
    ) = load_project_details()

    print("=" * 70)
    print("LINE LOSS COST CALCULATOR")
    print("=" * 70)
    print()

    if not reconductoring:
        print("Greenfield project detected - calculating line loss costs.")
        print()

        # Check if comparison capacity is provided
        if greenfield_comparison_capacity_mw is not None:
            # Greenfield with comparison - implement three comparison methods
            print("Comparison capacity detected - comparing two configurations.")
            print()

            print("PROJECT CONFIGURATION")
            print("-" * 70)
            print(f"Construction Type: {construction_type}")
            print(f"Line Utilization: {line_utilization_percent * 100:.1f}%")
            print(f"Project Lifetime: {project_lifetime} years")
            print(f"Electricity Price: ${baseline_electricity_price:.2f}/MWh")
            print()

            print("PRIMARY CONFIGURATION")
            print("-" * 70)
            print(f"Capacity: {capacity_mw} MW")
            print(f"AC/DC: {ac_dc}")
            print(f"Conductor Type: {conductor_type}")
            print()

            # Calculate primary configuration losses
            primary_losses_mwh_per_year, primary_lifetime_losses_mwh = (
                calculate_configuration_losses(
                    construction_type,
                    ac_dc,
                    capacity_mw,
                    conductor_type,
                    converter_type,
                    line_utilization_percent,
                    project_lifetime,
                )
            )

            print("COMPARISON CONFIGURATION")
            print("-" * 70)
            print(f"Capacity: {greenfield_comparison_capacity_mw} MW")
            print(f"AC/DC: {ac_dc}")
            print(f"Conductor Type: {greenfield_comparison_conductor_type}")
            print()

            # Calculate comparison configuration losses
            comparison_losses_mwh_per_year, comparison_lifetime_losses_mwh = (
                calculate_configuration_losses(
                    construction_type,
                    ac_dc,
                    greenfield_comparison_capacity_mw,
                    greenfield_comparison_conductor_type,
                    converter_type,
                    line_utilization_percent,
                    project_lifetime,
                )
            )

            # Calculate counterfactual: primary conductor at comparison capacity
            counterfactual_primary_losses_mwh_per_year, _ = (
                calculate_configuration_losses(
                    construction_type,
                    ac_dc,
                    greenfield_comparison_capacity_mw,  # Use comparison capacity
                    conductor_type,  # Use primary conductor
                    converter_type,
                    line_utilization_percent,
                    project_lifetime,
                )
            )

            # Calculate delivered energy for each configuration
            primary_delivered_mwh = capacity_mw * line_utilization_percent * 8760
            comparison_delivered_mwh = (
                greenfield_comparison_capacity_mw * line_utilization_percent * 8760
            )

            # Calculate loss percentages
            primary_loss_percent = (
                primary_losses_mwh_per_year / primary_delivered_mwh
            ) * 100
            comparison_loss_percent = (
                comparison_losses_mwh_per_year / comparison_delivered_mwh
            ) * 100

            # METHOD 1: Direct Comparison - Compare absolute losses
            direct_loss_difference_mwh = (
                primary_losses_mwh_per_year - comparison_losses_mwh_per_year
            )
            direct_annual_cost_difference = (
                direct_loss_difference_mwh * baseline_electricity_price
            )
            direct_lifetime_cost_difference = (
                direct_annual_cost_difference * project_lifetime
            )

            # METHOD 2: Counterfactual Comparison - Compare primary vs comparison conductor at comparison capacity
            counterfactual_loss_difference_mwh = (
                counterfactual_primary_losses_mwh_per_year
                - comparison_losses_mwh_per_year
            )
            counterfactual_annual_cost_difference = (
                counterfactual_loss_difference_mwh * baseline_electricity_price
            )
            counterfactual_lifetime_cost_difference = (
                counterfactual_annual_cost_difference * project_lifetime
            )

            # METHOD 3: Normalized (Per MWh) Comparison
            # Apply the difference in loss percentages to the comparison delivered energy
            normalized_loss_difference_mwh = (
                (primary_loss_percent - comparison_loss_percent)
                / 100
                * comparison_delivered_mwh
            )
            normalized_annual_cost_difference = (
                normalized_loss_difference_mwh * baseline_electricity_price
            )
            normalized_lifetime_cost_difference = (
                normalized_annual_cost_difference * project_lifetime
            )

            # Line losses start at first year of operation (COD)
            start_year = delay_years + construction_years + 1

            # Calculate NPVs for all three methods
            direct_npv = calculate_present_value(
                direct_annual_cost_difference,
                social_discount_rate,
                project_lifetime,
                start_year,
            )
            counterfactual_npv = calculate_present_value(
                counterfactual_annual_cost_difference,
                social_discount_rate,
                project_lifetime,
                start_year,
            )
            normalized_npv = calculate_present_value(
                normalized_annual_cost_difference,
                social_discount_rate,
                project_lifetime,
                start_year,
            )

            # Print results
            print("=" * 70)
            print("GREENFIELD LINE LOSS COST COMPARISON RESULTS")
            print("=" * 70)
            print()

            print("LOSS COMPARISON:")
            print("-" * 70)
            print(f"Primary Configuration: {primary_losses_mwh_per_year:,.2f} MWh/year")
            print(
                f"  Capacity: {capacity_mw} MW | Loss Rate: {primary_loss_percent:.2f}%"
            )
            print()
            print(
                f"Comparison Configuration: {comparison_losses_mwh_per_year:,.2f} MWh/year"
            )
            print(
                f"  Capacity: {greenfield_comparison_capacity_mw} MW | Loss Rate: {comparison_loss_percent:.2f}%"
            )
            print()
            print(
                f"Counterfactual (Primary Conductor @ Comparison Capacity): {counterfactual_primary_losses_mwh_per_year:,.2f} MWh/year"
            )
            print()

            print("=" * 70)
            print("METHOD 1: DIRECT COMPARISON")
            print("=" * 70)
            print(
                "Compares: Primary losses @ primary capacity vs. Comparison losses @ comparison capacity"
            )
            print()
            print("NOMINAL VALUES:")
            print(
                f"  Loss Difference: {direct_loss_difference_mwh:,.2f} MWh/year "
                f"({'Primary higher' if direct_loss_difference_mwh > 0 else 'Comparison higher'})"
            )
            print(
                f"  Annual Cost Difference: ${direct_annual_cost_difference:,.2f}/year "
                f"({'Primary more expensive' if direct_annual_cost_difference > 0 else 'Comparison more expensive'})"
            )
            print(
                f"  Lifetime Cost Difference: ${direct_lifetime_cost_difference:,.2f}"
            )
            print()
            print("DISCOUNTED VALUES (NPV):")
            print(f"  Discount Rate: {social_discount_rate * 100:.1f}%")
            print(f"  Start Year: {start_year:.1f} years")
            print(f"  Net Present Value: ${direct_npv:,.2f}")
            print()

            print("=" * 70)
            print("METHOD 2: COUNTERFACTUAL COMPARISON")
            print("=" * 70)
            print(
                "Compares: Primary conductor @ comparison capacity vs. Comparison conductor @ comparison capacity"
            )
            print()
            print("NOMINAL VALUES:")
            print(
                f"  Loss Difference: {counterfactual_loss_difference_mwh:,.2f} MWh/year "
                f"({'Primary conductor higher' if counterfactual_loss_difference_mwh > 0 else 'Comparison conductor higher'})"
            )
            print(
                f"  Annual Cost Difference: ${counterfactual_annual_cost_difference:,.2f}/year "
                f"({'Primary conductor more expensive' if counterfactual_annual_cost_difference > 0 else 'Comparison conductor more expensive'})"
            )
            print(
                f"  Lifetime Cost Difference: ${counterfactual_lifetime_cost_difference:,.2f}"
            )
            print()
            print("DISCOUNTED VALUES (NPV):")
            print(f"  Discount Rate: {social_discount_rate * 100:.1f}%")
            print(f"  Start Year: {start_year:.1f} years")
            print(f"  Net Present Value: ${counterfactual_npv:,.2f}")
            print()

            print("=" * 70)
            print("METHOD 3: NORMALIZED (PER MWH) COMPARISON")
            print("=" * 70)
            print("Compares: Loss percentages weighted by delivered energy")
            print()
            print("NOMINAL VALUES:")
            print(
                f"  Loss Difference: {normalized_loss_difference_mwh:,.2f} MWh/year "
                f"({'Primary higher' if normalized_loss_difference_mwh > 0 else 'Comparison higher'})"
            )
            print(
                f"  Annual Cost Difference: ${normalized_annual_cost_difference:,.2f}/year "
                f"({'Primary more expensive' if normalized_annual_cost_difference > 0 else 'Comparison more expensive'})"
            )
            print(
                f"  Lifetime Cost Difference: ${normalized_lifetime_cost_difference:,.2f}"
            )
            print()
            print("DISCOUNTED VALUES (NPV):")
            print(f"  Discount Rate: {social_discount_rate * 100:.1f}%")
            print(f"  Start Year: {start_year:.1f} years")
            print(f"  Net Present Value: ${normalized_npv:,.2f}")
            print()

            print("=" * 70)

            # Write to CSV using PRIMARY configuration's absolute losses (not comparison difference)
            # Comparison methods are informational only - BCR uses absolute losses
            primary_annual_loss_cost = (
                primary_losses_mwh_per_year * baseline_electricity_price
            )
            primary_lifetime_nominal_cost = primary_annual_loss_cost * project_lifetime
            primary_pv_loss_cost = calculate_present_value(
                primary_annual_loss_cost,
                social_discount_rate,
                project_lifetime,
                start_year,
            )

            csv_manager = CTCCOutputManager()
            results = {
                "annual_cost": primary_annual_loss_cost,  # Absolute cost of primary config
                "total_nominal": primary_lifetime_nominal_cost,
                "total_afudc": 0,  # Line loss costs are not AFUDC-eligible
                "total_pv": primary_pv_loss_cost,
            }
            csv_manager.add_line_loss_costs(results)
            csv_manager.write_batch_summary()
            return

        # No comparison - single configuration (existing behavior)
        # Calculate losses for the greenfield configuration
        losses_mwh_per_year, lifetime_losses_mwh = calculate_configuration_losses(
            construction_type,
            ac_dc,
            capacity_mw,
            conductor_type,
            converter_type,
            line_utilization_percent,
            project_lifetime,
        )

        # Calculate costs (losses × price)
        annual_loss_cost = losses_mwh_per_year * baseline_electricity_price
        lifetime_nominal_cost = annual_loss_cost * project_lifetime

        # Calculate present value
        # Line losses start at first year of operation (COD)
        start_year = delay_years + construction_years + 1
        pv_loss_cost = calculate_present_value(
            annual_loss_cost, social_discount_rate, project_lifetime, start_year
        )

        # Print results
        print("=" * 70)
        print("GREENFIELD LINE LOSS COST RESULTS")
        print("=" * 70)
        print()
        print(f"Project Capacity: {capacity_mw} MW")
        print(f"Line Utilization: {line_utilization_percent * 100:.1f}%")
        print(f"Electricity Price: ${baseline_electricity_price:.2f}/MWh")
        print()
        print("NOMINAL VALUES:")
        print(f"  Line Losses: {losses_mwh_per_year:,.2f} MWh/year")
        print(f"  Annual Cost: ${annual_loss_cost:,.2f}/year")
        print(f"  Lifetime Cost: ${lifetime_nominal_cost:,.2f}")
        print()
        print("DISCOUNTED VALUES (NPV):")
        print(f"  Discount Rate: {social_discount_rate * 100:.1f}%")
        print(f"  Start Year: {start_year:.1f} years")
        print(f"  Net Present Value: ${pv_loss_cost:,.2f}")
        print()
        print("=" * 70)

        # Write to CSV
        csv_manager = CTCCOutputManager()
        results = {
            "annual_cost": annual_loss_cost,
            "total_nominal": lifetime_nominal_cost,  # Cost, not benefit
            "total_afudc": 0,
            "total_pv": pv_loss_cost,
        }
        csv_manager.add_line_loss_costs(results)
        csv_manager.write_batch_summary()
        return

    # Load baseline configuration details using helper
    try:
        project_details = get_project_data_raw()
        if not project_details:
            raise ValueError("Project technical details file is empty or invalid")
        if "project" not in project_details:
            raise KeyError(
                "Missing 'project' key in project technical details"
            )
        project = project_details["project"]
        required_keys = ["old_capacity_mw", "old_conductor_type", "old_ac_dc"]
        for key in required_keys:
            if key not in project:
                raise KeyError(
                    f"Missing '{key}' key in project section of technical details"
                )
        old_capacity_mw = project["old_capacity_mw"]
        old_conductor_type = project["old_conductor_type"]
        old_ac_dc = project["old_ac_dc"]
    except FileNotFoundError:
        raise FileNotFoundError(
            f"Project technical details not found"
        )
    except yaml.YAMLError as e:
        raise ValueError(f"Error parsing project technical details: {e}")
    except KeyError as e:
        raise KeyError(f"Missing required key in project technical details: {e}")

    # For DC to DC, keep the same converter type
    if ac_dc == "DC" and old_ac_dc == "DC":
        old_converter_type = converter_type
    elif old_ac_dc == "AC":
        old_converter_type = "NA"
    else:
        old_converter_type = converter_type

    print(f"PROJECT CONFIGURATION")
    print("-" * 70)
    print(f"Construction Type: {construction_type}")
    print(f"Line Utilization: {line_utilization_percent * 100:.1f}%")
    print(f"Project Lifetime: {project_lifetime} years")
    print(f"Electricity Price: ${baseline_electricity_price:.2f}/MWh")
    print()

    print(f"BASELINE CONFIGURATION (Old)")
    print("-" * 70)
    print(f"Capacity: {old_capacity_mw} MW")
    print(f"AC/DC: {old_ac_dc}")
    print(f"Conductor Type: {old_conductor_type}")
    print()

    # Calculate baseline losses
    baseline_losses_mwh_per_year, baseline_lifetime_losses_mwh = (
        calculate_configuration_losses(
            construction_type,
            old_ac_dc,
            old_capacity_mw,
            old_conductor_type,
            old_converter_type,
            line_utilization_percent,
            project_lifetime,
        )
    )

    print(f"NEW CONFIGURATION (After Reconductoring)")
    print("-" * 70)
    print(f"Capacity: {capacity_mw} MW")
    print(f"AC/DC: {ac_dc}")
    print(f"Conductor Type: {conductor_type}")
    print()

    # Look up old voltage for reconductoring (physical towers unchanged)
    old_category = f"{construction_type}/{old_ac_dc}/{old_capacity_mw}MW/{old_conductor_type}/{old_converter_type}"
    old_voltage_kv, _, _, _, _, _ = load_circuit_and_resistance_details(old_category)

    # Calculate new configuration losses using OLD voltage (towers unchanged)
    new_losses_mwh_per_year, new_lifetime_losses_mwh = calculate_configuration_losses(
        construction_type,
        ac_dc,
        capacity_mw,
        conductor_type,
        converter_type,
        line_utilization_percent,
        project_lifetime,
        voltage_kv_override=old_voltage_kv,  # Use old voltage since towers unchanged
    )

    # Calculate counterfactual baseline losses (old conductor at new capacity @ old voltage)
    # This ensures both use the same voltage for fair comparison (informational only)
    (
        counterfactual_baseline_losses_mwh_per_year,
        counterfactual_baseline_lifetime_losses_mwh,
    ) = calculate_configuration_losses(
        construction_type,
        old_ac_dc,
        capacity_mw,  # Use NEW capacity
        old_conductor_type,
        old_converter_type,
        line_utilization_percent,
        project_lifetime,
        voltage_kv_override=old_voltage_kv,  # Use old voltage for fair comparison
    )

    # Calculate delivered energy for each configuration
    baseline_delivered_mwh = old_capacity_mw * line_utilization_percent * 8760
    new_delivered_mwh = capacity_mw * line_utilization_percent * 8760

    # Calculate loss percentages
    baseline_loss_percent = (
        baseline_losses_mwh_per_year / baseline_delivered_mwh
    ) * 100
    new_loss_percent = (new_losses_mwh_per_year / new_delivered_mwh) * 100

    # METHOD 1: Direct Comparison - Compare absolute losses
    direct_loss_reduction_mwh = baseline_losses_mwh_per_year - new_losses_mwh_per_year
    direct_annual_benefit = direct_loss_reduction_mwh * baseline_electricity_price
    direct_lifetime_benefit = direct_annual_benefit * project_lifetime

    # METHOD 2: Counterfactual Comparison - Compare old vs new conductor at new capacity
    counterfactual_loss_reduction_mwh = (
        counterfactual_baseline_losses_mwh_per_year - new_losses_mwh_per_year
    )
    counterfactual_annual_benefit = (
        counterfactual_loss_reduction_mwh * baseline_electricity_price
    )
    counterfactual_lifetime_benefit = counterfactual_annual_benefit * project_lifetime

    # METHOD 3: Normalized (Per MWh) Comparison
    # Apply the difference in loss percentages to the new delivered energy
    normalized_loss_reduction_mwh = (
        (baseline_loss_percent - new_loss_percent) / 100 * new_delivered_mwh
    )
    normalized_annual_benefit = (
        normalized_loss_reduction_mwh * baseline_electricity_price
    )
    normalized_lifetime_benefit = normalized_annual_benefit * project_lifetime

    # Line losses start at first year of operation (COD)
    start_year = delay_years + construction_years + 1

    # Calculate NPVs for all three methods
    direct_npv = calculate_present_value(
        direct_annual_benefit, social_discount_rate, project_lifetime, start_year
    )
    counterfactual_npv = calculate_present_value(
        counterfactual_annual_benefit,
        social_discount_rate,
        project_lifetime,
        start_year,
    )
    normalized_npv = calculate_present_value(
        normalized_annual_benefit, social_discount_rate, project_lifetime, start_year
    )

    # Print results
    print("=" * 70)
    print("LINE LOSS COST RESULTS")
    print("=" * 70)
    print()

    print("LOSS COMPARISON:")
    print("-" * 70)
    print(f"Baseline (Old Config): {baseline_losses_mwh_per_year:,.2f} MWh/year")
    print(f"  Capacity: {old_capacity_mw} MW | Loss Rate: {baseline_loss_percent:.2f}%")
    print()
    print(f"New Configuration: {new_losses_mwh_per_year:,.2f} MWh/year")
    print(f"  Capacity: {capacity_mw} MW | Loss Rate: {new_loss_percent:.2f}%")
    print()
    print(
        f"Counterfactual (Old Conductor @ New Capacity): {counterfactual_baseline_losses_mwh_per_year:,.2f} MWh/year"
    )
    print()

    print("=" * 70)
    print("METHOD 1: DIRECT COMPARISON")
    print("=" * 70)
    print("Compares: Baseline losses @ old capacity vs. New losses @ new capacity")
    print()
    print("NOMINAL VALUES:")
    print(f"  Loss Reduction: {direct_loss_reduction_mwh:,.2f} MWh/year")
    print(f"  Annual Benefit: ${direct_annual_benefit:,.2f}/year")
    print(f"  Lifetime Benefit: ${direct_lifetime_benefit:,.2f}")
    print()
    print("DISCOUNTED VALUES (NPV):")
    print(f"  Discount Rate: {social_discount_rate * 100:.1f}%")
    print(f"  Start Year: {start_year:.1f} years")
    print(f"  Net Present Value: ${direct_npv:,.2f}")
    print()

    print("=" * 70)
    print("METHOD 2: COUNTERFACTUAL COMPARISON")
    print("=" * 70)
    print("Compares: Old conductor @ new capacity vs. New conductor @ new capacity")
    print()
    print("NOMINAL VALUES:")
    print(f"  Loss Reduction: {counterfactual_loss_reduction_mwh:,.2f} MWh/year")
    print(f"  Annual Benefit: ${counterfactual_annual_benefit:,.2f}/year")
    print(f"  Lifetime Benefit: ${counterfactual_lifetime_benefit:,.2f}")
    print()
    print("DISCOUNTED VALUES (NPV):")
    print(f"  Discount Rate: {social_discount_rate * 100:.1f}%")
    print(f"  Start Year: {start_year:.1f} years")
    print(f"  Net Present Value: ${counterfactual_npv:,.2f}")
    print()

    print("=" * 70)
    print("METHOD 3: NORMALIZED (PER MWH) COMPARISON")
    print("=" * 70)
    print("Compares: Loss percentages weighted by delivered energy")
    print()
    print("NOMINAL VALUES:")
    print(f"  Loss Reduction: {normalized_loss_reduction_mwh:,.2f} MWh/year")
    print(f"  Annual Benefit: ${normalized_annual_benefit:,.2f}/year")
    print(f"  Lifetime Benefit: ${normalized_lifetime_benefit:,.2f}")
    print()
    print("DISCOUNTED VALUES (NPV):")
    print(f"  Discount Rate: {social_discount_rate * 100:.1f}%")
    print(f"  Start Year: {start_year:.1f} years")
    print(f"  Net Present Value: ${normalized_npv:,.2f}")
    print()

    print("=" * 70)

    # ========================================================================
    # CSV OUTPUT - Write results to batch summary and detail CSV
    # ========================================================================

    # Initialize CSV output manager
    csv_manager = CTCCOutputManager()

    # Write to CSV using NEW configuration's absolute losses (not difference/benefit)
    # Comparison methods are informational only - BCR uses absolute losses
    new_annual_loss_cost = new_losses_mwh_per_year * baseline_electricity_price
    new_lifetime_nominal_cost = new_annual_loss_cost * project_lifetime
    new_pv_loss_cost = calculate_present_value(
        new_annual_loss_cost, social_discount_rate, project_lifetime, start_year
    )

    # Prepare results dictionary
    results = {
        "annual_cost": new_annual_loss_cost,  # Absolute cost of new configuration
        "total_nominal": new_lifetime_nominal_cost,
        "total_afudc": 0,  # Line loss costs are not AFUDC-eligible
        "total_pv": new_pv_loss_cost,
    }

    # Write to CSV
    csv_manager.add_line_loss_costs(results)
    csv_manager.write_batch_summary()


if __name__ == "__main__":
    main()
