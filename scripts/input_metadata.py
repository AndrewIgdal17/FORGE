"""CTCC input field metadata — one entry per input field.

Bridges taxonomy items to form controls. Each entry declares which
taxonomy item a field feeds, which tab it appears on, its label,
tooltip, input type, validation, condition, and display ordering.

Phase 4 deliverable. Canonical source alongside taxonomy.py.
"""

from __future__ import annotations

from dataclasses import dataclass, field as dc_field
from functools import lru_cache
from typing import Any, Literal

InputType = Literal[
    "number", "currency", "percent", "toggle", "dropdown",
    "dynamic_dropdown", "year", "text", "fuel_mix_row",
]
Tier = Literal["first-glance", "working", "advanced"]
InputCondition = Literal["dc_only", "reconductoring_only", "always_hidden"]

TERRAINS = (
    "forested", "scrubbed_flat", "wetland", "farmland",
    "desert_barren", "urban", "rolling_hills", "mountain", "subsea",
)
FUELS = ("coal", "oil", "natural_gas", "solar", "wind", "hydro", "nuclear", "other")
CONSTRUCTION_TYPES = ("overhead", "underground", "subsea")


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


def _f(id: str, **kwargs: Any) -> InputField:
    return InputField(id=id, **kwargs)


def _terrain_label(t: str) -> str:
    return t.replace("_", " ").title()


# ===================================================================
# Tab 1 — Project (20 fields)
# ===================================================================

