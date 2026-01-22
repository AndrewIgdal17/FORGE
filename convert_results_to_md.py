#!/usr/bin/env python3
"""
Convert all CSV files in outputs/ to Markdown tables in outputs_md/

Usage:
    python3 convert_results_to_md.py
"""

import csv
import os
from pathlib import Path

def csv_to_markdown_table(csv_path):
    """Convert a CSV file to Markdown table format."""
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        headers = next(reader)
        rows = list(reader)
    
    # Generate title from filename
    title = csv_path.stem.replace('_', ' ').title()
    
    # Build Markdown table
    md_lines = [f"# {title}", ""]
    
    # Header row
    md_lines.append("| " + " | ".join(headers) + " |")
    
    # Separator row
    md_lines.append("|" + "|".join(["---" for _ in headers]) + "|")
    
    # Data rows
    for row in rows:
        # Handle empty rows
        if not row or all(not cell.strip() for cell in row):
            continue
        # Pad row if needed
        while len(row) < len(headers):
            row.append("")
        # Truncate if too long
        row = row[:len(headers)]
        md_lines.append("| " + " | ".join(str(cell) for cell in row) + " |")
    
    return "\n".join(md_lines)

def main():
    """Main conversion function."""
    # Get paths
    script_dir = Path(__file__).parent
    outputs_dir = script_dir / "outputs"
    outputs_md_dir = script_dir / "outputs_md"
    
    # Create outputs_md directory if it doesn't exist
    outputs_md_dir.mkdir(exist_ok=True)
    
    # Find all CSV files
    csv_files = sorted(outputs_dir.glob("*.csv"))
    
    if not csv_files:
        print("No CSV files found in outputs/")
        return
    
    print(f"Found {len(csv_files)} CSV files to convert...")
    print()
    
    # Convert each CSV
    converted = 0
    for csv_file in csv_files:
        try:
            md_content = csv_to_markdown_table(csv_file)
            md_file = outputs_md_dir / f"{csv_file.stem}.md"
            md_file.write_text(md_content, encoding='utf-8')
            print(f"✓ Converted {csv_file.name} → {md_file.name}")
            converted += 1
        except Exception as e:
            print(f"✗ Error converting {csv_file.name}: {e}")
    
    print()
    print(f"Conversion complete: {converted}/{len(csv_files)} files converted")
    print(f"Markdown files saved to: {outputs_md_dir}")

if __name__ == "__main__":
    main()




