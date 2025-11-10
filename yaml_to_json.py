"""
Convert all YAML files in the yamls/ directory to a single combined JSON file.
This version is designed for use with ctcc.py to enable JSON input mode.
"""

import json
import sys
from pathlib import Path

try:
    import yaml
except ModuleNotFoundError as exc:
    raise SystemExit("PyYAML is required. Install it with 'pip install pyyaml'.") from exc


def convert_yamls_to_combined_json(yamls_dir: Path, output_file: Path) -> None:
    """
    Convert all YAML files in a directory to a single combined JSON file.

    Args:
        yamls_dir: Directory containing YAML files
        output_file: Path to write the combined JSON file
    """
    combined = {}

    # Skip files with these basenames
    skip_basenames = ["project_category_template"]

    # Find all YAML files in the directory
    yaml_files = list(yamls_dir.glob("*.yaml")) + list(yamls_dir.glob("*.yml"))
    yaml_files.sort()

    if not yaml_files:
        raise ValueError(f"No YAML files found in {yamls_dir}")

    print(f"Converting {len(yaml_files)} YAML files from {yamls_dir}...")

    for yaml_file in yaml_files:
        # Skip template files
        if yaml_file.stem in skip_basenames:
            print(f"  Skipping: {yaml_file.name}")
            continue

        print(f"  Loading: {yaml_file.name}")
        try:
            with yaml_file.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                combined[yaml_file.stem] = data
        except Exception as e:
            print(f"  ERROR loading {yaml_file.name}: {e}")
            raise

    # Write combined JSON file
    print(f"\nWriting combined JSON to {output_file}...")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with output_file.open("w", encoding="utf-8") as f:
        json.dump(combined, f, separators=(",", ":"))
        f.write("\n")

    print(f"✓ Successfully created combined JSON with {len(combined)} sections")


def main():
    """Main entry point for standalone execution."""
    # Default paths relative to CTCC root
    script_dir = Path(__file__).parent
    yamls_dir = script_dir / "yamls"
    output_file = script_dir / "combined_data.json"

    # Allow command-line override
    if len(sys.argv) > 1:
        yamls_dir = Path(sys.argv[1])
    if len(sys.argv) > 2:
        output_file = Path(sys.argv[2])

    if not yamls_dir.exists():
        raise FileNotFoundError(f"YAML directory not found: {yamls_dir}")

    convert_yamls_to_combined_json(yamls_dir, output_file)
    print(f"\nCombined JSON file location: {output_file}")


if __name__ == "__main__":
    main()