_TAB1: list[InputField] = [
    _f("project_name", taxonomy_id="project_identity", input_tab="project-technical",
       yaml_section="01_project_technical_details", field_path="project.name",
       label="Name", help_text="Unique identifier for this project scenario",
       input_type="text", tier="first-glance", display_order=1,
       validation={"required": True}, sub_tab="identity", condition="always_hidden"),
    _f("construction_type", taxonomy_id="project_technology", input_tab="project-technical",
       yaml_section="01_project_technical_details", field_path="project.construction_type",
       label="Construction Type", help_text="Overhead, underground, or subsea transmission",
       input_type="dropdown", tier="first-glance", display_order=1,
       validation={"required": True, "options": ["Overhead", "Underground Direct-Buried", "Underground Tunnel", "Subsea"]},
       sub_tab="technology"),
    _f("ac_dc", taxonomy_id="project_technology", input_tab="project-technical",
       yaml_section="01_project_technical_details", field_path="project.ac_dc",
       label="AC/DC", help_text="Alternating current or direct current transmission",
       input_type="dropdown", tier="first-glance", display_order=2,
       validation={"required": True, "options": ["AC", "DC"]},
       sub_tab="technology"),
    _f("capacity_mw", taxonomy_id="project_technology", input_tab="project-technical",
       yaml_section="01_project_technical_details", field_path="project.capacity_mw",
       label="Capacity MW", help_text="Nameplate transfer capacity (C_new); feeds capacity relief and line loss calculations", unit="MW",
       input_type="dynamic_dropdown", tier="first-glance", display_order=3,
       validation={"required": True, "dependsOn": "01_project_technical_details.project.ac_dc",
                   "optionSets": {"AC": [140, 329, 394, 460, 657, 1792, 2598, 6625],
                                  "DC": [500, 1500, 2000, 2400, 6000]}, "suffix": " MW"},
       sub_tab="technology"),
    _f("conductor_type", taxonomy_id="project_technology", input_tab="project-technical",
       yaml_section="01_project_technical_details", field_path="project.conductor_type",
       label="Conductor Type", help_text="Determines resistance, cost per mile, and O&M rates",
       input_type="dynamic_dropdown", tier="first-glance", display_order=4,
       validation={"required": True,
                   "dependsOn": "01_project_technical_details.project.construction_type",
                   "optionSets": {
                       "Overhead": ["Standard Aluminum Conductor", "Advanced Aluminum Conductor"],
                       "Underground Direct-Buried": ["Underground Copper Conductor"],
                       "Underground Tunnel": ["Underground Copper Conductor"],
                       "Subsea": ["Subsea Copper Conductor"],
                   }},
       sub_tab="conductor-details"),
    _f("number_of_converters", taxonomy_id="project_technology", input_tab="project-technical",
       yaml_section="01_project_technical_details", field_path="project.number_of_converters",
       label="Number Of Converters", help_text="Number of converter stations (DC only)",
       input_type="dropdown", condition="dc_only", tier="first-glance", display_order=5,
       validation={"options": [0, 1, 2]}, sub_tab="converter-details"),
    _f("converter_type", taxonomy_id="project_technology", input_tab="project-technical",
       yaml_section="01_project_technical_details", field_path="project.converter_type",
       label="Converter Type", help_text="LCC or VSC converter station type",
       input_type="dynamic_dropdown", condition="dc_only", tier="first-glance", display_order=6,
       validation={"dependsOn": "01_project_technical_details.project.ac_dc",
                   "optionSets": {
                       "AC": ["NA"],
                       "DC": ["LCC Converter", "VSC Converter"],
                   }},
       sub_tab="converter-details"),
    _f("converter_loss_pct", taxonomy_id="project_technology", input_tab="project-technical",
       yaml_section="01_project_technical_details", field_path="project.converter_loss_percentage",
       label="Converter Loss Percentage", help_text="Loss per converter station (0.75% LCC, 1.0% VSC)", unit="%",
       input_type="percent", condition="always_hidden", tier="first-glance", display_order=7,
       sub_tab="technology"),
    _f("reconductoring", taxonomy_id="project_technology", input_tab="project-technical",
       yaml_section="01_project_technical_details", field_path="project.reconductoring",
       label="Reconductoring Project", help_text="Upgrade existing conductors; zeroes structure cost, relief = C_new minus C_old",
       input_type="toggle", tier="first-glance", display_order=8,
       sub_tab="technology"),
    _f("uses_existing_row", taxonomy_id="project_technology", input_tab="project-technical",
       yaml_section="01_project_technical_details", field_path="project.uses_existing_row",
       label="Project Uses Existing ROW", help_text="Zeroes acquisition/holding, includes delay in rent",
       input_type="toggle", tier="first-glance", display_order=9,
       sub_tab="rights-of-way"),
    _f("old_capacity_mw", taxonomy_id="project_technology", input_tab="project-technical",
       yaml_section="01_project_technical_details", field_path="project.old_capacity_mw",
       label="Old Capacity MW", help_text="Existing line capacity (C_old)", unit="MW",
       input_type="dynamic_dropdown", condition="reconductoring_only", tier="first-glance", display_order=11,
       validation={"dependsOn": "01_project_technical_details.project.old_ac_dc",
                   "optionSets": {"AC": [140, 329, 394, 460, 657, 1792, 2598, 6625],
                                  "DC": [500, 1500, 2000, 2400, 6000]}, "suffix": " MW"},
       sub_tab="technology"),
    _f("old_conductor_type", taxonomy_id="project_technology", input_tab="project-technical",
       yaml_section="01_project_technical_details", field_path="project.old_conductor_type",
       label="Old Conductor Type", help_text="Original conductor for reconductoring cost comparison",
       input_type="dynamic_dropdown", condition="reconductoring_only",
       tier="first-glance", display_order=12,
       validation={"dependsOn": "01_project_technical_details.project.construction_type",
                   "optionSets": {
                       "Overhead": ["Standard Aluminum Conductor", "Advanced Aluminum Conductor"],
                       "Underground Direct-Buried": ["Underground Copper Conductor"],
                       "Underground Tunnel": ["Underground Copper Conductor"],
                       "Subsea": ["Subsea Copper Conductor"],
                   },
                   "allowBlank": True},
       sub_tab="conductor-details"),
    _f("old_ac_dc", taxonomy_id="project_technology", input_tab="project-technical",
       yaml_section="01_project_technical_details", field_path="project.old_ac_dc",
       label="Old AC/DC", help_text="Original AC/DC type for reconductoring comparison",
       input_type="dropdown", condition="reconductoring_only",
       tier="first-glance", display_order=10, validation={"options": ["", "AC", "DC"]},
       sub_tab="technology"),
    _f("old_converter_type", taxonomy_id="project_technology", input_tab="project-technical",
       yaml_section="01_project_technical_details", field_path="project.old_converter_type",
       label="Old Converter Type", help_text="Original converter type for old DC line (used for reconductoring cost lookup)",
       input_type="dynamic_dropdown", condition="old_dc_only",
       tier="first-glance", display_order=13,
       validation={"dependsOn": "01_project_technical_details.project.old_ac_dc",
                   "optionSets": {"AC": [], "DC": ["LCC Converter", "VSC Converter"]}},
       sub_tab="converter-details"),
    _f("line_utilization", taxonomy_id="project_utilization", input_tab="project-technical",
       yaml_section="01_project_technical_details", field_path="project.line_utilization",
       label="Line Utilization", help_text="Fraction of nameplate capacity used on average",
       input_type="percent", tier="first-glance", display_order=1,
       validation={"min": 0, "max": 1, "step": 0.01, "pct": True},
       sub_tab="technology"),
    _f("baseline_price_mwh", taxonomy_id="project_utilization", input_tab="benefits",
       yaml_section="01_project_technical_details", field_path="project.value_of_load_per_mwh",
       label="Value of Load per MWh", help_text="Demand-side marginal value of delivered energy; values line losses and delivered energy benefit", unit="$/MWh",
       input_type="currency", condition="always_hidden", tier="first-glance", display_order=2,
       sub_tab="economic-details"),
    _f("construction_years", taxonomy_id="project_timing", input_tab="project-technical",
       yaml_section="01_project_technical_details", field_path="timeline.construction_years",
       label="Construction Years", help_text="Construction duration; affects AFUDC compounding and PV discounting",
       unit="years", tier="first-glance", display_order=1,
       validation={"required": True, "min": 1}, sub_tab="timeline"),
    _f("delay_years", taxonomy_id="project_timing", input_tab="project-technical",
       yaml_section="01_project_technical_details", field_path="timeline.delay_years",
       label="Delay Years", help_text="Pre-construction delay (permitting); drives delay costs and AFUDC timing",
       unit="years", tier="first-glance", display_order=2,
       validation={"required": True, "min": 0}, sub_tab="timeline"),
    _f("project_lifetime", taxonomy_id="project_timing", input_tab="project-technical",
       yaml_section="01_project_technical_details", field_path="timeline.project_lifetime",
       label="Project Lifetime", help_text="Operating years after COD; annual costs and benefits accrue over this period",
       unit="years", tier="first-glance", display_order=3,
       validation={"required": True, "min": 1}, sub_tab="timeline"),
    _f("greenfield_cmp_capacity", taxonomy_id="project_technology", input_tab="project-technical",
       yaml_section="01_project_technical_details", field_path="project.greenfield_comparison_capacity_mw",
       label="Greenfield Comparison Capacity MW", condition="always_hidden", display_order=99,
       sub_tab="technology"),
    _f("greenfield_cmp_conductor", taxonomy_id="project_technology", input_tab="project-technical",
       yaml_section="01_project_technical_details", field_path="project.greenfield_comparison_conductor_type",
       label="Greenfield Comparison Conductor Type", condition="always_hidden", display_order=100,
       sub_tab="technology"),
]

