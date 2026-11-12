"""FORGE input field metadata — one entry per input field.

Bridges taxonomy items to form controls. Each entry declares which
taxonomy item a field feeds, which tab it appears on, its label,
tooltip, input type, validation, condition, and display ordering.

Phase 4 deliverable. Canonical source alongside taxonomy.py.
"""

from __future__ import annotations

from dataclasses import dataclass, field as dc_field
from functools import lru_cache
from typing import Any, Literal

from forge.scripts.io.region_codes import EGRID_SUBREGIONS, GEA_NAMES, STATES

InputType = Literal[
    "number", "currency", "percent", "toggle", "dropdown",
    "dynamic_dropdown", "year", "text", "fuel_mix_row",
]
Tier = Literal["first-glance", "working", "advanced"]
InputCondition = Literal[
    "dc_only", "greenfield_only", "reconductoring_only",
    "reconductoring_or_rebuild", "rebuild_only", "always_hidden",
]

TERRAINS = (
    "forested", "scrubbed_flat", "wetland", "farmland",
    "desert_barren", "urban", "rolling_hills", "mountain",
)
FUELS = ("coal", "oil", "natural_gas", "solar", "wind", "hydro", "nuclear", "other")
CONSTRUCTION_TYPES = ("overhead", "underground")
WILDFIRE_CONSTRUCTION_TYPES = (
    "overhead",
    "underground_direct_buried",
    "underground_tunnel",
)


@dataclass(frozen=True)
class InputField:
    id: str
    taxonomy_id: str
    input_tab: str
    yaml_section: str
    field_path: str
    label: str
    help_text: str | None = None
    unit: str | None = None
    input_type: InputType = "number"
    condition: InputCondition | None = None
    validation: dict[str, Any] = dc_field(default_factory=dict)
    display_order: int = 1
    section_label: str | None = None
    tier: Tier = "working"
    sub_tab: str | None = None
    required_when: str | None = None
    required_stage: Literal["before_route", "after_route"] | None = None


def _f(id: str, **kwargs: Any) -> InputField:
    return InputField(id=id, **kwargs)


def _terrain_label(t: str) -> str:
    return t.replace("_", " ").title()


# ===================================================================
# Tab 1 — Project Identity (14 fields)
# ===================================================================

