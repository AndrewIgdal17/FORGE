#!/usr/bin/env python3
"""
Script to verify that values in results_tables.tex match the source CSV files.

CSV files are the source of truth. This script parses the LaTeX file to extract
actual values and compares them against the CSV outputs.
"""

import csv
import re
from pathlib import Path

# Map LaTeX labels to CSV field names
LABEL_TO_CSV_FIELD = {
    # Cost breakdown labels
    "Build Costs": "build_cost_pv",
    "Right-of-Way": "row_cost_pv",
    "Env. Mitigation": "env_mitigation_pv",
    "O\\&M": "oandm_pv",
    "Insurance": "insurance_pv",
    "Residual Exceedance": "residual_exceedance_pv",
    "Wildfire Risk": "wildfire_pv",
    "Outage Risk": "outage_pv",
    "Base Delay": "delay_cost_pv",
    "Congestion Delay": "congestion_delay_cost_pv",
    "Curtailment Delay": "curtailment_delay_cost_pv",
    "Energy Losses": "energy_losses_pv",
    "Line Losses": "energy_losses_pv",  # backward compat: old LaTeX may say "Line Losses"
    "Emissions": "emissions_cost_pv",
    "Total Costs": "total_costs_pv",
    "Congestion (haircut)": "congestion_benefit_haircut_pv",
    "Curtailment (haircut)": "curtailment_benefit_haircut_pv",
    "Revenue Requirements": "revenue_pv",
    "Total Benefits": "total_benefits_haircut_pv",
    "Net Lifetime Cost": "net_benefit_pv",
    "Net Lifetime Benefit": "net_benefit_pv",
    # BCR labels
    "BCR\\textsubscript{system}": "bcr_system",
    "BCR\\textsubscript{utility}": "bcr_utility",
    "BCR\\textsubscript{ratepayer}": "bcr_ratepayer",
    "BCR\\textsubscript{capital}": "bcr_capital",
    "BCR\\textsubscript{capital and delay}": "bcr_capital_and_delay",
    "BCR\\textsubscript{primary}": "bcr_primary",
}

# Map CSV field names to their source files and field names
CSV_FIELD_SOURCES = {
    "build_cost_pv": ("build_costs", "total_pv"),
    "row_cost_pv": ("row_costs", "total_pv"),
    "env_mitigation_pv": ("environmental_mitigation", "total_pv"),
    "insurance_pv": ("insurance_costs", "pv_total"),
    "oandm_pv": ("oandm_costs", "pv_total"),
    "wildfire_pv": ("batch_summary", "wildfire_pv"),
    "outage_pv": ("batch_summary", "outage_pv"),
    "delay_cost_pv": ("delay_costs", "total_pv"),
    "congestion_delay_cost_pv": ("batch_summary", "congestion_delay_cost_pv"),
    "curtailment_delay_cost_pv": ("batch_summary", "curtailment_delay_cost_pv"),
    "residual_exceedance_pv": ("batch_summary", "residual_exceedance_pv"),
    "energy_losses_pv": ("batch_summary", "energy_losses_pv"),
    "line_loss_cost_pv": ("batch_summary", "energy_losses_pv"),  # backward compat
    "emissions_cost_pv": ("emissions_costs", "cost_pv"),
    "total_costs_pv": ("batch_summary", "total_costs_pv"),
    "congestion_benefit_haircut_pv": ("batch_summary", "congestion_benefit_haircut_pv"),
    "curtailment_benefit_haircut_pv": (
        "batch_summary",
        "curtailment_benefit_haircut_pv",
    ),
    "revenue_pv": ("batch_summary", "revenue_pv"),
    "total_benefits_haircut_pv": ("batch_summary", "total_benefits_haircut_pv"),
    "net_benefit_pv": ("batch_summary", "net_benefit_pv"),
    "bcr_system": ("batch_summary", "bcr_system"),
    "bcr_utility": ("batch_summary", "bcr_utility"),
    "bcr_ratepayer": ("batch_summary", "bcr_ratepayer"),
    "bcr_capital": ("batch_summary", "bcr_capital"),
    "bcr_capital_and_delay": ("batch_summary", "bcr_capital_and_delay"),
    "bcr_primary": ("batch_summary", "bcr_primary"),
}


