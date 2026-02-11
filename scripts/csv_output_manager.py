# Author: Andrew Igdal
# Date: 2025-10-29
# Description: CSV output manager for CTCC batch analysis, sensitivity studies, and Monte Carlo simulations.

from __future__ import annotations

import csv
import os
import yaml
from datetime import datetime
from typing import Dict, Any, List, Optional
from path_config import OUTPUTS_DIR, YAMLS_DIR
from smart_loaders import (
    load_project_technical_details,
    load_physical_details,
    load_financing_social_discount_rate,
    get_project_data_raw,
)

BATCH_SUMMARY_FIELDS = [
    # 1. Identification
    "project_name",
    "scenario_id",
    "timestamp",
    # 2. Key Parameters
    "capacity_mw",
    "line_length_miles",
    "construction_type",
    "ac_dc",
    "social_discount_rate",
    # 3. Capital Costs PV (with breakdown)
    "build_cost_pv",
    "row_cost_pv",
    "row_capital_pv",
    "row_rent_pv",
    "row_capital_afudc",
    "row_capital_nominal",
    "row_rent_nominal",
    "env_mitigation_pv",
    "capital_costs_pv",
    # 4. Operational Costs PV (with breakdown)
    "insurance_pv",
    "oandm_pv",
    "operational_costs_pv",
    # 5. Risk Costs PV (with breakdown)
    "wildfire_pv",
    "wildfire_liability_insurance_pv",
    "outage_pv",
    "risk_costs_pv",
    # 6. Delay Costs PV
    "delay_cost_pv",
    "congestion_delay_cost_pv",
    "curtailment_delay_cost_pv",
    "residual_exceedance_pv",
    "delay_costs_pv",
    # 7. Energy/Emissions Costs PV (with breakdown)
    "emissions_cost_pv",
    "energy_losses_pv",
    "conductor_loss_pv",
    "converter_loss_pv",
    "energy_losses_nominal",
    "energy_emissions_costs_pv",
    # 8. Total Costs PV
    "total_costs_pv",
    # 9. Benefits PV (with breakdown)
    "congestion_benefit_pv",
    "curtailment_benefit_pv",
    "revenue_pv",
    "congestion_benefit_haircut_pv",
    "curtailment_benefit_haircut_pv",
    "total_benefits_pv",
    "total_benefits_haircut_pv",
    # 10. BCR Metrics
    "bcr_system",
    "bcr_capital",
    "bcr_capital_and_delay",
    "bcr_primary",
    # Combined risk BCRs (renamed)
    "bcr_excluding_wildfire_risk_and_outage_risk",
    "bcr_excluding_emissions_and_wildfire_risk_and_outage_risk",
    "bcr_excluding_linelosses_and_wildfire_risk_and_outage_risk",
    "bcr_excluding_emissions_and_linelosses_and_wildfire_risk_and_outage_risk",
    # Emissions/linelosses BCRs (unchanged)
    "bcr_excluding_emissions",
    "bcr_excluding_linelosses",
    "bcr_excluding_emissions_and_linelosses",
    # Wildfire-only BCRs (new)
    "bcr_excluding_wildfire_risk",
    "bcr_excluding_emissions_and_wildfire_risk",
    "bcr_excluding_linelosses_and_wildfire_risk",
    "bcr_excluding_emissions_and_linelosses_and_wildfire_risk",
    # Outage-only BCRs (new)
    "bcr_excluding_outage_risk",
    "bcr_excluding_emissions_and_outage_risk",
    "bcr_excluding_linelosses_and_outage_risk",
    "bcr_excluding_emissions_and_linelosses_and_outage_risk",
    # Stakeholder perspectives
    "bcr_utility",
    "bcr_ratepayer",
    # 11. Net Benefits PV
    "net_benefit_pv",
    "net_benefit_primary_pv",
    # Combined risk net benefits (renamed)
    "net_benefit_excluding_wildfire_risk_and_outage_risk_pv",
    "net_benefit_excluding_emissions_and_wildfire_risk_and_outage_risk_pv",
    "net_benefit_excluding_linelosses_and_wildfire_risk_and_outage_risk_pv",
    "net_benefit_excluding_emissions_and_linelosses_and_wildfire_risk_and_outage_risk_pv",
    # Emissions/linelosses net benefits (unchanged)
    "net_benefit_excluding_emissions_pv",
    "net_benefit_excluding_linelosses_pv",
    "net_benefit_excluding_emissions_and_linelosses_pv",
    # Wildfire-only net benefits (new)
    "net_benefit_excluding_wildfire_risk_pv",
    "net_benefit_excluding_emissions_and_wildfire_risk_pv",
    "net_benefit_excluding_linelosses_and_wildfire_risk_pv",
    "net_benefit_excluding_emissions_and_linelosses_and_wildfire_risk_pv",
    # Outage-only net benefits (new)
    "net_benefit_excluding_outage_risk_pv",
    "net_benefit_excluding_emissions_and_outage_risk_pv",
    "net_benefit_excluding_linelosses_and_outage_risk_pv",
    "net_benefit_excluding_emissions_and_linelosses_and_outage_risk_pv",
    # Capital and stakeholder net benefits
    "net_benefit_capital_only_pv",
    "net_benefit_capital_and_delay_pv",
    "net_benefit_utility_pv",
    "net_benefit_ratepayer_pv",
]