_TAB1: list[InputField] = [
    _f("construction_type", taxonomy_id="project_technology", input_tab="project-identity",
       yaml_section="01_project_technical_details", field_path="project.construction_type",
       label="Construction Type", help_text="Overhead or underground transmission",
       input_type="dropdown", tier="first-glance", display_order=1,
       validation={"required": True, "options": ["Overhead", "Underground Direct-Buried", "Underground Tunnel"]},
       sub_tab="technology"),
    _f("ac_dc", taxonomy_id="project_technology", input_tab="project-identity",
       yaml_section="01_project_technical_details", field_path="project.ac_dc",
       label="AC/DC", help_text="Alternating current or direct current transmission",
       input_type="dropdown", tier="first-glance", display_order=2,
       validation={"required": True, "options": ["AC", "DC"]},
       sub_tab="technology"),
    _f("capacity_mw", taxonomy_id="project_technology", input_tab="project-identity",
       yaml_section="01_project_technical_details", field_path="project.capacity_mw",
       label="Capacity MW", help_text="Nameplate transfer capacity (C_new); feeds capacity relief and line loss calculations", unit="MW",
       input_type="dynamic_dropdown", tier="first-glance", display_order=3,
       validation={"required": True, "nullable_number": True,
                   "dependsOn": "01_project_technical_details.project.ac_dc",
                   "optionSets": {"AC": [140, 329, 394, 460, 657, 1792, 2598, 6625],
                                  "DC": [500, 1500, 2000, 2400, 6000]}, "suffix": " MW"},
       required_when="always", required_stage="before_route",
       sub_tab="technology"),
    _f("conductor_type", taxonomy_id="project_technology", input_tab="equipment",
       yaml_section="01_project_technical_details", field_path="project.conductor_type",
       label="Conductor Type", help_text="Determines resistance, cost per mile, and O&M rates",
       input_type="dynamic_dropdown", tier="first-glance", display_order=4,
       validation={"required": True,
                   "dependsOn": "01_project_technical_details.project.construction_type",
                   "optionSets": {
                       "Overhead": ["Standard Aluminum Conductor", "Advanced Aluminum Conductor"],
                       "Underground Direct-Buried": ["Underground Copper Conductor"],
                       "Underground Tunnel": ["Underground Copper Conductor"],
                   }},
       sub_tab="conductor-details"),
    _f("number_of_converters", taxonomy_id="project_technology", input_tab="equipment",
       yaml_section="01_project_technical_details", field_path="project.number_of_converters",
       label="Number Of Converters", help_text="Number of converter stations (DC only)",
       input_type="dropdown", condition="dc_only", tier="first-glance", display_order=5,
       validation={"options": [0, 1, 2]}, sub_tab="converter-details"),
    _f("converter_type", taxonomy_id="project_technology", input_tab="equipment",
       yaml_section="01_project_technical_details", field_path="project.converter_type",
       label="Converter Type", help_text="LCC or VSC converter station type",
       input_type="dynamic_dropdown", condition="dc_only", tier="first-glance", display_order=6,
       validation={"dependsOn": "01_project_technical_details.project.ac_dc",
                   "optionSets": {
                       "AC": ["NA"],
                       "DC": ["LCC Converter", "VSC Converter"],
                   }},
       sub_tab="converter-details"),
    _f("converter_loss_pct", taxonomy_id="project_technology", input_tab="equipment",
       yaml_section="01_project_technical_details", field_path="project.converter_loss_percentage",
       label="Converter Loss (%)",
       help_text="Station loss as a percent of utilized capacity. Blank uses 0.75% LCC / 1.0% VSC.",
       unit="%", input_type="percent", condition="dc_only", tier="first-glance", display_order=7,
       validation={"min": 0, "max": 1, "step": 0.0001, "pct": True, "allowBlank": True},
       sub_tab="converter-details"),
    _f("project_type", taxonomy_id="project_technology", input_tab="project-identity",
       yaml_section="01_project_technical_details", field_path="project.project_type",
       label="Project Type", help_text="Greenfield: new line, full costs. Reconductoring: conductor swap on existing structures, zeroes structure cost. Rebuild: full structure replacement, incremental capacity formula.",
       input_type="dropdown", tier="first-glance", display_order=8,
       sub_tab="technology",
       validation={"required": True, "options": ["greenfield", "reconductoring", "rebuild"]}),
    _f("sending_source", taxonomy_id="project_technology", input_tab="project-identity",
       yaml_section="01_project_technical_details", field_path="project.sending_source",
       label="Sending-end source",
       help_text="Regional margin (the default) or a dedicated resource.",
       input_type="dropdown", tier="first-glance", display_order=9,
       validation={"required": True, "options": ["margin", "dedicated"]},
       sub_tab="technology"),
    _f("dedicated_contract_price", taxonomy_id="project_technology", input_tab="project-identity",
       yaml_section="01_project_technical_details",
       field_path="project.dedicated_resource.contract_price_per_mwh",
       label="Contract price ($/MWh)",
       help_text="All-in energy and capacity price of the dedicated resource.",
       unit="$/MWh", input_type="currency", tier="first-glance", display_order=14,
       validation={"nullable_number": True},
       required_when="dedicated", required_stage="before_route",
       sub_tab="technology"),
    _f("dedicated_emission_rate_co2e", taxonomy_id="project_technology", input_tab="project-identity",
       yaml_section="01_project_technical_details",
       field_path="project.dedicated_resource.emission_rate_kg_per_mwh.co2e",
       label="CO2e emission rate (kg/MWh)",
       help_text="Dedicated-resource CO2e rate. Wind or solar enters 0.",
       unit="kg/MWh", tier="first-glance", display_order=15,
       validation={"min": 0, "nullable_number": True},
       required_when="dedicated", required_stage="before_route",
       sub_tab="technology"),
    _f("dedicated_emission_rate_so2", taxonomy_id="project_technology", input_tab="project-identity",
       yaml_section="01_project_technical_details",
       field_path="project.dedicated_resource.emission_rate_kg_per_mwh.so2",
       label="SO2 emission rate (kg/MWh)",
       help_text="Dedicated-resource SO2 rate. Wind or solar enters 0.",
       unit="kg/MWh", tier="first-glance", display_order=16,
       validation={"min": 0, "nullable_number": True},
       required_when="dedicated", required_stage="before_route",
       sub_tab="technology"),
    _f("dedicated_emission_rate_nox", taxonomy_id="project_technology", input_tab="project-identity",
       yaml_section="01_project_technical_details",
       field_path="project.dedicated_resource.emission_rate_kg_per_mwh.nox",
       label="NOx emission rate (kg/MWh)",
       help_text="Dedicated-resource NOx rate. Wind or solar enters 0.",
       unit="kg/MWh", tier="first-glance", display_order=17,
       validation={"min": 0, "nullable_number": True},
       required_when="dedicated", required_stage="before_route",
       sub_tab="technology"),
    _f("old_capacity_mw", taxonomy_id="project_technology", input_tab="project-identity",
       yaml_section="01_project_technical_details", field_path="project.old_capacity_mw",
       label="Old Capacity MW", help_text="Existing line capacity (C_old)", unit="MW",
       input_type="dynamic_dropdown", condition="reconductoring_or_rebuild", tier="first-glance", display_order=11,
       validation={"dependsOn": "01_project_technical_details.project.old_ac_dc",
                   "optionSets": {"AC": [140, 329, 394, 460, 657, 1792, 2598, 6625],
                                  "DC": [500, 1500, 2000, 2400, 6000]}, "suffix": " MW"},
       required_when="reconductoring_or_rebuild", required_stage="before_route",
       sub_tab="technology"),
    _f("old_conductor_type", taxonomy_id="project_technology", input_tab="equipment",
       yaml_section="01_project_technical_details", field_path="project.old_conductor_type",
       label="Old Conductor Type", help_text="Original conductor for reconductoring cost comparison",
       input_type="dynamic_dropdown", condition="reconductoring_or_rebuild",
       tier="first-glance", display_order=12,
       validation={"dependsOn": "01_project_technical_details.project.construction_type",
                   "optionSets": {
                       "Overhead": ["Standard Aluminum Conductor", "Advanced Aluminum Conductor"],
                       "Underground Direct-Buried": ["Underground Copper Conductor"],
                       "Underground Tunnel": ["Underground Copper Conductor"],
                   },
                   "allowBlank": True},
       required_when="reconductoring_or_rebuild", required_stage="before_route",
       sub_tab="conductor-details"),
    _f("old_ac_dc", taxonomy_id="project_technology", input_tab="project-identity",
       yaml_section="01_project_technical_details", field_path="project.old_ac_dc",
       label="Old AC/DC", help_text="Original AC/DC type for reconductoring comparison",
       input_type="dropdown", condition="reconductoring_or_rebuild",
       tier="first-glance", display_order=10, validation={"options": ["", "AC", "DC"]},
       required_when="reconductoring_or_rebuild", required_stage="before_route",
       sub_tab="technology"),
    _f("old_converter_type", taxonomy_id="project_technology", input_tab="equipment",
       yaml_section="01_project_technical_details", field_path="project.old_converter_type",
       label="Old Converter Type", help_text="Original converter type for old DC line (used for reconductoring cost lookup)",
       input_type="dynamic_dropdown", condition="old_dc_only",
       tier="first-glance", display_order=13,
       validation={"dependsOn": "01_project_technical_details.project.old_ac_dc",
                   "optionSets": {"AC": [], "DC": ["LCC Converter", "VSC Converter"]}},
       required_when="reconductoring_or_rebuild_dc", required_stage="before_route",
       sub_tab="converter-details"),
    _f("line_utilization", taxonomy_id="project_utilization", input_tab="project-identity",
       yaml_section="01_project_technical_details", field_path="project.line_utilization",
       label="Line Utilization", help_text="Percent of nameplate capacity used on average.",
       input_type="percent", tier="first-glance", display_order=1,
       validation={"min": 0, "max": 1, "step": 0.01, "pct": True},
       sub_tab="technology"),
    _f("baseline_price_mwh", taxonomy_id="project_utilization", input_tab="benefits",
       yaml_section="01_project_technical_details", field_path="project.value_of_load_per_mwh",
       label="Receiving-end energy value ($/MWh)",
       help_text="Receiving-end energy value; prices losses and, for a dedicated resource, delivered energy.",
       unit="$/MWh", input_type="currency", tier="first-glance", display_order=2,
       validation={"min": 0, "nullable_number": True},
       required_when="always", required_stage="after_route",
       sub_tab="economic-details"),
    _f("construction_years", taxonomy_id="project_timing", input_tab="project-identity",
       yaml_section="01_project_technical_details", field_path="timeline.construction_years",
       label="Construction Years", help_text="Construction duration; affects AFUDC compounding and PV discounting",
       unit="years", tier="first-glance", display_order=1,
       validation={"required": True, "min": 1, "integer": True},
       required_when="always", required_stage="before_route",
       sub_tab="timeline"),
    _f("delay_years", taxonomy_id="project_timing", input_tab="project-identity",
       yaml_section="01_project_technical_details", field_path="timeline.delay_years",
       label="Delay Years", help_text="Pre-construction delay (permitting); drives delay costs and AFUDC timing",
       unit="years", tier="first-glance", display_order=2,
       validation={"required": True, "min": 0, "integer": True},
       required_when="always", required_stage="before_route",
       sub_tab="timeline"),
    _f("project_lifetime", taxonomy_id="project_timing", input_tab="project-identity",
       yaml_section="01_project_technical_details", field_path="timeline.project_lifetime",
       label="Project Lifetime (Years)", help_text="Operating years after COD; annual costs and benefits accrue over this period",
       unit="years", tier="first-glance", display_order=3,
       validation={"required": True, "min": 1, "integer": True},
       required_when="always", required_stage="before_route",
       sub_tab="timeline"),
    _f("baseline_delay_years", taxonomy_id="project_timing", input_tab="project-identity",
       yaml_section="01_project_technical_details", field_path="timeline.baseline_delay_years",
       label="Baseline (on-time) delay",
       help_text="The delay of the on-time project the cost of delay is measured against.",
       unit="years", tier="first-glance", display_order=4,
       validation={"required": True, "min": 0, "integer": True}, sub_tab="timeline"),
]

# Corona loss tiers (8 fields). Shown on Technology only for AC overhead.
_CORONA_HELP = "Annual-average corona loss added to I²R losses."
_CORONA_CEILINGS = ("230 kV", "345 kV", "500 kV", "open")
for _tier, _ceiling in enumerate(_CORONA_CEILINGS):
    _TAB1.append(_f(
        f"corona_tier_{_tier}_max_kv", taxonomy_id="project_technology",
        input_tab="project-identity", sub_tab="technology", condition="always_hidden",
        yaml_section="22_corona_losses",
        field_path=f"corona.voltage_class_tiers[{_tier}].max_kv",
        label=f"Voltage ceiling (kV), {_ceiling}",
        help_text=_CORONA_HELP, unit="kV", input_type="number",
        section_label="Corona Losses (AC Overhead)",
        tier="advanced", display_order=110 + _tier * 2,
        validation={"min": 0}))
    _TAB1.append(_f(
        f"corona_tier_{_tier}_kw_per_mile", taxonomy_id="project_technology",
        input_tab="project-identity", sub_tab="technology", condition="always_hidden",
        yaml_section="22_corona_losses",
        field_path=f"corona.voltage_class_tiers[{_tier}].kw_per_mile",
        label=f"Corona loss (kW/mile), {_ceiling}",
        help_text=_CORONA_HELP, unit="kW/mile", input_type="number",
        section_label="Corona Losses (AC Overhead)",
        tier="advanced", display_order=111 + _tier * 2,
        validation={"min": 0}))

