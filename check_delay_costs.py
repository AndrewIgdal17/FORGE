#!/usr/bin/env python3
"""
Quick diagnostic script to check delay cost magnitudes relative to total costs.

Usage:
    python check_delay_costs.py --results sensitivity_results/scenario_TEST3/results.csv
    python check_delay_costs.py --results sensitivity_results/scenario_TEST3/results.csv --verbose
    python check_delay_costs.py --results sensitivity_results/scenario_TEST3/results.csv --output delay_analysis.csv
"""

import argparse
import pandas as pd
import numpy as np
from pathlib import Path


def calculate_cost_breakdown(row):
    """
    Calculate cost breakdown for a single row.

    Returns:
        dict with cost components and percentages
    """
    # Capital costs (ROW = capital only, i.e. acquisition + holding; rent is operational)
    build_cost_pv = row.get("build_cost_pv", 0) or 0
    row_capital_pv = row.get("row_capital_pv", 0) or row.get("row_cost_pv", 0) or 0
    env_mitigation_pv = row.get("env_mitigation_pv", 0) or 0
    capital_costs_pv = build_cost_pv + row_capital_pv + env_mitigation_pv

    # Operational costs (O&M, insurance, ROW rent; energy/emissions in energy/emissions category)
    oandm_pv = row.get("oandm_pv", 0) or 0
    insurance_pv = row.get("insurance_pv", 0) or 0
    row_rent_pv = row.get("row_rent_pv", 0) or 0
    wildfire_liability_pv = row.get("wildfire_liability_pv", 0) or 0
    total_insurance_pv = insurance_pv + wildfire_liability_pv
    emissions_pv = row.get("emissions_cost_pv", 0) or 0
    energy_losses_pv = (
        row.get("energy_losses_pv", 0) or row.get("line_loss_cost_pv", 0) or 0
    )
    energy_losses_pv = max(0, energy_losses_pv)  # Only count as cost if positive
    operational_costs_pv = (
        oandm_pv + total_insurance_pv + row_rent_pv + energy_losses_pv + emissions_pv
    )

    # Risk costs
    wildfire_pv = row.get("wildfire_pv", 0) or 0
    outage_pv = row.get("outage_pv", 0) or 0
    risk_costs_pv = wildfire_pv + outage_pv

    # Delay costs
    delay_cost_pv = row.get("delay_cost_pv", 0) or 0
    congestion_delay_pv = row.get("congestion_delay_cost_pv", 0) or 0
    curtailment_delay_pv = row.get("curtailment_delay_cost_pv", 0) or 0
    residual_congestion_pv = row.get("residual_congestion_pv", 0) or 0
    delay_costs_pv = (
        delay_cost_pv
        + congestion_delay_pv
        + curtailment_delay_pv
        + residual_congestion_pv
    )

    # Total costs
    total_costs_pv = (
        capital_costs_pv + operational_costs_pv + risk_costs_pv + delay_costs_pv
    )
    total_costs_excluding_risk_pv = total_costs_pv - risk_costs_pv

    # Calculate percentages
    delay_pct_of_total = (
        (delay_costs_pv / total_costs_pv * 100) if total_costs_pv > 0 else 0
    )
    delay_pct_excluding_risk = (
        (delay_costs_pv / total_costs_excluding_risk_pv * 100)
        if total_costs_excluding_risk_pv > 0
        else 0
    )

    return {
        "capital_costs_pv": capital_costs_pv,
        "operational_costs_pv": operational_costs_pv,
        "risk_costs_pv": risk_costs_pv,
        "delay_costs_pv": delay_costs_pv,
        "total_costs_pv": total_costs_pv,
        "total_costs_excluding_risk_pv": total_costs_excluding_risk_pv,
        "delay_pct_of_total": delay_pct_of_total,
        "delay_pct_excluding_risk": delay_pct_excluding_risk,
        # Delay components
        "delay_cost_pv": delay_cost_pv,
        "congestion_delay_pv": congestion_delay_pv,
        "curtailment_delay_pv": curtailment_delay_pv,
        "residual_congestion_pv": residual_congestion_pv,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Check delay cost magnitudes in sensitivity analysis results"
    )
    parser.add_argument(
        "--results",
        required=True,
        help="Path to results.csv from sensitivity analysis",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed breakdown for each sample",
    )
    parser.add_argument(
        "--output",
        help="Optional: Save detailed breakdown to CSV file",
    )

    args = parser.parse_args()

    # Load results
    results_path = Path(args.results)
    if not results_path.exists():
        print(f"Error: Results file not found: {results_path}")
        return

    print("=" * 80)
    print("DELAY COST DIAGNOSTIC ANALYSIS")
    print("=" * 80)
    print(f"Results file: {results_path}")
    print()

    df = pd.read_csv(results_path)
    print(f"Loaded {len(df)} samples")
    print()

    # Calculate breakdowns for all rows
    breakdowns = []
    for idx, row in df.iterrows():
        breakdown = calculate_cost_breakdown(row)
        breakdown["sample_id"] = row.get("sample_id", f"sample_{idx+1:04d}")
        breakdown["delay_years"] = row.get("delay_years", 0)
        breakdowns.append(breakdown)

    breakdown_df = pd.DataFrame(breakdowns)

    # Summary statistics
    print("=" * 80)
    print("DELAY COST SUMMARY STATISTICS")
    print("=" * 80)
    print()

    print("Delay Costs as % of Total Costs (with risk):")
    print(f"  Mean:   {breakdown_df['delay_pct_of_total'].mean():.2f}%")
    print(f"  Median: {breakdown_df['delay_pct_of_total'].median():.2f}%")
    print(f"  Min:    {breakdown_df['delay_pct_of_total'].min():.2f}%")
    print(f"  Max:    {breakdown_df['delay_pct_of_total'].max():.2f}%")
    print(f"  P5:     {breakdown_df['delay_pct_of_total'].quantile(0.05):.2f}%")
    print(f"  P95:    {breakdown_df['delay_pct_of_total'].quantile(0.95):.2f}%")
    print()

    print("Delay Costs as % of Total Costs (excluding risk):")
    print(f"  Mean:   {breakdown_df['delay_pct_excluding_risk'].mean():.2f}%")
    print(f"  Median: {breakdown_df['delay_pct_excluding_risk'].median():.2f}%")
    print(f"  Min:    {breakdown_df['delay_pct_excluding_risk'].min():.2f}%")
    print(f"  Max:    {breakdown_df['delay_pct_excluding_risk'].max():.2f}%")
    print(f"  P5:     {breakdown_df['delay_pct_excluding_risk'].quantile(0.05):.2f}%")
    print(f"  P95:    {breakdown_df['delay_pct_excluding_risk'].quantile(0.95):.2f}%")
    print()

    print("=" * 80)
    print("DELAY COST COMPONENTS (Average)")
    print("=" * 80)
    print()
    print(
        f"  Direct delay costs:        ${breakdown_df['delay_cost_pv'].mean():>15,.0f}"
    )
    print(
        f"  Congestion delay costs:     ${breakdown_df['congestion_delay_pv'].mean():>15,.0f}"
    )
    print(
        f"  Curtailment delay costs:    ${breakdown_df['curtailment_delay_pv'].mean():>15,.0f}"
    )
    print(
        f"  Residual congestion:       ${breakdown_df['residual_congestion_pv'].mean():>15,.0f}"
    )
    print(
        f"  Total delay costs:          ${breakdown_df['delay_costs_pv'].mean():>15,.0f}"
    )
    print()

    print("=" * 80)
    print("COST BREAKDOWN (Average)")
    print("=" * 80)
    print()
    print(
        f"  Capital costs:              ${breakdown_df['capital_costs_pv'].mean():>15,.0f}  ({breakdown_df['capital_costs_pv'].mean() / breakdown_df['total_costs_pv'].mean() * 100:.1f}%)"
    )
    print(
        f"  Operational costs:          ${breakdown_df['operational_costs_pv'].mean():>15,.0f}  ({breakdown_df['operational_costs_pv'].mean() / breakdown_df['total_costs_pv'].mean() * 100:.1f}%)"
    )
    print(
        f"  Risk costs:                  ${breakdown_df['risk_costs_pv'].mean():>15,.0f}  ({breakdown_df['risk_costs_pv'].mean() / breakdown_df['total_costs_pv'].mean() * 100:.1f}%)"
    )
    print(
        f"  Delay costs:                 ${breakdown_df['delay_costs_pv'].mean():>15,.0f}  ({breakdown_df['delay_pct_of_total'].mean():.1f}%)"
    )
    print(
        f"  Total costs (with risk):     ${breakdown_df['total_costs_pv'].mean():>15,.0f}"
    )
    print(
        f"  Total costs (excl. risk):    ${breakdown_df['total_costs_excluding_risk_pv'].mean():>15,.0f}"
    )
    print()

    # Check if delay costs are suspiciously small
    mean_delay_pct = breakdown_df["delay_pct_of_total"].mean()
    mean_delay_pct_excl_risk = breakdown_df["delay_pct_excluding_risk"].mean()

    print("=" * 80)
    print("DIAGNOSTIC CHECK")
    print("=" * 80)
    print()
    if mean_delay_pct < 1.0:
        print(f"⚠️  WARNING: Delay costs are <1% of total costs ({mean_delay_pct:.2f}%)")
        print("   This could explain low sensitivity in bcr_excluding_risk")
    elif mean_delay_pct < 5.0:
        print(
            f"⚠️  CAUTION: Delay costs are relatively small ({mean_delay_pct:.2f}% of total)"
        )
        print("   Delay may have lower sensitivity than expected")
    else:
        print(f"✅ Delay costs are significant: {mean_delay_pct:.2f}% of total costs")

    if mean_delay_pct_excl_risk < mean_delay_pct:
        print(
            f"⚠️  WARNING: Delay % is LOWER when risk is excluded ({mean_delay_pct_excl_risk:.2f}% vs {mean_delay_pct:.2f}%)"
        )
        print(
            "   This is unexpected - delay should be MORE important when risk is excluded"
        )
    else:
        print(
            f"✅ Delay % increases when risk is excluded: {mean_delay_pct_excl_risk:.2f}% (expected)"
        )
    print()

    # Verbose mode: show sample-by-sample
    if args.verbose:
        print("=" * 80)
        print("DETAILED BREAKDOWN BY SAMPLE")
        print("=" * 80)
        print()
        for idx, row in breakdown_df.iterrows():
            print(f"Sample: {row['sample_id']} (delay_years={row['delay_years']:.1f})")
            print(f"  Delay costs: ${row['delay_costs_pv']:,.0f}")
            print(
                f"  Total costs (with risk): ${row['total_costs_pv']:,.0f} → Delay = {row['delay_pct_of_total']:.2f}%"
            )
            print(
                f"  Total costs (excl. risk): ${row['total_costs_excluding_risk_pv']:,.0f} → Delay = {row['delay_pct_excluding_risk']:.2f}%"
            )
            print()

    # Save to CSV if requested
    if args.output:
        output_path = Path(args.output)
        breakdown_df.to_csv(output_path, index=False)
        print(f"✅ Saved detailed breakdown to: {output_path}")
        print()

    print("=" * 80)


if __name__ == "__main__":
    main()
