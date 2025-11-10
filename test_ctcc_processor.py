#!/usr/bin/env python3
"""
Test that ctcc_processor correctly runs all calculation scripts in JSON mode.
"""

import sys
import os
import json

# Add serverFastAPI to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "serverFastAPI"))

def test_ctcc_processor_json_mode():
    """Test ctcc_processor.run_json_to_json with all calculation scripts."""
    print("=" * 80)
    print("Testing CTCC Processor - JSON Mode with All Calculation Scripts")
    print("=" * 80)

    # Load the combined JSON file
    combined_json_path = "serverFastAPI/json/final_combined.json"
    with open(combined_json_path, 'r') as f:
        combined_data = json.load(f)

    print(f"\n✓ Loaded combined JSON data from: {combined_json_path}")

    # Import ctcc_processor
    from app.ctcc_processor import run_ctcc_calculation

    # Create payload
    payload = {
        "input_mode": "json",
        "output_mode": "json",
        "scenario_id": "test_processor_001",
        "combined_data": combined_data
    }

    print(f"✓ Created test payload")
    print(f"  - Input mode: {payload['input_mode']}")
    print(f"  - Output mode: {payload['output_mode']}")
    print(f"  - Scenario ID: {payload['scenario_id']}")

    # Run calculations
    print(f"\n⏳ Running CTCC calculations...")
    print(f"   This will execute all 13 calculation scripts as subprocesses")
    print(f"   with JSON data loaded from temporary file...")
    print()

    result = run_ctcc_calculation(payload)

    # Display results
    print("=" * 80)
    print("RESULTS")
    print("=" * 80)

    print(f"\nSuccess: {result['success']}")
    print(f"Scenario ID: {result['scenario_id']}")
    print(f"Timestamp: {result['timestamp']}")
    print(f"Scripts Run: {result.get('scripts_run', 0)}/{result.get('total_scripts', 0)}")

    if result.get('error'):
        print(f"\n❌ ERRORS:")
        print(result['error'])
    else:
        print(f"\n✅ No errors reported")

    # Show script execution details
    if result.get('scripts_run') is not None:
        success_rate = (result['scripts_run'] / result['total_scripts'] * 100) if result['total_scripts'] > 0 else 0
        print(f"\n📊 Script Execution:")
        print(f"   - Success rate: {success_rate:.1f}%")
        print(f"   - Successful: {result['scripts_run']}")
        print(f"   - Total: {result['total_scripts']}")

    # Show results structure
    if result.get('results'):
        print(f"\n📄 Results Structure:")
        results = result['results']
        print(f"   - Scenario ID: {results.get('scenario_id')}")
        print(f"   - Input mode: {results.get('input_mode')}")
        print(f"   - Timestamp: {results.get('timestamp')}")

        if results.get('technical_parameters'):
            tech = results['technical_parameters']
            print(f"\n   Technical Parameters:")
            print(f"   - Project name: {tech.get('project_name')}")
            print(f"   - Construction type: {tech.get('construction_type')}")
            print(f"   - AC/DC: {tech.get('ac_dc')}")
            print(f"   - Capacity: {tech.get('capacity_mw')} MW")
            print(f"   - Line length: {tech.get('line_length_miles')} miles")

        if results.get('costs'):
            print(f"\n   Cost Modules Collected: {len(results['costs'])}")
            for cost_type in results['costs'].keys():
                print(f"      - {cost_type}")

        if results.get('benefits'):
            print(f"\n   Benefit Modules Collected: {len(results['benefits'])}")
            for benefit_type in results['benefits'].keys():
                print(f"      - {benefit_type}")

    # Final verdict
    print("\n" + "=" * 80)
    if result['success'] and result.get('scripts_run', 0) == result.get('total_scripts', 0):
        print("✅ ALL TESTS PASSED - ctcc_processor correctly runs all scripts in JSON mode!")
        print("=" * 80)
        return True
    elif result['success']:
        print("⚠️  PARTIAL SUCCESS - Some scripts may not have run")
        print("=" * 80)
        return True
    else:
        print("❌ TESTS FAILED - See errors above")
        print("=" * 80)
        return False


if __name__ == "__main__":
    success = test_ctcc_processor_json_mode()
    sys.exit(0 if success else 1)
