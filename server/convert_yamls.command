#!/bin/bash
# Convert all YAML files in a user-specified directory to JSON format

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Print large title
cat << 'EOF'
 _   _    _    __  __ _       _____ ___      _ ____   ___  _   _ 
| | | |  / \  |  \/  | |     |_   _/ _ \    | / ___| / _ \| \ | |
| |_| | / _ \ | |\/| | |       | || | | |   | \___ \| | | |  \| |
 \ _ / / ___ \| |  | | |___    | || |_| |  _| |___) | |_| | |\  |
  | | /_/   \_\_|  |_|_____|   |_| \___/  |___|____/ \___/|_| \_|
                                                                 
   ____  ___  _   _ _        _ _____ ____ _____ _____ ____           
  / ___/ _ \| \ | |  \      / | ____|  _ \_   _| ____|  _ \          
 | |  | | | |  \| |   \    /  |  _| | |_) || | |  _| | |_) |         
 | |__| |_| | |\  |    \  /   | |___|  _ < | | | |___|  _ <          
  \____\___/|_| \_|     \/    |_____|_| \_\|_| |_____|_| \_\        
                                                                 
EOF

echo "This tool converts all YAML files in a directory to JSON format."
echo "The JSON files will be saved to a 'json/' subdirectory."
echo

# Check if virtual environment exists
if [[ ! -d ".venv" ]]; then
  echo "Error: Virtual environment not found at .venv" >&2
  echo "Please run this script from the server directory with a configured .venv" >&2
  exit 1
fi

# Activate virtual environment
# shellcheck disable=SC1091
source ".venv/bin/activate"

# Check if yaml_to_json.py exists
if [[ ! -f "yaml_to_json.py" ]]; then
  echo "Error: yaml_to_json.py not found in current directory" >&2
  exit 1
fi