# ===================================================================
# Routing fields (78: 18 terrain + 60 ROW zones) — UI: Project Technical Details → Routing → Terrain Mix / Rights of Way
# ===================================================================

_TAB2: list[InputField] = []
for _i, _t in enumerate(TERRAINS):
    _TAB2.append(_f(
        f"terrain_miles_{_t}", taxonomy_id="route_terrain_miles", input_tab="project-technical",
        yaml_section="02_project_physical_details", field_path=f"terrain.terrain_miles.{_t}",
        label=_terrain_label(_t), help_text=f"Miles through {_terrain_label(_t).lower()} terrain",
        unit="miles", tier="first-glance", display_order=_i + 1, validation={"min": 0},
        sub_tab="terrain-mix",
    ))
for _i, _t in enumerate(TERRAINS):
    _TAB2.append(_f(
        f"terrain_mult_{_t}", taxonomy_id="route_terrain_multipliers", input_tab="project-technical",
        yaml_section="02_project_physical_details", field_path=f"terrain.terrain_multipliers.{_t}",
        label=_terrain_label(_t), help_text=f"Cost multiplier for {_terrain_label(_t).lower()} terrain",
        tier="advanced", display_order=_i + 1, validation={"min": 0},
        sub_tab="terrain-mix",
    ))

# ===================================================================
# Tab 3 — Financial (42 fields)
# ===================================================================

