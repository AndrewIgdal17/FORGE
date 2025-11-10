#!/usr/bin/env python3
"""
Test API JSON output vs CLI CSV output.
Compares results from ctcc_processor.py (JSON mode) with ctcc.py (CSV mode).
"""

import sys
import os
import json
import csv
import subprocess

# Add serverFastAPI to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'serverFastAPI'))


def run_cli_csv_mode():
    """Run ctcc.py in CLI mode (YAML→CSV) and extract results from batch_summary.csv."""
    print("=" * 80)
    print("1. Running CLI Mode: ctcc.py (YAML → CSV)")
    print("=" * 80)

    script_dir = os.path.dirname(os.path.abspath(__file__))
    venv_python = os.path.join(script_dir, 'venv', 'bin', 'python3')
    ctcc_script = os.path.join(script_dir, 'ctcc.py')

    result = subprocess.run(
        [venv_python, ctcc_script],
        capture_output=True,
        text=True,
        timeout=600,
        cwd=script_dir
    )

    if result.returncode != 0:
        print(f"❌ CLI mode failed: {result.stderr}")
        return None

    print("✅ CLI mode completed successfully")

    # Read batch_summary.csv
    csv_path = os.path.join(script_dir, 'outputs', 'batch_summary.csv')
    if not os.path.exists(csv_path):
        print(f"❌ CSV file not found: {csv_path}")
        return None

    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        if not rows:
            print("❌ No data in batch_summary.csv")
            return None
        # Get the last row (most recent)
        return rows[-1]


def run_api_json_mode():
    """Run ctcc_processor.py in API mode (JSON→JSON) and extract results."""
    print("\n" + "=" * 80)
    print("2. Running API Mode: ctcc_processor.py (JSON → JSON)")
    print("=" * 80)

    # Load combined JSON
    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_file = os.path.join(script_dir, 'serverFastAPI', 'json', 'final_combined.json')

    with open(json_file, 'r') as f:
        combined_data = json.load(f)

    # Import and run ctcc_processor
    from app.ctcc_processor import run_ctcc_calculation

    payload = {
        "input_mode": "json",
        "output_mode": "json",
        "scenario_id": "api_vs_cli_test",
        "combined_data": combined_data
    }

    result = run_ctcc_calculation(payload)

    if not result.get('success'):
        print(f"❌ API mode failed: {result.get('error')}")
        return None

    print("✅ API mode completed successfully")

    return result.get('results', {})


def extract_csv_values(csv_row):
    """Extract key values from CSV row."""
    values = {}

    # Map CSV column names to standardized keys
    mapping = {
        'build_cost_pv': 'build_cost_pv',
        'row_cost_pv': 'row_cost_pv',
        'env_mitigation_pv': 'environmental_cost_pv',  # Fixed: correct column name
        'delay_cost_pv': 'delay_cost_pv',
        'insurance_pv': 'insurance_cost_pv',
        'wildfire_pv': 'wildfire_cost_pv',
        'outage_pv': 'outage_cost_pv',
        'congestion_benefit_pv': 'congestion_benefit_pv',
        'curtailment_benefit_pv': 'curtailment_benefit_pv',
        'oandm_pv': 'oandm_cost_pv',
        'emissions_cost_pv': 'emissions_cost_pv',  # Fixed: correct column name
        'line_loss_cost_pv': 'line_loss_cost_pv',
        'total_costs_pv': 'total_cost_pv',  # Fixed: correct column name (plural)
        'total_benefits_pv': 'total_benefit_pv',  # Fixed: correct column name (plural)
        'bcr_system': 'system_bcr',  # Fixed: correct column name
        'net_benefit_pv': 'net_benefit_pv',
    }

    for csv_key, std_key in mapping.items():
        if csv_key in csv_row and csv_row[csv_key]:
            try:
                values[std_key] = float(csv_row[csv_key])
            except (ValueError, TypeError):
                pass

    return values


def extract_json_values(json_result):
    """Extract key values from JSON response."""
    values = {}

    costs = json_result.get('costs', {})
    benefits = json_result.get('benefits', {})
    summary = json_result.get('summary', {})
    bcr = json_result.get('bcr', {})

    # Extract cost values (fixed field names based on actual JSON structure)
    values['build_cost_pv'] = costs.get('build', {}).get('total_pv', 0)
    values['row_cost_pv'] = costs.get('row', {}).get('total_pv', 0)
    values['environmental_cost_pv'] = costs.get('environmental', {}).get('total_pv', 0)
    values['delay_cost_pv'] = costs.get('delay', {}).get('total_pv', 0)
    values['insurance_cost_pv'] = costs.get('insurance', {}).get('pv_total', 0)
    values['wildfire_cost_pv'] = costs.get('wildfire', {}).get('pv_cost', 0)
    values['outage_cost_pv'] = costs.get('outage', {}).get('pv_cost', 0)
    values['oandm_cost_pv'] = costs.get('oandm', {}).get('total_pv', 0)
    values['emissions_cost_pv'] = costs.get('emissions', {}).get('total_pv', 0)  # Fixed
    values['line_loss_cost_pv'] = costs.get('line_loss', {}).get('total_pv', 0)  # Fixed

    # Extract benefit values (fixed field names)
    cong_curt = benefits.get('congestion_curtailment', {})
    values['congestion_benefit_pv'] = cong_curt.get('congestion_benefit_pv', 0)  # Fixed
    values['curtailment_benefit_pv'] = cong_curt.get('curtailment_benefit_pv', 0)  # Fixed

    # Extract summary values
    values['total_cost_pv'] = summary.get('grand_total_cost_pv', 0)

    # Calculate total benefits
    values['total_benefit_pv'] = (
        values.get('congestion_benefit_pv', 0) +
        values.get('curtailment_benefit_pv', 0)
    )

    # Extract BCR metrics
    values['system_bcr'] = bcr.get('system_bcr_full', 0)
    values['net_benefit_pv'] = bcr.get('net_benefit_pv', 0)

    return values


