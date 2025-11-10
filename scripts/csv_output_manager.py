# Author: Andrew Igdal
# Date: 2025-10-29
# Description: CSV output manager for CTCC batch analysis, sensitivity studies, and Monte Carlo simulations.

import csv
import os
import yaml
from datetime import datetime


class CTCCOutputManager:
    """Manages CSV outputs for CTCC batch analysis."""

    def __init__(self, output_dir="../outputs", scenario_id=None):
        """
        Initialize output manager.

        Args:
            output_dir: Base directory for outputs
            scenario_id: Unique scenario identifier (auto-generated if None)
        """
        self.output_dir = output_dir
        # Use environment variable if set (for coordinated batch runs), otherwise generate new one
        self.scenario_id = scenario_id or os.environ.get('CTCC_SCENARIO_ID') or datetime.now().strftime("%Y%m%d_%H%M%S")
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

    def ensure_output_dirs(self):
        """Create output directory if it doesn't exist."""
        os.makedirs(self.output_dir, exist_ok=True)

    def load_technical_details(self):
        """
        Load technical parameters from YAML files to include in CSV outputs.

        Returns:
            Dictionary of technical parameters
        """
        try:
            # Get the scripts directory and yaml directory using absolute paths
            script_dir = os.path.dirname(os.path.abspath(__file__))
            yaml_dir = os.path.join(script_dir, "..", "yamls")

            # Load project technical details
            tech_file = os.path.join(yaml_dir, "01_project_technical_details.yaml")
            with open(tech_file, "r") as file:
                tech_data = yaml.load(file, Loader=yaml.FullLoader)

            # Load physical details for total line length
            physical_file = os.path.join(yaml_dir, "02_project_physical_details.yaml")
            with open(physical_file, "r") as file:
                physical_data = yaml.load(file, Loader=yaml.FullLoader)
            
            # Calculate total line length
            terrain_miles = physical_data.get("terrain", {}).get("terrain_miles", {})
            total_line_length = sum(terrain_miles.values())
            
            # Extract key technical parameters
            project = tech_data.get("project", {})
            timeline = tech_data.get("timeline", {})
            
            technical_details = {
                # Project identification
                "project_name": project.get("name", ""),
                
                # Core technical specs
                "construction_type": project.get("construction_type", ""),
                "ac_dc": project.get("ac_dc", ""),
                "capacity_mw": project.get("capacity_mw", 0),
                "conductor_type": project.get("conductor_type", ""),
                "line_length_miles": total_line_length,
                "line_utilization": project.get("line_utilization", 0),
                
                # Converter details (for DC projects)
                "converter_type": project.get("converter_type", "NA"),
                "number_of_converters": project.get("number_of_converters", 0) if project.get("ac_dc") == "DC" else 0,
                
                # Reconductoring details
                "reconductoring": project.get("reconductoring", False),
                "old_capacity_mw": project.get("old_capacity_mw", 0) if project.get("reconductoring") else 0,
                "old_conductor_type": project.get("old_conductor_type", "") if project.get("reconductoring") else "",
                "old_ac_dc": project.get("old_ac_dc", "") if project.get("reconductoring") else "",
                
                # Financial parameters
                "baseline_electricity_price_per_mwh": project.get("baseline_electricity_price_per_mwh", 0),
                "social_discount_rate": project.get("social_discount_rate", 0),
                
                # Timeline
                "construction_years": timeline.get("construction_years", 0),
                "delay_years": timeline.get("delay_years", 0),
                "project_lifetime_years": timeline.get("project_lifetime", 0),
            }
            
            return technical_details
            
        except Exception as e:
            print(f"Warning: Could not load technical details: {e}")
            return {}

    def append_to_batch_summary(self, data_dict):
        """
        Add data to the batch summary dictionary.

        Args:
            data_dict: Dictionary of key-value pairs to add
        """
        self.batch_summary_data.update(data_dict)

    def write_batch_summary(self):
        """Write or update the batch summary to CSV."""
        batch_path = os.path.join(self.output_dir, "batch_summary.csv")
        file_exists = os.path.exists(batch_path)

        # Get all keys in a consistent order
        fieldnames = list(self.batch_summary_data.keys())

        # If file exists, read all existing data and merge
        if file_exists:
            with open(batch_path, "r", newline="") as f:
                reader = csv.DictReader(f)
                existing_fields = reader.fieldnames
                # Merge: existing fields first, then any new ones
                fieldnames = list(existing_fields) + [
                    f for f in fieldnames if f not in existing_fields
                ]
                
                # Read all existing rows
                existing_rows = list(reader)
            
            # Check if this scenario_id already exists
            scenario_row_idx = None
            for idx, row in enumerate(existing_rows):
                if row.get('scenario_id') == self.scenario_id:
                    scenario_row_idx = idx
                    break
            
            # Update existing row or append new one
            if scenario_row_idx is not None:
                # Merge new data into existing row
                existing_rows[scenario_row_idx].update(self.batch_summary_data)
            else:
                # Add as new row
                existing_rows.append(self.batch_summary_data)
            
            # Write all rows back
            with open(batch_path, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(existing_rows)
        else:
            # First time writing - create new file
            with open(batch_path, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerow(self.batch_summary_data)

        print(f"\n✅ Batch summary updated: {batch_path}")

    def write_module_csv(
        self, module_name, detail_rows=None, summary_row=None, append=True
    ):
        """
        Write module-specific CSV with optional detail and summary rows.
        Technical parameters are automatically added to each row.

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

        # Extract technical parameters to prepend to each row
        tech_param_keys = [
            'project_name', 'construction_type', 'ac_dc', 'capacity_mw', 
            'conductor_type', 'line_length_miles', 'line_utilization',
            'converter_type', 'number_of_converters', 'reconductoring',
            'old_capacity_mw', 'old_conductor_type', 'old_ac_dc',
            'baseline_electricity_price_per_mwh', 'social_discount_rate',
            'construction_years', 'delay_years', 'project_lifetime_years'
        ]
        
        # Build technical params dict from batch_summary_data
        tech_params = {k: self.batch_summary_data.get(k, '') for k in tech_param_keys}
        
        # Add scenario_id and timestamp
        tech_params['scenario_id'] = self.scenario_id
        tech_params['timestamp'] = self.timestamp
        
        # Prepend technical parameters to each row
        enriched_rows = []
        for row in all_rows:
            enriched_row = {**tech_params, **row}  # Tech params first, then row data
            enriched_rows.append(enriched_row)

        # Determine fieldnames: tech params first, then the rest
        first_row_other_keys = [k for k in all_rows[0].keys() if k not in tech_params]
        fieldnames = list(tech_params.keys()) + first_row_other_keys

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
        construction_type,
        ac_dc,
        capacity_mw,
        conductor_type,
        converter_type,
        total_miles,
        weighted_miles,
        terrain_multiplier,
        delay_years,
        construction_years,
        project_lifetime,
    ):
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
        self, wacc_nominal, wacc_real, social_discount_rate, inflation_rate, afudc_rate
    ):
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

    def add_build_costs(self, results):
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

        # Write module CSV (summary only)
        summary_row = {
            "scenario_id": self.scenario_id,
            "row_type": "summary",
            "total_nominal": results.get("total_nominal", 0),
            "total_afudc": results.get("total_afudc", 0),
            "total_pv": results.get("total_pv", 0),
            "conductor_nominal": results.get("conductor_nominal", 0),
            "structure_nominal": results.get("structure_nominal", 0),
            "converter_nominal": results.get("converter_nominal", 0),
            "conductor_afudc": results.get("conductor_afudc", 0),
            "structure_afudc": results.get("structure_afudc", 0),
            "converter_afudc": results.get("converter_afudc", 0),
        }
        self.write_module_csv("build_costs", summary_row=summary_row)

    def add_row_costs(self, results):
        """Add ROW cost results to batch summary."""
        self.append_to_batch_summary(
            {
                "row_cost_nominal": results.get("total_nominal", 0),
                "row_cost_afudc": results.get("total_afudc", 0),
                "row_cost_pv": results.get("total_pv", 0),
                "row_acquisition_nominal": results.get("acquisition_nominal", 0),
                "row_holding_nominal": results.get("holding_nominal", 0),
                "row_rent_nominal": results.get("rent_nominal", 0),
            }
        )

        # Write module CSV
        summary_row = {
            "scenario_id": self.scenario_id,
            "row_type": "summary",
            "total_nominal": results.get("total_nominal", 0),
            "total_afudc": results.get("total_afudc", 0),
            "total_pv": results.get("total_pv", 0),
            "acquisition_nominal": results.get("acquisition_nominal", 0),
            "holding_nominal": results.get("holding_nominal", 0),
            "rent_nominal": results.get("rent_nominal", 0),
        }
        self.write_module_csv("row_costs", summary_row=summary_row)

    def add_environmental_mitigation(self, results):
        """Add environmental mitigation results to batch summary."""
        self.append_to_batch_summary(
            {
                "env_mitigation_nominal": results.get("total_nominal", 0),
                "env_mitigation_afudc": results.get("total_afudc", 0),
                "env_mitigation_pv": results.get("total_pv", 0),
                "env_base_cost": results.get("base_cost_nominal", 0),
                "env_credits_cost": results.get("credits_nominal", 0),
            }
        )

        # Write module CSV
        summary_row = {
            "scenario_id": self.scenario_id,
            "row_type": "summary",
            "total_nominal": results.get("total_nominal", 0),
            "total_afudc": results.get("total_afudc", 0),
            "total_pv": results.get("total_pv", 0),
            "base_cost_nominal": results.get("base_cost_nominal", 0),
            "credits_nominal": results.get("credits_nominal", 0),
        }
        self.write_module_csv("environmental_mitigation", summary_row=summary_row)

    def add_delay_costs(self, results):
        """Add delay cost results to batch summary."""
        self.append_to_batch_summary(
            {
                "delay_cost_nominal": results.get("total_nominal", 0),
                "delay_cost_afudc": results.get("total_afudc", 0),
                "delay_cost_pv": results.get("total_pv", 0),
            }
        )

        # Write module CSV
        summary_row = {
            "scenario_id": self.scenario_id,
            "row_type": "summary",
            "total_nominal": results.get("total_nominal", 0),
            "total_afudc": results.get("total_afudc", 0),
            "total_pv": results.get("total_pv", 0),
        }
        self.write_module_csv("delay_costs", summary_row=summary_row)

    def add_insurance_costs(self, results):
        """Add insurance cost results to batch summary."""
        self.append_to_batch_summary(
            {
                "insurance_annual": results.get("annual_premium", 0),
                "insurance_nominal": results.get("nominal_lifetime_cost", 0),
                "insurance_pv": results.get("pv_total", 0),
            }
        )

        # Write module CSV
        summary_row = {
            "scenario_id": self.scenario_id,
            "row_type": "summary",
            "annual_premium": results.get("annual_premium", 0),
            "nominal_total": results.get("nominal_lifetime_cost", 0),
            "pv_total": results.get("pv_total", 0),
            "insurable_value": results.get("insurable_value", 0),
            "premium_rate": results.get("premium_rate", 0),
        }
        self.write_module_csv("insurance_costs", summary_row=summary_row)

    def add_wildfire_costs(self, results):
        """Add wildfire cost results to batch summary and detail CSV."""
        self.append_to_batch_summary(
            {
                "wildfire_eal": results.get("EAL", 0),
                "wildfire_nominal": results.get("nominal_total", 0),
                "wildfire_pv": results.get("pv_cost", 0),
                "wildfire_events_per_year": results.get("lambda_total", 0),
            }
        )

        # Write detail rows
        detail_rows = []
        for terrain, data in results.get("lambda_by_terrain", {}).items():
            detail_rows.append(
                {
                    "scenario_id": self.scenario_id,
                    "row_type": "detail",
                    "terrain": terrain,
                    "miles": data["miles"],
                    "base_ignition_rate": data["base_rate"],
                    "construction_multiplier": data["construction_multiplier"],
                    "effective_rate": data["rate_per_mile"],
                    "events_per_year": data["events_per_year"],
                    "severity_per_event": results.get("severity", 0),
                    "annual_cost": data["events_per_year"] * results.get("severity", 0),
                    "growth_rate": results.get("growth_rate", 0),
                    "discount_rate": results.get("discount_rate", 0),
                }
            )

        # Summary row
        summary_row = {
            "scenario_id": self.scenario_id,
            "row_type": "summary",
            "terrain": "all",
            "miles": sum(d["miles"] for d in detail_rows),
            "base_ignition_rate": None,
            "construction_multiplier": None,
            "effective_rate": None,
            "events_per_year": results.get("lambda_total", 0),
            "severity_per_event": results.get("severity", 0),
            "annual_cost": results.get("EAL", 0),
            "growth_rate": results.get("growth_rate", 0),
            "discount_rate": results.get("discount_rate", 0),
        }

        self.write_module_csv(
            "wildfire_costs", detail_rows=detail_rows, summary_row=summary_row
        )

    def add_outage_costs(self, results):
        """Add outage cost results to batch summary and detail CSV."""
        self.append_to_batch_summary(
            {
                "outage_eac": results.get("EAC", 0),
                "outage_nominal": results.get("nominal_total", 0),
                "outage_pv": results.get("pv_cost", 0),
                "outage_events_per_year": results.get("lambda_total", 0),
            }
        )

        # Write detail rows
        detail_rows = []
        for terrain, data in results.get("outage_by_terrain", {}).items():
            detail_rows.append(
                {
                    "scenario_id": self.scenario_id,
                    "row_type": "detail",
                    "terrain": terrain,
                    "miles": data["miles"],
                    "outage_rate": data["outage_rate"],
                    "outages_per_year": data["outages_per_year"],
                    "duration_base": data["duration_base"],
                    "duration_multiplier": data["duration_multiplier"],
                    "duration_effective": data["duration_effective"],
                    "unserved_mwh_per_event": data["unserved_mwh_per_event"],
                    "cost_per_event": data["cost_per_event"],
                    "annual_cost": data["annual_cost"],
                    "capacity_at_risk": results.get("capacity_at_risk", 1.0),
                }
            )

        # Summary row
        summary_row = {
            "scenario_id": self.scenario_id,
            "row_type": "summary",
            "terrain": "all",
            "miles": sum(d["miles"] for d in detail_rows),
            "outage_rate": None,
            "outages_per_year": results.get("lambda_total", 0),
            "duration_base": None,
            "duration_multiplier": None,
            "duration_effective": None,
            "unserved_mwh_per_event": None,
            "cost_per_event": None,
            "annual_cost": results.get("EAC", 0),
            "capacity_at_risk": results.get("capacity_at_risk", 1.0),
        }

        self.write_module_csv(
            "outage_costs", detail_rows=detail_rows, summary_row=summary_row
        )

    def add_oandm_costs(self, results):
        """Add O&M cost results to batch summary and detail CSV."""
        self.append_to_batch_summary(
            {
                "oandm_annual": results.get("total_annual", 0),
                "oandm_nominal": results.get("total_nominal", 0),
                "oandm_pv": results.get("total_pv", 0),
            }
        )

        # Write detail rows by component
        detail_rows = []
        for component in ["conductor", "converter", "structure", "vegetation"]:
            detail_rows.append(
                {
                    "scenario_id": self.scenario_id,
                    "row_type": "detail",
                    "component": component,
                    "annual_cost": results.get(f"{component}_annual", 0),
                    "nominal_total": results.get(f"{component}_nominal", 0),
                    "pv_total": results.get(f"{component}_pv", 0),
                }
            )

        # Summary row
        summary_row = {
            "scenario_id": self.scenario_id,
            "row_type": "summary",
            "component": "all",
            "annual_cost": results.get("total_annual", 0),
            "nominal_total": results.get("total_nominal", 0),
            "pv_total": results.get("total_pv", 0),
        }

        self.write_module_csv(
            "oandm_costs", detail_rows=detail_rows, summary_row=summary_row
        )

    def add_emissions_costs(self, results):
        """Add emissions cost results to batch summary and detail CSV."""
        self.append_to_batch_summary(
            {
                "emissions_cost_nominal": results.get("total_nominal", 0),
                "emissions_cost_pv": results.get("total_pv", 0),
                "emissions_annual_cost": results.get("annual_cost", 0),
            }
        )

        # Write detail rows by pollutant
        detail_rows = []
        for pollutant in ["co2", "sox", "nox"]:
            detail_rows.append(
                {
                    "scenario_id": self.scenario_id,
                    "row_type": "detail",
                    "pollutant": pollutant,
                    "emissions_kg": results.get(f"{pollutant}_emissions_kg", 0),
                    "cost_nominal": results.get(f"{pollutant}_cost_nominal", 0),
                    "cost_pv": results.get(f"{pollutant}_cost_pv", 0),
                }
            )

        # Summary row
        summary_row = {
            "scenario_id": self.scenario_id,
            "row_type": "summary",
            "pollutant": "all",
            "emissions_kg": None,
            "cost_nominal": results.get("total_nominal", 0),
            "cost_pv": results.get("total_pv", 0),
        }

        self.write_module_csv(
            "emissions_costs", detail_rows=detail_rows, summary_row=summary_row
        )

    def add_line_loss_costs(self, results):
        """Add line loss cost results to batch summary."""
        self.append_to_batch_summary(
            {
                "line_loss_cost_nominal": results.get("total_nominal", 0),
                "line_loss_cost_pv": results.get("total_pv", 0),
                "line_loss_annual_cost": results.get("annual_cost", 0),
            }
        )

        # Write module CSV
        summary_row = {
            "scenario_id": self.scenario_id,
            "row_type": "summary",
            "annual_cost": results.get("annual_cost", 0),
            "nominal_total": results.get("total_nominal", 0),
            "pv_total": results.get("total_pv", 0),
        }
        self.write_module_csv("line_loss_costs", summary_row=summary_row)

    def add_congestion_curtailment(self, results):
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
                "congestion_benefit_annual": results.get("congestion_benefit_annual", 0),
                "congestion_benefit_nominal": results.get("congestion_benefit_nominal", 0),
                "congestion_benefit_pv": results.get("congestion_benefit_pv", 0),
                "congestion_benefit_haircut_pv": results.get("congestion_benefit_haircut_pv", 0),
                "curtailment_benefit_annual": results.get("curtailment_benefit_annual", 0),
                "curtailment_benefit_nominal": results.get("curtailment_benefit_nominal", 0),
                "curtailment_benefit_pv": results.get("curtailment_benefit_pv", 0),
                "curtailment_benefit_haircut_pv": results.get("curtailment_benefit_haircut_pv", 0),
                # COSTS (increase system cost)
                "congestion_delay_cost_nominal": results.get("congestion_delay_cost_nominal", 0),
                "congestion_delay_cost_pv": results.get("congestion_delay_cost_pv", 0),
                "curtailment_delay_cost_nominal": results.get("curtailment_delay_cost_nominal", 0),
                "curtailment_delay_cost_pv": results.get("curtailment_delay_cost_pv", 0),
                "residual_congestion_annual": results.get("residual_congestion_annual", 0),
                "residual_congestion_nominal": results.get("residual_congestion_nominal", 0),
                "residual_congestion_pv": results.get("residual_congestion_pv", 0),
            }
        )

        # Build detail rows distinguishing benefits from costs
        detail_rows = [
            # BENEFITS - Congestion reduction (full value)
            {
                "scenario_id": self.scenario_id,
                "row_type": "detail",
                "benefit_or_cost": "benefit",
                "constraint_type": "congestion",
                "value_type": "full",
                "annual": results.get("congestion_benefit_annual", 0),
                "nominal": results.get("congestion_benefit_nominal", 0),
                "pv": results.get("congestion_benefit_pv", 0),
            },
            # BENEFITS - Congestion reduction (haircut/conservative)
            {
                "scenario_id": self.scenario_id,
                "row_type": "detail",
                "benefit_or_cost": "benefit",
                "constraint_type": "congestion",
                "value_type": "haircut",
                "annual": results.get("congestion_benefit_haircut_annual", 0),
                "nominal": results.get("congestion_benefit_haircut_nominal", 0),
                "pv": results.get("congestion_benefit_haircut_pv", 0),
            },
            # BENEFITS - Curtailment reduction (full value)
            {
                "scenario_id": self.scenario_id,
                "row_type": "detail",
                "benefit_or_cost": "benefit",
                "constraint_type": "curtailment",
                "value_type": "full",
                "annual": results.get("curtailment_benefit_annual", 0),
                "nominal": results.get("curtailment_benefit_nominal", 0),
                "pv": results.get("curtailment_benefit_pv", 0),
            },
            # BENEFITS - Curtailment reduction (haircut/conservative)
            {
                "scenario_id": self.scenario_id,
                "row_type": "detail",
                "benefit_or_cost": "benefit",
                "constraint_type": "curtailment",
                "value_type": "haircut",
                "annual": results.get("curtailment_benefit_haircut_annual", 0),
                "nominal": results.get("curtailment_benefit_haircut_nominal", 0),
                "pv": results.get("curtailment_benefit_haircut_pv", 0),
            },
            # COSTS - Congestion during delay/construction (opportunity cost)
            {
                "scenario_id": self.scenario_id,
                "row_type": "detail",
                "benefit_or_cost": "cost",
                "constraint_type": "congestion_delay",
                "value_type": "NA",
                "annual": None,
                "nominal": results.get("congestion_delay_cost_nominal", 0),
                "pv": results.get("congestion_delay_cost_pv", 0),
            },
            # COSTS - Curtailment during delay/construction (opportunity cost)
            {
                "scenario_id": self.scenario_id,
                "row_type": "detail",
                "benefit_or_cost": "cost",
                "constraint_type": "curtailment_delay",
                "value_type": "NA",
                "annual": None,
                "nominal": results.get("curtailment_delay_cost_nominal", 0),
                "pv": results.get("curtailment_delay_cost_pv", 0),
            },
            # COSTS - Residual unrelieved congestion
            {
                "scenario_id": self.scenario_id,
                "row_type": "detail",
                "benefit_or_cost": "cost",
                "constraint_type": "residual_congestion",
                "value_type": "NA",
                "annual": results.get("residual_congestion_annual", 0),
                "nominal": results.get("residual_congestion_nominal", 0),
                "pv": results.get("residual_congestion_pv", 0),
            },
        ]

        # Calculate summary totals
        total_benefits_annual = (
            results.get("congestion_benefit_annual", 0)
            + results.get("curtailment_benefit_annual", 0)
        )
        total_benefits_nominal = (
            results.get("congestion_benefit_nominal", 0)
            + results.get("curtailment_benefit_nominal", 0)
        )
        total_benefits_pv = (
            results.get("congestion_benefit_pv", 0)
            + results.get("curtailment_benefit_pv", 0)
        )
        
        total_costs_nominal = (
            results.get("congestion_delay_cost_nominal", 0)
            + results.get("curtailment_delay_cost_nominal", 0)
            + results.get("residual_congestion_nominal", 0)
        )
        total_costs_pv = (
            results.get("congestion_delay_cost_pv", 0)
            + results.get("curtailment_delay_cost_pv", 0)
            + results.get("residual_congestion_pv", 0)
        )

        summary_row = {
            "scenario_id": self.scenario_id,
            "row_type": "summary",
            "benefit_or_cost": "net",
            "constraint_type": "all",
            "value_type": "summary",
            "annual": total_benefits_annual,
            "nominal": total_benefits_nominal - total_costs_nominal,
            "pv": total_benefits_pv - total_costs_pv,
        }

        self.write_module_csv(
            "congestion_curtailment",
            detail_rows=detail_rows,
            summary_row=summary_row,
        )

    def calculate_grand_totals(self):
        """Calculate grand totals and add to batch summary."""
        # Capital costs (have AFUDC)
        capital_nominal = sum(
            [
                self.batch_summary_data.get("build_cost_nominal", 0),
                self.batch_summary_data.get("row_cost_nominal", 0),
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
                self.batch_summary_data.get("row_cost_pv", 0),
                self.batch_summary_data.get("env_mitigation_pv", 0),
            ]
        )

        # Operational costs (no AFUDC) - includes congestion/curtailment constraint costs
        operational_nominal = sum(
            [
                self.batch_summary_data.get("insurance_nominal", 0),
                self.batch_summary_data.get("oandm_nominal", 0),
                self.batch_summary_data.get("congestion_cost_nominal", 0),
                self.batch_summary_data.get("curtailment_cost_nominal", 0),
            ]
        )
        operational_pv = sum(
            [
                self.batch_summary_data.get("insurance_pv", 0),
                self.batch_summary_data.get("oandm_pv", 0),
                self.batch_summary_data.get("congestion_cost_pv", 0),
                self.batch_summary_data.get("curtailment_cost_pv", 0),
            ]
        )

        # Risk costs (no AFUDC)
        risk_nominal = sum(
            [
                self.batch_summary_data.get("wildfire_nominal", 0),
                self.batch_summary_data.get("outage_nominal", 0),
            ]
        )
        risk_pv = sum(
            [
                self.batch_summary_data.get("wildfire_pv", 0),
                self.batch_summary_data.get("outage_pv", 0),
            ]
        )

        # Other costs
        emissions_nominal = self.batch_summary_data.get("emissions_cost_nominal", 0)
        emissions_pv = self.batch_summary_data.get("emissions_cost_pv", 0)
        line_loss_nominal = self.batch_summary_data.get("line_loss_cost_nominal", 0)
        line_loss_pv = self.batch_summary_data.get("line_loss_cost_pv", 0)

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
            + line_loss_nominal
        )
        grand_total_afudc = (
            capital_afudc
            + operational_nominal
            + risk_nominal
            + delay_afudc
            + emissions_nominal
            + line_loss_nominal
        )
        grand_total_pv = (
            capital_pv
            + operational_pv
            + risk_pv
            + delay_pv
            + emissions_pv
            + line_loss_pv
        )

        self.append_to_batch_summary(
            {
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
        )

    def add_bcr_metrics(self, bcr_results):
        """
        Add benefit-cost ratio metrics to batch summary.
        
        Args:
            bcr_results: Dictionary containing BCR metrics from bcr_calculator
                Expected keys:
                - total_benefits_pv
                - total_benefits_haircut_pv
                - total_costs_pv
                - capital_costs_pv
                - bcr_system
                - bcr_capital
                - bcr_haircut
                - net_benefit_pv
        """
        self.append_to_batch_summary(bcr_results)
