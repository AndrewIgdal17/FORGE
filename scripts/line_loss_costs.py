# Author: Andrew Igdal
# Date: 2025-10-27
# Description: This script uses the energy_losses script to calculate the line losses for
# a reconductoring project and its original state. Then it calculates each years
# lossbenefit = (Lbase(t) - L reconductoring(t)) * price_per_mwh
#

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from csv_output_manager import CTCCOutputManager

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
from yaml_loaders import load_financing_social_discount_rate
from path_config import YAMLS_DIR


def load_project_details():
    """Load project technical details with line_loss_costs specific fields."""
    import yaml

    with open(YAMLS_DIR / "01_project_technical_details.yaml", "r") as file:
        project_details = yaml.load(file, Loader=yaml.FullLoader)

    construction_type = project_details["project"]["construction_type"]
    ac_dc = project_details["project"]["ac_dc"]
    capacity_mw = project_details["project"]["capacity_mw"]
    conductor_type = project_details["project"]["conductor_type"]
    converter_type = (
        project_details["project"]["converter_type"] if ac_dc != "AC" else "NA"
    )
    line_utilization_percent = project_details["project"]["line_utilization"]
    baseline_electricity_price = project_details["project"][
        "baseline_electricity_price_per_mwh"
    ]
    social_discount_rate = load_financing_social_discount_rate()
    reconductoring = project_details["project"]["reconductoring"]

    delay_years = project_details["timeline"]["delay_years"]
    construction_years = project_details["timeline"]["construction_years"]
    project_lifetime = project_details["timeline"]["project_lifetime"]

    # Get number_of_converters if DC
    if ac_dc == "DC":
        number_of_converters = project_details["project"]["number_of_converters"]
    else:
        number_of_converters = 0

    # Get greenfield comparison fields (optional, only for greenfield projects)
    greenfield_comparison_capacity_mw = project_details["project"].get(
        "greenfield_comparison_capacity_mw", None
    )
    greenfield_comparison_conductor_type = project_details["project"].get(
        "greenfield_comparison_conductor_type", None
    )

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
        project_lifetime,
        delay_years,
        construction_years,
        greenfield_comparison_capacity_mw,
        greenfield_comparison_conductor_type,
    )


def calculate_configuration_losses(
    construction_type,
    ac_dc,
    capacity_mw,
    conductor_type,
    converter_type,
    line_utilization_percent,
    project_lifetime,
    voltage_kv_override=None,
):
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
    voltage_kv = voltage_kv_override if voltage_kv_override is not None else voltage_kv_lookup

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


def calculate_present_value(annual_cost, discount_rate, total_years, start_year=1):
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


def main():
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
        project_lifetime,
        delay_years,
        construction_years,
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
                (primary_loss_percent - comparison_loss_percent) / 100
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
            print(
                f"Primary Configuration: {primary_losses_mwh_per_year:,.2f} MWh/year"
            )
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
            print(f"  Lifetime Cost Difference: ${direct_lifetime_cost_difference:,.2f}")
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
            print(f"  Lifetime Cost Difference: ${normalized_lifetime_cost_difference:,.2f}")
            print()
            print("DISCOUNTED VALUES (NPV):")
            print(f"  Discount Rate: {social_discount_rate * 100:.1f}%")
            print(f"  Start Year: {start_year:.1f} years")
            print(f"  Net Present Value: ${normalized_npv:,.2f}")
            print()

            print("=" * 70)

            # Write to CSV using PRIMARY configuration's absolute losses (not comparison difference)
            # Comparison methods are informational only - BCR uses absolute losses
            primary_annual_loss_cost = primary_losses_mwh_per_year * baseline_electricity_price
            primary_lifetime_nominal_cost = primary_annual_loss_cost * project_lifetime
            primary_pv_loss_cost = calculate_present_value(
                primary_annual_loss_cost, social_discount_rate, project_lifetime, start_year
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

    # Load baseline configuration details
    with open(YAMLS_DIR / "01_project_technical_details.yaml", "r") as file:
        project_details = yaml.load(file, Loader=yaml.FullLoader)

    old_capacity_mw = project_details["project"]["old_capacity_mw"]
    old_conductor_type = project_details["project"]["old_conductor_type"]
    old_ac_dc = project_details["project"]["old_ac_dc"]

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

    # Look up voltage for new configuration first (for counterfactual comparison)
    new_category = (
        f"{construction_type}/{ac_dc}/{capacity_mw}MW/{conductor_type}/{converter_type}"
    )
    voltage_kv_new, _, _, _, _, _ = load_circuit_and_resistance_details(new_category)

    # Calculate new configuration losses
    new_losses_mwh_per_year, new_lifetime_losses_mwh = calculate_configuration_losses(
        construction_type,
        ac_dc,
        capacity_mw,
        conductor_type,
        converter_type,
        line_utilization_percent,
        project_lifetime,
    )

    # Calculate counterfactual baseline losses (old conductor at new capacity @ new voltage)
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
        voltage_kv_override=voltage_kv_new,  # Use new voltage for fair comparison
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
