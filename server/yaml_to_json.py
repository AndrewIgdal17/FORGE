"""Simple YAML → JSON converter with optional directory aggregation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

try:
    import yaml
except ModuleNotFoundError as exc:  # pragma: no cover
    raise SystemExit("PyYAML is required. Install it with 'pip install pyyaml'.") from exc

COMBINED_FILENAME = "final_combined.json"
SKIP_BASENAME = "project_category_template"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert a YAML file to JSON.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("input", type=Path, help="Path to the YAML file to convert")
    parser.add_argument(
        "output",
        type=Path,
        nargs="?",
        help="Output JSON file (defaults to stdout if omitted)",
    )
    parser.add_argument(
        "--indent",
        type=int,
        default=2,
        help="Number of spaces to indent JSON output (ignored for combined file)",
    )
    parser.add_argument(
        "--no-combine",
        action="store_true",
        help="Skip building the combined JSON file when writing to disk",
    )
    return parser.parse_args()


def load_yaml(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def dump_json(data: Any, output: Path | None, indent: int) -> None:
    if output:
        with output.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=indent)
            handle.write("\n")
    else:
        json.dump(data, sys.stdout, indent=indent)
        sys.stdout.write("\n")


def build_combined_json(directory: Path) -> None:
    """Combine individual JSON files into a minimized aggregate."""
    combined: Dict[str, Any] = {}

    for json_file in sorted(directory.glob("*.json")):
        if json_file.name == COMBINED_FILENAME:
            continue
        if json_file.stem == SKIP_BASENAME:
            continue
        with json_file.open("r", encoding="utf-8") as handle:
            combined[json_file.stem] = json.load(handle)

    combined_path = directory / COMBINED_FILENAME
    with combined_path.open("w", encoding="utf-8") as handle:
        json.dump(combined, handle, separators=(",", ":"))
        handle.write("\n")


def main() -> None:
    args = parse_args()
    data = load_yaml(args.input)
    dump_json(data, args.output, args.indent)

    if args.output and not args.no_combine:
        build_combined_json(args.output.parent)


if __name__ == "__main__":
    main()