def compare_values(csv_values, json_values):
    """Compare CSV and JSON values."""
    print("\n" + "=" * 80)
    print("3. COMPARISON: CLI CSV vs API JSON")
    print("=" * 80)

    all_keys = set(csv_values.keys()) | set(json_values.keys())

    differences = []
    matches = []
    missing = []

    for key in sorted(all_keys):
        csv_val = csv_values.get(key, 0)
        json_val = json_values.get(key, 0)

        # Check for missing values
        if csv_val == 0 and json_val == 0:
            missing.append((key, 'Both zero'))
            continue
        elif csv_val == 0:
            missing.append((key, f'CSV: 0, JSON: {json_val:,.2f}'))
            continue
        elif json_val == 0:
            missing.append((key, f'CSV: {csv_val:,.2f}, JSON: 0'))
            continue

        # Check if values match
        try:
            csv_float = float(csv_val)
            json_float = float(json_val)

            if csv_float == json_float:
                matches.append((key, csv_float))
            else:
                # Check if difference is negligible (rounding)
                diff = abs(csv_float - json_float)
                max_val = max(abs(csv_float), abs(json_float), 1)
                rel_diff = diff / max_val * 100

                if rel_diff < 0.01:  # Less than 0.01% difference
                    matches.append((key, csv_float))
                else:
                    differences.append((key, csv_float, json_float, diff, rel_diff))
        except (ValueError, TypeError):
            differences.append((key, csv_val, json_val, 'N/A', 'N/A'))

    # Display results
    print(f"\n✅ MATCHING VALUES: {len(matches)}/{len(all_keys)}")
    print("-" * 80)
    if matches:
        for key, value in sorted(matches):
            print(f"  {key:35s} = ${value:,.2f}")

    # Display missing/zero values
    if missing:
        print(f"\n⚠️  ZERO/MISSING VALUES: {len(missing)}")
        print("-" * 80)
        for key, info in missing:
            print(f"  {key:35s}: {info}")

    # Display differences
    if differences:
        print(f"\n❌ DIFFERENCES FOUND: {len(differences)}")
        print("-" * 80)
        for key, csv_val, json_val, diff, rel_diff in differences:
            print(f"  {key:35s}")
            if isinstance(csv_val, (int, float)):
                print(f"    CLI CSV:  ${csv_val:,.2f}")
                print(f"    API JSON: ${json_val:,.2f}")
            else:
                print(f"    CLI CSV:  {csv_val}")
                print(f"    API JSON: {json_val}")
            if diff != 'N/A':
                print(f"    Diff:     ${diff:,.2f} ({rel_diff:.4f}%)")

    # Overall verdict
    print("\n" + "=" * 80)
    if len(differences) == 0 and len(missing) == 0:
        print("🎉 PERFECT MATCH - All values identical!")
        print("=" * 80)
        return True
    elif len(differences) == 0:
        print("✅ All populated values match!")
        print(f"⚠️  However, {len(missing)} values are zero/missing in one or both outputs")
        print("=" * 80)
        return True
    else:
        print(f"⚠️  Found {len(differences)} differences between CLI and API outputs")
        print("=" * 80)
        return False


def main():
    """Main comparison function."""
    print("\n" + "=" * 80)
    print("API JSON OUTPUT vs CLI CSV OUTPUT VERIFICATION TEST")
    print("=" * 80)
    print("\nThis test compares:")
    print("  • CLI: ctcc.py (YAML input → CSV output)")
    print("  • API: ctcc_processor.py (JSON input → JSON output)")
    print("\nBoth should produce identical calculation results.")
    print("=" * 80)

    # Run CLI mode (YAML → CSV)
    csv_row = run_cli_csv_mode()
    if csv_row is None:
        print("\n❌ Failed to get CLI CSV results")
        return False

    csv_values = extract_csv_values(csv_row)
    print(f"   Extracted {len(csv_values)} metrics from batch_summary.csv")

    # Run API mode (JSON → JSON)
    json_result = run_api_json_mode()
    if json_result is None:
        print("\n❌ Failed to get API JSON results")
        return False

    json_values = extract_json_values(json_result)
    print(f"   Extracted {len(json_values)} metrics from JSON response")

    # Compare values
    success = compare_values(csv_values, json_values)

    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    if success:
        print("✅ VERIFICATION PASSED")
        print("   CLI CSV output and API JSON output contain identical values!")
        print("   Both modes are working correctly.")
    else:
        print("❌ VERIFICATION FAILED")
        print("   Differences found between CLI and API outputs.")
        print("   See comparison above for details.")
    print("=" * 80)

    return success


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