# ===================================================================
# Tab 2 — Routing (85 fields: 18 terrain + 60 ROW + 1 flag + 6 terminals)
# ===================================================================

_TAB2: list[InputField] = []
for _i, _t in enumerate(TERRAINS):
    _TAB2.append(_f(
        f"terrain_miles_{_t}", taxonomy_id="route_terrain_miles", input_tab="routing",
        yaml_section="02_project_physical_details", field_path=f"terrain.terrain_miles.{_t}",
        label=_terrain_label(_t), help_text=f"Miles through {_terrain_label(_t).lower()} terrain",
        unit="miles", tier="first-glance", display_order=_i + 1, validation={"min": 0},
        sub_tab="terrain-mix",
    ))
for _i, _t in enumerate(("forested", "scrubbed_flat", "desert_barren", "rolling_hills", "mountain")):
    _TAB2.append(_f(
        f"protected_area_acres_{_t}", taxonomy_id="route_terrain_miles", input_tab="routing",
        yaml_section="02_project_physical_details",
        field_path=f"terrain.protected_area_acres.{_t}",
        label=f"{_terrain_label(_t)} protected-area acres",
        help_text="Acres of this class inside protected areas. Habitat credits use this area. Required.",
        unit="acres", tier="first-glance", display_order=20 + _i,
        validation={"required": True, "min": 0},
        sub_tab="terrain-mix",
    ))
for _i, _t in enumerate(TERRAINS):
    _TAB2.append(_f(
        f"terrain_mult_{_t}", taxonomy_id="route_terrain_multipliers", input_tab="routing",
        yaml_section="02_project_physical_details", field_path=f"terrain.terrain_multipliers.{_t}",
        label=_terrain_label(_t), help_text=f"Cost multiplier for {_terrain_label(_t).lower()} terrain",
        tier="advanced", display_order=_i + 1, validation={"min": 0},
        sub_tab="terrain-mix",
    ))

# ===================================================================
# Tab 3 — Financial (43 fields)
# ===================================================================

_TAB3: list[InputField] = [
    # --- Core rates (Rates sub-tab, custom-rendered) ---
    _f("base_year", taxonomy_id="financial_rates", input_tab="financial",
       sub_tab="rates", condition="always_hidden",
       yaml_section="03_financing", field_path="financial.base_year",
       label="Base Year", help_text="Reference year for all present values (base-year dollars)",
       input_type="dropdown", tier="first-glance", display_order=1,
       validation={"options": [2025]}),
    _f("inflation_rate", taxonomy_id="financial_rates", input_tab="financial",
       sub_tab="rates", condition="always_hidden",
       yaml_section="03_financing", field_path="financial.inflation_rate",
       label="Inflation Rate", help_text="Annual inflation rate for Fisher equation",
       input_type="percent", tier="first-glance", display_order=2,
       validation={"min": 0, "max": 0.2, "step": 0.005, "pct": True}),
    _f("wacc_nominal", taxonomy_id="financial_rates", input_tab="financial",
       sub_tab="rates", condition="always_hidden",
       yaml_section="03_financing", field_path="financial.wacc_nominal",
       label="WACC Nominal", help_text="Nominal WACC; real WACC derived via Fisher equation",
       input_type="percent", tier="first-glance", display_order=3,
       validation={"min": 0, "max": 0.2, "step": 0.005, "pct": True}),
    _f("social_discount_rate", taxonomy_id="financial_rates", input_tab="financial",
       sub_tab="rates", condition="always_hidden",
       yaml_section="03_financing", field_path="financial.social_discount_rate",
       label="Social Discount Rate", help_text="Discount rate for social externalities (risk, emissions)",
       input_type="percent", tier="first-glance", display_order=4,
       validation={"min": 0, "max": 0.1, "step": 0.005, "pct": True}),
    _f("construction_cost_escalation_nominal", taxonomy_id="financial_rates", input_tab="financial",
       sub_tab="rates", condition="always_hidden",
       yaml_section="03_financing", field_path="financial.construction_cost_escalation_nominal",
       label="Construction cost escalation (%/yr)",
       help_text="nominal; converted to real by the Fisher relation and applied to each construction year",
       input_type="percent", tier="working", display_order=5,
       validation={"min": 0, "max": 0.2, "step": 0.005, "pct": True}),
    _f("benefit_price_escalation_real", taxonomy_id="financial_rates", input_tab="financial",
       sub_tab="rates", condition="always_hidden",
       yaml_section="17_congestion_reductions", field_path="benefit_price_escalation_real",
       label="Benefit price escalation (%/yr, real)",
       help_text="Default 1%/yr real",
       input_type="percent", tier="working", display_order=6,
       validation={"min": 0, "max": 0.2, "step": 0.005, "pct": True}),
    # --- Contingencies ---
    _f("conductor_contingency", taxonomy_id="financial_contingencies", input_tab="capital-costs",
       sub_tab="conductor",
       yaml_section="03_financing", field_path="financial.contingencies.conductor_contingency",
       label="Conductor Contingency", help_text="Percentage markup on conductor cost for contingencies",
       input_type="percent", tier="working", display_order=1,
       validation={"min": 0, "max": 0.5, "step": 0.01, "pct": True}),
    _f("structure_contingency", taxonomy_id="financial_contingencies", input_tab="capital-costs",
       sub_tab="structure",
       yaml_section="03_financing", field_path="financial.contingencies.structure_contingency",
       label="Structure Contingency", help_text="Percentage markup on structure cost for contingencies",
       input_type="percent", tier="working", display_order=2,
       validation={"min": 0, "max": 0.5, "step": 0.01, "pct": True}),
    _f("converter_contingency", taxonomy_id="financial_contingencies", input_tab="capital-costs",
       sub_tab="converter",
       yaml_section="03_financing", field_path="financial.contingencies.converter_contingency",
       label="Converter Contingency", help_text="Percentage markup on converter cost for contingencies (DC only)",
       input_type="percent", condition="dc_only",
       tier="working", display_order=3,
       validation={"min": 0, "max": 0.5, "step": 0.01, "pct": True}),
    _f("soft_cost_multiplier", taxonomy_id="financial_contingencies", input_tab="capital-costs",
       sub_tab="conductor",
       yaml_section="10_project_category_build_costs", field_path="soft_cost_multiplier",
       label="Soft cost adder (%)",
       help_text="Project management, engineering, and administrative costs, applied after contingency. Default 10%.",
       input_type="percent", tier="working", display_order=4,
       validation={"min": 0, "max": 1, "step": 0.01, "pct": True}),
    _f("override_variable_conductor_cost_per_mile", taxonomy_id="build_conductor",
       input_tab="capital-costs", sub_tab="conductor",
       yaml_section="10_project_category_build_costs",
       field_path="overrides.variable_conductor_cost_per_mile",
       label="Conductor cost ($/mile)",
       help_text="Blank uses the equipment catalog. A number replaces the catalog value.",
       unit="$/mile", input_type="currency", section_label="Build cost overrides",
       tier="working", display_order=5,
       validation={"min": 0, "allowBlank": True}),
    _f("override_fixed_conductor_cost", taxonomy_id="build_conductor",
       input_tab="capital-costs", sub_tab="conductor",
       yaml_section="10_project_category_build_costs",
       field_path="overrides.fixed_conductor_cost",
       label="Conductor fixed cost ($)",
       help_text="Blank uses the equipment catalog. A number replaces the catalog value.",
       unit="$", input_type="currency", section_label="Build cost overrides",
       tier="working", display_order=6,
       validation={"min": 0, "allowBlank": True}),
    _f("override_variable_structure_cost_per_mile", taxonomy_id="build_structure",
       input_tab="capital-costs", sub_tab="conductor",
       yaml_section="10_project_category_build_costs",
       field_path="overrides.variable_structure_cost_per_mile",
       label="Structure cost ($/mile)",
       help_text="Blank uses the equipment catalog. A number replaces the catalog value.",
       unit="$/mile", input_type="currency", section_label="Build cost overrides",
       tier="working", display_order=7,
       validation={"min": 0, "allowBlank": True}),
    _f("override_fixed_converter_cost", taxonomy_id="build_converter",
       input_tab="capital-costs", sub_tab="conductor",
       yaml_section="10_project_category_build_costs",
       field_path="overrides.fixed_converter_cost",
       label="Converter cost, one end ($)",
       help_text="Blank uses the equipment catalog. A number replaces the catalog value.",
       unit="$", input_type="currency", condition="dc_only",
       section_label="Build cost overrides",
       tier="working", display_order=8,
       validation={"min": 0, "allowBlank": True}),
    # --- Revenue (Rates sub-tab, custom-rendered) ---
    _f("revenue_enabled", taxonomy_id="financial_revenue_config", input_tab="financial",
       sub_tab="rates", condition="always_hidden",
       yaml_section="03_financing", field_path="financial.revenue.rate_based.enabled",
       label="Revenue Requirement", help_text="Enable rate-based revenue calculation",
       input_type="toggle", tier="working", display_order=1),
    # --- AFUDC (AFUDC sub-tab, custom-rendered) ---
    _f("apply_afudc", taxonomy_id="financial_afudc", input_tab="financial",
       sub_tab="afudc", condition="always_hidden",
       yaml_section="03_financing", field_path="financial.afudc.apply_afudc",
       label="Apply AFUDC", help_text="Toggle AFUDC capitalization",
       input_type="toggle", tier="advanced", display_order=1),
]

