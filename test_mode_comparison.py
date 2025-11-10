#!/usr/bin/env python3
"""
Compare results from YAML mode and JSON mode to verify they produce identical calculations.
"""

import sys
import os
import json
import subprocess
import re

def extract_bcr_results(output):
    """Extract BCR results from command output."""
    results = {}

    # Extract benefits
    patterns = {
        'congestion_benefit': r'Congestion Reduction:\s+\$\s+([\d,]+)',
        'curtailment_benefit': r'Curtailment Reduction:\s+\$\s+([\d,]+)',
        'line_loss_impact': r'Line Loss Impact:\s+\$\s+(-?[\d,]+)',
        'total_benefits': r'Total Benefits:\s+\$\s+([\d,]+)',

        # Capital costs
        'build_cost': r'Build:\s+\$\s+([\d,]+)',
        'row_cost': r'Right-of-Way:\s+\$\s+([\d,]+)',
        'environmental_cost': r'Environmental:\s+\$\s+([\d,]+)',
        'capital_subtotal': r'Capital Costs:.*?Subtotal:\s+\$\s+([\d,]+)',

        # Operational costs
        'oandm_cost': r'O&M:\s+\$\s+([\d,]+)',
        'insurance_cost': r'Insurance:\s+\$\s+([\d,]+)',
        'line_losses_cost': r'Line Losses:\s+\$\s+([\d,]+)',
        'emissions_cost': r'Emissions:\s+\$\s+([\d,]+)',
        'operational_subtotal': r'Operational Costs:.*?Subtotal:\s+\$\s+([\d,]+)',

        # Risk costs
        'wildfire_cost': r'Wildfire:\s+\$\s+([\d,]+)',
        'outage_cost': r'Outage:\s+\$\s+([\d,]+)',
        'risk_subtotal': r'Risk Costs:.*?Subtotal:\s+\$\s+([\d,]+)',

        # Delay costs
        'construction_delay': r'Construction Delay:\s+\$\s+([\d,]+)',
        'congestion_delay': r'Congestion Delay:\s+\$\s+([\d,]+)',
        'curtailment_delay': r'Curtailment Delay:\s+\$\s+([\d,]+)',
        'delay_subtotal': r'Delay Costs:.*?Subtotal:\s+\$\s+([\d,]+)',

        # Totals
        'total_costs': r'Total Costs:\s+\$\s+([\d,]+)',

        # BCR metrics
        'system_bcr': r'System BCR \(full\):\s+([\d.]+)',
        'system_bcr_haircut': r'System BCR \(haircut\):\s+([\d.]+)',
        'capital_bcr': r'Capital BCR:\s+([\d.]+)',
        'net_benefit_pv': r'Net Benefit \(PV\):\s+\$\s+(-?[\d,]+)',
        'net_benefit_nominal': r'Net Benefit \(Nominal\):\s+\$\s+(-?[\d,]+)',
    }

    for key, pattern in patterns.items():
        match = re.search(pattern, output, re.MULTILINE | re.DOTALL)
        if match:
            value = match.group(1).replace(',', '')
            try:
                results[key] = float(value)
            except ValueError:
                results[key] = value

    return results


def run_yaml_mode():
    """Run CTCC in YAML mode and capture results."""
    print("🔄 Running YAML mode (ctcc.py)...")
    result = subprocess.run(
        ['venv/bin/python3', 'ctcc.py'],
        capture_output=True,
        text=True,
        timeout=600
    )

    if result.returncode != 0:
        print(f"❌ YAML mode failed: {result.stderr}")
        return None

    return extract_bcr_results(result.stdout)


def run_json_mode():
    """Run CTCC in JSON mode and capture results."""
    print("🔄 Running JSON mode (test_ctcc_processor.py)...")
    result = subprocess.run(
        ['python3', 'test_ctcc_processor.py'],
        capture_output=True,
        text=True,
        timeout=300
    )

    if result.returncode != 0:
        print(f"❌ JSON mode failed: {result.stderr}")
        return None

    return extract_bcr_results(result.stdout)


def compare_results(yaml_results, json_results):
    """Compare results from both modes."""
    print("\n" + "=" * 80)
    print("COMPARISON RESULTS")
    print("=" * 80)

    all_keys = set(yaml_results.keys()) | set(json_results.keys())

    differences = []
    matches = []

    for key in sorted(all_keys):
        yaml_val = yaml_results.get(key, 'MISSING')
        json_val = json_results.get(key, 'MISSING')

        if yaml_val == 'MISSING' or json_val == 'MISSING':
            differences.append((key, yaml_val, json_val, 'MISSING VALUE'))
        elif yaml_val == json_val:
            matches.append((key, yaml_val))
        else:
            # Check if difference is negligible (rounding)
            try:
                diff = abs(float(yaml_val) - float(json_val))
                rel_diff = diff / max(abs(float(yaml_val)), abs(float(json_val)), 1) * 100
                if rel_diff < 0.01:  # Less than 0.01% difference
                    matches.append((key, yaml_val))
                else:
                    differences.append((key, yaml_val, json_val, f'DIFF: {diff:,.2f} ({rel_diff:.4f}%)'))
            except (ValueError, TypeError):
                differences.append((key, yaml_val, json_val, 'TYPE MISMATCH'))

    # Display matches
    print(f"\n✅ MATCHING VALUES: {len(matches)}/{len(all_keys)}")
    print("-" * 80)
    for key, value in matches[:10]:  # Show first 10
        print(f"  {key:30s} = {value}")
    if len(matches) > 10:
        print(f"  ... and {len(matches) - 10} more matching values")

    # Display differences
    if differences:
        print(f"\n❌ DIFFERENCES FOUND: {len(differences)}")
        print("-" * 80)
        for key, yaml_val, json_val, note in differences:
            print(f"  {key:30s}")
            print(f"    YAML: {yaml_val}")
            print(f"    JSON: {json_val}")
            print(f"    Note: {note}")
    else:
        print(f"\n🎉 NO DIFFERENCES FOUND - PERFECT MATCH!")

    return len(differences) == 0


def main():
    """Main comparison function."""
    print("=" * 80)
    print("CTCC MODE COMPARISON TEST")
    print("Comparing YAML mode vs JSON mode calculation results")
    print("=" * 80)

    # Run both modes
    yaml_results = run_yaml_mode()
    if yaml_results is None:
        print("❌ YAML mode failed to execute")
        return False

    print(f"✅ YAML mode completed - extracted {len(yaml_results)} metrics")

    json_results = run_json_mode()
    if json_results is None:
        print("❌ JSON mode failed to execute")
        return False

    print(f"✅ JSON mode completed - extracted {len(json_results)} metrics")

    # Compare results
    success = compare_results(yaml_results, json_results)

    print("\n" + "=" * 80)
    if success:
        print("✅ VERIFICATION PASSED - YAML and JSON modes produce identical results!")
    else:
        print("❌ VERIFICATION FAILED - Differences found between modes")
    print("=" * 80)

    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