_TAB3: list[InputField] = [
    # --- Core rates (Rates sub-tab, custom-rendered) ---
    _f("base_year", taxonomy_id="financial_rates", input_tab="financial",
       sub_tab="rates", condition="always_hidden",
       yaml_section="03_financing", field_path="financial.base_year",
       label="Base Year", help_text="Reference year for all present values (base-year dollars)",
       input_type="dropdown", tier="first-glance", display_order=1,
       validation={"options": list(range(2020, 2051))}),
    _f("inflation_rate", taxonomy_id="financial_rates", input_tab="financial",
       sub_tab="rates", condition="always_hidden",
       yaml_section="03_financing", field_path="financial.inflation_rate",
       label="Inflation Rate", help_text="Annual inflation rate for Fisher equation",
       input_type="percent", tier="first-glance", display_order=2,
       validation={"min": 0, "max": 0.2, "step": 0.005, "pct": True}),
    _f("wacc_nominal", taxonomy_id="financial_rates", input_tab="financial",
       sub_tab="rates", condition="always_hidden",
       yaml_section="03_financing", field_path="financial.wacc_nominal",
       label="WACC Nominal", help_text="Nominal WACC; real WACC derived via Fisher equation; also used as AFUDC rate",
       input_type="percent", tier="first-glance", display_order=3,
       validation={"min": 0, "max": 0.2, "step": 0.005, "pct": True}),
    _f("social_discount_rate", taxonomy_id="financial_rates", input_tab="financial",
       sub_tab="rates", condition="always_hidden",
       yaml_section="03_financing", field_path="financial.social_discount_rate",
       label="Social Discount Rate", help_text="Discount rate for social externalities (risk, emissions)",
       input_type="percent", tier="first-glance", display_order=4,
       validation={"min": 0, "max": 0.1, "step": 0.005, "pct": True}),
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
    # --- Revenue (Rates sub-tab, custom-rendered) ---
    _f("revenue_enabled", taxonomy_id="financial_revenue_config", input_tab="financial",
       sub_tab="rates", condition="always_hidden",
       yaml_section="03_financing", field_path="financial.revenue.rate_based.enabled",
       label="Revenue Requirement", help_text="Enable rate-based revenue calculation",
       input_type="toggle", tier="working", display_order=1),
    _f("allowed_return_rate", taxonomy_id="financial_revenue_config", input_tab="financial",
       sub_tab="rates", condition="always_hidden",
       yaml_section="03_financing", field_path="financial.revenue.rate_based.allowed_return_rate",
       label="Allowed Return Rate", help_text="Annual return on rate base",
       input_type="percent", tier="working", display_order=2,
       validation={"min": 0, "max": 0.2, "step": 0.005, "pct": True}),
    # --- AFUDC (AFUDC sub-tab, custom-rendered) ---
    _f("apply_afudc", taxonomy_id="financial_afudc", input_tab="financial",
       sub_tab="afudc", condition="always_hidden",
       yaml_section="03_financing", field_path="financial.afudc.apply_afudc",
       label="Apply AFUDC", help_text="Toggle AFUDC capitalization",
       input_type="toggle", tier="advanced", display_order=1),
    _f("delay_period_active_work", taxonomy_id="financial_afudc", input_tab="financial",
       sub_tab="afudc", condition="always_hidden",
       yaml_section="03_financing", field_path="financial.afudc.delay_period_active_work",
       label="Delay Period Active Work", help_text="AFUDC accrues during delay if active work continues",
       input_type="toggle", tier="advanced", display_order=2),
]