# Construction spending profiles (26 year-weights: 5 + 6 + 7 + 8).
_SPENDING_HELP = (
    "Share of construction spend in each year. The calculator pools these into "
    "one S-curve and resamples to the construction duration. A 1-year project "
    "ignores these weights."
)
_spending_order = 1
for _duration, _years in (("5", 5), ("6", 6), ("7", 7), ("8", 8)):
    for _year in range(_years):
        _TAB3.append(_f(
            f"spending_profile_{_duration}_year_{_year + 1}",
            taxonomy_id="financial_timing_patterns", input_tab="financial",
            sub_tab="afudc", condition="always_hidden",
            yaml_section="19_cost_timing_patterns",
            field_path=f"construction_spending_profiles.{_duration}[{_year}]",
            label=f"{_duration}-year spending profile, year {_year + 1} (%)",
            help_text=_SPENDING_HELP, input_type="percent",
            section_label="Construction Spending Profiles",
            tier="advanced", display_order=_spending_order,
            validation={"min": 0, "max": 1, "step": 0.01, "pct": True}))
        _spending_order += 1

_TAB2.append(_f(
    "row_agreement_type", taxonomy_id="row_acquisition", input_tab="routing",
    yaml_section="01_project_technical_details", field_path="project.row_agreement_type",
    label="ROW agreement",
    help_text=(
        "New permanent easement: acquisition and holding, no rent. Lease or license "
        "of an existing corridor: rent from year 1, no acquisition or holding. "
        "Federal hybrid: acquisition, holding, and rent from the start of "
        "construction. If none is chosen, greenfield takes a new easement and "
        "reconductoring or rebuild takes a lease."
    ),
    input_type="dropdown", tier="working", display_order=0,
    validation={"options": [
        "permanent_easement_new",
        "federal_hybrid",
        "lease_license_existing",
    ], "retired_options": {
        "fee_simple": "fee_simple is no longer an agreement type. Choose another agreement.",
    }},
    sub_tab="rights-of-way"))

# ROW zones (15 zones × 4 fields = 60) — rendered on Project Technical Details / Routing / Rights of Way
for _z in range(1, 16):
    _zn = f"zone_{_z}"
    _zl = f"Zone {_z}"
    for _fi, (_fk, _fl, _fu, _fh) in enumerate([
        ("miles", "Miles", "miles", "Route miles through this ROW zone"),
        ("acquisition_cost", "Acquisition Cost", "$/acre", "Per-acre land acquisition cost"),
        ("rent_cost", "Rent Cost", "$/acre/year", "Annual per-acre rent"),
        ("hold_cost", "Hold Cost", "$/acre/year", "Annual per-acre holding cost (option fee)"),
    ]):
        _tid = "row_rent" if _fk == "rent_cost" else ("row_holding" if _fk == "hold_cost" else "row_acquisition")
        _TAB2.append(_f(
            f"row_{_zn}_{_fk}", taxonomy_id=_tid, input_tab="routing",
            yaml_section="11_project_row_details", field_path=f"right_of_way.{_zn}.{_fk}",
            label=f"{_zl} {_fl}", help_text=_fh, unit=_fu,
            input_type="currency" if "cost" in _fk.lower() else "number",
            tier="first-glance", display_order=(_z - 1) * 4 + _fi + 1,
            section_label=_zl, validation={"min": 0},
            sub_tab="rights-of-way"))

_TAB2.append(_f(
    "row_rent_escalation_real", taxonomy_id="row_rent", input_tab="routing",
    yaml_section="11_project_row_details", field_path="row_rent_escalation_real",
    label="ROW rent escalation (%/yr, real)",
    help_text="Real growth of ROW rent. Holding stays flat. Default 0%/yr.",
    input_type="percent", tier="working", display_order=61,
    validation={"min": 0, "max": 0.2, "step": 0.005, "pct": True},
    sub_tab="rights-of-way"))

for _end_i, (_end, _end_label) in enumerate((("sending", "Sending"), ("receiving", "Receiving"))):
    for _key_i, (_key, _kind, _options) in enumerate((
        ("gea", "GEA region", list(GEA_NAMES)),
        ("egrid_subregion", "eGRID subregion", list(EGRID_SUBREGIONS)),
        ("state", "state", list(STATES)),
    )):
        _TAB2.append(_f(
            f"{_end}_terminal_{_key}",
            taxonomy_id="project_technology",
            input_tab="routing",
            yaml_section="01_project_technical_details",
            field_path=f"terminals.{_end}.{_key}",
            label=f"{_end_label} terminal {_kind}",
            help_text=f"{_end_label} terminal {_kind}. Route analysis fills this. No default.",
            input_type="dropdown",
            tier="working",
            display_order=_end_i * 3 + _key_i + 1,
            validation={"options": _options},
            sub_tab="terminals",
        ))

# ===================================================================
# Tab 4 — Environmental Costs (40 fields: 1 uplift + 31 base + 6 credits + 2 read-only displays)
# ===================================================================

_TAB4: list[InputField] = []

# Uplift factor (base-mitigation sub-tab)
_TAB4.append(_f(
    "env_uplift_factor", taxonomy_id="env_mitigation", input_tab="capital-costs",
    yaml_section="09_environmental_mitigation",
    field_path="environmental_mitigation.mitigation_uplift_factor",
    label="Mitigation Uplift Factor", help_text="TCE factor for construction width beyond ROW",
    tier="working", display_order=1, sub_tab="base-mitigation"))