def parse_latex_file(latex_path):
    """Parse LaTeX file and extract values for each scenario."""
    with open(latex_path, "r") as f:
        content = f.read()

    scenarios = {}
    current_scenario = None

    # Find all scenario sections
    scenario_pattern = r"\\section\{Scenario (\d+):"
    matches = list(re.finditer(scenario_pattern, content))

    for i, match in enumerate(matches):
        scenario_num = match.group(1)
        current_scenario = f"S{scenario_num}"
        scenarios[current_scenario] = {}

        # Find the end of this scenario section (next section or end of file)
        start_pos = match.end()
        if i + 1 < len(matches):
            end_pos = matches[i + 1].start()
        else:
            end_pos = len(content)

        scenario_content = content[start_pos:end_pos]

        # Extract cost breakdown values
        # Pattern: \quad Label & value \\ or \textbf{Label} & \textbf{value} \\
        # Handle both regular and bold entries
        cost_pattern = r"\\quad\s+([^&]+?)\s*&\s*([0-9,.-]+)\s*\\\\"
        for cost_match in re.finditer(cost_pattern, scenario_content):
            label = cost_match.group(1).strip()
            # Remove LaTeX formatting
            label = re.sub(r"\\textbf\{([^}]+)\}", r"\1", label)
            label = re.sub(r"\\textit\{([^}]+)\}", r"\1", label)
            value_str = cost_match.group(2).replace(",", "").strip()
            try:
                value = float(value_str)
                # Map label to CSV field
                if label in LABEL_TO_CSV_FIELD:
                    csv_field = LABEL_TO_CSV_FIELD[label]
                    scenarios[current_scenario][csv_field] = value
            except ValueError:
                pass

        # Extract bold Total Costs
        total_costs_pattern = r"\\textbf\{Total Costs\}\s*&\s*\\textbf\{([0-9,.-]+)\}"
        total_match = re.search(total_costs_pattern, scenario_content)
        if total_match:
            value_str = total_match.group(1).replace(",", "").strip()
            try:
                value = float(value_str)
                scenarios[current_scenario]["total_costs_pv"] = value
            except ValueError:
                pass

        # Extract bold Net Lifetime Cost/Benefit
        net_pattern = (
            r"\\textbf\{Net Lifetime (Cost|Benefit)\}\s*&\s*\\textbf\{([0-9,.-]+)\}"
        )
        net_match = re.search(net_pattern, scenario_content)
        if net_match:
            value_str = net_match.group(2).replace(",", "").strip()
            try:
                value = float(value_str)
                scenarios[current_scenario]["net_benefit_pv"] = value
            except ValueError:
                pass

        # Extract BCR values
        # Pattern: BCR\textsubscript{...} & value \\
        bcr_pattern = r"BCR\\textsubscript\{([^}]+)\}\s*&\s*([0-9.]+)\s*\\\\"
        for bcr_match in re.finditer(bcr_pattern, scenario_content):
            bcr_type = bcr_match.group(1)
            value_str = bcr_match.group(2).strip()
            try:
                value = float(value_str)
                # Map BCR type to CSV field
                bcr_label = f"BCR\\textsubscript{{{bcr_type}}}"
                if bcr_label in LABEL_TO_CSV_FIELD:
                    csv_field = LABEL_TO_CSV_FIELD[bcr_label]
                    scenarios[current_scenario][csv_field] = value
            except ValueError:
                pass

    return scenarios