# Function to browse and select directory
browse_for_directory() {
  if command -v osascript >/dev/null 2>&1; then
    # Use macOS file picker dialog
    selected_dir=$(osascript -e 'try
      set selectedFolder to choose folder with prompt "Select directory containing YAML files:"
      return POSIX path of selectedFolder
    on error
      return ""
    end try' 2>/dev/null)
    
    if [[ -n "$selected_dir" && "$selected_dir" != "" ]]; then
      # Remove trailing newline and spaces
      selected_dir=$(echo "$selected_dir" | tr -d '\n\r' | sed 's/[[:space:]]*$//')
      # Remove trailing slash if present
      selected_dir="${selected_dir%/}"
      echo "$selected_dir"
      return 0
    fi
  fi
  return 1
}

# Function to prompt for directory
prompt_for_directory() {
  while true; do
    echo -n "Enter the path to the directory containing YAML files: "
    read -r yaml_dir
    
    # Expand tilde and make absolute path
    yaml_dir="${yaml_dir/#\~/$HOME}"
    yaml_dir="$(realpath "$yaml_dir" 2>/dev/null || echo "$yaml_dir")"
    
    if [[ ! -d "$yaml_dir" ]]; then
      echo "Error: Directory '$yaml_dir' does not exist. Please try again."
      continue
    fi
    
    # Check if directory contains any YAML files
    if ! find "$yaml_dir" -maxdepth 1 -name "*.yaml" -o -name "*.yml" | grep -q .; then
      echo "Warning: No YAML files (*.yaml or *.yml) found in '$yaml_dir'."
      echo -n "Continue anyway? (y/n): "
      read -r continue_choice
      if [[ "$continue_choice" != "y" && "$continue_choice" != "Y" ]]; then
        continue
      fi
    fi
    
    break
  done
}

# Define possible YAML directories
ctcc_yaml_dir="$(dirname "$SCRIPT_DIR")/yamls"  # CTCC/yamls/
local_yaml_dir="$SCRIPT_DIR/yamls"              # server/yamls/

echo "Select YAML source directory:"
echo "1. CTCC/yamls/ ($(basename "$(dirname "$SCRIPT_DIR")")/yamls/)"
echo "2. yamls/ from command directory ($(basename "$SCRIPT_DIR")/yamls/)"
echo "3. Browse for directory (macOS file picker)"
echo -n "Enter choice (1, 2, or 3): "
read -r dir_choice

case "$dir_choice" in
  "1")
    if [[ -d "$ctcc_yaml_dir" ]]; then
      yaml_dir="$ctcc_yaml_dir"
      echo "Using: $yaml_dir"
      
      # Check if it contains YAML files
      yaml_count_check=$(find "$yaml_dir" -maxdepth 1 \( -name "*.yaml" -o -name "*.yml" \) | wc -l)
      if [[ $yaml_count_check -eq 0 ]]; then
        echo "Warning: No YAML files found in selected directory."
        echo -n "Would you like to select a different directory? (y/n): "
        read -r select_different
        if [[ "$select_different" == "y" || "$select_different" == "Y" ]]; then
          if browsed_dir=$(browse_for_directory); then
            yaml_dir="$browsed_dir"
          else
            echo "Browse cancelled. Using empty directory."
          fi
        fi
      fi
    else
      echo "Error: CTCC/yamls/ directory not found at $ctcc_yaml_dir"
      echo "Falling back to browse option..."
      if browsed_dir=$(browse_for_directory); then
        yaml_dir="$browsed_dir"
      else
        echo "Browse cancelled or not available. Falling back to manual entry."
        prompt_for_directory
      fi
    fi
    ;;
  "2")
    if [[ -d "$local_yaml_dir" ]]; then
      yaml_dir="$local_yaml_dir"
      echo "Using: $yaml_dir"
      
      # Check if it contains YAML files
      yaml_count_check=$(find "$yaml_dir" -maxdepth 1 \( -name "*.yaml" -o -name "*.yml" \) | wc -l)
      if [[ $yaml_count_check -eq 0 ]]; then
        echo "Warning: No YAML files found in selected directory."
        echo -n "Would you like to select a different directory? (y/n): "
        read -r select_different
        if [[ "$select_different" == "y" || "$select_different" == "Y" ]]; then
          if browsed_dir=$(browse_for_directory); then
            yaml_dir="$browsed_dir"
          else
            echo "Browse cancelled. Using empty directory."
          fi
        fi
      fi
    else
      echo "Error: yamls/ directory not found at $local_yaml_dir"
      echo "Falling back to browse option..."
      if browsed_dir=$(browse_for_directory); then
        yaml_dir="$browsed_dir"
      else
        echo "Browse cancelled or not available. Falling back to manual entry."
        prompt_for_directory
      fi
    fi
    ;;
  "3")
    echo "Opening macOS file picker..."
    if browsed_dir=$(browse_for_directory); then
      yaml_dir="$browsed_dir"
    else
      echo "Browse cancelled or not available. Falling back to manual entry."
      prompt_for_directory
    fi
    ;;
  *)
    echo "Invalid choice. Falling back to browse option..."
    if browsed_dir=$(browse_for_directory); then
      yaml_dir="$browsed_dir"
    else
      echo "Browse cancelled or not available. Falling back to manual entry."
      prompt_for_directory
    fi
    ;;
esac

echo
echo "Processing YAML files in: $yaml_dir"

# Create json subdirectory in the script directory (not the yaml directory)
json_dir="$SCRIPT_DIR/json"
mkdir -p "$json_dir"

echo "JSON files will be saved to: $json_dir"
echo

# Count YAML files
yaml_count=$(find "$yaml_dir" -maxdepth 1 \( -name "*.yaml" -o -name "*.yml" \) | wc -l)
echo "Found $yaml_count YAML file(s) to process."
echo

if [[ $yaml_count -eq 0 ]]; then
  echo "No YAML files to process. Exiting."
  exit 0
fi

# Process each YAML file
processed=0
failed=0

for yaml_file in "$yaml_dir"/*.yaml "$yaml_dir"/*.yml; do
  # Skip if file doesn't exist (handles case where no files match pattern)
  [[ ! -f "$yaml_file" ]] && continue
  
  basename_file=$(basename "$yaml_file")
  basename_no_ext="${basename_file%.*}"
  json_output="$json_dir/${basename_no_ext}.json"
  
  echo "Converting: $basename_file → ${basename_no_ext}.json"
  
  if python yaml_to_json.py "$yaml_file" "$json_output"; then
    ((processed++))
  else
    echo "  ❌ Failed to convert $basename_file"
    ((failed++))
  fi
done

echo
echo "Conversion complete!"
echo "✅ Successfully converted: $processed files"
if [[ $failed -gt 0 ]]; then
  echo "❌ Failed conversions: $failed files"
fi

echo
echo "JSON files are available in: $json_dir"

# Check if combined file was created
if [[ -f "$json_dir/final_combined.json" ]]; then
  echo "📦 Combined file created: $json_dir/final_combined.json"
fi

echo
echo "Press any key to exit..."
read -n 1 -s