# Base mitigation: overhead (8), underground_direct_buried (8), underground_tunnel (8)
_ENV_CT = [
    ("overhead", "Overhead", TERRAINS),
    ("underground_direct_buried", "Underground Direct Buried", TERRAINS),
    ("underground_tunnel", "Underground Tunnel", TERRAINS),
]
_env_order = 2
for _ct_key, _ct_label, _ct_terrains in _ENV_CT:
    for _t in _ct_terrains:
        _TAB4.append(_f(
            f"env_base_{_ct_key}_{_t}", taxonomy_id="env_mitigation", input_tab="capital-costs",
            yaml_section="09_environmental_mitigation",
            field_path=f"environmental_mitigation.base_mitigation_cost_per_acre.{_ct_key}.{_t}",
            label=_terrain_label(_t), help_text=f"Per-acre mitigation/restoration cost for {_terrain_label(_t).lower()} terrain",
            section_label=f"Base Mitigation — {_ct_label}",
            unit="$/acre", input_type="currency", tier="working", display_order=_env_order,
            sub_tab="base-mitigation"))
        _env_order += 1

# Credits: 1 wetland + 5 habitat = 6 fields
_TAB4.append(_f(
    "env_credit_cost_wetland", taxonomy_id="env_mitigation", input_tab="capital-costs",
    yaml_section="09_environmental_mitigation",
    field_path="environmental_mitigation.wetland_credit_cost_per_acre",
    label="Wetland Credit Cost",
    help_text="Per-acre credit purchase cost for wetland mitigation banking",
    section_label="Credit Costs",
    unit="$/acre", input_type="currency", tier="working", display_order=_env_order,
    sub_tab="credits"))
_env_order += 1
for _terrain in ["forested", "scrubbed_flat", "desert_barren", "rolling_hills", "mountain"]:
    _TAB4.append(_f(
        f"env_credit_cost_habitat_{_terrain}", taxonomy_id="env_mitigation", input_tab="capital-costs",
        yaml_section="09_environmental_mitigation",
        field_path=f"environmental_mitigation.habitat_credit_cost_per_credit.{_terrain}",
        label=f"Habitat — {_terrain_label(_terrain)}",
        help_text=f"Per-acre habitat credit cost for {_terrain_label(_terrain).lower()} terrain",
        section_label="Credit Costs",
        unit="$/credit", input_type="currency", tier="working", display_order=_env_order,
        sub_tab="credits"))
    _env_order += 1

_TAB4.append(_f(
    "env_wetland_compensation_ratio", taxonomy_id="env_mitigation", input_tab="capital-costs",
    yaml_section="09_environmental_mitigation",
    field_path="environmental_mitigation.wetland_compensation_ratio",
    label="Wetland compensation ratio",
    help_text="Multiplies wetland acres. The wetland price is dollars per impact acre. Default 1.0.",
    input_type="number", tier="working", display_order=_env_order,
    validation={"min": 0, "step": 0.1},
    sub_tab="credits",
))
_env_order += 1

_TAB4.append(_f(
    "env_habitat_compensation_ratio", taxonomy_id="env_mitigation", input_tab="capital-costs",
    yaml_section="09_environmental_mitigation",
    field_path="environmental_mitigation.habitat_compensation_ratio",
    label="Habitat compensation ratio",
    help_text="Credits per impact acre. Default 2.0.",
    input_type="number", tier="working", display_order=_env_order,
    validation={"min": 0, "step": 0.1},
    sub_tab="credits",
))
_env_order += 1

_TAB4.append(_f(
    "disturbance_multiplier_rebuild", taxonomy_id="env_mitigation",
    input_tab="capital-costs", yaml_section="09_environmental_mitigation",
    field_path="environmental_mitigation.disturbance_multiplier_rebuild",
    label="Rebuild disturbance multiplier",
    help_text="Scales on-site restoration and wetland and habitat credits on a rebuild. Reconductoring uses 0. Greenfield uses 1. Default 0.5.",
    input_type="percent", tier="working", display_order=_env_order,
    sub_tab="credits", condition="rebuild_only",
    validation={"min": 0, "max": 1, "step": 0.01, "pct": True}))

# ===================================================================
# Tab 5 — Operating Costs (53 fields: 10 insurance + 36 veg + 5 structure + 2 converter)
# ===================================================================

_TAB5: list[InputField] = [
    _f("insurance_premium_rate", taxonomy_id="insurance", input_tab="operating",
       yaml_section="04_insurance", field_path="insurance.premium_rate_default",
       label="Fallback Premium Rate (%)",
       help_text="Used only when the construction type has no specific rate. All default construction types have specific rates.",
       input_type="percent", condition="always_hidden", tier="working", display_order=1,
       validation={"min": 0, "max": 1, "step": 0.001, "pct": True},
       sub_tab="operational-insurance"),
    _f("insurable_conductors", taxonomy_id="insurance", input_tab="operating",
       yaml_section="04_insurance", field_path="insurance.insurable_components.conductors",
       label="Conductors", help_text="Include conductor costs in insurable value",
       input_type="toggle", condition="always_hidden", tier="working", display_order=2,
       sub_tab="operational-insurance"),
    _f("insurable_structures", taxonomy_id="insurance", input_tab="operating",
       yaml_section="04_insurance", field_path="insurance.insurable_components.structures",
       label="Structures", help_text="Include structure costs in insurable value",
       input_type="toggle", condition="always_hidden", tier="working", display_order=3,
       sub_tab="operational-insurance"),
    _f("insurable_converters", taxonomy_id="insurance", input_tab="operating",
       yaml_section="04_insurance", field_path="insurance.insurable_components.converters",
       label="Converters", help_text="Include converter costs in insurable value",
       input_type="toggle", condition="always_hidden", tier="working", display_order=4,
       sub_tab="operational-insurance"),
    _f("insurance_premium_overhead", taxonomy_id="insurance", input_tab="operating",
       yaml_section="04_insurance", field_path="insurance.premium_rate_by_type.overhead",
       label="Overhead premium rate (% of insurable value)",
       help_text="Annual self-insurance reserve. Default 0.20%. Commercial T&D coverage is generally unavailable.",
       input_type="percent", condition="always_hidden", tier="working", display_order=5,
       validation={"min": 0, "max": 1, "step": 0.0001, "pct": True},
       sub_tab="operational-insurance"),
    _f("insurance_premium_underground_direct_buried", taxonomy_id="insurance", input_tab="operating",
       yaml_section="04_insurance",
       field_path="insurance.premium_rate_by_type.underground_direct_buried",
       label="Direct-buried premium rate (% of insurable value)",
       help_text="Same 0.20% reserve as overhead. Higher capital cost is captured in insurable value.",
       input_type="percent", condition="always_hidden", tier="working", display_order=6,
       validation={"min": 0, "max": 1, "step": 0.0001, "pct": True},
       sub_tab="operational-insurance"),
    _f("insurance_premium_underground_tunnel", taxonomy_id="insurance", input_tab="operating",
       yaml_section="04_insurance",
       field_path="insurance.premium_rate_by_type.underground_tunnel",
       label="Tunnel premium rate (% of insurable value)",
       help_text="Same 0.20% reserve as direct-buried underground.",
       input_type="percent", condition="always_hidden", tier="working", display_order=7,
       validation={"min": 0, "max": 1, "step": 0.0001, "pct": True},
       sub_tab="operational-insurance"),
    _f("insurance_premium_converter", taxonomy_id="insurance", input_tab="operating",
       yaml_section="04_insurance", field_path="insurance.premium_rate_by_type.converter",
       label="Converter premium rate (% of converter value)",
       help_text="Commercial converter premium. Range about 0.4–1.0%. Default 0.70%. Independent of the line rate.",
       input_type="percent", condition="always_hidden", tier="working", display_order=9,
       validation={"min": 0, "max": 1, "step": 0.0001, "pct": True},
       sub_tab="operational-insurance"),
    _f("insurance_escalation_rate", taxonomy_id="insurance", input_tab="operating",
       yaml_section="04_insurance", field_path="insurance.escalation_rate",
       label="Insurance escalation (%/yr, real)",
       help_text="Real annual growth of the premium. Default 2.0%/yr. Source: WTW (2025); Powerlink (2025).",
       input_type="percent", condition="always_hidden", tier="working", display_order=10,
       validation={"min": 0, "max": 0.2, "step": 0.005, "pct": True},
       sub_tab="operational-insurance"),
]

