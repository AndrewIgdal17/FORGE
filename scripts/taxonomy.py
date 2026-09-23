"""FORGE taxonomy — single source of truth for Python.

Defines the 36-item taxonomy (25 cost/benefit + 12 utility), dimensions
registry, BCR definitions, excludable groups, and calculator key mappings.
Read-only reference data; importable by any module without circular imports.

Canonical source: .cursor/plans/2026-05-10__forge-cost-benefit-taxonomy.md
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from functools import lru_cache
from pathlib import Path
from typing import Literal

# ---------------------------------------------------------------------------
# Type aliases (mirror SQL CHECK constraints)
# ---------------------------------------------------------------------------

Side = Literal["cost", "benefit", "transfer", "reporting_only", "utility"]
Category = Literal[
    "hard", "soft", "risk", "emissions",
    "remedial", "enabling", "transfer", "reporting",
    "project", "route", "financial",
]
DiscountRate = Literal["wacc_real", "social", "wacc_nominal"]
Condition = Literal["dc_only", "not_reconductoring", "reconductoring_only", "rebuild_only"]
NumeratorRule = Literal[
    "all_benefits", "remedial", "remedial_enabling",
    "capital_recovery", "revenue_requirement",
]
DenominatorRule = Literal[
    "all_costs", "hard", "hard_delay",
    "atrr_delay", "revenue_requirement_loss",
]
Perspective = Literal["societal", "stakeholder"]
Family = Literal["societal", "firm"]

# ---------------------------------------------------------------------------
# Core data structures
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TaxonomyItem:
    id: str
    side: Side
    category: Category
    subgroup: str
    label: str
    discount_rate: DiscountRate | None
    condition: Condition | None
    display_order: int
    description: str


@dataclass(frozen=True)
class DimensionEntry:
    taxonomy_id: str
    dimension: str
    notes: str


@dataclass(frozen=True)
class ExcludableGroup:
    id: str
    label: str
    taxonomy_ids: frozenset[str]


@dataclass(frozen=True)
class BCRDefinition:
    id: str
    label: str
    family: Family
    perspective: Perspective
    numerator_rule: NumeratorRule
    denominator_rule: DenominatorRule
    exclude_groups: frozenset[str]
    display_order: int
    notes: str | None


# ---------------------------------------------------------------------------
# Section 1 — Taxonomy seed (24 items)
# ---------------------------------------------------------------------------

TAXONOMY_ITEMS: tuple[TaxonomyItem, ...] = (
    # --- Hard costs (category: hard) ---
    TaxonomyItem("build_conductor", "cost", "hard", "build",
                 "Conductor Cost", "wacc_real", None, 1,
                 "Terrain-adjusted, contingency-applied conductor cost (variable + fixed)."),
    TaxonomyItem("build_structure", "cost", "hard", "build",
                 "Structure Cost", "wacc_real", "not_reconductoring", 2,
                 "Terrain-adjusted structure cost. Zero for reconductoring; full for greenfield and rebuild."),
    TaxonomyItem("build_converter", "cost", "hard", "build",
                 "Converter Cost", "wacc_real", "dc_only", 3,
                 "Fixed converter station cost. Zero for AC and reconductoring."),
    TaxonomyItem("row_acquisition", "cost", "hard", "row_capital",
                 "ROW Acquisition", "wacc_real", None, 4,
                 "One-time land acquisition cost (fee simple or easement)."),
    TaxonomyItem("row_holding", "cost", "hard", "row_capital",
                 "ROW Holding Cost", "wacc_real", None, 5,
                 "Annual option/holding fee during delay period."),
    TaxonomyItem("env_mitigation", "cost", "hard", "environmental",
                 "Environmental Mitigation", "wacc_real", None, 6,
                 "Base per-acre mitigation + wetland/habitat credit costs."),
    # --- Soft costs (category: soft) ---
    TaxonomyItem("oandm", "cost", "soft", "operational",
                 "O&M", "wacc_real", None, 1,
                 "Annual conductor + structure + converter + vegetation management O&M."),
    TaxonomyItem("insurance", "cost", "soft", "operational",
                 "Operational Insurance", "wacc_real", None, 2,
                 "Annual premium on insurable asset value (build components)."),
    TaxonomyItem("row_rent", "cost", "soft", "operational",
                 "ROW Rent", "wacc_real", None, 3,
                 "Annual per-acre rent for existing/leased ROW corridor."),
    TaxonomyItem("line_loss_conductor", "cost", "soft", "energy",
                 "Conductor Losses", "wacc_real", None, 4,
                 "Thermal energy losses from conductor resistance, valued at electricity price."),
    TaxonomyItem("line_loss_converter", "cost", "soft", "energy",
                 "Converter Losses", "wacc_real", "dc_only", 5,
                 "Energy losses from AC/DC converter stations. Zero for AC projects."),
    TaxonomyItem("base_delay", "cost", "soft", "delay",
                 "Base Delay Cost", "wacc_real", None, 6,
                 "Annual pre-construction delay costs (legal, admin, labor, regulatory)."),
    TaxonomyItem("congestion_delay", "cost", "soft", "delay",
                 "Congestion Delay Cost", "wacc_real", None, 7,
                 "Opportunity cost of congestion during delay + construction period."),
    TaxonomyItem("emissions_displacement_delay", "cost", "soft", "delay",
                 "Displacement Delay Emissions Cost", "social", None, 9,
                 "Foregone emissions displacement benefit during delay period. Valued at year-specific SCC."),
    # --- Risk costs (category: risk) ---
    TaxonomyItem("wildfire_eac", "cost", "risk", "wildfire",
                 "Expected Wildfire Cost", "social", None, 1,
                 "Expected annual loss from wildfire (ignition rate x severity x risk growth)."),
    TaxonomyItem("outage_eac", "cost", "risk", "outage",
                 "Expected Outage Cost", "social", None, 2,
                 "Expected annual cost from transmission outages (rate x duration x VoLL x risk growth)."),
    # --- Emissions costs (category: emissions) ---
    TaxonomyItem("emissions_comp", "cost", "emissions", "loss_compensation",
                 "Loss-Compensation Emissions", "social", None, 1,
                 "Social cost of emissions from generation compensating for line losses."),
    TaxonomyItem("emissions_fac", "reporting_only", "reporting", "facilitated",
                 "Facilitated Emissions", "social", None, 2,
                 "Intermediate quantity (not a BCR cost or benefit). Social cost of pollutant emissions from the energy delivered via this project path. The Avoided Emissions Benefit equals the no-line equivalent minus this value."),
    # --- Benefits (categories: remedial, enabling, avoided_emissions) ---
    TaxonomyItem("congestion_benefit", "benefit", "remedial", "congestion",
                 "Congestion Reduction Benefit", "wacc_real", None, 1,
                 "Value of congestion relief MWh. Remedial: fixes pre-existing deadweight loss."),
    TaxonomyItem("delivered_energy_benefit", "benefit", "enabling", "delivered_energy",
                 "Delivered Energy Benefit", "wacc_real", None, 1,
                 "Value of deliverable energy. Enabling: new throughput."),
    TaxonomyItem("capacity_value_benefit", "benefit", "enabling", "capacity_value",
                 "Capacity Value Benefit", "wacc_real", None, 2,
                 "Resource adequacy value of incremental transfer capability. "
                 "Net CONE × capacity credit × effective capacity × applicability gate. "
                 "Parametric screening proxy (Brattle 2013); not LOLE/RPM simulation."),
    # --- Transfer ---
    TaxonomyItem("capital_recovery", "transfer", "transfer", "capital_recovery",
                 "Capital Recovery (Rate-Based)", "wacc_real", None, 1,
                 "Utility-ratepayer transfer: allowed return x rate base. Not in societal NB."),
    # --- Avoided emissions benefit ---
    TaxonomyItem("displacement_avoided", "benefit", "avoided_emissions", "displacement",
                 "Avoided Emissions Benefit", "social", None, 1,
                 "Benefit from cleaner generation enabled by this project. Equals the difference between the no-line and project-path societal emission costs, discounted at the social rate."),
    # --- Utility (shared input groups, no scenario_results) ---
    TaxonomyItem("project_identity", "utility", "project", "configuration",
                 "Project Identity", None, None, 1,
                 "Project name and scenario identifier."),
    TaxonomyItem("project_technology", "utility", "project", "configuration",
                 "Technology Configuration", None, None, 2,
                 "Construction type, AC/DC, capacity, conductor/converter selection."),
    TaxonomyItem("project_timing", "utility", "project", "timing",
                 "Project Timing", None, None, 3,
                 "Construction years, delay years, project lifetime."),
    TaxonomyItem("project_utilization", "utility", "project", "utilization",
                 "Line Utilization", None, None, 4,
                 "Line utilization factor."),
    TaxonomyItem("route_terrain_miles", "utility", "route", "terrain",
                 "Terrain Miles", None, None, 1,
                 "Route miles by terrain type. Zero-mile terrains hidden from cost calculations."),
    TaxonomyItem("route_terrain_multipliers", "utility", "route", "terrain",
                 "Terrain Multipliers", None, None, 2,
                 "Cost multiplier by terrain type for weighted miles."),
    TaxonomyItem("financial_rates", "utility", "financial", "rates",
                 "Financial Parameters", None, None, 1,
                 "Base year, inflation, WACC nominal, social discount rate."),
    TaxonomyItem("financial_contingencies", "utility", "financial", "contingencies",
                 "Build Contingencies", None, None, 2,
                 "Contingency factors for conductor, structure, converter costs."),
    TaxonomyItem("financial_revenue_config", "utility", "financial", "revenue",
                 "Revenue & Return Configuration", None, None, 4,
                 "Rate-based revenue: enabled flag, FERC declining-balance formula."),
    TaxonomyItem("financial_afudc", "utility", "financial", "afudc",
                 "AFUDC Configuration", None, None, 5,
                 "AFUDC application toggle and delay period active work flag."),
    TaxonomyItem("financial_timing_patterns", "utility", "financial", "timing_patterns",
                 "Cost Timing Patterns", None, None, 6,
                 "Spending split by cost component for AFUDC capitalization."),
)

TAXONOMY: dict[str, TaxonomyItem] = {item.id: item for item in TAXONOMY_ITEMS}
assert len(TAXONOMY) == 34, f"Expected 34 taxonomy items, got {len(TAXONOMY)}"

# ---------------------------------------------------------------------------
# Section 2 — Dimensions registry
# ---------------------------------------------------------------------------

TAXONOMY_DIMENSIONS: tuple[DimensionEntry, ...] = (
    DimensionEntry("build_conductor", "terrain", "Per-terrain weighted-mile cost breakdown"),
    DimensionEntry("build_structure", "terrain", "Per-terrain weighted-mile cost breakdown"),
    DimensionEntry("row_acquisition", "zone", "Per-zone (up to 15 ROW zones) acquisition cost"),
    DimensionEntry("row_acquisition", "row_regime", "Easement, fee simple, lease, license"),
    DimensionEntry("row_acquisition", "terrain", "Per-terrain ROW valuation (future terrain-mile mode)"),
    DimensionEntry("row_holding", "zone", "Per-zone holding/option fee over delay period"),
    DimensionEntry("row_holding", "row_regime", "Easement, fee simple, lease, license"),
    DimensionEntry("env_mitigation", "terrain", "Per-terrain base mitigation acreage"),
    DimensionEntry("env_mitigation", "credit_type", "Wetland credits, habitat credits"),
    DimensionEntry("oandm", "terrain", "Vegetation management varies by terrain"),
    DimensionEntry("oandm", "component", "Conductor, structure, converter, vegetation sub-totals"),
    DimensionEntry("row_rent", "zone", "Per-zone annual rent"),
    DimensionEntry("line_loss_conductor", "terrain", "Loss MWh varies with resistance (terrain-adjusted miles)"),
    DimensionEntry("wildfire_eac", "year", "Risk growth over project lifetime"),
    DimensionEntry("outage_eac", "year", "Risk growth over project lifetime"),
    DimensionEntry("outage_eac", "voll_tier", "VoLL is piecewise by duration tier"),
    DimensionEntry("emissions_comp", "pollutant", "CO2, SOx, NOx"),
    DimensionEntry("emissions_comp", "source", "Per-source mix contribution"),
    DimensionEntry("emissions_comp", "year", "Evolving mix over project lifetime"),
    DimensionEntry("emissions_fac", "pollutant", "CO2, SOx, NOx"),
    DimensionEntry("emissions_fac", "source", "Per-source mix contribution"),
    DimensionEntry("emissions_fac", "year", "Evolving mix over project lifetime"),
    DimensionEntry("emissions_fac", "instance", "Project vs. no-line (two engine runs)"),
    DimensionEntry("displacement_avoided", "pollutant", "CO2, SOx, NOx avoided mass + cost"),
    DimensionEntry("displacement_avoided", "year", "Evolving differential over project lifetime"),
    DimensionEntry("congestion_benefit", "allocation", "Overlap vs. non-overlap binding hours"),
    DimensionEntry("base_delay", "category", "Legal, admin, labor, regulatory, etc. (8 categories from YAML)"),
    DimensionEntry("insurance", "component", "Conductors, structures, converters insurable base"),
)

_dim_map: dict[str, list[str]] = defaultdict(list)
for _de in TAXONOMY_DIMENSIONS:
    assert _de.taxonomy_id in TAXONOMY, (
        f"Dimension references unknown taxonomy_id: {_de.taxonomy_id!r}"
    )
    _dim_map[_de.taxonomy_id].append(_de.dimension)
DIMENSIONS_BY_ITEM: dict[str, list[str]] = dict(_dim_map)

# ---------------------------------------------------------------------------
# Section 3a — Excludable groups
# ---------------------------------------------------------------------------

EXCLUDABLE_GROUPS: dict[str, ExcludableGroup] = {
    "emissions": ExcludableGroup(
        "emissions", "Line Loss Compensation Emissions",
        frozenset({"emissions_comp"}),
    ),
    "avoided_emissions": ExcludableGroup(
        "avoided_emissions", "Avoided Emissions",
        frozenset({"displacement_avoided"}),
    ),
    "line_losses": ExcludableGroup(
        "line_losses", "Line Losses (conductor + converter)",
        frozenset({"line_loss_conductor", "line_loss_converter"}),
    ),
    "wildfire": ExcludableGroup(
        "wildfire", "Wildfire Risk",
        frozenset({"wildfire_eac"}),
    ),
    "outage": ExcludableGroup(
        "outage", "Outage Risk",
        frozenset({"outage_eac"}),
    ),
}

# ---------------------------------------------------------------------------
# Section 3b — Core BCR perspectives (3)
# ---------------------------------------------------------------------------

BCR_DEFINITIONS: dict[str, BCRDefinition] = {
    "bcr_societal": BCRDefinition(
        "bcr_societal", "Societal", "societal", "societal",
        "all_benefits", "all_costs", frozenset(), 1,
        "Full societal benchmark. Revenue excluded.",
    ),
    "bcr_utility": BCRDefinition(
        "bcr_utility", "Utility / TSP", "firm", "stakeholder",
        "revenue_requirement", "atrr_delay", frozenset(), 6,
        "Pure utility: ATRR / (ATRR + base delay). BCR = 1.0 by identity for zero-delay regulated projects.",
    ),
    "bcr_ratepayer": BCRDefinition(
        "bcr_ratepayer", "Ratepayer", "firm", "stakeholder",
        "remedial_enabling", "revenue_requirement_loss", frozenset(), 7,
        "Whether ratepayers receive more value than they pay through rates (full ATRR + losses).",
    ),
}

BCR_FAMILY_META: dict[Family, dict[str, str | int]] = {
    "societal": {"label": "Societal", "order": 1},
    "firm": {"label": "Firm", "order": 3},
}

# ---------------------------------------------------------------------------
# Section 3c — Exclusion variants (3 Tier 1, analytically motivated)
#
# Only variants with a clear regulatory or analytical question are retained.
# See: Projects/FORGE/docs/research/2026-07-08__bcr-framework-justification.md
# The interactive "Custom BCR" builder (powered by EXCLUDABLE_GROUPS above)
# lets users compose arbitrary exclusions on demand.
# ---------------------------------------------------------------------------

BCR_EXCLUSION_VARIANTS: dict[str, BCRDefinition] = {
    "bcr_excl_avoided_emissions": BCRDefinition(
        "bcr_excl_avoided_emissions", "Excl. Avoided Emissions",
        "societal", "societal",
        "all_benefits", "all_costs", frozenset({"avoided_emissions"}),
        10, "FERC-minimum benefit set (no emissions benefits).",
    ),
    "bcr_excl_emissions_costs": BCRDefinition(
        "bcr_excl_emissions_costs", "Excl. Emissions Costs",
        "societal", "societal",
        "all_benefits", "all_costs", frozenset({"emissions"}),
        11, "Societal BCR without loss-compensation emissions costs.",
    ),
    "bcr_excl_all_emissions": BCRDefinition(
        "bcr_excl_all_emissions", "Excl. All Emissions",
        "societal", "societal",
        "all_benefits", "all_costs", frozenset({"avoided_emissions", "emissions"}),
        12, "No emissions anywhere: pure market-flow BCR.",
    ),
    "bcr_excl_outage": BCRDefinition(
        "bcr_excl_outage", "Excl. Outage",
        "societal", "societal",
        "all_benefits", "all_costs", frozenset({"outage"}),
        13, "Societal BCR excluding outage risk only.",
    ),
    "bcr_excl_wildfire": BCRDefinition(
        "bcr_excl_wildfire", "Excl. Wildfire",
        "societal", "societal",
        "all_benefits", "all_costs", frozenset({"wildfire"}),
        14, "For low-wildfire regions.",
    ),
    "bcr_excl_outage_wildfire": BCRDefinition(
        "bcr_excl_outage_wildfire", "Excl. Wildfire + Outage",
        "societal", "societal",
        "all_benefits", "all_costs", frozenset({"wildfire", "outage"}),
        15, "Deterministic BCR (no risk costs).",
    ),
}
ALL_BCR_DEFINITIONS: dict[str, BCRDefinition] = {
    **BCR_DEFINITIONS,
    **BCR_EXCLUSION_VARIANTS,
}

# ---------------------------------------------------------------------------
# Calculator key mapping (taxonomy id -> BCRInputData / calculate_costs key)
# ---------------------------------------------------------------------------

TAXONOMY_TO_CALCULATOR_KEY: dict[str, str] = {
    # Hard costs — build items share aggregate key build_cost_pv
    "build_conductor": "build_cost_pv",
    "build_structure": "build_cost_pv",
    "build_converter": "build_cost_pv",
    # Hard costs — ROW items share aggregate key row_capital_pv
    "row_acquisition": "row_capital_pv",
    "row_holding": "row_capital_pv",
    # Hard costs — individual keys
    "env_mitigation": "env_mitigation_pv",
    # Soft costs — operational
    "oandm": "oandm_pv",
    "insurance": "insurance_pv",
    "row_rent": "row_rent_pv",
    # Soft costs — energy
    "line_loss_conductor": "conductor_loss_pv",
    "line_loss_converter": "converter_loss_pv",
    # Soft costs — delay
    "base_delay": "delay_cost_pv",
    "congestion_delay": "congestion_delay_cost_pv",
    # Risk costs
    "wildfire_eac": "wildfire_pv",
    "outage_eac": "outage_pv",
    # Emissions costs
    "emissions_comp": "emissions_comp_cost_pv",
    "emissions_fac": "fac_emissions_project_pv",
    # Benefits
    "congestion_benefit": "congestion_benefit_pv",
    "delivered_energy_benefit": "delivered_benefit_pv",
    "capacity_value_benefit": "capacity_value_benefit_pv",
    # Transfer
    "capital_recovery": "capital_recovery_pv",
    # Reporting-only
    "displacement_avoided": "displacement_avoided_cost_pv",
    # Soft costs — delay (displacement)
    "emissions_displacement_delay": "emissions_displacement_delay_pv",
}

# ---------------------------------------------------------------------------
# Helper functions (public API)
# ---------------------------------------------------------------------------


def get_items_by_side(side: Side) -> list[TaxonomyItem]:
    """Return taxonomy items filtered by side, sorted by (category, display_order)."""
    return sorted(
        (item for item in TAXONOMY_ITEMS if item.side == side),
        key=lambda item: (item.category, item.display_order),
    )


def get_items_by_category(category: Category) -> list[TaxonomyItem]:
    """Return taxonomy items filtered by category, sorted by display_order."""
    return sorted(
        (item for item in TAXONOMY_ITEMS if item.category == category),
        key=lambda item: item.display_order,
    )


def get_items_by_subgroup(subgroup: str) -> list[TaxonomyItem]:
    """Return taxonomy items filtered by subgroup, sorted by display_order."""
    return sorted(
        (item for item in TAXONOMY_ITEMS if item.subgroup == subgroup),
        key=lambda item: item.display_order,
    )


def get_excluded_taxonomy_ids(exclude_groups: list[str]) -> set[str]:
    """Resolve excludable group names to the union of their taxonomy IDs.

    Raises KeyError for unknown group names.
    """
    result: set[str] = set()
    for group_name in exclude_groups:
        result |= EXCLUDABLE_GROUPS[group_name].taxonomy_ids
    return result


def get_dimensions(taxonomy_id: str) -> list[str]:
    """Return dimension names for a taxonomy item, or empty list."""
    return DIMENSIONS_BY_ITEM.get(taxonomy_id, [])


# ---------------------------------------------------------------------------
# JSON export
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def taxonomy_to_dict() -> dict:
    """Return the full taxonomy as a JSON-serializable dict.

    Shape: {items, dimensions, excludable_groups, bcr_definitions}
    """
    return {
        "items": [asdict(item) for item in TAXONOMY_ITEMS],
        "dimensions": {
            tid: dims for tid, dims in DIMENSIONS_BY_ITEM.items()
        },
        "excludable_groups": {
            gid: {"id": g.id, "label": g.label, "taxonomy_ids": sorted(g.taxonomy_ids)}
            for gid, g in EXCLUDABLE_GROUPS.items()
        },
        "bcr_families": {
            fid: {"id": fid, "label": meta["label"], "order": meta["order"]}
            for fid, meta in BCR_FAMILY_META.items()
        },
        "bcr_definitions": {
            did: {
                "id": d.id,
                "label": d.label,
                "family": d.family,
                "perspective": d.perspective,
                "numerator_rule": d.numerator_rule,
                "denominator_rule": d.denominator_rule,
                "exclude_groups": sorted(d.exclude_groups),
                "display_order": d.display_order,
                "notes": d.notes,
            }
            for did, d in ALL_BCR_DEFINITIONS.items()
        },
    }


# ---------------------------------------------------------------------------
# Verification + JSON export when run directly
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # 8a. Item count
    assert len(TAXONOMY) == 34, f"Expected 34 items, got {len(TAXONOMY)}"

    # 8b. Category membership
    _side_category_rules: dict[str, set[str]] = {
        "cost": {"hard", "soft", "risk", "emissions"},
        "benefit": {"remedial", "enabling", "avoided_emissions"},
        "transfer": {"transfer"},
        "reporting_only": {"reporting"},
        "utility": {"project", "route", "financial"},
    }
    for _item in TAXONOMY_ITEMS:
        _allowed = _side_category_rules[_item.side]
        assert _item.category in _allowed, (
            f"{_item.id}: side={_item.side!r} requires category in {_allowed}, "
            f"got {_item.category!r}"
        )

    # 8c. Discount rate
    _expected_social = {"wildfire_eac", "outage_eac", "emissions_comp",
                        "emissions_fac", "displacement_avoided",
                        "emissions_displacement_delay"}
    _actual_social = {item.id for item in TAXONOMY_ITEMS if item.discount_rate == "social"}
    assert _actual_social == _expected_social, (
        f"Social discount rate mismatch: expected {_expected_social}, got {_actual_social}"
    )
    _expected_null_dr = {item.id for item in TAXONOMY_ITEMS if item.side == "utility"}
    _actual_null_dr = {item.id for item in TAXONOMY_ITEMS if item.discount_rate is None}
    assert _actual_null_dr == _expected_null_dr, (
        f"NULL discount_rate mismatch: expected {_expected_null_dr}, got {_actual_null_dr}"
    )
    _actual_wacc = {item.id for item in TAXONOMY_ITEMS if item.discount_rate == "wacc_real"}
    assert _actual_wacc == set(TAXONOMY) - _expected_social - _expected_null_dr, (
        "Some items have unexpected discount_rate"
    )

    # 8d. BCR coverage
    assert len(BCR_DEFINITIONS) == 3, (
        f"Expected 3 core BCR definitions, got {len(BCR_DEFINITIONS)}"
    )
    assert len(BCR_EXCLUSION_VARIANTS) == 6, (
        f"Expected 6 exclusion variants, got {len(BCR_EXCLUSION_VARIANTS)}"
    )
    assert len(ALL_BCR_DEFINITIONS) == 9, (
        f"Expected 9 total BCR definitions, got {len(ALL_BCR_DEFINITIONS)}"
    )

    # 8e. Excludable groups
    assert len(EXCLUDABLE_GROUPS) == 5, (
        f"Expected 5 excludable groups, got {len(EXCLUDABLE_GROUPS)}"
    )
    _all_excl_ids: set[str] = set()
    for _g in EXCLUDABLE_GROUPS.values():
        for _tid in _g.taxonomy_ids:
            assert _tid in TAXONOMY, (
                f"Excludable group {_g.id!r} references unknown taxonomy_id: {_tid!r}"
            )
            _all_excl_ids.add(_tid)
    assert len(_all_excl_ids) == 6, (
        f"Expected 6 total excludable taxonomy_ids, got {len(_all_excl_ids)}"
    )

    # 8f. Calculator key mapping
    assert len(TAXONOMY_TO_CALCULATOR_KEY) == 23, (
        f"Expected 23 calculator key mappings, got {len(TAXONOMY_TO_CALCULATOR_KEY)}"
    )
    for _tid in TAXONOMY_TO_CALCULATOR_KEY:
        assert _tid in TAXONOMY, (
            f"Calculator key mapping references unknown taxonomy_id: {_tid!r}"
        )

    print("Taxonomy verification passed: 34 items, 9 BCR definitions, 5 excludable groups")

    # Write JSON export
    _json_path = Path(__file__).resolve().parent.parent / "server" / "json" / "taxonomy.json"
    _json_path.write_text(json.dumps(taxonomy_to_dict(), indent=2) + "\n")
    print(f"Wrote {_json_path}")
