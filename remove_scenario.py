#!/usr/bin/env python3
"""
Interactive script to remove a specific scenario ID from all CSV files in the outputs directory.
Scans all CSV files, lists unique scenario IDs, and prompts user to select which one to delete.
"""

import os
import csv
from pathlib import Path
from collections import defaultdict

# Configuration
OUTPUTS_DIR = Path("outputs")

def scan_scenario_ids():
    """Scan all CSV files and collect unique scenario IDs with their details."""
    if not OUTPUTS_DIR.exists():
        print(f"Error: Directory '{OUTPUTS_DIR}' does not exist")
        return None
    
    csv_files = sorted(OUTPUTS_DIR.glob("*.csv"))
    
    if not csv_files:
        print(f"No CSV files found in '{OUTPUTS_DIR}'")
        return None
    
    scenario_info = defaultdict(lambda: {
        'project_name': None,
        'timestamp': None,
        'files_found': []
    })
    
    print(f"Scanning {len(csv_files)} CSV file(s) in '{OUTPUTS_DIR}'...\n")
    
    for csv_file in csv_files:
        try:
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    scenario_id = row.get('scenario_id')
                    if scenario_id:
                        scenario_info[scenario_id]['project_name'] = row.get('project_name', 'Unknown')
                        scenario_info[scenario_id]['timestamp'] = row.get('timestamp', 'Unknown')
                        if csv_file.name not in scenario_info[scenario_id]['files_found']:
                            scenario_info[scenario_id]['files_found'].append(csv_file.name)
        except Exception as e:
            print(f"  Warning: Error reading {csv_file.name}: {e}")
            continue
    
    return dict(scenario_info)

def display_scenario_list(scenario_info):
    """Display numbered list of scenario IDs."""
    if not scenario_info:
        print("No scenario IDs found in CSV files.")
        return None
    
    scenarios = sorted(scenario_info.items(), key=lambda x: x[1]['timestamp'] or '')
    
    print("=" * 80)
    print("Found Scenario IDs:")
    print("=" * 80)
    
    for idx, (scenario_id, info) in enumerate(scenarios, start=1):
        project_name = info['project_name'] or 'Unknown'
        timestamp = info['timestamp'] or 'Unknown'
        file_count = len(info['files_found'])
        
        print(f"{idx:2d}. Scenario ID: {scenario_id}")
        print(f"    Project: {project_name}")
        print(f"    Timestamp: {timestamp}")
        print(f"    Found in {file_count} file(s)")
        print()
    
    return scenarios

def get_user_selection(scenarios):
    """Get user's selection for which scenario to delete."""
    if not scenarios:
        return None
    
    max_num = len(scenarios)
    
    while True:
        try:
            choice = input(f"Enter the number (1-{max_num}) of the scenario to delete, or 'q' to quit: ").strip()
            
            if choice.lower() == 'q':
                print("Cancelled.")
                return None
            
            choice_num = int(choice)
            
            if 1 <= choice_num <= max_num:
                selected_scenario_id = scenarios[choice_num - 1][0]
                return selected_scenario_id
            else:
                print(f"Please enter a number between 1 and {max_num}.")
        except ValueError:
            print("Please enter a valid number or 'q' to quit.")
        except KeyboardInterrupt:
            print("\nCancelled.")
            return None

def count_rows_to_remove(csv_file_path, scenario_id):
    """Count how many rows will be removed from a CSV file."""
    try:
        with open(csv_file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            count = sum(1 for row in reader if row.get('scenario_id') == scenario_id)
        return count
    except Exception:
        return 0

def remove_scenario_from_csv(csv_file_path, scenario_id):
    """Remove all rows with the given scenario_id from a CSV file."""
    # Read the CSV file
    with open(csv_file_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        rows = list(reader)
    
    if not rows:
        return False, 0
    
    # Get header and data rows
    header = rows[0]
    data_rows = rows[1:]
    
    # Find the scenario_id column index
    try:
        scenario_id_col_idx = header.index('scenario_id')
    except ValueError:
        return False, 0
    
    # Filter out rows that match the scenario_id
    original_count = len(data_rows)
    filtered_rows = [row for row in data_rows if row[scenario_id_col_idx] != scenario_id]
    removed_count = original_count - len(filtered_rows)
    
    if removed_count == 0:
        return False, 0
    
    # Write back to file
    with open(csv_file_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(filtered_rows)
    
    return True, removed_count

def main():
    """Main function to process all CSV files."""
    # Scan for scenario IDs
    scenario_info = scan_scenario_ids()
    
    if not scenario_info:
        return
    
    # Display list and get user selection
    scenarios = display_scenario_list(scenario_info)
    selected_scenario_id = get_user_selection(scenarios)
    
    if not selected_scenario_id:
        return
    
    # Confirm deletion
    selected_info = scenario_info[selected_scenario_id]
    print("\n" + "=" * 80)
    print(f"Selected Scenario ID: {selected_scenario_id}")
    print(f"Project: {selected_info['project_name']}")
    print(f"Timestamp: {selected_info['timestamp']}")
    print("=" * 80)
    
    # Count rows to be removed
    csv_files = sorted(OUTPUTS_DIR.glob("*.csv"))
    total_rows = 0
    files_with_data = []
    
    for csv_file in csv_files:
        count = count_rows_to_remove(csv_file, selected_scenario_id)
        if count > 0:
            total_rows += count
            files_with_data.append((csv_file.name, count))
    
    print(f"\nThis will remove {total_rows} row(s) from {len(files_with_data)} file(s):")
    for filename, count in files_with_data:
        print(f"  - {filename}: {count} row(s)")
    
    confirm = input(f"\nAre you sure you want to delete scenario '{selected_scenario_id}'? (yes/no): ").strip().lower()
    
    if confirm not in ['yes', 'y']:
        print("Deletion cancelled.")
        return
    
    # Perform deletion
    print(f"\nRemoving scenario '{selected_scenario_id}' from all CSV files...\n")
    
    files_modified = 0
    total_removed = 0
    
    for csv_file in csv_files:
        modified, removed = remove_scenario_from_csv(csv_file, selected_scenario_id)
        if modified:
            files_modified += 1
            total_removed += removed
            print(f"  ✓ Removed {removed} row(s) from {csv_file.name}")
    
    print(f"\n{'=' * 80}")
    print(f"Done! Removed {total_removed} row(s) from {files_modified} file(s).")
    print("=" * 80)

if __name__ == "__main__":
    main()