# Vegetation management: 3 construction types × 8 terrains = 24
_VEG_CT = [
    ("Overhead", "Overhead"), ("Underground Direct Buried", "Underground Direct Buried"),
    ("Underground Tunnel", "Underground Tunnel"),
]
_veg_order = 1
for _ct_key, _ct_label in _VEG_CT:
    for _t in TERRAINS:
        _TAB5.append(_f(
            f"veg_{_ct_key.lower().replace(' ', '_')}_{_t}", taxonomy_id="oandm",
            input_tab="operating", yaml_section="12_project_om_vegetation_management",
            field_path=f"vegetation_management_om_costs.{_ct_key}.{_t}",
            label=_terrain_label(_t), help_text=f"Annual vegetation management cost for {_terrain_label(_t).lower()} terrain",
            section_label=f"Vegetation Mgmt — {_ct_label}",
            unit="$/mile/year", input_type="currency", condition="always_hidden",
            tier="first-glance", display_order=_veg_order, validation={"min": 0},
            sub_tab="vegetation-management"))
        _veg_order += 1

# Structure O&M rates (custom-rendered by StructureMaintenance)
_TAB5 += [
    _f("struct_om_overhead", taxonomy_id="oandm", input_tab="operating",
       yaml_section="14_category_om_structures",
       field_path="project_categories_om_structures.Overhead.base_om_per_mile_year",
       label="Base O&M ($/mile/year)",
       help_text="Annual structure maintenance per mile, excluding vegetation management. Default $19,090/mile/year (2025$). Source: Connecticut Siting Council (2022) lifecycle analysis (CTSitingCouncil2022LCA).",
       unit="$/mile/year", input_type="currency", condition="always_hidden",
       tier="working", display_order=1, validation={"min": 0},
       sub_tab="structure-maintenance"),
    _f("struct_om_ug_direct_buried", taxonomy_id="oandm", input_tab="operating",
       yaml_section="14_category_om_structures",
       field_path="project_categories_om_structures.Underground direct-buried.om_pct_of_line_capex",
       label="O&M (% of line CAPEX/year)",
       help_text="Annual line O&M as a percent of line capital cost. Default 0.15%/yr. Source: CIET/Powerlink (2023) (CIET2023).",
       input_type="percent", condition="always_hidden",
       tier="working", display_order=2,
       validation={"min": 0, "max": 1, "step": 0.0001, "pct": True},
       sub_tab="structure-maintenance"),
    _f("struct_om_ug_tunnel", taxonomy_id="oandm", input_tab="operating",
       yaml_section="14_category_om_structures",
       field_path="project_categories_om_structures.Underground tunnel.om_pct_of_line_capex",
       label="O&M (% of line CAPEX/year)",
       help_text="Annual line O&M as a percent of line capital cost. Default 0.4%/yr. Source: IET and Mott MacDonald (2025) (IETMottMac2025).",
       input_type="percent", condition="always_hidden",
       tier="working", display_order=3,
       validation={"min": 0, "max": 1, "step": 0.0001, "pct": True},
       sub_tab="structure-maintenance"),
    _f("om_real_escalation_rate", taxonomy_id="oandm", input_tab="operating",
       yaml_section="14_category_om_structures",
       field_path="om_real_escalation_rate",
       label="O&M escalation (%/yr, real)",
       help_text="Real growth of line, vegetation, and converter O&M. Default 2.0%/yr.",
       input_type="percent", condition="always_hidden",
       tier="working", display_order=5,
       validation={"min": 0, "max": 0.2, "step": 0.005, "pct": True},
       sub_tab="structure-maintenance"),
    _f("converter_om_lcc", taxonomy_id="oandm", input_tab="operating",
       yaml_section="15_category_om_converters",
       field_path="converter_om_rate.LCC Converter",
       label="Annual converter O&M (% of station CAPEX)",
       help_text="Annual converter O&M as a percent of station capital cost. Default 0.5%/yr. Source: UCLM (2023).",
       input_type="percent", condition="always_hidden",
       tier="working", display_order=1,
       validation={"min": 0, "max": 1, "step": 0.001, "pct": True},
       sub_tab="converter-maintenance"),
    _f("converter_om_vsc", taxonomy_id="oandm", input_tab="operating",
       yaml_section="15_category_om_converters",
       field_path="converter_om_rate.VSC Converter",
       label="Annual converter O&M (% of station CAPEX)",
       help_text="Annual converter O&M as a percent of station capital cost. Default 0.5%/yr. Source: UCLM (2023).",
       input_type="percent", condition="always_hidden",
       tier="working", display_order=2,
       validation={"min": 0, "max": 1, "step": 0.001, "pct": True},
       sub_tab="converter-maintenance"),
]

# ===================================================================
# Tab 6 — Delay Costs (single field, merged into operating tab)
# ===================================================================

_TAB6: list[InputField] = [
    _f("delay_annual_base", taxonomy_id="base_delay", input_tab="operating",
       sub_tab="delay-costs",
       yaml_section="05_delays", field_path="annual_base_delay_cost",
       label="Annual Base Delay Cost",
       help_text="Total direct out-of-pocket annual spend during the pre-construction/permitting period (legal, admin, PM, regulatory, etc.). Foregone congestion benefits during delay are modeled separately.",
       unit="$/year",
       input_type="currency", tier="first-glance", display_order=1),
]

# ===================================================================
# Tab 7 — Risk Costs (24 fields: 8 wildfire + 16 outage)
# ===================================================================

_TAB7: list[InputField] = [
    _f("wf_severity", taxonomy_id="wildfire_eac", input_tab="risk",
       yaml_section="06_wildfire_costs", field_path="wildfire.severity_per_event",
       label="Uninsured Severity ($/event)", help_text="Mean loss per wildfire event",
       unit="$/event", input_type="currency", condition="always_hidden", tier="working",
       display_order=1, sub_tab="wildfire-risk"),
    _f("wf_growth_rate", taxonomy_id="wildfire_eac", input_tab="risk",
       yaml_section="06_wildfire_costs", field_path="wildfire.risk_growth_rate",
       label="Risk Growth Rate", help_text="Annual increase in ignition probability",
       input_type="percent", condition="always_hidden", tier="working", display_order=2,
       validation={"min": 0, "max": 0.1, "step": 0.005, "pct": True},
       sub_tab="wildfire-risk"),
]
_TAB7.append(_f(
    "wf_base_ignition_rate", taxonomy_id="wildfire_eac", input_tab="risk",
    yaml_section="06_wildfire_costs", field_path="wildfire.base_ignition_rate",
    label="Base Ignition Rate", help_text="Line-level ignition rate for overhead baseline (events/mi/yr)",
    section_label="Base Ignition Rate",
    unit="events/mi/yr", condition="always_hidden", tier="working",
    display_order=10, validation={"min": 0}, sub_tab="wildfire-risk"))