class CTCCOutputManager:
    """Manages CSV outputs for CTCC batch analysis."""

    def __init__(
        self, output_dir: str = str(OUTPUTS_DIR), scenario_id: Optional[str] = None
    ) -> None:
        """
        Initialize output manager.

        Args:
            output_dir: Base directory for outputs
            scenario_id: Unique scenario identifier (auto-generated if None)
        """
        self.output_dir = output_dir
        # Use environment variable if set (for coordinated batch runs), otherwise generate new one
        # Use microseconds to ensure uniqueness even if runs happen in the same second
        self.scenario_id = (
            scenario_id
            or os.environ.get("CTCC_SCENARIO_ID")
            or datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        )
        self.timestamp = datetime.now().isoformat()

        # Ensure output directory exists
        self.ensure_output_dirs()

        # Load technical details
        technical_details = self.load_technical_details()

        # Storage for batch summary data - technical details first, then scenario info
        self.batch_summary_data = {
            **technical_details,  # Technical parameters come first
            "scenario_id": self.scenario_id,
            "timestamp": self.timestamp,
        }

    def ensure_output_dirs(self) -> None:
        """Create output directory if it doesn't exist."""
        os.makedirs(self.output_dir, exist_ok=True)

    def load_technical_details(self) -> Dict[str, Any]:
        """
        Load technical parameters using centralized loaders to include in CSV outputs.
        Supports both YAML and JSON input modes.

        Returns:
            Dictionary of technical parameters
        """
        try:
            # Load from centralized loaders
            # load_project_technical_details returns:
            # (construction_type, ac_dc, capacity_mw, conductor_type, converter_type,
            #  line_utilization, reconductoring, delay_years, construction_years,
            #  project_lifetime, converter_loss_percentage)
            from yaml_loaders import ProjectTechnicalDetails

            project_details: ProjectTechnicalDetails = load_project_technical_details()

            construction_type = project_details.construction_type
            ac_dc = project_details.ac_dc
            capacity_mw = project_details.capacity_mw
            conductor_type = project_details.conductor_type
            converter_type = project_details.converter_type
            line_utilization = project_details.line_utilization
            reconductoring = project_details.reconductoring
            uses_existing_row = project_details.uses_existing_row
            delay_years = project_details.delay_years
            construction_years = project_details.construction_years
            project_lifetime = project_details.project_lifetime
            _converter_loss_percentage = project_details.converter_loss_percentage

            # Get total line length from centralized loader
            total_line_length = load_physical_details()

            # Get social discount rate from centralized loader
            social_discount_rate = load_financing_social_discount_rate()

            # Get additional fields not in centralized loader return
            project_data = get_project_data_raw()
            project = project_data.get("project", {})

            technical_details = {
                # Project identification
                "project_name": project.get("name", ""),
                # Core technical specs (from centralized loader)
                "construction_type": construction_type,
                "ac_dc": ac_dc,
                "capacity_mw": capacity_mw,
                "conductor_type": conductor_type,
                "line_length_miles": total_line_length,
                "line_utilization": line_utilization,
                # Converter details (for DC projects)
                "converter_type": converter_type,
                "number_of_converters": (
                    project.get("number_of_converters", 0) if ac_dc == "DC" else 0
                ),
                # Reconductoring details
                "reconductoring": reconductoring,
                "old_capacity_mw": (
                    project.get("old_capacity_mw", 0) if reconductoring else 0
                ),
                "old_conductor_type": (
                    project.get("old_conductor_type", "") if reconductoring else ""
                ),
                "old_ac_dc": (project.get("old_ac_dc", "") if reconductoring else ""),
                # Financial parameters
                "baseline_electricity_price_per_mwh": project.get(
                    "baseline_electricity_price_per_mwh", 0
                ),
                "social_discount_rate": social_discount_rate,
                # Timeline (from centralized loader)
                "construction_years": construction_years,
                "delay_years": delay_years,
                "project_lifetime_years": project_lifetime,
            }

            return technical_details

        except Exception as e:
            print(f"Warning: Could not load technical details: {e}")
            return {}

    def append_to_batch_summary(self, data_dict: Dict[str, Any]) -> None:
        """
        Add data to the batch summary dictionary.

        Args:
            data_dict: Dictionary of key-value pairs to add
        """
        self.batch_summary_data.update(data_dict)

    def write_batch_summary(self) -> None:
        """
        Write or update the batch summary to CSV.
        High-level summary with PV values grouped by cost category.
        """
        batch_path = os.path.join(self.output_dir, "batch_summary.csv")
        file_exists = os.path.exists(batch_path)

        # Use shared batch summary schema to keep CSV/JSON aligned
        organized_fieldnames = BATCH_SUMMARY_FIELDS

        # Build summary row with only organized fields (use 0 for missing values)
        summary_row = {}
        for field in organized_fieldnames:
            value = self.batch_summary_data.get(field)
            summary_row[field] = value if value is not None else 0

        # If file exists, read all existing data and merge
        if file_exists:
            with open(batch_path, "r", newline="") as f:
                reader = csv.DictReader(f)
                existing_fields = list(reader.fieldnames)
                existing_rows = list(reader)

            # Check if this scenario_id already exists
            scenario_row_idx = None
            for idx, row in enumerate(existing_rows):
                if row.get("scenario_id") == self.scenario_id:
                    scenario_row_idx = idx
                    break

            # Update existing row or append new one
            if scenario_row_idx is not None:
                # Merge new data into existing row - preserve existing values, only update with new non-zero values
                # This preserves data from previous script runs that may not be in current batch_summary_data
                existing_row = existing_rows[scenario_row_idx]
                for field, value in summary_row.items():
                    # Only update if:
                    # 1. The new value is non-zero (we have real data to add), OR
                    # 2. The field doesn't exist in existing row yet (new field), OR
                    # 3. The existing value is zero/empty (nothing to preserve)
                    existing_value = existing_row.get(field, 0)
                    try:
                        existing_value_float = (
                            float(existing_value) if existing_value else 0
                        )
                    except (ValueError, TypeError):
                        existing_value_float = 0

                    if (
                        value != 0
                        or field not in existing_row
                        or existing_value_float == 0
                    ):
                        existing_row[field] = value
            else:
                # Add as new row
                existing_rows.append(summary_row)

            # Merge fieldnames: existing first, then any new organized fields
            fieldnames = list(existing_fields) + [
                f for f in organized_fieldnames if f not in existing_fields
            ]

            # Write all rows back
            with open(batch_path, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(existing_rows)
        else:
            # First time writing - create new file with organized structure
            with open(batch_path, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=organized_fieldnames)
                writer.writeheader()
                writer.writerow(summary_row)

        # Also write project_details.csv (idempotent - updates if exists)
        self.write_project_details()

        # Also write AFUDC.csv (idempotent - updates if exists)
        self.write_afudc_csv()

        print(f"\n✅ Batch summary updated: {batch_path}")

    def write_project_details(self) -> None:
        """
        Write project_details.csv with all project metadata.
        This file contains all technical parameters that are shared across modules.
        """
        csv_path = os.path.join(self.output_dir, "project_details.csv")

        # Extract all project metadata (excluding calculated values)
        project_detail_keys = [
            "project_name",
            "construction_type",
            "ac_dc",
            "capacity_mw",
            "conductor_type",
            "line_length_miles",
            "line_utilization",
            "converter_type",
            "number_of_converters",
            "reconductoring",
            "old_capacity_mw",
            "old_conductor_type",
            "old_ac_dc",
            "baseline_electricity_price_per_mwh",
            "social_discount_rate",
            "construction_years",
            "delay_years",
            "project_lifetime_years",
            "scenario_id",
            "timestamp",
        ]

        # Build project details dict
        project_details = {
            k: self.batch_summary_data.get(k, "") for k in project_detail_keys
        }

        # Check if file exists
        file_exists = os.path.exists(csv_path)

        if file_exists:
            # Read existing data
            with open(csv_path, "r", newline="") as f:
                reader = csv.DictReader(f)
                existing_fields = list(reader.fieldnames)
                existing_rows = list(reader)

            # Check if this scenario_id already exists
            scenario_row_idx = None
            for idx, row in enumerate(existing_rows):
                if row.get("scenario_id") == self.scenario_id:
                    scenario_row_idx = idx
                    break

            # Update existing row or append new one
            if scenario_row_idx is not None:
                existing_rows[scenario_row_idx].update(project_details)
            else:
                existing_rows.append(project_details)

            # Merge fieldnames
            fieldnames = list(existing_fields) + [
                f for f in project_detail_keys if f not in existing_fields
            ]

            # Write all rows back
            with open(csv_path, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(existing_rows)
        else:
            # First time writing - create new file
            with open(csv_path, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=project_detail_keys)
                writer.writeheader()
                writer.writerow(project_details)

        print(f"  Project details written: {csv_path}")

    def write_afudc_csv(self) -> None:
        """
        Write AFUDC.csv with all AFUDC (regulatory) values.
        This file contains all AFUDC-related cost calculations.
        """
        csv_path = os.path.join(self.output_dir, "AFUDC.csv")

        # Extract all AFUDC-related columns from batch_summary_data
        # Ordered: individual components first, then totals
        afudc_keys = [
            "build_cost_afudc",
            "row_cost_afudc",
            "env_mitigation_afudc",
            "delay_cost_afudc",
            "total_capital_afudc",
        ]

        # Build AFUDC data dict - include project identification
        afudc_data = {
            "project_name": self.batch_summary_data.get("project_name", ""),
            "scenario_id": self.scenario_id,
            "timestamp": self.timestamp,
        }

        # Ensure total capital AFUDC is populated if missing
        total_capital_afudc = self.batch_summary_data.get("total_capital_afudc")
        if total_capital_afudc is None:
            total_capital_afudc = (
                self.batch_summary_data.get("build_cost_afudc", 0)
                + self.batch_summary_data.get("row_cost_afudc", 0)
                + self.batch_summary_data.get("env_mitigation_afudc", 0)
            )
            self.batch_summary_data["total_capital_afudc"] = total_capital_afudc

        # Add all AFUDC values that exist (use 0 if not present, to ensure consistent columns)
        for key in afudc_keys:
            value = self.batch_summary_data.get(key, 0)
            afudc_data[key] = value

        # Define fieldnames in order: identification, then AFUDC values
        all_fields = ["project_name", "scenario_id", "timestamp"] + afudc_keys

        # Check if file exists
        file_exists = os.path.exists(csv_path)

        if file_exists:
            # Read existing data
            with open(csv_path, "r", newline="") as f:
                reader = csv.DictReader(f)
                existing_fields = list(reader.fieldnames)
                existing_rows = list(reader)

            # Check if this scenario_id already exists
            scenario_row_idx = None
            for idx, row in enumerate(existing_rows):
                if row.get("scenario_id") == self.scenario_id:
                    scenario_row_idx = idx
                    break

            # Update existing row or append new one
            if scenario_row_idx is not None:
                # Merge new data into existing row - preserve existing values, only update with new non-zero values
                # This preserves data from previous script runs that may not be in current batch_summary_data
                existing_row = existing_rows[scenario_row_idx]
                for field, value in afudc_data.items():
                    # Only update if:
                    # 1. The new value is non-zero (we have real data to add), OR
                    # 2. The field doesn't exist in existing row yet (new field), OR
                    # 3. The existing value is zero/empty (nothing to preserve)
                    existing_value = existing_row.get(field, 0)
                    try:
                        existing_value_float = (
                            float(existing_value) if existing_value else 0
                        )
                    except (ValueError, TypeError):
                        existing_value_float = 0

                    if (
                        value != 0
                        or field not in existing_row
                        or existing_value_float == 0
                    ):
                        existing_row[field] = value
            else:
                existing_rows.append(afudc_data)

            # Merge fieldnames: existing first, then any new ones
            fieldnames = list(existing_fields) + [
                f for f in all_fields if f not in existing_fields
            ]

            # Write all rows back
            with open(csv_path, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(existing_rows)
        else:
            # First time writing - create new file
            with open(csv_path, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=all_fields)
                writer.writeheader()
                writer.writerow(afudc_data)

        print(f"  AFUDC values written: {csv_path}")

    def write_module_csv(
        self,
        module_name: str,
        detail_rows: Optional[List[Dict[str, Any]]] = None,
        summary_row: Optional[Dict[str, Any]] = None,
        append: bool = True,
    ) -> None:
        """
        Write module-specific CSV with optional detail and summary rows.
        Only includes project_name, scenario_id, and timestamp (not full project metadata).

        Args:
            module_name: Name of the module (e.g., 'wildfire_costs', 'build_costs')
            detail_rows: List of dicts for detail rows (optional)
            summary_row: Dict for summary row (optional)
            append: If True, append to existing file; if False, overwrite
        """
        csv_path = os.path.join(self.output_dir, f"{module_name}.csv")

        # Collect all rows to write
        all_rows = []
        if detail_rows:
            all_rows.extend(detail_rows)
        if summary_row:
            all_rows.append(summary_row)

        if not all_rows:
            return

        # Only include minimal project identification (not full metadata)
        minimal_params = {
            "project_name": self.batch_summary_data.get("project_name", ""),
            "scenario_id": self.scenario_id,
            "timestamp": self.timestamp,
        }

        # Prepend minimal params to each row
        enriched_rows = []
        for row in all_rows:
            enriched_row = {
                **minimal_params,
                **row,
            }  # Minimal params first, then row data
            enriched_rows.append(enriched_row)

        # Determine fieldnames: minimal params first, then the rest
        first_row_other_keys = [
            k for k in all_rows[0].keys() if k not in minimal_params
        ]
        fieldnames = list(minimal_params.keys()) + first_row_other_keys

        # Check if file exists and we're appending
        file_exists = os.path.exists(csv_path) and append

        mode = "a" if append else "w"

        with open(csv_path, mode, newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if not file_exists or not append:
                writer.writeheader()
            writer.writerows(enriched_rows)

        action = "appended to" if append else "written to"
        print(f"  CSV {action}: {csv_path}")

    def add_project_params(
        self,
        construction_type: str,
        ac_dc: str,
        capacity_mw: int,
        conductor_type: str,
        converter_type: str,
        total_miles: float,
        weighted_miles: float,
        terrain_multiplier: float,
        delay_years: float,
        construction_years: int,
        project_lifetime: int,
    ) -> None:
        """Add project parameters to batch summary."""
        self.append_to_batch_summary(
            {
                "construction_type": construction_type,
                "ac_dc": ac_dc,
                "capacity_mw": capacity_mw,
                "conductor_type": conductor_type,
                "converter_type": converter_type,
                "total_miles": total_miles,
                "weighted_miles": weighted_miles,
                "terrain_multiplier": terrain_multiplier,
                "delay_years": delay_years,
                "construction_years": construction_years,
                "project_lifetime": project_lifetime,
            }
        )

    def add_financial_params(
        self,
        wacc_nominal: float,
        wacc_real: float,
        social_discount_rate: float,
        inflation_rate: float,
        afudc_rate: float,
    ) -> None:
        """Add financial parameters to batch summary."""
        self.append_to_batch_summary(
            {
                "wacc_nominal": wacc_nominal,
                "wacc_real": wacc_real,
                "social_discount_rate": social_discount_rate,
                "inflation_rate": inflation_rate,
                "afudc_rate": afudc_rate,
            }
        )

    def add_build_costs(self, results: Dict[str, float]) -> None:
        """Add build cost results to batch summary."""
        self.append_to_batch_summary(
            {
                "build_cost_nominal": results.get("total_nominal", 0),
                "build_cost_afudc": results.get("total_afudc", 0),
                "build_cost_pv": results.get("total_pv", 0),
                "build_conductor_nominal": results.get("conductor_nominal", 0),
                "build_structure_nominal": results.get("structure_nominal", 0),
                "build_converter_nominal": results.get("converter_nominal", 0),
            }
        )

        # Write module CSV - columns ordered: row_type, PV values, nominal values, module-specific
        summary_row = {
            "row_type": "summary",
            "total_pv": results.get("total_pv", 0),
            "total_nominal": results.get("total_nominal", 0),
            "conductor_nominal": results.get("conductor_nominal", 0),
            "structure_nominal": results.get("structure_nominal", 0),
            "converter_nominal": results.get("converter_nominal", 0),
        }
        self.write_module_csv("build_costs", summary_row=summary_row)

    def add_row_costs(self, results: Dict[str, float]) -> None:
        """Add ROW cost results to batch summary."""
        self.append_to_batch_summary(
            {
                "row_cost_nominal": results.get("total_nominal", 0),
                "row_cost_afudc": results.get("total_afudc", 0),
                "row_cost_pv": results.get("total_pv", 0),
                "row_capital_pv": results.get("row_capital_pv", 0),
                "row_rent_pv": results.get("row_rent_pv", 0),
                "row_capital_afudc": results.get("row_capital_afudc", 0),
                "row_capital_nominal": results.get("row_capital_nominal", 0),
                "row_rent_nominal": results.get("row_rent_nominal", 0)
                or results.get("rent_nominal", 0),
                "row_acquisition_nominal": results.get("acquisition_nominal", 0),
                "row_holding_nominal": results.get("holding_nominal", 0),
            }
        )

        # Write module CSV - columns ordered: row_type, PV values, nominal values, module-specific
        summary_row = {
            "row_type": "summary",
            "total_pv": results.get("total_pv", 0),
            "total_nominal": results.get("total_nominal", 0),
            "row_capital_pv": results.get("row_capital_pv", 0),
            "row_rent_pv": results.get("row_rent_pv", 0),
            "acquisition_nominal": results.get("acquisition_nominal", 0),
            "holding_nominal": results.get("holding_nominal", 0),
            "rent_nominal": results.get("rent_nominal", 0),
        }
        self.write_module_csv("row_costs", summary_row=summary_row)

    def add_environmental_mitigation(self, results: Dict[str, float]) -> None:
        """Add environmental mitigation results to batch summary."""
        self.append_to_batch_summary(
            {
                "env_mitigation_nominal": results.get("total_nominal", 0),
                "env_mitigation_afudc": results.get("total_afudc", 0),
                "env_mitigation_pv": results.get("total_pv", 0),
                "env_base_cost": results.get("base_cost_nominal", 0),
                "env_credits_cost": results.get("credits_nominal", 0),
                "env_credits_pv": results.get("credits_pv", 0),
            }
        )

        # Write module CSV - columns ordered: row_type, PV values, nominal values, module-specific
        summary_row = {
            "row_type": "summary",
            "total_pv": results.get("total_pv", 0),
            "credits_pv": results.get("credits_pv", 0),
            "total_nominal": results.get("total_nominal", 0),
            "base_cost_nominal": results.get("base_cost_nominal", 0),
            "credits_nominal": results.get("credits_nominal", 0),
        }
        self.write_module_csv("environmental_mitigation", summary_row=summary_row)

    def add_delay_costs(self, results: Dict[str, float]) -> None:
        """Add delay cost results to batch summary."""
        self.append_to_batch_summary(
            {
                "delay_cost_nominal": results.get("total_nominal", 0),
                "delay_cost_afudc": results.get("total_afudc", 0),
                "delay_cost_pv": results.get("total_pv", 0),
            }
        )

        # Write module CSV - columns ordered: row_type, PV values, nominal values
        summary_row = {
            "row_type": "summary",
            "total_pv": results.get("total_pv", 0),
            "total_nominal": results.get("total_nominal", 0),
        }
        self.write_module_csv("delay_costs", summary_row=summary_row)

    def add_revenue(self, results: Dict[str, float]) -> None:
        """Add revenue calculation results to batch summary."""
        self.append_to_batch_summary(
            {
                "revenue_nominal": results.get("revenue_nominal", 0),
                "revenue_pv": results.get("revenue_pv", 0),
                "annual_revenue": results.get("annual_revenue", 0),
                "rate_base_pv": results.get("rate_base_pv", 0),
                "allowed_return_rate": results.get("allowed_return_rate", 0),
            }
        )

        # Write module CSV - columns ordered: row_type, PV values, annual values, nominal values, module-specific
        summary_row = {
            "row_type": "rate_based",
            "pv_total": results.get("revenue_pv", 0),
            "rate_base_pv": results.get("rate_base_pv", 0),
            "annual_revenue": results.get("annual_revenue", 0),
            "nominal_total": results.get("revenue_nominal", 0),
            "allowed_return_rate": results.get("allowed_return_rate", 0),
        }
        self.write_module_csv("revenue", summary_row=summary_row)

    def add_insurance_costs(self, results: Dict[str, float]) -> None:
        """Add operational insurance cost results to batch summary."""
        self.append_to_batch_summary(
            {
                "insurance_annual": results.get("annual_premium", 0),
                "insurance_nominal": results.get("nominal_lifetime_cost", 0),
                "insurance_pv": results.get("pv_total", 0),
            }
        )

        # Write module CSV - columns ordered: row_type, PV values, annual values, nominal values, module-specific
        summary_row = {
            "row_type": "operational",
            "pv_total": results.get("pv_total", 0),
            "annual_premium": results.get("annual_premium", 0),
            "nominal_total": results.get("nominal_lifetime_cost", 0),
            "insurable_value": results.get("insurable_value", 0),
            "premium_rate": results.get("premium_rate", 0),
        }
        self.write_module_csv("insurance_costs", summary_row=summary_row)

    def add_wildfire_liability_costs(self, results: Dict[str, float]) -> None:
        """Add wildfire liability insurance cost results to batch summary."""
        self.append_to_batch_summary(
            {
                "wildfire_liability_annual": results.get("annual_premium", 0),
                "wildfire_liability_nominal": results.get("nominal_lifetime_cost", 0),
                "wildfire_liability_insurance_pv": results.get("pv_total", 0),
            }
        )

        # Write module CSV - columns ordered: row_type, PV values, annual values, nominal values, module-specific
        summary_row = {
            "row_type": "wildfire_liability",
            "pv_total": results.get("pv_total", 0),
            "annual_premium": results.get("annual_premium", 0),
            "nominal_total": results.get("nominal_lifetime_cost", 0),
            "liability_limit": results.get("liability_limit", 0),
            "rate_on_line": results.get("rate_on_line", 0),
        }
        self.write_module_csv("insurance_costs", summary_row=summary_row)

    def add_wildfire_costs(self, results: Dict[str, Any]) -> None:
        """Add wildfire cost results to batch summary and detail CSV."""
        self.append_to_batch_summary(
            {
                "wildfire_eal": results.get("EAL", 0),
                "wildfire_nominal": results.get("nominal_total", 0),
                "wildfire_pv": results.get("pv_cost", 0),
                "wildfire_events_per_year": results.get("lambda_total", 0),
            }
        )

        # Write detail rows - columns ordered: row_type, PV values, annual values, nominal values, module-specific
        detail_rows = []
        for terrain, data in results.get("lambda_by_terrain", {}).items():
            detail_rows.append(
                {
                    "row_type": "detail",
                    "terrain": terrain,
                    "annual_cost": data["events_per_year"] * results.get("severity", 0),
                    "miles": data["miles"],
                    "base_ignition_rate": data["base_rate"],
                    "construction_multiplier": data["construction_multiplier"],
                    "effective_rate": data["rate_per_mile"],
                    "events_per_year": data["events_per_year"],
                    "severity_per_event": results.get("severity", 0),
                    "growth_rate": results.get("growth_rate", 0),
                    "discount_rate": results.get("discount_rate", 0),
                }
            )

        # Summary row - columns ordered: row_type, PV values, annual values, module-specific
        summary_row = {
            "row_type": "summary",
            "terrain": "all",
            "annual_cost": results.get("EAL", 0),
            "miles": sum(d["miles"] for d in detail_rows),
            "events_per_year": results.get("lambda_total", 0),
            "severity_per_event": results.get("severity", 0),
            "growth_rate": results.get("growth_rate", 0),
            "discount_rate": results.get("discount_rate", 0),
        }

        self.write_module_csv(
            "wildfire_costs", detail_rows=detail_rows, summary_row=summary_row
        )

    def add_outage_costs(self, results: Dict[str, Any]) -> None:
        """Add outage cost results to batch summary and detail CSV."""
        self.append_to_batch_summary(
            {
                "outage_eac": results.get("EAC", 0),
                "outage_nominal": results.get("nominal_total", 0),
                "outage_pv": results.get("pv_cost", 0),
                "outage_events_per_year": results.get("lambda_total", 0),
            }
        )

        # Write detail rows - columns ordered: row_type, annual values, module-specific
        detail_rows = []
        for terrain, data in results.get("outage_by_terrain", {}).items():
            detail_rows.append(
                {
                    "row_type": "detail",
                    "terrain": terrain,
                    "annual_cost": data["annual_cost"],
                    "miles": data["miles"],
                    "outage_rate": data["outage_rate"],
                    "outages_per_year": data["outages_per_year"],
                    "duration_base": data["duration_base"],
                    "duration_multiplier": data["duration_multiplier"],
                    "duration_effective": data["duration_effective"],
                    "unserved_mwh_per_event": data["unserved_mwh_per_event"],
                    "cost_per_event": data["cost_per_event"],
                    "capacity_at_risk": results.get("capacity_at_risk", 1.0),
                }
            )

        # Summary row - columns ordered: row_type, annual values, module-specific
        summary_row = {
            "row_type": "summary",
            "terrain": "all",
            "annual_cost": results.get("EAC", 0),
            "miles": sum(d["miles"] for d in detail_rows),
            "outages_per_year": results.get("lambda_total", 0),
            "capacity_at_risk": results.get("capacity_at_risk", 1.0),
        }

        self.write_module_csv(
            "outage_costs", detail_rows=detail_rows, summary_row=summary_row
        )

    def add_oandm_costs(self, results: Dict[str, float]) -> None:
        """Add O&M cost results to batch summary and detail CSV."""
        self.append_to_batch_summary(
            {
                "oandm_annual": results.get("total_annual", 0),
                "oandm_nominal": results.get("total_nominal", 0),
                "oandm_pv": results.get("total_pv", 0),
            }
        )

        # Write detail rows by component - columns ordered: row_type, PV values, annual values, nominal values, module-specific
        detail_rows = []
        for component in ["conductor", "converter", "structure", "vegetation"]:
            detail_rows.append(
                {
                    "row_type": "detail",
                    "component": component,
                    "pv_total": results.get(f"{component}_pv", 0),
                    "annual_cost": results.get(f"{component}_annual", 0),
                    "nominal_total": results.get(f"{component}_nominal", 0),
                }
            )

        # Summary row - columns ordered: row_type, PV values, annual values, nominal values
        summary_row = {
            "row_type": "summary",
            "component": "all",
            "pv_total": results.get("total_pv", 0),
            "annual_cost": results.get("total_annual", 0),
            "nominal_total": results.get("total_nominal", 0),
        }

        self.write_module_csv(
            "oandm_costs", detail_rows=detail_rows, summary_row=summary_row
        )

    def add_emissions_costs(self, results: Dict[str, float]) -> None:
        """Add emissions cost results to batch summary and detail CSV."""
        self.append_to_batch_summary(
            {
                "emissions_cost_nominal": results.get("total_nominal", 0),
                "emissions_cost_pv": results.get("total_pv", 0),
                "emissions_annual_cost": results.get("annual_cost", 0),
            }
        )

        # Write detail rows by pollutant - columns ordered: row_type, PV values, nominal values, module-specific
        detail_rows = []
        for pollutant in ["co2", "sox", "nox"]:
            detail_rows.append(
                {
                    "row_type": "detail",
                    "pollutant": pollutant,
                    "cost_pv": results.get(f"{pollutant}_cost_pv", 0),
                    "cost_nominal": results.get(f"{pollutant}_cost_nominal", 0),
                    "emissions_kg": results.get(f"{pollutant}_emissions_kg", 0),
                }
            )

        # Summary row - columns ordered: row_type, PV values, nominal values
        summary_row = {
            "row_type": "summary",
            "pollutant": "all",
            "cost_pv": results.get("total_pv", 0),
            "cost_nominal": results.get("total_nominal", 0),
        }

        self.write_module_csv(
            "emissions_costs", detail_rows=detail_rows, summary_row=summary_row
        )

    def add_line_loss_costs(self, results: Dict[str, float]) -> None:
        """Add energy loss cost results to batch summary. Total = conductor + converter for DC. No 'line loss' keys."""
        batch_data = {
            "conductor_loss_pv": results.get("line_cost_pv", 0),
            "converter_loss_pv": results.get("converter_cost_pv", 0),
            "energy_losses_pv": results.get("total_pv", 0),
            "energy_losses_nominal": results.get("total_nominal", 0),
        }
        self.append_to_batch_summary(batch_data)

        # Breakdown present when converter losses are reported (DC with converters)
        has_breakdown = results.get("converter_loss_mwh_yr", 0) != 0

        if has_breakdown:
            detail_rows = [
                {
                    "row_type": "conductor",
                    "loss_mwh_yr": results.get("line_loss_mwh_yr", 0),
                    "annual_cost": results.get("line_annual_cost", 0),
                    "pv_total": results.get("line_cost_pv", 0),
                    "nominal_total": results.get("line_nominal_total", 0),
                },
                {
                    "row_type": "converter",
                    "loss_mwh_yr": results.get("converter_loss_mwh_yr", 0),
                    "annual_cost": results.get("converter_annual_cost", 0),
                    "pv_total": results.get("converter_cost_pv", 0),
                    "nominal_total": results.get("converter_nominal_total", 0),
                },
            ]
            summary_row = {
                "row_type": "total",
                "loss_mwh_yr": results.get("total_loss_mwh_yr", 0),
                "annual_cost": results.get("annual_cost", 0),
                "pv_total": results.get("total_pv", 0),
                "nominal_total": results.get("total_nominal", 0),
            }
            self.write_module_csv(
                "line_loss_costs", detail_rows=detail_rows, summary_row=summary_row
            )
        else:
            summary_row = {
                "row_type": "summary",
                "pv_total": results.get("total_pv", 0),
                "annual_cost": results.get("annual_cost", 0),
                "nominal_total": results.get("total_nominal", 0),
            }
            self.write_module_csv("line_loss_costs", summary_row=summary_row)

    def add_congestion_curtailment(self, results: Dict[str, float]) -> None:
        """
        Add congestion and curtailment benefits and costs to batch summary.

        Benefits (reduce system cost):
        - Congestion reduction benefit (operational, full + haircut)
        - Curtailment reduction benefit (operational, full + haircut)

        Costs (increase system cost):
        - Congestion during delay/construction (opportunity cost)
        - Curtailment during delay/construction (opportunity cost)
        - Residual congestion (unrelieved)
        """
        # Append to batch summary with clear benefit vs cost distinction
        self.append_to_batch_summary(
            {
                # BENEFITS (reduce system cost)
                "congestion_benefit_annual": results.get(
                    "congestion_benefit_annual", 0
                ),
                "congestion_benefit_nominal": results.get(
                    "congestion_benefit_nominal", 0
                ),
                "congestion_benefit_pv": results.get("congestion_benefit_pv", 0),
                "congestion_benefit_haircut_pv": results.get(
                    "congestion_benefit_haircut_pv", 0
                ),
                "curtailment_benefit_annual": results.get(
                    "curtailment_benefit_annual", 0
                ),
                "curtailment_benefit_nominal": results.get(
                    "curtailment_benefit_nominal", 0
                ),
                "curtailment_benefit_pv": results.get("curtailment_benefit_pv", 0),
                "curtailment_benefit_haircut_pv": results.get(
                    "curtailment_benefit_haircut_pv", 0
                ),
                # COSTS (increase system cost)
                "congestion_delay_cost_nominal": results.get(
                    "congestion_delay_cost_nominal", 0
                ),
                "congestion_delay_cost_pv": results.get("congestion_delay_cost_pv", 0),
                "curtailment_delay_cost_nominal": results.get(
                    "curtailment_delay_cost_nominal", 0
                ),
                "curtailment_delay_cost_pv": results.get(
                    "curtailment_delay_cost_pv", 0
                ),
                "residual_exceedance_annual": results.get(
                    "residual_exceedance_annual", 0
                ),
                "residual_exceedance_nominal": results.get(
                    "residual_exceedance_nominal", 0
                ),
                "residual_exceedance_pv": results.get("residual_exceedance_pv", 0),
                "energy_residual_exceedance_mwh_yr": results.get(
                    "energy_residual_exceedance_mwh_yr", 0
                ),
            }
        )

        # Build detail rows distinguishing benefits from costs
        # Columns ordered: row_type, PV values, annual values, nominal values, module-specific
        detail_rows = [
            # BENEFITS - Congestion reduction (full value)
            {
                "row_type": "detail",
                "benefit_or_cost": "benefit",
                "constraint_type": "congestion",
                "value_type": "full",
                "pv": results.get("congestion_benefit_pv", 0),
                "annual": results.get("congestion_benefit_annual", 0),
                "nominal": results.get("congestion_benefit_nominal", 0),
            },
            # BENEFITS - Congestion reduction (haircut/conservative)
            {
                "row_type": "detail",
                "benefit_or_cost": "benefit",
                "constraint_type": "congestion",
                "value_type": "haircut",
                "pv": results.get("congestion_benefit_haircut_pv", 0),
                "annual": results.get("congestion_benefit_haircut_annual", 0),
                "nominal": results.get("congestion_benefit_haircut_nominal", 0),
            },
            # BENEFITS - Curtailment reduction (full value)
            {
                "row_type": "detail",
                "benefit_or_cost": "benefit",
                "constraint_type": "curtailment",
                "value_type": "full",
                "pv": results.get("curtailment_benefit_pv", 0),
                "annual": results.get("curtailment_benefit_annual", 0),
                "nominal": results.get("curtailment_benefit_nominal", 0),
            },
            # BENEFITS - Curtailment reduction (haircut/conservative)
            {
                "row_type": "detail",
                "benefit_or_cost": "benefit",
                "constraint_type": "curtailment",
                "value_type": "haircut",
                "pv": results.get("curtailment_benefit_haircut_pv", 0),
                "annual": results.get("curtailment_benefit_haircut_annual", 0),
                "nominal": results.get("curtailment_benefit_haircut_nominal", 0),
            },
            # COSTS - Congestion during delay/construction (opportunity cost)
            {
                "row_type": "detail",
                "benefit_or_cost": "cost",
                "constraint_type": "congestion_delay",
                "value_type": "NA",
                "pv": results.get("congestion_delay_cost_pv", 0),
                "nominal": results.get("congestion_delay_cost_nominal", 0),
            },
            # COSTS - Curtailment during delay/construction (opportunity cost)
            {
                "row_type": "detail",
                "benefit_or_cost": "cost",
                "constraint_type": "curtailment_delay",
                "value_type": "NA",
                "pv": results.get("curtailment_delay_cost_pv", 0),
                "nominal": results.get("curtailment_delay_cost_nominal", 0),
            },
            # COSTS - Residual unrelieved exceedance
            {
                "row_type": "detail",
                "benefit_or_cost": "cost",
                "constraint_type": "residual_exceedance",
                "value_type": "NA",
                "pv": results.get("residual_exceedance_pv", 0),
                "annual": results.get("residual_exceedance_annual", 0),
                "nominal": results.get("residual_exceedance_nominal", 0),
            },
        ]

        # Calculate summary totals
        total_benefits_annual = results.get(
            "congestion_benefit_annual", 0
        ) + results.get("curtailment_benefit_annual", 0)
        total_benefits_nominal = results.get(
            "congestion_benefit_nominal", 0
        ) + results.get("curtailment_benefit_nominal", 0)
        total_benefits_pv = results.get("congestion_benefit_pv", 0) + results.get(
            "curtailment_benefit_pv", 0
        )

        total_costs_nominal = (
            results.get("congestion_delay_cost_nominal", 0)
            + results.get("curtailment_delay_cost_nominal", 0)
            + results.get("residual_exceedance_nominal", 0)
        )
        total_costs_pv = (
            results.get("congestion_delay_cost_pv", 0)
            + results.get("curtailment_delay_cost_pv", 0)
            + results.get("residual_exceedance_pv", 0)
        )

        # Summary row - columns ordered: row_type, PV values, annual values, nominal values, module-specific
        summary_row = {
            "row_type": "summary",
            "benefit_or_cost": "net",
            "constraint_type": "all",
            "value_type": "summary",
            "pv": total_benefits_pv - total_costs_pv,
            "annual": total_benefits_annual,
            "nominal": total_benefits_nominal - total_costs_nominal,
        }

        self.write_module_csv(
            "congestion_curtailment",
            detail_rows=detail_rows,
            summary_row=summary_row,
        )

    def load_existing_afudc_values(self) -> None:
        """Load existing AFUDC values from AFUDC.csv if they exist."""
        afudc_csv_path = os.path.join(self.output_dir, "AFUDC.csv")
        if os.path.exists(afudc_csv_path):
            try:
                with open(afudc_csv_path, "r", newline="") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        if row.get("scenario_id") == self.scenario_id:
                            # Load AFUDC values from CSV
                            for key in [
                                "build_cost_afudc",
                                "row_cost_afudc",
                                "env_mitigation_afudc",
                                "delay_cost_afudc",
                            ]:
                                value_str = row.get(key, "0")
                                try:
                                    value = float(value_str) if value_str else 0
                                    if (
                                        value != 0
                                    ):  # Only update if non-zero (preserve existing data)
                                        self.batch_summary_data[key] = value
                                except (ValueError, TypeError):
                                    pass
                            break
            except Exception:
                pass  # If file read fails, continue without loading

    def calculate_grand_totals(self) -> None:
        """Calculate grand totals and add to batch summary."""
        # Load existing AFUDC values from CSV if not already in batch_summary_data
        self.load_existing_afudc_values()
        # Capital costs (have AFUDC) - ROW capital only (acquisition + holding), not rent
        capital_nominal = sum(
            [
                self.batch_summary_data.get("build_cost_nominal", 0),
                self.batch_summary_data.get("row_capital_nominal", 0),
                self.batch_summary_data.get("env_mitigation_nominal", 0),
            ]
        )
        capital_afudc = sum(
            [
                self.batch_summary_data.get("build_cost_afudc", 0),
                self.batch_summary_data.get("row_cost_afudc", 0),
                self.batch_summary_data.get("env_mitigation_afudc", 0),
            ]
        )
        capital_pv = sum(
            [
                self.batch_summary_data.get("build_cost_pv", 0),
                self.batch_summary_data.get("row_capital_pv", 0),
                self.batch_summary_data.get("env_mitigation_pv", 0),
            ]
        )

        # Operational costs (no AFUDC) - O&M, insurance, ROW rent, congestion/curtailment constraint costs
        operational_nominal = sum(
            [
                self.batch_summary_data.get("insurance_nominal", 0),
                self.batch_summary_data.get("oandm_nominal", 0),
                self.batch_summary_data.get("row_rent_nominal", 0),
                self.batch_summary_data.get("congestion_cost_nominal", 0),
                self.batch_summary_data.get("curtailment_cost_nominal", 0),
            ]
        )
        operational_pv = sum(
            [
                self.batch_summary_data.get("insurance_pv", 0),
                self.batch_summary_data.get("oandm_pv", 0),
                self.batch_summary_data.get("row_rent_pv", 0),
                self.batch_summary_data.get("congestion_cost_pv", 0),
                self.batch_summary_data.get("curtailment_cost_pv", 0),
            ]
        )

        # Risk costs (no AFUDC)
        risk_nominal = sum(
            [
                self.batch_summary_data.get("wildfire_nominal", 0),
                self.batch_summary_data.get("wildfire_liability_nominal", 0),
                self.batch_summary_data.get("outage_nominal", 0),
            ]
        )
        risk_pv = sum(
            [
                self.batch_summary_data.get("wildfire_pv", 0),
                self.batch_summary_data.get("wildfire_liability_insurance_pv", 0),
                self.batch_summary_data.get("outage_pv", 0),
            ]
        )

        # Other costs
        emissions_nominal = self.batch_summary_data.get("emissions_cost_nominal", 0)
        emissions_pv = self.batch_summary_data.get("emissions_cost_pv", 0)
        energy_losses_nominal = self.batch_summary_data.get(
            "energy_losses_nominal", 0
        ) or self.batch_summary_data.get("line_loss_cost_nominal", 0)
        energy_losses_pv = self.batch_summary_data.get(
            "energy_losses_pv", 0
        ) or self.batch_summary_data.get("line_loss_cost_pv", 0)

        # Delay costs
        delay_nominal = self.batch_summary_data.get("delay_cost_nominal", 0)
        delay_afudc = self.batch_summary_data.get("delay_cost_afudc", 0)
        delay_pv = self.batch_summary_data.get("delay_cost_pv", 0)

        # Grand totals
        grand_total_nominal = (
            capital_nominal
            + operational_nominal
            + risk_nominal
            + delay_nominal
            + emissions_nominal
            + energy_losses_nominal
        )
        grand_total_afudc = (
            capital_afudc
            + operational_nominal
            + risk_nominal
            + delay_afudc
            + emissions_nominal
            + energy_losses_nominal
        )
        grand_total_pv = (
            capital_pv
            + operational_pv
            + risk_pv
            + delay_pv
            + emissions_pv
            + energy_losses_pv
        )

        totals_dict = {
            "total_capital_nominal": capital_nominal,
            "total_capital_afudc": capital_afudc,
            "total_capital_pv": capital_pv,
            "total_operational_nominal": operational_nominal,
            "total_operational_pv": operational_pv,
            "total_risk_nominal": risk_nominal,
            "total_risk_pv": risk_pv,
            "grand_total_cost_nominal": grand_total_nominal,
            "grand_total_cost_afudc": grand_total_afudc,
            "grand_total_cost_pv": grand_total_pv,
        }
        self.append_to_batch_summary(totals_dict)

    def add_bcr_metrics(self, bcr_results: Dict[str, float]) -> None:
        """
        Add benefit-cost ratio metrics to batch summary.

        Args:
            bcr_results: Dictionary containing BCR metrics from bcr_calculator
                Expected keys include:
                - total_benefits_pv
                - total_benefits_haircut_pv
                - total_costs_pv
                - capital_costs_pv
                - bcr_system (uses conservative/haircut benefits)
                - bcr_capital (uses conservative/haircut benefits)
                - bcr_capital_and_delay (uses conservative/haircut benefits)
                - bcr_excluding_wildfire_risk_and_outage_risk (renamed from bcr_excluding_risk)
                - bcr_excluding_wildfire_risk (new: excludes wildfire + liability only)
                - bcr_excluding_outage_risk (new: excludes outage only)
                - bcr_excluding_emissions (uses conservative/haircut benefits)
                - bcr_excluding_linelosses (uses conservative/haircut benefits)
                - bcr_excluding_emissions_and_linelosses (uses conservative/haircut benefits)
                - bcr_excluding_emissions_and_wildfire_risk_and_outage_risk (renamed)
                - bcr_excluding_linelosses_and_wildfire_risk_and_outage_risk (renamed)
                - bcr_excluding_emissions_and_linelosses_and_wildfire_risk_and_outage_risk (renamed)
                - Plus all combinations with emissions/linelosses for wildfire-only and outage-only
                - bcr_utility, bcr_ratepayer
                - net_benefit_pv and all net benefit variants (matching BCR naming)
        """
        self.append_to_batch_summary(bcr_results)