# --- Cost timing patterns (27 fields: 9 categories × 3 fields) ---
_TIMING_CATEGORIES = [
    ("build_costs", "Build Costs"), ("row_acquisition", "ROW Acquisition"),
    ("row_holding", "ROW Holding"), ("row_rent", "ROW Rent"),
    ("environmental_mitigation_base", "Environmental Mitigation Base"),
    ("environmental_mitigation_credits", "Environmental Mitigation Credits"),
    ("delay_costs", "Delay Costs"), ("operations_and_maintenance", "O&M"),
    ("construction_insurance", "Construction Insurance"),
]
for _ci, (_cat, _cat_label) in enumerate(_TIMING_CATEGORIES):
    _base = f"cost_timing_patterns.{_cat}"
    _TAB3.append(_f(
        f"timing_{_cat}_delay", taxonomy_id="financial_timing_patterns", input_tab="financial",
        sub_tab="afudc", condition="always_hidden",
        yaml_section="19_cost_timing_patterns", field_path=f"{_base}.during_delay",
        label="During Delay", help_text=f"Fraction of {_cat_label} cost incurred during delay period",
        section_label=_cat_label, input_type="percent",
        tier="advanced", display_order=_ci * 3 + 1,
        validation={"min": 0, "max": 1, "step": 0.01, "pct": True}))
    _TAB3.append(_f(
        f"timing_{_cat}_construction", taxonomy_id="financial_timing_patterns", input_tab="financial",
        sub_tab="afudc", condition="always_hidden",
        yaml_section="19_cost_timing_patterns", field_path=f"{_base}.during_construction",
        label="During Construction", help_text=f"Fraction of {_cat_label} cost incurred during construction",
        section_label=_cat_label, input_type="percent",
        tier="advanced", display_order=_ci * 3 + 2,
        validation={"min": 0, "max": 1, "step": 0.01, "pct": True}))
    _TAB3.append(_f(
        f"timing_{_cat}_afudc", taxonomy_id="financial_timing_patterns", input_tab="financial",
        sub_tab="afudc", condition="always_hidden",
        yaml_section="19_cost_timing_patterns", field_path=f"{_base}.afudc_eligible",
        label="AFUDC Eligible", help_text=f"Whether {_cat_label} costs are AFUDC-eligible (compounded to COD)",
        section_label=_cat_label, input_type="toggle",
        tier="advanced", display_order=_ci * 3 + 3))

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
            f"row_{_zn}_{_fk}", taxonomy_id=_tid, input_tab="project-technical",
            yaml_section="11_project_row_details", field_path=f"right_of_way.{_zn}.{_fk}",
            label=f"{_zl} {_fl}", help_text=_fh, unit=_fu,
            input_type="currency" if "cost" in _fk.lower() else "number",
            tier="first-glance", display_order=(_z - 1) * 4 + _fi + 1,
            section_label=_zl, validation={"min": 0},
            sub_tab="rights-of-way"))

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

# Base mitigation: overhead (9), underground_direct_buried (9), underground_tunnel (11), subsea (2)
_ENV_CT = [
    ("overhead", "Overhead", TERRAINS),
    ("underground_direct_buried", "Underground Direct Buried", TERRAINS),
    ("underground_tunnel", "Underground Tunnel",
     TERRAINS + ("linear_corridor_default", "shaft_site_default")),
    ("subsea", "Subsea", ("seabed_corridor_default", "landfall_default")),
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
        field_path=f"environmental_mitigation.habitat_credit_cost_per_acre.{_terrain}",
        label=f"Habitat — {_terrain_label(_terrain)}",
        help_text=f"Per-acre habitat credit cost for {_terrain_label(_terrain).lower()} terrain",
        section_label="Credit Costs",
        unit="$/acre", input_type="currency", tier="working", display_order=_env_order,
        sub_tab="credits"))
    _env_order += 1

# ===================================================================
# Tab 5 — Operational Costs (40 fields: 4 insurance + 36 veg mgmt)
# ===================================================================

_TAB5: list[InputField] = [
    _f("insurance_premium_rate", taxonomy_id="insurance", input_tab="operational",
       yaml_section="04_insurance", field_path="insurance.premium_rate",
       label="Premium Rate", help_text="Annual insurance premium as % of insurable value",
       input_type="percent", condition="always_hidden", tier="working", display_order=1,
       validation={"min": 0, "max": 1, "step": 0.001, "pct": True},
       sub_tab="operational-insurance"),
    _f("insurable_conductors", taxonomy_id="insurance", input_tab="operational",
       yaml_section="04_insurance", field_path="insurance.insurable_components.conductors",
       label="Conductors", help_text="Include conductor costs in insurable value",
       input_type="toggle", condition="always_hidden", tier="working", display_order=2,
       sub_tab="operational-insurance"),
    _f("insurable_structures", taxonomy_id="insurance", input_tab="operational",
       yaml_section="04_insurance", field_path="insurance.insurable_components.structures",
       label="Structures", help_text="Include structure costs in insurable value",
       input_type="toggle", condition="always_hidden", tier="working", display_order=3,
       sub_tab="operational-insurance"),
    _f("insurable_converters", taxonomy_id="insurance", input_tab="operational",
       yaml_section="04_insurance", field_path="insurance.insurable_components.converters",
       label="Converters", help_text="Include converter costs in insurable value",
       input_type="toggle", condition="always_hidden", tier="working", display_order=4,
       sub_tab="operational-insurance"),
]