for _ci, _ct in enumerate(WILDFIRE_CONSTRUCTION_TYPES):
    _TAB7.append(_f(
        f"wf_mult_{_ct}", taxonomy_id="wildfire_eac", input_tab="risk",
        yaml_section="06_wildfire_costs", field_path=f"wildfire.ignition_rate_multiplier.{_ct}",
        label=_ct.title(), help_text=f"Multiplier on base ignition rate for {_ct} (1.0 = overhead baseline)",
        section_label="Construction-Type Multipliers",
        condition="always_hidden", tier="working", display_order=20 + _ci,
        validation={"min": 0}, sub_tab="wildfire-risk"))

# Outage (16 fields) — all always_hidden, custom rendered
_TAB7 += [
    _f("out_growth_rate", taxonomy_id="outage_eac", input_tab="risk",
       yaml_section="07_outage_costs", field_path="outage.risk_growth_rate",
       label="Risk Growth Rate", help_text="Annual increase in outage rates over project lifetime",
       input_type="percent", condition="always_hidden", tier="working", display_order=1,
       validation={"min": 0, "max": 0.1, "step": 0.005, "pct": True},
       sub_tab="outage-risk"),
    _f("out_capacity_at_risk", taxonomy_id="outage_eac", input_tab="risk",
       yaml_section="07_outage_costs", field_path="outage.capacity_at_risk_factor",
       label="Capacity at risk (fraction of nameplate)", help_text="Fraction of capacity lost per outage. Default 'auto' = 1/N_poles from conductor table (1.0 for AC, 0.5 for DC bipole). Numeric override accepted.",
       input_type="number", condition="always_hidden", tier="working", display_order=3,
       validation={"min": 0, "max": 1, "step": 0.01},
       sub_tab="outage-risk"),
    _f("out_load_shed_fraction", taxonomy_id="outage_eac", input_tab="risk",
       yaml_section="07_outage_costs", field_path="outage.load_shed_fraction",
       label="Load-shed fraction (%)",
       help_text="Share of lost megawatts priced at the value of lost load. The rest uses the redispatch cost. Auto is 5% for AC and 80% for DC.",
       input_type="percent", condition="always_hidden", tier="working", display_order=2,
       validation={"min": 0, "max": 1, "step": 0.01, "pct": True},
       sub_tab="outage-risk"),
    _f("out_redispatch_cost", taxonomy_id="outage_eac", input_tab="risk",
       yaml_section="07_outage_costs", field_path="outage.redispatch_cost_per_mwh",
       label="Redispatch Cost", help_text="Congestion premium for rerouting power during outage ($/MWh). Default $20 from LBNL empirical data.",
       unit="$/MWh", input_type="currency", condition="always_hidden", tier="working",
       display_order=4, sub_tab="outage-risk"),
]
# VoLL tiers (10 tiers × 2 fields = 20) — moved to System Details (Economic Details)
# Fields are always_hidden; rendered via custom table in renderEconomicDetailsPanel()
_VOLL_TIER_LABELS = [
    "0-1h", "1-2h", "2-4h", "4-8h", "8-16h",
    "16-32h", "32-64h", "64h-7d", "7-30d", ">30d",
]
for _ti in range(10):
    _tier_label = _VOLL_TIER_LABELS[_ti]
    _TAB7.append(_f(
        f"out_voll_tier{_ti+1}_hours", taxonomy_id="outage_eac", input_tab="benefits",
        yaml_section="07_outage_costs", field_path=f"outage.value_of_lost_load.tiers[{_ti}].max_hours",
        label=f"Max Hours — {_tier_label}", help_text=f"Upper bound for {_tier_label} duration tier",
        section_label="Value of Lost Load (VoLL Tiers)",
        unit="hours", condition="always_hidden", tier="working", display_order=10 + _ti * 2,
        sub_tab="economic-details"))
    _TAB7.append(_f(
        f"out_voll_tier{_ti+1}_value", taxonomy_id="outage_eac", input_tab="benefits",
        yaml_section="07_outage_costs", field_path=f"outage.value_of_lost_load.tiers[{_ti}].value_per_mwh",
        label=f"Value — {_tier_label}", help_text=f"Cost of unserved energy in {_tier_label} tier",
        section_label="Value of Lost Load (VoLL Tiers)",
        unit="$/MWh", input_type="currency", condition="always_hidden", tier="working",
        display_order=11 + _ti * 2, sub_tab="economic-details"))

# Base outage duration (single scalar)
_TAB7.append(_f(
    "out_duration", taxonomy_id="outage_eac", input_tab="risk",
    yaml_section="07_outage_costs", field_path="outage.outage_duration",
    label="Base Outage Duration", help_text="Base outage duration (hrs/event); effective = base × construction multiplier",
    section_label="Outage Duration",
    unit="hrs/event", condition="always_hidden", tier="working",
    display_order=20, validation={"min": 0}, sub_tab="outage-risk"))

# Duration multiplier by construction type (3)
for _ci, _ct in enumerate(CONSTRUCTION_TYPES):
    _TAB7.append(_f(
        f"out_dur_mult_{_ct}", taxonomy_id="outage_eac", input_tab="risk",
        yaml_section="07_outage_costs", field_path=f"outage.outage_duration_multiplier.{_ct}",
        label=_ct.title(), help_text=f"Duration multiplier for {_ct} construction (1.0 = overhead baseline)",
        section_label="Duration Multipliers by Construction Type",
        condition="always_hidden", tier="working", display_order=30 + _ci,
        validation={"min": 0}, sub_tab="outage-risk"))

# Outage rates by construction type (3)
for _ci, _ct in enumerate(CONSTRUCTION_TYPES):
    _TAB7.append(_f(
        f"out_rate_{_ct}", taxonomy_id="outage_eac", input_tab="risk",
        yaml_section="07_outage_costs", field_path=f"outage.outage_rate.{_ct}",
        label=_ct.title(), help_text=f"Line-level outage frequency for {_ct} construction",
        section_label="Outage Frequency by Construction Type",
        unit="outages/mi/yr", condition="always_hidden", tier="working",
        display_order=40 + _ci, validation={"min": 0},
        sub_tab="outage-risk"))

# ===================================================================
# Tab 8 — Emissions (29 fields) + Energy Mix (32 fields)
# Most fields are condition="always_hidden" — rendered via custom tables, not renderTaxonomySections.
# compensation_percent is visible (no always_hidden) so the Emissions page can bind it.
# ===================================================================

_TAB8: list[InputField] = [
    _f("compensation_percent", taxonomy_id="emissions_comp", input_tab="emissions",
       yaml_section="16_emissions_reductions", field_path="emissions_reductions.compensation_percent",
       label="Loss Compensation (%)",
       help_text="Share of line losses replaced by additional generation. Default 100%. Stored as a decimal.",
       input_type="percent", tier="first-glance", display_order=1,
       validation={"min": 0, "max": 1, "step": 0.01, "pct": True},
       sub_tab="energy-emissions-emissions"),
]
# Societal costs (3)
for _pi, (_pk, _pl) in enumerate([("co2_cost_per_kg", "CO\u2082 Cost per kg"),
                                    ("sox_cost_per_kg", "SO\u2093 Cost per kg"),
                                    ("nox_cost_per_kg", "NO\u2093 Cost per kg")]):
    _TAB8.append(_f(
        f"societal_{_pk}", taxonomy_id="emissions_comp", input_tab="emissions",
        yaml_section="16_emissions_reductions",
        field_path=f"emissions_reductions.societal_costs_per_kg.{_pk}",
        label=_pl, help_text=f"Social cost per kg of {_pl.split()[0]} emissions (externality value)",
        unit="$/kg", input_type="currency", condition="always_hidden", tier="first-glance",
        display_order=2 + _pi, sub_tab="energy-emissions-emissions"))