def load_csv_data(csv_path):
    """Load CSV data and return as dict keyed by project_name."""
    data = {}
    with open(csv_path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            project_name = row["project_name"]
            # For emissions CSV, use summary row (row_type='summary' and pollutant='all')
            if (
                "pollutant" in row
                and row.get("row_type") == "summary"
                and row.get("pollutant") == "all"
            ):
                data[project_name] = row
            elif "pollutant" not in row:
                # For other CSVs, use the row (may be summary or detail)
                data[project_name] = row
    return data


def compare_values(tex_val, csv_val, tolerance=0.1, name=""):
    """Compare two values with tolerance."""
    diff = abs(tex_val - csv_val)
    if diff <= tolerance:
        return True, diff
    else:
        return False, diff


def get_csv_value(csv_field, scenario_name, csv_data_dict):
    """Get CSV value for a given field and scenario."""
    if csv_field not in CSV_FIELD_SOURCES:
        return None

    source_file, field_name = CSV_FIELD_SOURCES[csv_field]
    csv_data = csv_data_dict.get(source_file, {})
    scenario_data = csv_data.get(scenario_name, {})

    if not scenario_data:
        return None

    # Backward compat: energy_losses_pv may be in batch_summary as line_loss_cost_pv in old CSVs
    if field_name == "energy_losses_pv" and source_file == "batch_summary":
        value_str = (
            scenario_data.get("energy_losses_pv")
            or scenario_data.get("line_loss_cost_pv")
            or "0"
        )
    else:
        value_str = scenario_data.get(field_name, "0")
    if not value_str or value_str == "":
        return None

    try:
        value = float(value_str)
        # Convert to millions for dollar amounts (not BCR ratios)
        if not csv_field.startswith("bcr_"):
            value = value / 1e6
        return value
    except (ValueError, TypeError):
        return None


def main():
    outputs_dir = Path("outputs")
    latex_path = Path("papers/paper1/results_tables.tex")

    # Parse LaTeX file to extract actual values
    print("Parsing LaTeX file to extract values...")
    latex_scenarios = parse_latex_file(latex_path)
    print(f"Found {len(latex_scenarios)} scenarios in LaTeX file")

    # Load CSV files (source of truth)
    print("Loading CSV files (source of truth)...")
    csv_data_dict = {
        "batch_summary": load_csv_data(outputs_dir / "batch_summary.csv"),
        "build_costs": load_csv_data(outputs_dir / "build_costs.csv"),
        "row_costs": load_csv_data(outputs_dir / "row_costs.csv"),
        "environmental_mitigation": load_csv_data(
            outputs_dir / "environmental_mitigation.csv"
        ),
        "insurance_costs": load_csv_data(outputs_dir / "insurance_costs.csv"),
        "oandm_costs": load_csv_data(outputs_dir / "oandm_costs.csv"),
        "wildfire_costs": load_csv_data(outputs_dir / "wildfire_costs.csv"),
        "outage_costs": load_csv_data(outputs_dir / "outage_costs.csv"),
        "delay_costs": load_csv_data(outputs_dir / "delay_costs.csv"),
        "line_loss_costs": load_csv_data(outputs_dir / "line_loss_costs.csv"),
        "emissions_costs": load_csv_data(outputs_dir / "emissions_costs.csv"),
    }

    # Map scenario IDs to project names
    scenario_map = {
        "S1": "S1_California_Rural_Overhead_AC_657MW",
        "S2": "S2_California_Highway_Route_AC_657MW",
        "S3": "S3_California_Underground_AC_657MW",
        "S4": "S4_LongDistance_HVDC_1500MW",
        "S5": "S5_LongDistance_HVDC_1500MW_LCC",
        "S6": "S6_LongDistance_AC_1792MW",
        "S7": "S7_Reconductoring_329to657MW",
        "S8": "S8_Greenfield_657MW_StandardAC",
    }

    errors = []
    warnings = []
    rounding_warnings = []

    for scenario_id, scenario_name in scenario_map.items():
        print(f"\n{'='*60}")
        print(f"Verifying {scenario_id}: {scenario_name}")
        print(f"CSV is source of truth - checking if LaTeX matches CSV")
        print(f"{'='*60}")

        if scenario_name not in csv_data_dict["batch_summary"]:
            errors.append(f"{scenario_id}: Missing from batch_summary.csv")
            continue

        if scenario_id not in latex_scenarios:
            errors.append(f"{scenario_id}: Not found in LaTeX file")
            continue

        latex_vals = latex_scenarios[scenario_id]

        # Compare each value found in LaTeX against CSV
        for csv_field, latex_val in latex_vals.items():
            csv_val = get_csv_value(csv_field, scenario_name, csv_data_dict)

            if csv_val is None:
                warnings.append(
                    f"{scenario_id}: Could not find CSV value for {csv_field}"
                )
                continue

            # Determine tolerances
            # Error tolerance: strict threshold for actual errors
            # Rounding tolerance: more lenient threshold for acceptable rounding differences
            if csv_field.startswith("bcr_"):
                error_tolerance = 0.001
                rounding_tolerance = 0.01  # 1% for ratios
            else:
                error_tolerance = 0.1  # 0.1M for dollar amounts
                rounding_tolerance = 1.0  # 1M for dollar amounts (acceptable rounding)

            match, diff = compare_values(latex_val, csv_val, tolerance=error_tolerance)
            rounding_match, _ = compare_values(
                latex_val, csv_val, tolerance=rounding_tolerance
            )

            if not match:
                unit = "" if csv_field.startswith("bcr_") else "M"
                if rounding_match:
                    # Within rounding tolerance but outside error tolerance - minor rounding issue
                    rounding_msg = f"  ⚠ {csv_field}: LaTeX={latex_val:.4f}{unit} vs CSV={csv_val:.4f}{unit} (diff={diff:.4f}{unit}) - minor rounding difference"
                    rounding_warnings.append(f"{scenario_id}: {rounding_msg}")
                    print(rounding_msg)
                else:
                    # Actual error - exceeds both tolerances
                    error_msg = f"  ❌ {csv_field}: LaTeX shows {latex_val:.4f}{unit} but CSV (source of truth) has {csv_val:.4f}{unit}, diff={diff:.4f}{unit}"
                    errors.append(f"{scenario_id}: {error_msg}")
                    print(error_msg)
            else:
                unit = "" if csv_field.startswith("bcr_") else "M"
                if csv_field.startswith("bcr_"):
                    print(
                        f"  ✓ {csv_field}: LaTeX={latex_val:.4f} matches CSV={csv_val:.4f} (diff={diff:.6f})"
                    )
                else:
                    print(
                        f"  ✓ {csv_field}: LaTeX={latex_val:.1f}M matches CSV={csv_val:.1f}M (diff={diff:.4f}M)"
                    )

    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(
        "\nCSV files are the source of truth. This script verifies LaTeX matches CSV."
    )
    if errors:
        print(f"\n❌ Found {len(errors)} errors where LaTeX does not match CSV:")
        for error in errors:
            print(f"  {error}")
    else:
        print("\n✓ No errors found - all LaTeX values match the CSV source of truth!")

    if rounding_warnings:
        print(
            f"\n⚠ Found {len(rounding_warnings)} minor rounding differences (acceptable but noted):"
        )
        for rounding_warning in rounding_warnings:
            print(f"  {rounding_warning}")

    if warnings:
        print(f"\n⚠ Found {len(warnings)} warnings:")
        for warning in warnings:
            print(f"  {warning}")


if __name__ == "__main__":
    main()
