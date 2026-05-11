"""CTCC taxonomy — single source of truth for Python.

Defines the 36-item taxonomy (24 cost/benefit + 12 utility), dimensions
registry, BCR definitions, excludable groups, and calculator key mappings.
Read-only reference data; importable by any module without circular imports.

Canonical source: .cursor/plans/2026-05-10__ctcc-cost-benefit-taxonomy.md
"""

from __future__ import annotations

import itertools
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
Bucket = Literal[
    "hard", "soft", "risk", "emissions",
    "remedial", "enabling", "transfer", "reporting",
    "project", "route", "financial",
]
DiscountRate = Literal["wacc_real", "social", "wacc_nominal"]
Condition = Literal["dc_only", "greenfield_only", "reconductoring_only"]
NumeratorRule = Literal["all_benefits", "revenue"]
DenominatorRule = Literal[
    "all_costs", "hard", "hard_delay", "hard_delay_operational", "revenue_loss",
]
Perspective = Literal["societal", "stakeholder"]

# ---------------------------------------------------------------------------
# Core data structures
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TaxonomyItem:
    id: str
    side: Side
    bucket: Bucket
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
    # --- Hard costs (bucket: hard) ---
    TaxonomyItem("build_conductor", "cost", "hard", "build",
                 "Conductor Cost", "wacc_real", None, 1,
                 "Terrain-adjusted, contingency-applied conductor cost (variable + fixed)."),
    TaxonomyItem("build_structure", "cost", "hard", "build",
                 "Structure Cost", "wacc_real", "greenfield_only", 2,
                 "Terrain-adjusted structure cost. Zero for reconductoring."),
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
    # --- Soft costs (bucket: soft) ---
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
    TaxonomyItem("residual_exceedance", "cost", "soft", "energy",
                 "Residual Exceedance", "wacc_real", None, 6,
                 "Cost of transmission constraint exceedance not relieved by the project."),
    TaxonomyItem("base_delay", "cost", "soft", "delay",
                 "Base Delay Cost", "wacc_real", None, 7,
                 "Annual pre-construction delay costs (legal, admin, labor, regulatory)."),
    TaxonomyItem("congestion_delay", "cost", "soft", "delay",
                 "Congestion Delay Cost", "wacc_real", None, 8,
                 "Opportunity cost of congestion during delay + construction period."),
    TaxonomyItem("curtailment_delay", "cost", "soft", "delay",
                 "Curtailment Delay Cost", "wacc_real", None, 9,
                 "Opportunity cost of curtailment during delay + construction period."),
    # --- Risk costs (bucket: risk) ---
    TaxonomyItem("wildfire_eac", "cost", "risk", "wildfire",
                 "Expected Wildfire Cost", "social", None, 1,
                 "Expected annual loss from wildfire (ignition rate x severity x risk growth)."),
    TaxonomyItem("outage_eac", "cost", "risk", "outage",
                 "Expected Outage Cost", "social", None, 2,
                 "Expected annual cost from transmission outages (rate x duration x VoLL x risk growth)."),
    # --- Emissions costs (bucket: emissions) ---
    TaxonomyItem("emissions_comp", "cost", "emissions", "loss_compensation",
                 "Loss-Compensation Emissions", "social", None, 1,
                 "Social cost of emissions from generation compensating for line losses."),
    TaxonomyItem("emissions_fac", "cost", "emissions", "facilitated",
                 "Facilitated Emissions", "social", None, 2,
                 "Social cost of project-path generation mix over delivered energy."),
    # --- Benefits (buckets: remedial, enabling) ---
    TaxonomyItem("congestion_benefit", "benefit", "remedial", "congestion",
                 "Congestion Reduction Benefit", "wacc_real", None, 1,
                 "Value of congestion relief MWh. Remedial: fixes pre-existing deadweight loss."),
    TaxonomyItem("curtailment_benefit", "benefit", "remedial", "curtailment",
                 "Curtailment Reduction Benefit", "wacc_real", None, 2,
                 "Value of curtailment relief MWh. Remedial: fixes curtailed renewables."),
    TaxonomyItem("delivered_energy_benefit", "benefit", "enabling", "delivered_energy",
                 "Delivered Energy Benefit", "wacc_real", None, 1,
                 "Value of deliverable energy. Enabling: new throughput."),
    # --- Transfer ---
    TaxonomyItem("revenue", "transfer", "transfer", "revenue",
                 "Revenue (Rate-Based)", "wacc_real", None, 1,
                 "Utility-ratepayer transfer: allowed return x rate base. Not in societal NB."),
    # --- Reporting-only ---
    TaxonomyItem("displacement_avoided", "reporting_only", "reporting", "displacement",
                 "Displacement Avoided Emissions", "social", None, 1,
                 "Reported for transparency; not in NB or BCR."),
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
                 "Utilization & Reference Price", None, None, 4,
                 "Line utilization factor and baseline electricity price."),
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
    TaxonomyItem("financial_capital_structure", "utility", "financial", "capital_structure",
                 "Capital Structure", None, None, 3,
                 "Equity/debt split, cost of equity/debt."),
    TaxonomyItem("financial_revenue_config", "utility", "financial", "revenue",
                 "Revenue & Return Configuration", None, None, 4,
                 "Rate-based revenue: enabled flag, allowed return rate."),
    TaxonomyItem("financial_afudc", "utility", "financial", "afudc",
                 "AFUDC Configuration", None, None, 5,
                 "AFUDC application toggle and delay period active work flag."),
    TaxonomyItem("financial_timing_patterns", "utility", "financial", "timing_patterns",
                 "Cost Timing Patterns", None, None, 6,
                 "Spending split by cost component for AFUDC capitalization."),
)

