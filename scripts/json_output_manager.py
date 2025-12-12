# Author: Claude Code
# Date: 2025-11-10
# Description: JSON output manager for CTCC API calculations.
#              Parallel implementation to csv_output_manager.py that collects results in memory as JSON.

from datetime import datetime
from typing import Dict, Any, Optional
import json_loaders
import json
import os


class JSONOutputManager:
    """
    Manages JSON outputs for CTCC API calculations.
    Collects all calculation results in memory and provides structured JSON output.
    """

    def __init__(self, scenario_id: Optional[str] = None):
        """
        Initialize JSON output manager.

        Args:
            scenario_id: Unique scenario identifier (auto-generated if None)
        """
        self.scenario_id = scenario_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        self.timestamp = datetime.now().isoformat()

        # Load technical details from JSON data source
        self.technical_details = self.load_technical_details()

        # Storage for all calculation results
        self.costs = {}
        self.benefits = {}
        self.summary = {}
        self.bcr = {}

    def load_technical_details(self) -> Dict[str, Any]:
        """
        Load technical parameters from JSON data source.

        Returns:
            Dictionary of technical parameters
        """
        try:
            # Use json_loaders to get data
            (construction_type, ac_dc, capacity_mw, conductor_type, converter_type,
             line_utilization, reconductoring, delay_years, construction_years,
             project_lifetime) = json_loaders.load_project_technical_details()

            total_line_length = json_loaders.load_physical_details()

            # Get additional details for reconductoring
            tech_data = json_loaders._data_source.get_data("01_project_technical_details")
            project = tech_data.get("project", {})

            # Get financial parameters
            financing_data = json_loaders._data_source.get_data("03_financing")

            technical_details = {
                # Project identification
                "project_name": project.get("name", ""),

                # Core technical specs
                "construction_type": construction_type,
                "ac_dc": ac_dc,
                "capacity_mw": capacity_mw,
                "conductor_type": conductor_type,
                "line_length_miles": total_line_length,
                "line_utilization": line_utilization,

                # Converter details (for DC projects)
                "converter_type": converter_type,
                "number_of_converters": project.get("number_of_converters", 0) if ac_dc == "DC" else 0,

                # Reconductoring details
                "reconductoring": reconductoring,
                "old_capacity_mw": project.get("old_capacity_mw", 0) if reconductoring else 0,
                "old_conductor_type": project.get("old_conductor_type", "") if reconductoring else "",
                "old_ac_dc": project.get("old_ac_dc", "") if reconductoring else "",

                # Financial parameters
                "baseline_electricity_price_per_mwh": project.get("baseline_electricity_price_per_mwh", 0),
                "social_discount_rate": financing_data["financial"].get("social_discount_rate", 0),

                # Timeline
                "construction_years": construction_years,
                "delay_years": delay_years,
                "project_lifetime_years": project_lifetime,
            }

            return technical_details

        except Exception as e:
            # Return minimal technical details if loading fails
            return {
                "project_name": "",
                "construction_type": "Unknown",
                "ac_dc": "Unknown",
                "capacity_mw": 0,
                "error": f"Failed to load technical details: {str(e)}"
            }

    def add_build_costs(self, results: Dict[str, Any]):
        """Add build cost results."""
        self.costs["build"] = results

    def add_row_costs(self, results: Dict[str, Any]):
        """Add ROW cost results."""
        self.costs["row"] = results

    def add_environmental_mitigation(self, results: Dict[str, Any]):
        """Add environmental mitigation results."""
        self.costs["environmental"] = results

    def add_delay_costs(self, results: Dict[str, Any]):
        """Add delay cost results."""
        self.costs["delay"] = results

    def add_insurance_costs(self, results: Dict[str, Any]):
        """Add insurance cost results."""
        self.costs["insurance"] = results

    def add_wildfire_liability_costs(self, results: Dict[str, Any]):
        """Add wildfire liability insurance cost results."""
        self.costs["wildfire_liability"] = results

    def add_wildfire_costs(self, results: Dict[str, Any]):
        """Add wildfire cost results."""
        self.costs["wildfire"] = results

    def add_outage_costs(self, results: Dict[str, Any]):
        """Add outage cost results."""
        self.costs["outage"] = results

    def add_oandm_costs(self, results: Dict[str, Any]):
        """Add O&M cost results."""
        self.costs["oandm"] = results

    def add_emissions_costs(self, results: Dict[str, Any]):
        """Add emissions cost results."""
        self.costs["emissions"] = results

    def add_line_loss_costs(self, results: Dict[str, Any]):
        """Add line loss cost results."""
        self.costs["line_loss"] = results

    def add_congestion_curtailment(self, results: Dict[str, Any]):
        """Add congestion and curtailment reduction benefits."""
        self.benefits["congestion_curtailment"] = results

    def add_revenue(self, results: Dict[str, Any]):
        """Add revenue results."""
        self.benefits["revenue"] = results

    def add_project_params(self, **kwargs):
        """Add project parameters (stored in technical_parameters)."""
        self.technical_details.update(kwargs)

    def add_financial_params(self, **kwargs):
        """Add financial parameters (stored in technical_parameters)."""
        self.technical_details.update(kwargs)

    def add_bcr_metrics(self, bcr_results: Dict[str, Any]):
        """Add benefit-cost ratio metrics."""
        self.bcr = bcr_results

    def calculate_summary(self):
        """
        Calculate summary totals from all cost and benefit modules.
        """
        # Capital costs
        build = self.costs.get("build", {})
        row = self.costs.get("row", {})
        env = self.costs.get("environmental", {})

        # Operational costs
        insurance = self.costs.get("insurance", {})
        oandm = self.costs.get("oandm", {})
        line_loss = self.costs.get("line_loss", {})
        emissions = self.costs.get("emissions", {})

        # Risk costs
        wildfire = self.costs.get("wildfire", {})
        outage = self.costs.get("outage", {})

        # Delay costs
        delay = self.costs.get("delay", {})

        self.summary = {
            # Capital costs
            "total_capital_nominal": (
                build.get("total_nominal", 0) +
                row.get("total_nominal", 0) +
                env.get("total_nominal", 0)
            ),
            "total_capital_afudc": (
                build.get("total_afudc", 0) +
                row.get("total_afudc", 0) +
                env.get("total_afudc", 0)
            ),
            "total_capital_pv": (
                build.get("total_pv", 0) +
                row.get("total_pv", 0) +
                env.get("total_pv", 0)
            ),

            # Operational costs
            "total_operational_nominal": (
                insurance.get("nominal_lifetime_cost", 0) +
                oandm.get("total_nominal", 0) +
                line_loss.get("lifetime_cost_nominal", 0) +
                emissions.get("lifetime_cost_nominal", 0)
            ),
            "total_operational_pv": (
                insurance.get("pv_total", 0) +
                oandm.get("total_pv", 0) +
                line_loss.get("lifetime_cost_pv", 0) +
                emissions.get("lifetime_cost_pv", 0)
            ),

            # Risk costs
            "total_risk_nominal": (
                wildfire.get("nominal_total", 0) +
                outage.get("nominal_total", 0)
            ),
            "total_risk_pv": (
                wildfire.get("pv_cost", 0) +
                outage.get("pv_cost", 0)
            ),

            # Grand totals
            "grand_total_cost_nominal": 0,  # Calculated below
            "grand_total_cost_afudc": 0,  # Calculated below
            "grand_total_cost_pv": 0,  # Calculated below
        }

        # Calculate grand totals
        self.summary["grand_total_cost_nominal"] = (
            self.summary["total_capital_nominal"] +
            self.summary["total_operational_nominal"] +
            self.summary["total_risk_nominal"] +
            delay.get("total_nominal", 0)
        )

        self.summary["grand_total_cost_afudc"] = (
            self.summary["total_capital_afudc"] +
            delay.get("total_afudc", 0)
        )

        self.summary["grand_total_cost_pv"] = (
            self.summary["total_capital_pv"] +
            self.summary["total_operational_pv"] +
            self.summary["total_risk_pv"] +
            delay.get("total_pv", 0)
        )

    def get_json_results(self) -> Dict[str, Any]:
        """
        Get all calculation results as JSON-serializable dictionary.

        Returns:
            Complete results structure with all costs, benefits, and metrics
        """
        # Calculate summary if not already done
        if not self.summary:
            self.calculate_summary()

        return {
            "scenario_id": self.scenario_id,
            "timestamp": self.timestamp,
            "input_mode": "json",
            "technical_parameters": self.technical_details,
            "costs": self.costs,
            "benefits": self.benefits,
            "summary": self.summary,
            "bcr": self.bcr,
        }

    def save_to_file(self, output_dir: str = None, module_name: str = None):
        """
        Save current state to a JSON file for subprocess communication.

        Args:
            output_dir: Directory to save the JSON file (default: ../outputs relative to script dir)
            module_name: Name of the calling module (for unique filename)

        Returns:
            Path to the saved JSON file
        """
        if output_dir is None:
            # Default to outputs directory relative to scripts directory
            script_dir = os.path.dirname(os.path.abspath(__file__))
            output_dir = os.path.join(script_dir, "..", "outputs")

        os.makedirs(output_dir, exist_ok=True)

        # If module_name provided, create unique file for this module
        # Otherwise use generic filename (may be overwritten by other modules)
        if module_name:
            json_file = os.path.join(output_dir, f"json_output_{self.scenario_id}_{module_name}.json")
        else:
            json_file = os.path.join(output_dir, f"json_output_{self.scenario_id}.json")

        # Create state dictionary
        state = {
            "scenario_id": self.scenario_id,
            "timestamp": self.timestamp,
            "technical_details": self.technical_details,
            "costs": self.costs,
            "benefits": self.benefits,
            "summary": self.summary,
            "bcr": self.bcr,
        }

        # Write to file
        with open(json_file, "w") as f:
            json.dump(state, f, indent=2)

        return json_file

    def load_from_file(self, json_file: str):
        """
        Load state from a JSON file (for aggregating subprocess results).

        Args:
            json_file: Path to JSON file to load
        """
        if not os.path.exists(json_file):
            return

        with open(json_file, "r") as f:
            state = json.load(f)

        # Merge state (taking the latest data from each module)
        if state.get("costs"):
            for key, value in state["costs"].items():
                if value:  # Only update if there's actual data
                    self.costs[key] = value

        if state.get("benefits"):
            for key, value in state["benefits"].items():
                if value:
                    self.benefits[key] = value

        if state.get("bcr"):
            self.bcr = state["bcr"]
