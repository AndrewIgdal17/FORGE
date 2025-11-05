# Author: Andrew Igdal
# Date: 2025-11-04
# Description: Calculate benefit-cost ratios (BCR) for transmission projects.
#              Compares congestion/curtailment benefits against all project costs.

import csv
import os


def load_scenario_data(scenario_id, output_dir="../outputs"):
    """
    Load scenario data from batch_summary.csv for the given scenario_id.
    
    Args:
        scenario_id: Unique identifier for the scenario
        output_dir: Directory containing batch_summary.csv
        
    Returns:
        Dictionary with all data for the scenario, or None if not found
    """
    batch_path = os.path.join(output_dir, "batch_summary.csv")
    
    if not os.path.exists(batch_path):
        print(f"Warning: batch_summary.csv not found at {batch_path}")
        return None
    
    with open(batch_path, 'r', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get('scenario_id') == scenario_id:
                # Convert numeric strings to floats
                for key, value in row.items():
                    if value and value != '':
                        try:
                            row[key] = float(value)
                        except (ValueError, TypeError):
                            pass  # Keep as string if not numeric
                return row
    
    print(f"Warning: scenario_id '{scenario_id}' not found in batch_summary.csv")
    return None


def calculate_benefits(data):
    """
    Calculate total benefits from scenario data.
    
    For most projects, benefits are:
      - Congestion reduction savings
      - Curtailment reduction savings
    
    For reconductoring projects, also includes:
      - Line loss reduction (if line_loss_cost is negative)
    
    Args:
        data: Dictionary with scenario data
        
    Returns:
        Dictionary with benefit breakdown and total (both nominal and PV)
    """
    # Present value benefits
    congestion_benefit_pv = data.get('congestion_benefit_pv', 0) or 0
    curtailment_benefit_pv = data.get('curtailment_benefit_pv', 0) or 0
    line_loss_pv = data.get('line_loss_cost_pv', 0) or 0
    
    # Nominal benefits
    congestion_benefit_nominal = data.get('congestion_benefit_nominal', 0) or 0
    curtailment_benefit_nominal = data.get('curtailment_benefit_nominal', 0) or 0
    line_loss_nominal = data.get('line_loss_cost_nominal', 0) or 0
    
    # For reconductoring, line losses are typically negative (benefit)
    # For greenfield, line losses are positive (cost)
    line_loss_benefit_pv = 0
    line_loss_benefit_nominal = 0
    if line_loss_pv < 0:
        line_loss_benefit_pv = abs(line_loss_pv)
        line_loss_benefit_nominal = abs(line_loss_nominal)
    
    total_benefits_pv = congestion_benefit_pv + curtailment_benefit_pv + line_loss_benefit_pv
    total_benefits_nominal = congestion_benefit_nominal + curtailment_benefit_nominal + line_loss_benefit_nominal
    
    # Also calculate haircut benefits (conservative estimate)
    congestion_benefit_haircut = data.get('congestion_benefit_haircut_pv', 0) or 0
    curtailment_benefit_haircut = data.get('curtailment_benefit_haircut_pv', 0) or 0
    total_benefits_haircut_pv = congestion_benefit_haircut + curtailment_benefit_haircut + line_loss_benefit_pv
    
    return {
        'congestion_benefit_pv': congestion_benefit_pv,
        'curtailment_benefit_pv': curtailment_benefit_pv,
        'line_loss_benefit_pv': line_loss_benefit_pv,
        'total_benefits_pv': total_benefits_pv,
        'total_benefits_nominal': total_benefits_nominal,
        'total_benefits_haircut_pv': total_benefits_haircut_pv,
    }


def calculate_costs(data):
    """
    Calculate total costs from scenario data.
    
    Costs include:
      - Capital: build, ROW, environmental mitigation
      - Operational: O&M, insurance, line losses (greenfield), emissions
      - Risk: wildfire, outage
      - Delay: construction delay, congestion/curtailment delay, residual congestion
    
    Args:
        data: Dictionary with scenario data
        
    Returns:
        Dictionary with cost breakdown by category and total (both nominal and PV)
    """
    # Capital costs (PV)
    build_cost_pv = data.get('build_cost_pv', 0) or 0
    row_cost_pv = data.get('row_cost_pv', 0) or 0
    env_mitigation_pv = data.get('env_mitigation_pv', 0) or 0
    capital_costs_pv = build_cost_pv + row_cost_pv + env_mitigation_pv
    
    # Capital costs (Nominal)
    build_cost_nominal = data.get('build_cost_nominal', 0) or 0
    row_cost_nominal = data.get('row_cost_nominal', 0) or 0
    env_mitigation_nominal = data.get('env_mitigation_nominal', 0) or 0
    capital_costs_nominal = build_cost_nominal + row_cost_nominal + env_mitigation_nominal
    
    # Operational costs (PV)
    oandm_pv = data.get('oandm_pv', 0) or 0
    insurance_pv = data.get('insurance_pv', 0) or 0
    emissions_pv = data.get('emissions_cost_pv', 0) or 0
    
    # Line losses - only count as cost if positive (greenfield)
    line_loss_pv = data.get('line_loss_cost_pv', 0) or 0
    line_loss_cost_pv = max(0, line_loss_pv)
    
    operational_costs_pv = oandm_pv + insurance_pv + line_loss_cost_pv + emissions_pv
    
    # Operational costs (Nominal)
    oandm_nominal = data.get('oandm_nominal', 0) or 0
    insurance_nominal = data.get('insurance_nominal', 0) or 0
    emissions_nominal = data.get('emissions_cost_nominal', 0) or 0
    line_loss_nominal = data.get('line_loss_cost_nominal', 0) or 0
    line_loss_cost_nominal = max(0, line_loss_nominal)
    
    operational_costs_nominal = oandm_nominal + insurance_nominal + line_loss_cost_nominal + emissions_nominal
    
    # Risk costs (PV)
    wildfire_pv = data.get('wildfire_pv', 0) or 0
    outage_pv = data.get('outage_pv', 0) or 0
    risk_costs_pv = wildfire_pv + outage_pv
    
    # Risk costs (Nominal)
    wildfire_nominal = data.get('wildfire_nominal', 0) or 0
    outage_nominal = data.get('outage_nominal', 0) or 0
    risk_costs_nominal = wildfire_nominal + outage_nominal
    
    # Delay costs (PV)
    delay_cost_pv = data.get('delay_cost_pv', 0) or 0
    congestion_delay_pv = data.get('congestion_delay_cost_pv', 0) or 0
    curtailment_delay_pv = data.get('curtailment_delay_cost_pv', 0) or 0
    residual_congestion_pv = data.get('residual_congestion_pv', 0) or 0
    delay_costs_pv = delay_cost_pv + congestion_delay_pv + curtailment_delay_pv + residual_congestion_pv
    
    # Delay costs (Nominal)
    delay_cost_nominal = data.get('delay_cost_nominal', 0) or 0
    congestion_delay_nominal = data.get('congestion_delay_cost_nominal', 0) or 0
    curtailment_delay_nominal = data.get('curtailment_delay_cost_nominal', 0) or 0
    residual_congestion_nominal = data.get('residual_congestion_nominal', 0) or 0
    delay_costs_nominal = delay_cost_nominal + congestion_delay_nominal + curtailment_delay_nominal + residual_congestion_nominal
    
    # Totals
    total_costs_pv = capital_costs_pv + operational_costs_pv + risk_costs_pv + delay_costs_pv
    total_costs_nominal = capital_costs_nominal + operational_costs_nominal + risk_costs_nominal + delay_costs_nominal
    
    return {
        # Capital (PV)
        'build_cost_pv': build_cost_pv,
        'row_cost_pv': row_cost_pv,
        'env_mitigation_pv': env_mitigation_pv,
        'capital_costs_pv': capital_costs_pv,
        
        # Operational (PV)
        'oandm_pv': oandm_pv,
        'insurance_pv': insurance_pv,
        'line_loss_cost_pv': line_loss_cost_pv,
        'emissions_cost_pv': emissions_pv,
        'operational_costs_pv': operational_costs_pv,
        
        # Risk (PV)
        'wildfire_pv': wildfire_pv,
        'outage_pv': outage_pv,
        'risk_costs_pv': risk_costs_pv,
        
        # Delay (PV)
        'delay_cost_pv': delay_cost_pv,
        'congestion_delay_cost_pv': congestion_delay_pv,
        'curtailment_delay_cost_pv': curtailment_delay_pv,
        'residual_congestion_pv': residual_congestion_pv,
        'delay_costs_pv': delay_costs_pv,
        
        # Totals (PV)
        'total_costs_pv': total_costs_pv,
        
        # Totals (Nominal)
        'capital_costs_nominal': capital_costs_nominal,
        'operational_costs_nominal': operational_costs_nominal,
        'risk_costs_nominal': risk_costs_nominal,
        'delay_costs_nominal': delay_costs_nominal,
        'total_costs_nominal': total_costs_nominal,
    }


def calculate_bcr_metrics(benefits, costs):
    """
    Calculate benefit-cost ratios and net benefits.
    
    Args:
        benefits: Dictionary with benefit breakdown
        costs: Dictionary with cost breakdown
        
    Returns:
        Dictionary with BCR metrics (both nominal and PV)
    """
    # Present value metrics
    total_benefits_pv = benefits['total_benefits_pv']
    total_benefits_haircut = benefits['total_benefits_haircut_pv']
    total_costs_pv = costs['total_costs_pv']
    capital_costs_pv = costs['capital_costs_pv']
    
    # Nominal metrics
    total_benefits_nominal = benefits['total_benefits_nominal']
    total_costs_nominal = costs['total_costs_nominal']
    
    # Prevent division by zero
    bcr_system = total_benefits_pv / total_costs_pv if total_costs_pv > 0 else 0
    bcr_capital = total_benefits_pv / capital_costs_pv if capital_costs_pv > 0 else 0
    bcr_haircut = total_benefits_haircut / total_costs_pv if total_costs_pv > 0 else 0
    
    net_benefit_pv = total_benefits_pv - total_costs_pv
    net_benefit_nominal = total_benefits_nominal - total_costs_nominal
    
    return {
        'bcr_system': bcr_system,
        'bcr_capital': bcr_capital,
        'bcr_haircut': bcr_haircut,
        'net_benefit_pv': net_benefit_pv,
        'net_benefit_nominal': net_benefit_nominal,
    }


def calculate_and_display_bcr(scenario_id, output_dir="../outputs"):
    """
    Main function to calculate and display BCR analysis.
    
    Args:
        scenario_id: Unique identifier for the scenario
        output_dir: Directory containing batch_summary.csv
        
    Returns:
        Dictionary with all BCR results, or None if calculation fails
    """
    # Load scenario data
    data = load_scenario_data(scenario_id, output_dir)
    if data is None:
        return None
    
    # Calculate benefits and costs
    benefits = calculate_benefits(data)
    costs = calculate_costs(data)
    
    # Calculate BCR metrics
    bcr_metrics = calculate_bcr_metrics(benefits, costs)
    
    # Combine all results
    results = {
        **benefits,
        **costs,
        **bcr_metrics,
    }
    
    # Display results
    print_bcr_summary(benefits, costs, bcr_metrics, data)
    
    return results


def print_bcr_summary(benefits, costs, bcr_metrics, data):
    """
    Print formatted BCR summary to terminal.
    
    Args:
        benefits: Dictionary with benefit breakdown
        costs: Dictionary with cost breakdown
        bcr_metrics: Dictionary with BCR metrics
        data: Original scenario data
    """
    print()
    print("=" * 80)
    print("BENEFIT-COST RATIO ANALYSIS")
    print("=" * 80)
    print()
    
    # Benefits section
    print("BENEFITS (Present Value):")
    print(f"  Congestion Reduction:        ${benefits['congestion_benefit_pv']:>15,.0f}")
    print(f"  Curtailment Reduction:       ${benefits['curtailment_benefit_pv']:>15,.0f}")
    
    line_loss_pv = data.get('line_loss_cost_pv', 0) or 0
    is_reconductoring = data.get('reconductoring', False)
    if line_loss_pv < 0:
        print(f"  Line Loss Benefit:           ${benefits['line_loss_benefit_pv']:>15,.0f}  (reconductoring)")
    else:
        print(f"  Line Loss Impact:            ${-line_loss_pv:>15,.0f}  (cost - see below)")
    
    print("  " + "-" * 78)
    print(f"  Total Benefits:              ${benefits['total_benefits_pv']:>15,.0f}")
    print()
    
    # Costs section
    print("COSTS (Present Value):")
    print("  Capital Costs:")
    print(f"    Build:                     ${costs['build_cost_pv']:>15,.0f}")
    print(f"    Right-of-Way:              ${costs['row_cost_pv']:>15,.0f}")
    print(f"    Environmental:             ${costs['env_mitigation_pv']:>15,.0f}")
    print(f"    Subtotal:                  ${costs['capital_costs_pv']:>15,.0f}")
    print()
    print("  Operational Costs:")
    print(f"    O&M:                       ${costs['oandm_pv']:>15,.0f}")
    print(f"    Insurance:                 ${costs['insurance_pv']:>15,.0f}")
    print(f"    Line Losses:               ${costs['line_loss_cost_pv']:>15,.0f}")
    print(f"    Emissions:                 ${costs['emissions_cost_pv']:>15,.0f}")
    print(f"    Subtotal:                  ${costs['operational_costs_pv']:>15,.0f}")
    print()
    print("  Risk Costs:")
    print(f"    Wildfire:                  ${costs['wildfire_pv']:>15,.0f}")
    print(f"    Outage:                    ${costs['outage_pv']:>15,.0f}")
    print(f"    Subtotal:                  ${costs['risk_costs_pv']:>15,.0f}")
    print()
    print("  Delay Costs:")
    print(f"    Construction Delay:        ${costs['delay_cost_pv']:>15,.0f}")
    print(f"    Congestion Delay:          ${costs['congestion_delay_cost_pv']:>15,.0f}")
    print(f"    Curtailment Delay:         ${costs['curtailment_delay_cost_pv']:>15,.0f}")
    print(f"    Residual Congestion:       ${costs['residual_congestion_pv']:>15,.0f}")
    print(f"    Subtotal:                  ${costs['delay_costs_pv']:>15,.0f}")
    print()
    print("  " + "-" * 78)
    print(f"  Total Costs:                 ${costs['total_costs_pv']:>15,.0f}")
    print()
    
    # BCR metrics
    print("BENEFIT-COST RATIOS:")
    
    bcr_system = bcr_metrics['bcr_system']
    viable_symbol = "✅" if bcr_system >= 1.0 else "❌"
    viable_text = ">= 1.0: economically viable" if bcr_system >= 1.0 else "< 1.0: not economically viable"
    
    print(f"  System BCR (full):           {bcr_system:>6.3f}  {viable_symbol} ({viable_text})")
    print(f"  System BCR (haircut):        {bcr_metrics['bcr_haircut']:>6.3f}")
    print(f"  Capital BCR:                 {bcr_metrics['bcr_capital']:>6.3f}")
    print()
    
    net_benefit_pv = bcr_metrics['net_benefit_pv']
    net_benefit_nominal = bcr_metrics['net_benefit_nominal']
    
    net_symbol_pv = "✅" if net_benefit_pv >= 0 else "❌"
    net_text_pv = "positive: benefits exceed costs" if net_benefit_pv >= 0 else "negative: costs exceed benefits"
    
    net_symbol_nominal = "✅" if net_benefit_nominal >= 0 else "❌"
    net_text_nominal = "positive: benefits exceed costs" if net_benefit_nominal >= 0 else "negative: costs exceed benefits"
    
    print(f"  Net Benefit (PV):            ${net_benefit_pv:>15,.0f}  {net_symbol_pv} ({net_text_pv})")
    print(f"  Net Benefit (Nominal):       ${net_benefit_nominal:>15,.0f}  {net_symbol_nominal} ({net_text_nominal})")
    print()
    print("=" * 80)
    print()


if __name__ == "__main__":
    # For testing - use the most recent scenario_id
    import sys
    
    if len(sys.argv) > 1:
        scenario_id = sys.argv[1]
    else:
        # Try to get the most recent scenario_id from batch_summary.csv
        batch_path = "../outputs/batch_summary.csv"
        if os.path.exists(batch_path):
            with open(batch_path, 'r') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                if rows:
                    scenario_id = rows[-1]['scenario_id']
                    print(f"Using most recent scenario_id: {scenario_id}")
                else:
                    print("No scenarios found in batch_summary.csv")
                    sys.exit(1)
        else:
            print("batch_summary.csv not found")
            sys.exit(1)
    
    results = calculate_and_display_bcr(scenario_id)
    
    if results:
        print(f"\nBCR calculation completed for scenario {scenario_id}")
    else:
        print(f"\nBCR calculation failed for scenario {scenario_id}")