TAXONOMY: dict[str, TaxonomyItem] = {item.id: item for item in TAXONOMY_ITEMS}
assert len(TAXONOMY) == 36, f"Expected 36 taxonomy items, got {len(TAXONOMY)}"

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
    DimensionEntry("wildfire_eac", "terrain", "Per-terrain ignition rate x miles"),
    DimensionEntry("wildfire_eac", "year", "Risk growth over project lifetime"),
    DimensionEntry("outage_eac", "terrain", "Per-terrain outage rate x duration x miles"),
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
    DimensionEntry("curtailment_benefit", "allocation", "Curtailment-first capacity allocation"),
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
        "emissions", "Emissions (loss-comp + facilitated)",
        frozenset({"emissions_comp", "emissions_fac"}),
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
# Section 3b — Core BCR perspectives (5)
# ---------------------------------------------------------------------------

BCR_DEFINITIONS: dict[str, BCRDefinition] = {
    "bcr_system": BCRDefinition(
        "bcr_system", "System (Societal)", "societal",
        "all_benefits", "all_costs", frozenset(), 1,
        "Full societal benchmark. Revenue excluded.",
    ),
    "bcr_capital": BCRDefinition(
        "bcr_capital", "Capital Only", "societal",
        "all_benefits", "hard", frozenset(), 2,
        "Capital screening; shows what narrow views miss.",
    ),
    "bcr_capital_and_delay": BCRDefinition(
        "bcr_capital_and_delay", "Capital + Delay", "societal",
        "all_benefits", "hard_delay", frozenset(), 3,
        "Capital and delay exposure.",
    ),
    "bcr_utility": BCRDefinition(
        "bcr_utility", "Utility / TSP", "stakeholder",
        "revenue", "hard_delay_operational", frozenset(), 4,
        "Whether utility recovers out-of-pocket costs.",
    ),
    "bcr_ratepayer": BCRDefinition(
        "bcr_ratepayer", "Ratepayer", "stakeholder",
        "all_benefits", "revenue_loss", frozenset(), 5,
        "Whether ratepayers receive more value than they pay.",
    ),
}

# ---------------------------------------------------------------------------
# Section 3c — Exclusion variants (15, auto-generated)
# ---------------------------------------------------------------------------

_excl_variants: dict[str, BCRDefinition] = {}
_display_base = 10
for _r in range(1, len(EXCLUDABLE_GROUPS) + 1):
    for _combo in itertools.combinations(sorted(EXCLUDABLE_GROUPS), _r):
        if len(_combo) == len(EXCLUDABLE_GROUPS):
            _variant_id = "bcr_excl_all"
            _label = "Excl. All"
        else:
            _variant_id = "bcr_excl_" + "_".join(_combo)
            _label = "Excl. " + " + ".join(
                g.replace("_", " ").title() for g in _combo
            )
        _excl_variants[_variant_id] = BCRDefinition(
            _variant_id, _label, "societal",
            "all_benefits", "all_costs", frozenset(_combo),
            _display_base, None,
        )
        _display_base += 1