_TAB8.append(_f(
    "co2_cost_annual_growth", taxonomy_id="emissions_comp", input_tab="emissions",
    yaml_section="16_emissions_reductions",
    field_path="emissions_reductions.societal_costs_per_kg.co2_cost_annual_growth",
    label="CO\u2082 Cost Annual Growth",
    help_text="Real annual escalation rate for CO\u2082 societal cost (Rennert et al. 2022). Default 2%/yr.",
    input_type="percent", condition="always_hidden", tier="working",
    display_order=6, sub_tab="energy-emissions-emissions",
    validation={"min": 0, "max": 0.1, "step": 0.005, "pct": True}))

# Emission intensities: 3 pollutants × 8 fuels = 24
_POLLUTANTS = [("co2", "CO\u2082"), ("sox", "SO\u2093"), ("nox", "NO\u2093")]
_int_order = 10
for _pk, _pl in _POLLUTANTS:
    for _fi, _fuel in enumerate(FUELS):
        _TAB8.append(_f(
            f"intensity_{_pk}_{_fuel}", taxonomy_id="emissions_comp", input_tab="emissions",
            yaml_section="16_emissions_reductions",
            field_path=f"emissions_reductions.emission_intensities.{_pk}_intensity_kg_per_mwh.{_fuel}",
            label=_fuel.replace("_", " ").title(),
            help_text=f"{_pl} emitted per MWh from {_fuel.replace('_', ' ')} generation",
            section_label=f"{_pl} Intensity (kg/MWh)",
            unit="kg/MWh", condition="always_hidden", tier="advanced", display_order=_int_order,
            sub_tab="energy-emissions-emissions"))
        _int_order += 1

# Grid mix (single-trajectory model): 8 fuels × 3 groups = 24 fields.
# initial = starting regional grid mix (%); rate_pre_cod/rate_post_cod = annual
# growth/decline rates without/with the line's influence.
for _group_key, _group_label in [
    ("initial", "Grid Mix — Initial (Year 0)"),
    ("rate_pre_cod", "Grid Mix — Rate Without Line (Pre-COD)"),
    ("rate_post_cod", "Grid Mix — Rate With Line (Post-COD)"),
]:
    _is_pct = _group_key == "initial"
    for _fi, _fuel in enumerate(FUELS):
        _TAB8.append(_f(
            f"grid_mix_{_group_key}_{_fuel}", taxonomy_id="avoided_emissions_benefit", input_tab="energy-mix",
            yaml_section="18_energy_source_mix",
            field_path=f"grid_mix.{_group_key}.{_fuel}",
            label="Percentage" if _is_pct else "Rate Of Change",
            help_text=(
                f"Share of {_fuel.replace('_', ' ')} in the regional grid at year 0 (must sum to 100)"
                if _is_pct else
                f"Annual growth/decline rate for {_fuel.replace('_', ' ')} share under this regime (decimal; mix renormalized yearly)"
            ),
            section_label=f"{_group_label} — {_fuel.replace('_', ' ').title()}",
            input_type="fuel_mix_row" if _is_pct else "number",
            condition="always_hidden", tier="working",
            display_order=_fi + 1, sub_tab="energy-emissions-energy"))

# ===================================================================
# Tab 9 — Benefits (24 fields)
# ===================================================================

def _cc_fields(prefix: str, label_prefix: str, yaml_root: str) -> list[InputField]:
    """Generate congestion constraint fields for greenfield or reconductoring."""
    fields: list[InputField] = []
    _has_flow = "greenfield" in yaml_root
    _base = "17_congestion_reductions"
    spread_when = (
        "greenfield_margin" if _has_flow else "reconductoring_or_rebuild_and_margin"
    )
    # Congestion fields stay hidden here; the benefits panel renders them.
    if _has_flow:
        fields.append(_f(
            f"{prefix}_flow_factor", taxonomy_id="congestion_benefit", input_tab="benefits",
            yaml_section=_base, field_path=f"{yaml_root}.constraints.flow_factor",
            label="Flow Factor", help_text="Deliverability to targeted constraint [0,1]",
            input_type="percent", condition="always_hidden", tier="first-glance", display_order=1,
            validation={"min": 0, "max": 1, "step": 0.01, "nullable_number": True},
            required_when="greenfield_margin", required_stage="before_route",
            sub_tab="system-constraints"))
    fields += [
        _f(f"{prefix}_avg_exceedance", taxonomy_id="congestion_benefit", input_tab="benefits",
           yaml_section=_base, field_path=f"{yaml_root}.constraints.average_exceedance",
           label="Average exceedance (MW)",
           help_text="Empty means equal to the effective capacity, so the minimum does not bind. A supplied value is at least 0.",
           unit="MW", condition="always_hidden", tier="first-glance", display_order=3,
           validation={"min": 0, "nullable_number": True},
           sub_tab="system-constraints"),
        _f(f"{prefix}_cong_price", taxonomy_id="congestion_benefit", input_tab="benefits",
           yaml_section=_base, field_path=f"{yaml_root}.prices.average_congestion_price",
           label="Congestion spread ($/MWh, mean over all 8,760 hours)",
           help_text="Mean congestion spread over all 8,760 hours. A negative spread is allowed.",
           unit="$/MWh", input_type="currency", condition="always_hidden",
           tier="first-glance", display_order=4,
           validation={"nullable_number": True},
           required_when=spread_when, required_stage="after_route",
           sub_tab="system-constraints"),
    ]
    return fields

_TAB9: list[InputField] = (
    _cc_fields("gf", "Greenfield", "greenfield_congestion_reductions")
    + _cc_fields("rc", "Reconductoring", "incremental_congestion_reductions")
    + [
        _f("applicability_gate", taxonomy_id="capacity_value_benefit", input_tab="benefits",
           sub_tab="system-constraints", condition="always_hidden",
           yaml_section="20_capacity_value", field_path="applicability_gate",
           label="Receiving region is capacity-short",
           help_text="Capacity value stays zero unless this is on and credit and price are both positive.",
           input_type="toggle", section_label="Capacity Value",
           tier="working", display_order=5),
        _f("capacity_credit", taxonomy_id="capacity_value_benefit", input_tab="benefits",
           sub_tab="system-constraints", condition="always_hidden",
           yaml_section="20_capacity_value", field_path="capacity_credit",
           label="Capacity credit (%)",
           help_text="ELCC share of effective transfer capacity. Default 0 (off).",
           input_type="percent", section_label="Capacity Value",
           tier="working", display_order=6,
           validation={"min": 0, "max": 1, "step": 0.01, "pct": True}),
        _f("capacity_price", taxonomy_id="capacity_value_benefit", input_tab="benefits",
           sub_tab="system-constraints", condition="always_hidden",
           yaml_section="20_capacity_value", field_path="capacity_price",
           label="Capacity price ($/MW-year)",
           help_text="Net CONE or clearing price. Default 0.",
           unit="$/MW-year", input_type="currency", section_label="Capacity Value",
           tier="working", display_order=7,
           validation={"min": 0}),
    ]
)

# ===================================================================
# Combined registry
# ===================================================================

_ALL_FIELDS = _TAB1 + _TAB2 + _TAB3 + _TAB4 + _TAB5 + _TAB6 + _TAB7 + _TAB8 + _TAB9

INPUT_METADATA: dict[str, InputField] = {f.id: f for f in _ALL_FIELDS}


@lru_cache(maxsize=1)
def input_metadata_to_dict() -> list[dict]:
    """Serialize all input metadata entries for the browser."""
    from dataclasses import asdict
    return [asdict(f) for f in _ALL_FIELDS]