# Vegetation management: 4 construction types × 9 terrains = 36
_VEG_CT = [
    ("Overhead", "Overhead"), ("Underground Direct Buried", "Underground Direct Buried"),
    ("Underground Tunnel", "Underground Tunnel"), ("Subsea", "Subsea"),
]
_veg_order = 1
for _ct_key, _ct_label in _VEG_CT:
    for _t in TERRAINS:
        _TAB5.append(_f(
            f"veg_{_ct_key.lower().replace(' ', '_')}_{_t}", taxonomy_id="oandm",
            input_tab="operational", yaml_section="12_project_om_vegetation_management",
            field_path=f"vegetation_management_om_costs.{_ct_key}.{_t}",
            label=_terrain_label(_t), help_text=f"Annual vegetation management cost for {_terrain_label(_t).lower()} terrain",
            section_label=f"Vegetation Mgmt — {_ct_label}",
            unit="$/mile/year", input_type="currency", condition="always_hidden",
            tier="first-glance", display_order=_veg_order, validation={"min": 0},
            sub_tab="vegetation-management"))
        _veg_order += 1

# ===================================================================
# Tab 6 — Delay Costs (8 fields)
# ===================================================================

_DELAY_CATS = [
    ("legal", "Legal"), ("admin", "Admin"), ("labor", "Labor"),
    ("material_and_equipment", "Material And Equipment"),
    ("regulatory", "Regulatory"), ("public_relations", "Public Relations"),
    ("project_management", "Project Management"), ("miscellaneous", "Miscellaneous"),
]
_TAB6: list[InputField] = [
    _f(f"delay_{k}", taxonomy_id="base_delay", input_tab="delay-costs",
       yaml_section="05_delays", field_path=f"annual_delay_costs.{k}",
       label=lab, help_text=f"Annual {lab.lower()} costs during delay period", unit="$/year",
       input_type="currency", tier="first-glance", display_order=i + 1)
    for i, (k, lab) in enumerate(_DELAY_CATS)
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
    _f("wf_dr_source", taxonomy_id="wildfire_eac", input_tab="risk",
       yaml_section="06_wildfire_costs", field_path="wildfire.discount_rate_source",
       label="Discount Rate Source", input_type="dropdown", condition="always_hidden",
       display_order=3, validation={"options": ["social", "wacc_real", "custom"]},
       sub_tab="wildfire-risk"),
    _f("wf_dr_custom", taxonomy_id="wildfire_eac", input_tab="risk",
       yaml_section="06_wildfire_costs", field_path="wildfire.discount_rate_custom",
       label="Discount Rate Custom", condition="always_hidden", display_order=4,
       sub_tab="wildfire-risk"),
]
_TAB7.append(_f(
    "wf_base_ignition_rate", taxonomy_id="wildfire_eac", input_tab="risk",
    yaml_section="06_wildfire_costs", field_path="wildfire.base_ignition_rate",
    label="Base Ignition Rate", help_text="Line-level ignition rate for overhead baseline (events/mi/yr)",
    section_label="Base Ignition Rate",
    unit="events/mi/yr", condition="always_hidden", tier="working",
    display_order=10, validation={"min": 0}, sub_tab="wildfire-risk"))