BCR_EXCLUSION_VARIANTS: dict[str, BCRDefinition] = _excl_variants
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
    "residual_exceedance": "residual_exceedance_pv",
    # Soft costs — delay
    "base_delay": "delay_cost_pv",
    "congestion_delay": "congestion_delay_cost_pv",
    "curtailment_delay": "curtailment_delay_cost_pv",
    # Risk costs
    "wildfire_eac": "wildfire_pv",
    "outage_eac": "outage_pv",
    # Emissions costs
    "emissions_comp": "emissions_comp_cost_pv",
    "emissions_fac": "fac_emissions_project_pv",
    # Benefits
    "congestion_benefit": "congestion_benefit_pv",
    "curtailment_benefit": "curtailment_benefit_pv",
    "delivered_energy_benefit": "delivered_benefit_pv",
    # Transfer
    "revenue": "revenue_pv",
    # Reporting-only
    "displacement_avoided": "displacement_avoided_cost_pv",
}

# ---------------------------------------------------------------------------
# Helper functions (public API)
# ---------------------------------------------------------------------------


def get_items_by_side(side: Side) -> list[TaxonomyItem]:
    """Return taxonomy items filtered by side, sorted by (bucket, display_order)."""
    return sorted(
        (item for item in TAXONOMY_ITEMS if item.side == side),
        key=lambda item: (item.bucket, item.display_order),
    )


def get_items_by_bucket(bucket: Bucket) -> list[TaxonomyItem]:
    """Return taxonomy items filtered by bucket, sorted by display_order."""
    return sorted(
        (item for item in TAXONOMY_ITEMS if item.bucket == bucket),
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
        "bcr_definitions": {
            did: {
                "id": d.id,
                "label": d.label,
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
    assert len(TAXONOMY) == 36, f"Expected 36 items, got {len(TAXONOMY)}"

    # 8b. Bucket membership
    _side_bucket_rules: dict[str, set[str]] = {
        "cost": {"hard", "soft", "risk", "emissions"},
        "benefit": {"remedial", "enabling"},
        "transfer": {"transfer"},
        "reporting_only": {"reporting"},
        "utility": {"project", "route", "financial"},
    }
    for _item in TAXONOMY_ITEMS:
        _allowed = _side_bucket_rules[_item.side]
        assert _item.bucket in _allowed, (
            f"{_item.id}: side={_item.side!r} requires bucket in {_allowed}, "
            f"got {_item.bucket!r}"
        )

    # 8c. Discount rate
    _expected_social = {"wildfire_eac", "outage_eac", "emissions_comp",
                        "emissions_fac", "displacement_avoided"}
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
    assert len(BCR_DEFINITIONS) == 5, (
        f"Expected 5 core BCR definitions, got {len(BCR_DEFINITIONS)}"
    )
    assert len(BCR_EXCLUSION_VARIANTS) == 15, (
        f"Expected 15 exclusion variants, got {len(BCR_EXCLUSION_VARIANTS)}"
    )
    assert len(ALL_BCR_DEFINITIONS) == 20, (
        f"Expected 20 total BCR definitions, got {len(ALL_BCR_DEFINITIONS)}"
    )

    # 8e. Excludable groups
    assert len(EXCLUDABLE_GROUPS) == 4, (
        f"Expected 4 excludable groups, got {len(EXCLUDABLE_GROUPS)}"
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
    assert len(TAXONOMY_TO_CALCULATOR_KEY) == 24, (
        f"Expected 24 calculator key mappings, got {len(TAXONOMY_TO_CALCULATOR_KEY)}"
    )
    for _tid in TAXONOMY_TO_CALCULATOR_KEY:
        assert _tid in TAXONOMY, (
            f"Calculator key mapping references unknown taxonomy_id: {_tid!r}"
        )

    print("Taxonomy verification passed: 36 items (24 cost/benefit + 12 utility), 20 BCR definitions, 4 excludable groups")

    # Write JSON export
    _json_path = Path(__file__).resolve().parent.parent / "server" / "json" / "taxonomy.json"
    _json_path.write_text(json.dumps(taxonomy_to_dict(), indent=2) + "\n")
    print(f"Wrote {_json_path}")
