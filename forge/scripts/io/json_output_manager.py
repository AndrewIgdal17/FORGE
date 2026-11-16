# Date: 2025-11-10
# Description: JSON output manager for FORGE API calculations.
#              Collects per-module results in memory as JSON.

import json
import logging
import os
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


_MARKET_KEYS = (
    "congestion_spread_per_mwh",
    "hours_receiving_more_congested",
    "hours_sending_more_congested",
    "receiving_energy_value_per_mwh",
)


def _stored_market_measurements(technical: dict) -> dict:
    """Four route measurements as stored, including null."""
    block = technical.get("market_measurements") or {}
    if not isinstance(block, dict):
        block = {}
    return {key: block.get(key) for key in _MARKET_KEYS}


def _stored(mapping: dict, key: str, default=0):
    """Missing key uses default. A present None stays None."""
    if key not in mapping:
        return default
    return mapping[key]


def _sum_stored(*values):
    """Sum numbers. One None addend makes the sum None."""
    total = 0
    for value in values:
        if value is None:
            return None
        total += value
    return total


def _acquisition_or_total(row: dict, acquisition_key: str, total_key: str):
    """Use a positive acquisition figure, else the module total.

    A present None stays None. A missing acquisition key, or a stored 0,
    falls through to the total key. A missing total is 0.
    """
    if acquisition_key in row:
        value = row[acquisition_key]
        if value is None:
            return None
        if value:
            return value
    return _stored(row, total_key, 0)


def _require_when_reconductoring(
    project: Dict[str, Any], key: str, is_reconductoring_or_rebuild: bool, irrelevant_default: Any
) -> Any:
    """
    Read an old-configuration project field (old_capacity_mw/old_conductor_type/
    old_ac_dc) that is required when the project is reconductoring or rebuild,
    but unused (and legitimately absent) for greenfield projects.

    Raises KeyError if the project is reconductoring/rebuild and the field is
    missing or null, instead of silently substituting a default that would mask
    malformed scenario input.
    """
    if not is_reconductoring_or_rebuild:
        return irrelevant_default
    value = project.get(key)
    if value is None:
        raise KeyError(
            f"Missing '{key}' in project technical details: required for "
            "reconductoring/rebuild projects"
        )
    return value


