#!/bin/bash
# Regenerate all JSON files from YAML files
# This ensures the web app loads the latest values from YAML files

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CTCC_DIR="$(dirname "$SCRIPT_DIR")"
YAMLS_DIR="$CTCC_DIR/yamls"
JSON_DIR="$SCRIPT_DIR/json"

echo "Regenerating JSON files from YAML files..."
echo "Source: $YAMLS_DIR"
echo "Destination: $JSON_DIR"
echo

# Check if venv exists
if [[ ! -d "$CTCC_DIR/venv" ]]; then
  echo "Error: Virtual environment not found at $CTCC_DIR/venv" >&2
  exit 1
fi

# Activate virtual environment
source "$CTCC_DIR/venv/bin/activate"

# Count YAML files
yaml_count=$(find "$YAMLS_DIR" -maxdepth 1 -name "*.yaml" | wc -l | tr -d ' ')
echo "Found $yaml_count YAML file(s) to process."
echo

if [[ $yaml_count -eq 0 ]]; then
  echo "No YAML files found. Exiting."
  exit 1
fi

# Process each YAML file
processed=0
failed=0

for yaml_file in "$YAMLS_DIR"/*.yaml; do
  [[ ! -f "$yaml_file" ]] && continue
  
  basename_file=$(basename "$yaml_file")
  basename_no_ext="${basename_file%.yaml}"
  json_output="$JSON_DIR/${basename_no_ext}.json"
  
  echo "Converting: $basename_file → ${basename_no_ext}.json"
  
  if python3 -c "
import yaml
import json
from pathlib import Path

yaml_path = Path('$yaml_file')
json_path = Path('$json_output')

data = yaml.safe_load(yaml_path.open('r', encoding='utf-8'))
json_path.parent.mkdir(parents=True, exist_ok=True)
json.dump(data, json_path.open('w', encoding='utf-8'), indent=2)
" 2>/dev/null; then
    ((processed++))
    echo "  ✅ Success"
  else
    echo "  ❌ Failed"
    ((failed++))
  fi
done

echo
echo "Conversion complete!"
echo "✅ Successfully converted: $processed files"
if [[ $failed -gt 0 ]]; then
  echo "❌ Failed conversions: $failed files"
fi

# Rebuild final_combined.json
echo
echo "Rebuilding final_combined.json..."
if python3 -c "
from pathlib import Path
import json

json_dir = Path('$JSON_DIR')
combined = {}

for json_file in sorted(json_dir.glob('*.json')):
    if json_file.name == 'final_combined.json':
        continue
    if json_file.stem == 'project_category_template':
        continue
    with json_file.open('r', encoding='utf-8') as f:
        combined[json_file.stem] = json.load(f)

combined_path = json_dir / 'final_combined.json'
with combined_path.open('w', encoding='utf-8') as f:
    json.dump(combined, f, separators=(',', ':'))
    f.write('\n')

print(f'✅ final_combined.json created with {len(combined)} sections')
" 2>/dev/null; then
  echo "✅ final_combined.json regenerated"
else
  echo "❌ Failed to regenerate final_combined.json"
  exit 1
fi

echo
echo "All JSON files have been regenerated from YAML files."
echo "The web app will now load the latest values from the YAML files."

