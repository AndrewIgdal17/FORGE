"""Taxonomy adapters — convert module output dicts to TaxonomyResult envelopes.

Reads from the assembled JSONOutputManager json_results dict (after all
calculation modules have run) and produces a list of TaxonomyResult objects
tagged with taxonomy IDs. A backward-compat shim converts results back to
flat keys for the existing BCRInputData pipeline.

No calculation module is modified by this file.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from taxonomy import TAXONOMY

# ---------------------------------------------------------------------------
# Result envelope dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DetailRow:
    dimension: str
    dimension_key: str
    value_pv: float
    value_nominal: float | None = None
    value_annual: float | None = None


@dataclass(frozen=True)
class TaxonomyResult:
    taxonomy_id: str
    value_pv: float
    value_nominal: float
    value_annual: float | None = None
    detail: tuple[DetailRow, ...] | None = None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _safe(d: dict, key: str) -> float:
    """Return numeric value from dict, treating None/empty/missing as 0."""
    v = d.get(key, 0)
    if v is None or v == "":
        return 0.0
    return float(v)


def _proportional_pv(
    total_pv: float, component_nominal: float, total_nominal: float
) -> float:
    """Split an aggregate PV proportionally by nominal ratio."""
    if total_nominal == 0:
        return 0.0
    return total_pv * component_nominal / total_nominal


# ---------------------------------------------------------------------------
# Per-module adapter functions
# ---------------------------------------------------------------------------


def adapt_build(build: dict) -> list[TaxonomyResult]:
    """Adapt costs.build -> build_conductor, build_structure, build_converter."""
    if not build:
        return []
    total_pv = _safe(build, "total_pv")
    total_nominal = _safe(build, "total_nominal")
    cond_nom = _safe(build, "conductor_nominal")
    struct_nom = _safe(build, "structure_nominal")
    conv_nom = _safe(build, "converter_nominal")
    return [
        TaxonomyResult(
            "build_conductor",
            value_pv=_proportional_pv(total_pv, cond_nom, total_nominal),
            value_nominal=cond_nom,
        ),
        TaxonomyResult(
            "build_structure",
            value_pv=_proportional_pv(total_pv, struct_nom, total_nominal),
            value_nominal=struct_nom,
        ),
        TaxonomyResult(
            "build_converter",
            value_pv=_proportional_pv(total_pv, conv_nom, total_nominal),
            value_nominal=conv_nom,
        ),
    ]


def adapt_row(row: dict) -> list[TaxonomyResult]:
    """Adapt costs.row -> row_acquisition, row_holding, row_rent."""
    if not row:
        return []
    cap_pv = _safe(row, "row_capital_pv")
    cap_nom = _safe(row, "row_capital_nominal")
    acq_nom = _safe(row, "acquisition_nominal")
    hold_nom = _safe(row, "holding_nominal")
    return [
        TaxonomyResult(
            "row_acquisition",
            value_pv=_proportional_pv(cap_pv, acq_nom, cap_nom),
            value_nominal=acq_nom,
        ),
        TaxonomyResult(
            "row_holding",
            value_pv=_proportional_pv(cap_pv, hold_nom, cap_nom),
            value_nominal=hold_nom,
        ),
        TaxonomyResult(
            "row_rent",
            value_pv=_safe(row, "row_rent_pv"),
            value_nominal=_safe(row, "row_rent_nominal"),
        ),
    ]


def adapt_environmental(env: dict) -> list[TaxonomyResult]:
    """Adapt costs.environmental -> env_mitigation."""
    if not env:
        return []
    detail = None
    base_nom = _safe(env, "base_cost_nominal")
    credits_nom = _safe(env, "credits_nominal")
    if base_nom or credits_nom:
        credits_pv = _safe(env, "credits_pv")
        total_pv = _safe(env, "total_pv")
        base_pv = total_pv - credits_pv if credits_pv else total_pv
        detail = (
            DetailRow("credit_type", "base", value_pv=base_pv, value_nominal=base_nom),
            DetailRow("credit_type", "credits", value_pv=credits_pv, value_nominal=credits_nom),
        )
    return [
        TaxonomyResult(
            "env_mitigation",
            value_pv=_safe(env, "total_pv"),
            value_nominal=_safe(env, "total_nominal"),
            detail=detail,
        ),
    ]


def adapt_oandm(oandm: dict) -> list[TaxonomyResult]:
    """Adapt costs.oandm -> oandm with component detail."""
    if not oandm:
        return []
    components = ("conductor", "converter", "structure", "vegetation")
    detail_rows: list[DetailRow] = []
    for comp in components:
        pv = _safe(oandm, f"{comp}_pv")
        nom = _safe(oandm, f"{comp}_nominal")
        ann = _safe(oandm, f"{comp}_annual")
        if pv or nom or ann:
            detail_rows.append(
                DetailRow("component", comp, value_pv=pv, value_nominal=nom, value_annual=ann)
            )
    return [
        TaxonomyResult(
            "oandm",
            value_pv=_safe(oandm, "total_pv"),
            value_nominal=_safe(oandm, "total_nominal"),
            value_annual=_safe(oandm, "total_annual"),
            detail=tuple(detail_rows) if detail_rows else None,
        ),
    ]


def adapt_insurance(insurance: dict) -> list[TaxonomyResult]:
    """Adapt costs.insurance -> insurance."""
    if not insurance:
        return []
    return [
        TaxonomyResult(
            "insurance",
            value_pv=_safe(insurance, "pv_total"),
            value_nominal=_safe(insurance, "nominal_lifetime_cost"),
            value_annual=_safe(insurance, "annual_premium"),
        ),
    ]


def adapt_line_loss(line_loss: dict) -> list[TaxonomyResult]:
    """Adapt costs.line_loss -> line_loss_conductor, line_loss_converter."""
    if not line_loss:
        return []
    return [
        TaxonomyResult(
            "line_loss_conductor",
            value_pv=_safe(line_loss, "line_cost_pv"),
            value_nominal=_safe(line_loss, "line_nominal_total"),
            value_annual=_safe(line_loss, "line_annual_cost"),
        ),
        TaxonomyResult(
            "line_loss_converter",
            value_pv=_safe(line_loss, "converter_cost_pv"),
            value_nominal=_safe(line_loss, "converter_nominal_total"),
            value_annual=_safe(line_loss, "converter_annual_cost"),
        ),
    ]


def adapt_delay(delay: dict) -> list[TaxonomyResult]:
    """Adapt costs.delay -> base_delay."""
    if not delay:
        return []
    return [
        TaxonomyResult(
            "base_delay",
            value_pv=_safe(delay, "total_pv"),
            value_nominal=_safe(delay, "total_nominal"),
        ),
    ]


def adapt_wildfire(wildfire: dict) -> list[TaxonomyResult]:
    """Adapt costs.wildfire -> wildfire_eac."""
    if not wildfire:
        return []
    return [
        TaxonomyResult(
            "wildfire_eac",
            value_pv=_safe(wildfire, "pv_cost"),
            value_nominal=_safe(wildfire, "nominal_total"),
            value_annual=_safe(wildfire, "EAL"),
        ),
    ]


def adapt_outage(outage: dict) -> list[TaxonomyResult]:
    """Adapt costs.outage -> outage_eac with two-tier detail rows."""
    if not outage:
        return []
    detail_rows: list[DetailRow] = []
    ls = _safe(outage, "cost_loadshed")
    rd = _safe(outage, "cost_redispatch")
    if ls or rd:
        detail_rows.append(
            DetailRow("component", "load_shed_per_event", value_pv=0.0, value_annual=ls)
        )
        detail_rows.append(
            DetailRow("component", "redispatch_per_event", value_pv=0.0, value_annual=rd)
        )
    return [
        TaxonomyResult(
            "outage_eac",
            value_pv=_safe(outage, "pv_cost"),
            value_nominal=_safe(outage, "nominal_total"),
            value_annual=_safe(outage, "EAC"),
            detail=tuple(detail_rows) if detail_rows else None,
        ),
    ]


def adapt_emissions_comp(emissions: dict) -> list[TaxonomyResult]:
    """Adapt costs.emissions -> emissions_comp with pollutant detail."""
    if not emissions:
        return []
    pollutants = ("co2", "sox", "nox")
    detail_rows = tuple(
        DetailRow(
            "pollutant", p,
            value_pv=_safe(emissions, f"{p}_cost_pv"),
            value_nominal=_safe(emissions, f"{p}_cost_nominal"),
        )
        for p in pollutants
        if _safe(emissions, f"{p}_cost_pv") or _safe(emissions, f"{p}_cost_nominal")
    )
    return [
        TaxonomyResult(
            "emissions_comp",
            value_pv=_safe(emissions, "total_pv"),
            value_nominal=_safe(emissions, "total_nominal"),
            value_annual=_safe(emissions, "annual_cost"),
            detail=detail_rows if detail_rows else None,
        ),
    ]


def adapt_facilitated_emissions(fac_em: dict) -> list[TaxonomyResult]:
    """Adapt costs.facilitated_emissions -> emissions_fac, displacement_avoided."""
    if not fac_em:
        return []
    pollutants = ("co2", "sox", "nox")
    fac_detail = tuple(
        DetailRow(
            "pollutant", p,
            value_pv=_safe(fac_em, f"project_{p}_pv"),
        )
        for p in pollutants
        if _safe(fac_em, f"project_{p}_pv")
    )
    return [
        TaxonomyResult(
            "emissions_fac",
            value_pv=_safe(fac_em, "fac_emissions_project_pv"),
            value_nominal=_safe(fac_em, "fac_emissions_project_nominal"),
            detail=fac_detail if fac_detail else None,
        ),
        TaxonomyResult(
            "displacement_avoided",
            value_pv=_safe(fac_em, "displacement_avoided_cost_pv"),
            value_nominal=_safe(fac_em, "displacement_avoided_cost_nominal"),
        ),
    ]


def adapt_displacement_delay_cost(disp_delay: dict) -> list[TaxonomyResult]:
    """Adapt costs.displacement_delay -> emissions_displacement_delay."""
    if not disp_delay:
        return []
    pollutants = ("co2", "sox", "nox")
    detail_rows = tuple(
        DetailRow(
            "pollutant", p,
            value_pv=_safe(disp_delay, f"{p}_pv"),
        )
        for p in pollutants
        if _safe(disp_delay, f"{p}_pv")
    )
    return [
        TaxonomyResult(
            "emissions_displacement_delay",
            value_pv=_safe(disp_delay, "displacement_delay_cost_pv"),
            value_nominal=_safe(disp_delay, "displacement_delay_cost_nominal"),
            detail=detail_rows if detail_rows else None,
        ),
    ]


def adapt_congestion_curtailment(cc: dict) -> list[TaxonomyResult]:
    """Adapt benefits.congestion_curtailment -> 5 taxonomy items.

    Three benefits (congestion, curtailment, delivered energy) and two
    cost-side items (congestion delay, curtailment delay).
    """
    if not cc:
        return []
    return [
        TaxonomyResult(
            "congestion_benefit",
            value_pv=_safe(cc, "congestion_benefit_pv"),
            value_nominal=_safe(cc, "congestion_benefit_nominal"),
            value_annual=_safe(cc, "congestion_benefit_annual"),
        ),
        TaxonomyResult(
            "curtailment_benefit",
            value_pv=_safe(cc, "curtailment_benefit_pv"),
            value_nominal=_safe(cc, "curtailment_benefit_nominal"),
            value_annual=_safe(cc, "curtailment_benefit_annual"),
        ),
        TaxonomyResult(
            "delivered_energy_benefit",
            value_pv=_safe(cc, "delivered_benefit_pv"),
            value_nominal=_safe(cc, "delivered_benefit_nominal"),
            value_annual=_safe(cc, "delivered_benefit_annual"),
        ),
        TaxonomyResult(
            "congestion_delay",
            value_pv=_safe(cc, "congestion_delay_cost_pv"),
            value_nominal=_safe(cc, "congestion_delay_cost_nominal"),
        ),
        TaxonomyResult(
            "curtailment_delay",
            value_pv=_safe(cc, "curtailment_delay_cost_pv"),
            value_nominal=_safe(cc, "curtailment_delay_cost_nominal"),
        ),
    ]


def adapt_capital_recovery(capital_recovery: dict) -> list[TaxonomyResult]:
    """Adapt benefits.capital_recovery -> capital_recovery."""
    if not capital_recovery:
        return []
    return [
        TaxonomyResult(
            "capital_recovery",
            value_pv=_safe(capital_recovery, "capital_recovery_pv"),
            value_nominal=_safe(capital_recovery, "capital_recovery_nominal"),
            value_annual=_safe(capital_recovery, "annual_revenue"),
        ),
    ]


# ---------------------------------------------------------------------------
# Master adapter
# ---------------------------------------------------------------------------


def adapt_all_results(json_results: dict) -> list[TaxonomyResult]:
    """Convert assembled JSONOutputManager results to taxonomy-tagged results.

    Calls each per-module adapter with its slice of the json_results dict.
    Returns the concatenated list of all TaxonomyResult objects.
    """
    costs = json_results.get("costs", {}) or {}
    benefits = json_results.get("benefits", {}) or {}

    results: list[TaxonomyResult] = []
    results += adapt_build(costs.get("build", {}))
    results += adapt_row(costs.get("row", {}))
    results += adapt_environmental(costs.get("environmental", {}))
    results += adapt_oandm(costs.get("oandm", {}))
    results += adapt_insurance(costs.get("insurance", {}))
    results += adapt_line_loss(costs.get("line_loss", {}))
    results += adapt_delay(costs.get("delay", {}))
    results += adapt_wildfire(costs.get("wildfire", {}))
    results += adapt_outage(costs.get("outage", {}))
    results += adapt_emissions_comp(costs.get("emissions", {}))
    results += adapt_facilitated_emissions(benefits.get("facilitated_emissions", {}))
    results += adapt_displacement_delay_cost(costs.get("displacement_delay", {}))
    results += adapt_congestion_curtailment(benefits.get("congestion_curtailment", {}))
    results += adapt_capital_recovery(benefits.get("capital_recovery", {}))

    for r in results:
        assert r.taxonomy_id in TAXONOMY, (
            f"Adapter produced unknown taxonomy_id: {r.taxonomy_id!r}"
        )

    return results


# ---------------------------------------------------------------------------
# Flat-key bridge for BCR calculator
# ---------------------------------------------------------------------------


def taxonomy_results_to_flat_keys(results: list[TaxonomyResult]) -> dict:
    """Convert taxonomy results to the flat-key dict consumed by compute_all_bcrs().

    This is the canonical bridge between the taxonomy system and the BCR calculator.
    """
    by_id: dict[str, TaxonomyResult] = {r.taxonomy_id: r for r in results}

    def _pv(tid: str) -> float:
        r = by_id.get(tid)
        return r.value_pv if r else 0.0

    def _nom(tid: str) -> float:
        r = by_id.get(tid)
        return r.value_nominal if r else 0.0

    build_pv = _pv("build_conductor") + _pv("build_structure") + _pv("build_converter")
    build_nom = _nom("build_conductor") + _nom("build_structure") + _nom("build_converter")
    row_cap_pv = _pv("row_acquisition") + _pv("row_holding")
    row_cap_nom = _nom("row_acquisition") + _nom("row_holding")
    energy_losses_pv = _pv("line_loss_conductor") + _pv("line_loss_converter")
    energy_losses_nom = _nom("line_loss_conductor") + _nom("line_loss_converter")

    return {
        "build_cost_pv": build_pv,
        "build_cost_nominal": build_nom,
        "row_cost_pv": row_cap_pv,
        "row_cost_nominal": row_cap_nom,
        "row_capital_pv": row_cap_pv,
        "row_capital_nominal": row_cap_nom,
        "row_rent_pv": _pv("row_rent"),
        "row_rent_nominal": _nom("row_rent"),
        "env_mitigation_pv": _pv("env_mitigation"),
        "env_mitigation_nominal": _nom("env_mitigation"),
        "oandm_pv": _pv("oandm"),
        "oandm_nominal": _nom("oandm"),
        "insurance_pv": _pv("insurance"),
        "insurance_nominal": _nom("insurance"),
        "energy_losses_pv": energy_losses_pv,
        "energy_losses_nominal": energy_losses_nom,
        "conductor_loss_pv": _pv("line_loss_conductor"),
        "converter_loss_pv": _pv("line_loss_converter"),
        "emissions_comp_cost_pv": _pv("emissions_comp"),
        "emissions_comp_cost_nominal": _nom("emissions_comp"),
        "fac_emissions_project_pv": _pv("emissions_fac"),
        "fac_emissions_project_nominal": _nom("emissions_fac"),
        "displacement_avoided_cost_pv": _pv("displacement_avoided"),
        "wildfire_pv": _pv("wildfire_eac"),
        "wildfire_nominal": _nom("wildfire_eac"),
        "outage_pv": _pv("outage_eac"),
        "outage_nominal": _nom("outage_eac"),
        "delay_cost_pv": _pv("base_delay"),
        "delay_cost_nominal": _nom("base_delay"),
        "congestion_delay_cost_pv": _pv("congestion_delay"),
        "congestion_delay_cost_nominal": _nom("congestion_delay"),
        "curtailment_delay_cost_pv": _pv("curtailment_delay"),
        "curtailment_delay_cost_nominal": _nom("curtailment_delay"),
        "congestion_benefit_pv": _pv("congestion_benefit"),
        "congestion_benefit_nominal": _nom("congestion_benefit"),
        "curtailment_benefit_pv": _pv("curtailment_benefit"),
        "curtailment_benefit_nominal": _nom("curtailment_benefit"),
        "delivered_benefit_pv": _pv("delivered_energy_benefit"),
        "delivered_benefit_nominal": _nom("delivered_energy_benefit"),
        "capital_recovery_pv": _pv("capital_recovery"),
        "capital_recovery_nominal": _nom("capital_recovery"),
        "emissions_displacement_delay_pv": _pv("emissions_displacement_delay"),
        "emissions_displacement_delay_nominal": _nom("emissions_displacement_delay"),
    }


# ---------------------------------------------------------------------------
# Serialization helper
# ---------------------------------------------------------------------------


def taxonomy_results_to_json_list(results: list[TaxonomyResult]) -> list[dict]:
    """Serialize taxonomy results to a JSON-compatible list of dicts."""
    return [
        {
            "taxonomy_id": r.taxonomy_id,
            "value_pv": r.value_pv,
            "value_nominal": r.value_nominal,
            "value_annual": r.value_annual,
            "detail": [
                {
                    "dimension": d.dimension,
                    "dimension_key": d.dimension_key,
                    "value_pv": d.value_pv,
                    "value_nominal": d.value_nominal,
                    "value_annual": d.value_annual,
                }
                for d in (r.detail or ())
            ],
        }
        for r in results
    ]