for _ci, _ct in enumerate(CONSTRUCTION_TYPES):
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
    _f("out_dr_type", taxonomy_id="outage_eac", input_tab="risk",
       yaml_section="07_outage_costs", field_path="outage.discount_rate_type",
       label="Discount Rate Type", input_type="dropdown", condition="always_hidden",
       display_order=2, validation={"options": ["social", "wacc_real"]},
       sub_tab="outage-risk"),
    _f("out_capacity_at_risk", taxonomy_id="outage_eac", input_tab="risk",
       yaml_section="07_outage_costs", field_path="outage.capacity_at_risk_factor",
       label="Capacity at Risk (\u03C6)", help_text="Fraction of capacity lost per outage. Default 'auto' = 1/N_poles from conductor table (1.0 for AC, 0.5 for DC bipole). Numeric override accepted.",
       input_type="percent", condition="always_hidden", tier="working", display_order=3,
       validation={"min": 0, "max": 1, "step": 0.01},
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
# Tab 8 — Energy and Emissions (60 fields: 28 reductions + 32 energy mix)
# All fields are condition="always_hidden" — rendered via custom tables, not renderTaxonomySections.
# ===================================================================

_TAB8: list[InputField] = [
    _f("compensation_percent", taxonomy_id="emissions_comp", input_tab="emissions",
       yaml_section="16_emissions_reductions", field_path="emissions_reductions.compensation_percent",
       label="Loss Compensation Rate (\u03B1)", help_text="Fraction of line losses compensated by generation",
       input_type="percent", condition="always_hidden", tier="first-glance", display_order=1,
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

# Energy source mix: 8 fuels × 2 fields × 2 instances = 32
for _instance, _inst_label, _yaml_key in [
    ("proj", "Energy Source Mix (Project Path)", "energy_source_mix"),
    ("cf", "Counterfactual Energy Source Mix (No-Line)", "counterfactual_energy_source_mix"),
]:
    for _fi, _fuel in enumerate(FUELS):
        _TAB8.append(_f(
            f"mix_{_instance}_{_fuel}_pct", taxonomy_id="emissions_fac", input_tab="emissions",
            yaml_section="18_energy_source_mix",
            field_path=f"{_yaml_key}.{_fuel}.percentage",
            label="Percentage", help_text=f"Share of {_fuel.replace('_', ' ')} in this generation mix (must sum to 100)",
            section_label=f"{_inst_label} — {_fuel.replace('_', ' ').title()}",
            input_type="fuel_mix_row", condition="always_hidden", tier="working",
            display_order=_fi * 2 + 1, sub_tab="energy-emissions-energy"))
        _TAB8.append(_f(
            f"mix_{_instance}_{_fuel}_rate", taxonomy_id="emissions_fac", input_tab="emissions",
            yaml_section="18_energy_source_mix",
            field_path=f"{_yaml_key}.{_fuel}.rate_of_change",
            label="Rate Of Change", help_text=f"Annual growth/decline rate for {_fuel.replace('_', ' ')} share (decimal; mix renormalized yearly)",
            section_label=f"{_inst_label} — {_fuel.replace('_', ' ').title()}",
            condition="always_hidden", tier="working", display_order=_fi * 2 + 2,
            sub_tab="energy-emissions-energy"))

# ===================================================================
# Tab 9 — Benefits (24 fields)
# ===================================================================

def _cc_fields(prefix: str, label_prefix: str, yaml_root: str) -> list[InputField]:
    """Generate congestion/curtailment fields for greenfield or reconductoring."""
    fields: list[InputField] = []
    _has_flow = "greenfield" in yaml_root
    _base = f"17_congestion_curtailment_reductions"
    # All fields are always_hidden — rendered via custom panels in renderConstraintsPanel()
    if _has_flow:
        fields.append(_f(
            f"{prefix}_flow_factor", taxonomy_id="congestion_benefit", input_tab="benefits",
            yaml_section=_base, field_path=f"{yaml_root}.congestion.constraints.flow_factor",
            label="Flow Factor", help_text="Deliverability to targeted constraint [0,1]",
            input_type="percent", condition="always_hidden", tier="first-glance", display_order=1,
            validation={"min": 0, "max": 1, "step": 0.01},
            sub_tab="system-constraints"))
    fields += [
        _f(f"{prefix}_binding_hours", taxonomy_id="congestion_benefit", input_tab="benefits",
           yaml_section=_base, field_path=f"{yaml_root}.congestion.constraints.binding_hours",
           label="Binding Hours", help_text="Hours/year the targeted constraint is binding",
           unit="hrs/year", condition="always_hidden", tier="first-glance", display_order=2,
           sub_tab="system-constraints"),
        _f(f"{prefix}_avg_exceedance", taxonomy_id="congestion_benefit", input_tab="benefits",
           yaml_section=_base, field_path=f"{yaml_root}.congestion.constraints.average_exceedance",
           label="Average Exceedance", help_text="Average MW exceedance during binding hours",
           unit="MW", condition="always_hidden", tier="first-glance", display_order=3,
           sub_tab="system-constraints"),
        _f(f"{prefix}_near_binding_hours", taxonomy_id="congestion_benefit", input_tab="benefits",
           yaml_section=_base, field_path=f"{yaml_root}.congestion.constraints.near_binding_hours",
           label="Near Binding Hours", condition="always_hidden", display_order=90,
           sub_tab="system-constraints"),
        _f(f"{prefix}_near_avg_exceedance", taxonomy_id="congestion_benefit", input_tab="benefits",
           yaml_section=_base, field_path=f"{yaml_root}.congestion.constraints.near_average_exceedance",
           label="Near Average Exceedance", condition="always_hidden", display_order=91,
           sub_tab="system-constraints"),
        _f(f"{prefix}_near_relief_factor", taxonomy_id="congestion_benefit", input_tab="benefits",
           yaml_section=_base, field_path=f"{yaml_root}.congestion.constraints.near_binding_relief_factor",
           label="Near Binding Relief Factor", condition="always_hidden", display_order=92,
           sub_tab="system-constraints"),
        _f(f"{prefix}_cong_price", taxonomy_id="congestion_benefit", input_tab="benefits",
           yaml_section=_base, field_path=f"{yaml_root}.congestion.costs.average_congestion_price",
           label="Average Congestion Price", help_text="Marginal congestion cost during binding hours; monetizes relief",
           unit="$/MWh", input_type="currency", condition="always_hidden",
           tier="first-glance", display_order=4,
           sub_tab="system-constraints"),
        _f(f"{prefix}_curt_hours", taxonomy_id="curtailment_benefit", input_tab="benefits",
           yaml_section=_base, field_path=f"{yaml_root}.curtailment.curtailment_hours_total",
           label="Curtailment Hours Total", help_text="Hours/year of renewable curtailment on this constraint",
           unit="hrs/year", condition="always_hidden", tier="first-glance", display_order=6,
           sub_tab="system-constraints"),
        _f(f"{prefix}_curt_mw", taxonomy_id="curtailment_benefit", input_tab="benefits",
           yaml_section=_base, field_path=f"{yaml_root}.curtailment.average_curtailment_mw",
           label="Average Curtailment MW", help_text="Average curtailed MW during curtailment hours",
           unit="MW", condition="always_hidden", tier="first-glance", display_order=7,
           sub_tab="system-constraints"),
        _f(f"{prefix}_curt_price", taxonomy_id="curtailment_benefit", input_tab="benefits",
           yaml_section=_base, field_path=f"{yaml_root}.curtailment.average_curtailment_price",
           label="Average Curtailment Price", help_text="Value per MWh of curtailed energy (PPA proxy / avoided cost)",
           unit="$/MWh", input_type="currency", condition="always_hidden",
           tier="first-glance", display_order=8,
           sub_tab="system-constraints"),
    ]
    if "reconductoring" in yaml_root:
        fields.append(_f(
            f"{prefix}_hot_hour_weights", taxonomy_id="congestion_benefit", input_tab="benefits",
            yaml_section=_base, field_path=f"{yaml_root}.congestion.constraints.hot_hour_weights",
            label="Hot Hour Weights", help_text="Fraction of binding hours at or near maximum operating temperature",
            condition="always_hidden", tier="first-glance", display_order=9,
            sub_tab="system-constraints"))
    return fields

_TAB9: list[InputField] = (
    _cc_fields("gf", "Greenfield", "greenfield_congestion_curtailment_reductions")
    + _cc_fields("rc", "Reconductoring", "reconductoring_congestion_curtailment_reductions")
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


if __name__ == "__main__":
    tabs: dict[str, int] = {}
    for f in _ALL_FIELDS:
        tabs[f.input_tab] = tabs.get(f.input_tab, 0) + 1
    hidden = sum(1 for f in _ALL_FIELDS if f.condition == "always_hidden")

    print(f"Input metadata: {len(INPUT_METADATA)} fields ({hidden} always_hidden)")
    for tab, count in sorted(tabs.items()):
        print(f"  {tab}: {count}")
    print(f"Tabs with entries: {len(tabs)}")

    from taxonomy import TAXONOMY
    bad_refs = [f.id for f in _ALL_FIELDS if f.taxonomy_id not in TAXONOMY]
    if bad_refs:
        print(f"ERROR: {len(bad_refs)} fields reference unknown taxonomy_ids: {bad_refs[:5]}")
    else:
        print("All taxonomy_id references valid")

    dupes = len(_ALL_FIELDS) - len(INPUT_METADATA)
    if dupes:
        print(f"ERROR: {dupes} duplicate field IDs")
    else:
        print("No duplicate field IDs")