class JSONOutputManager:
    """
    Manages JSON outputs for FORGE API calculations.
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
        """Load technical parameters from the active run's inputs."""
        from forge.scripts.utils.smart_loaders import (
            load_project_technical_details,
            load_physical_details,
            get_project_data_raw,
            get_financing_data_raw,
        )

        project_details = load_project_technical_details()

        construction_type = project_details.construction_type
        ac_dc = project_details.ac_dc
        capacity_mw = project_details.capacity_mw
        conductor_type = project_details.conductor_type
        converter_type = project_details.converter_type
        line_utilization = project_details.line_utilization
        project_type = project_details.project_type
        is_reconductoring_or_rebuild = project_type in ("reconductoring", "rebuild")
        delay_years = project_details.delay_years
        construction_years = project_details.construction_years
        project_lifetime = project_details.project_lifetime
        converter_loss_percentage = project_details.converter_loss_percentage

        total_line_length = load_physical_details()

        # Get additional details for reconductoring/rebuild
        tech_data = get_project_data_raw()
        project = tech_data.get("project", {})

        # Get financial parameters
        financing_data = get_financing_data_raw()

        return {
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
            "number_of_converters": (
                project.get("number_of_converters", 0) if ac_dc == "DC" else 0
            ),
            "converter_loss_percentage": converter_loss_percentage,
            # Project type / legacy reconductoring-or-rebuild details
            "project_type": project_type,
            "old_capacity_mw": (
                _require_when_reconductoring(
                    project, "old_capacity_mw", is_reconductoring_or_rebuild, 0
                )
            ),
            "old_conductor_type": (
                _require_when_reconductoring(
                    project, "old_conductor_type", is_reconductoring_or_rebuild, ""
                )
            ),
            "old_ac_dc": (
                _require_when_reconductoring(
                    project, "old_ac_dc", is_reconductoring_or_rebuild, ""
                )
            ),
            # Route measurements, including null when the archive has no price.
            "market_measurements": _stored_market_measurements(tech_data),
            "social_discount_rate": financing_data["financial"].get(
                "social_discount_rate", 0
            ),
            # Timeline
            "construction_years": construction_years,
            "delay_years": delay_years,
            "project_lifetime_years": project_lifetime,
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


    def add_wildfire_costs(self, results: Dict[str, Any]):
        """Add wildfire cost results."""
        self.costs["wildfire"] = results

    def add_outage_costs(self, results: Dict[str, Any]):
        """Add outage cost results."""
        self.costs["outage"] = results

    def add_oandm_costs(self, results: Dict[str, Any]):
        """Add O&M cost results."""
        self.costs["oandm"] = results

    def add_emissions_comp_costs(self, results: Dict[str, Any]):
        """Add loss-compensation emissions cost results."""
        self.costs["emissions"] = results

    def add_avoided_emissions(self, results: Dict[str, Any]):
        """Add avoided-emissions benefit results."""
        self.benefits["avoided_emissions"] = results

    def add_line_loss_costs(self, results: Dict[str, Any]):
        """Add line loss cost results."""
        self.costs["line_loss"] = results

    def add_congestion(self, results: Dict[str, Any]):
        """Add congestion and delivered-energy benefits.
        results includes delivered_benefit_annual, delivered_benefit_nominal, delivered_benefit_pv as own keys."""
        self.benefits["congestion"] = results

    def add_revenue(self, results: Dict[str, Any]):
        """Add revenue results."""
        self.benefits["capital_recovery"] = results

    def add_project_params(self, **kwargs):
        """Add project parameters (stored in technical_parameters)."""
        self.technical_details.update(kwargs)

    def add_financial_params(self, **kwargs):
        """Add financial parameters (stored in technical_parameters)."""
        self.technical_details.update(kwargs)

    def add_bcr_metrics(self, bcr_results: Dict[str, Any]):
        """Add benefit-cost ratio metrics."""
        self.bcr = bcr_results

    def require_upstream(self, category: str, module_key: str, field: str) -> float:
        """Read a single field from an upstream module's output, failing loudly if absent.

        Args:
            category: "costs" or "benefits"
            module_key: The module's output key (e.g. "build", "congestion")
            field: The specific field name within that module's output dict

        Returns:
            The field value as a float.

        Raises:
            KeyError: If the module hasn't written results or the field doesn't exist.
        """
        store = self.costs if category == "costs" else self.benefits
        if module_key not in store:
            raise KeyError(
                f"Module '{module_key}' has not run or written to {category}. "
                f"Cannot read '{field}'. Check pipeline ordering."
            )
        module_dict = store[module_key]
        if field not in module_dict:
            raise KeyError(
                f"Field '{field}' not found in {category}['{module_key}']. "
                f"Available keys: {list(module_dict.keys())}"
            )
        return float(module_dict[field])

    def require_upstream_dict(self, category: str, module_key: str) -> dict:
        """Return the full output dict from an upstream module, failing loudly if absent.

        Args:
            category: "costs" or "benefits"
            module_key: The module's output key (e.g. "build", "congestion")

        Returns:
            The module's full output dict.

        Raises:
            KeyError: If the module hasn't written results.
        """
        store = self.costs if category == "costs" else self.benefits
        if module_key not in store:
            raise KeyError(
                f"Module '{module_key}' has not run or written to {category}. "
                f"Check pipeline ordering."
            )
        return store[module_key]

    def calculate_summary(self):
        """
        Calculate summary totals from all cost and benefit modules.

        A missing component key is 0. A present None stays None and is not
        added to a number. On the JSON-input path, summary_override from
        build_summary_from_csv_equivalent() replaces this fallback.
        """
        build = self.costs.get("build", {})
        row = self.costs.get("row", {})
        env = self.costs.get("environmental", {})
        insurance = self.costs.get("insurance", {})
        oandm = self.costs.get("oandm", {})
        line_loss = self.costs.get("line_loss", {})
        emissions = self.costs.get("emissions", {})
        wildfire = self.costs.get("wildfire", {})
        outage = self.costs.get("outage", {})
        delay = self.costs.get("delay", {})

        total_capital_nominal = _sum_stored(
            _stored(build, "total_nominal"),
            _acquisition_or_total(row, "acquisition_nominal_total", "total_nominal"),
            _stored(env, "total_nominal"),
        )
        total_capital_afudc = _sum_stored(
            _stored(build, "total_afudc"),
            _stored(row, "total_afudc"),
            _stored(env, "total_afudc"),
        )
        total_capital_pv = _sum_stored(
            _stored(build, "total_pv"),
            _acquisition_or_total(row, "acquisition_pv", "total_pv"),
            _stored(env, "total_pv"),
        )
        total_operational_nominal = _sum_stored(
            _stored(insurance, "nominal_lifetime_cost"),
            _stored(oandm, "total_nominal"),
            _stored(row, "row_rent_nominal"),
        )
        total_operational_pv = _sum_stored(
            _stored(insurance, "pv_total"),
            _stored(oandm, "total_pv"),
            _stored(row, "row_rent_pv"),
        )
        total_energy_emissions_nominal = _sum_stored(
            _stored(line_loss, "total_nominal"),
            _stored(emissions, "total_nominal"),
        )
        total_energy_emissions_pv = _sum_stored(
            _stored(line_loss, "total_pv"),
            _stored(emissions, "total_pv"),
        )
        total_risk_nominal = _sum_stored(
            _stored(wildfire, "nominal_total"),
            _stored(outage, "nominal_total"),
        )
        total_risk_pv = _sum_stored(
            _stored(wildfire, "pv_cost"),
            _stored(outage, "pv_cost"),
        )
        delay_nominal = _stored(delay, "total_nominal")
        delay_afudc = _stored(delay, "total_afudc")
        delay_pv = _stored(delay, "total_pv")

        self.summary = {
            "total_capital_nominal": total_capital_nominal,
            "total_capital_afudc": total_capital_afudc,
            "total_capital_pv": total_capital_pv,
            "total_operational_nominal": total_operational_nominal,
            "total_operational_pv": total_operational_pv,
            "total_energy_emissions_nominal": total_energy_emissions_nominal,
            "total_energy_emissions_pv": total_energy_emissions_pv,
            "total_risk_nominal": total_risk_nominal,
            "total_risk_pv": total_risk_pv,
            "grand_total_cost_nominal": _sum_stored(
                total_capital_nominal,
                total_operational_nominal,
                total_risk_nominal,
                delay_nominal,
                total_energy_emissions_nominal,
            ),
            "grand_total_cost_afudc": _sum_stored(total_capital_afudc, delay_afudc),
            "grand_total_cost_pv": _sum_stored(
                total_capital_pv,
                total_operational_pv,
                total_risk_pv,
                delay_pv,
                total_energy_emissions_pv,
            ),
        }

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
            json_file = os.path.join(
                output_dir, f"json_output_{self.scenario_id}_{module_name}.json"
            )
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
                # Debug: Log line_loss specifically
                if key == "line_loss":
                    logger.debug(
                        f"DEBUG: Loading line_loss from {os.path.basename(json_file)}: {value}"
                    )
                # Update if value exists (allow zero values and empty dicts for line_loss)
                if value is not None:
                    # Always include line_loss, even if empty dict or zero values
                    if key == "line_loss" or value:
                        self.costs[key] = value

        if state.get("benefits"):
            for key, value in state["benefits"].items():
                if value is not None:
                    self.benefits[key] = value

        if state.get("bcr"):
            self.bcr = state["bcr"]
