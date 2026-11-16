# Date: 2025-11-04
# Description: Calculate benefit-cost ratios (BCR) for transmission projects.
#              Taxonomy-driven aggregation (Phase 2.3 rewrite).

from __future__ import annotations

import logging
from dataclasses import replace
from typing import Dict, Tuple

from forge.scripts.io.taxonomy import (
    ALL_BCR_DEFINITIONS,
    INSURANCE_IDS,
    OANDM_IDS,
    TAXONOMY,
    get_excluded_taxonomy_ids,
)
from forge.scripts.io.taxonomy_adapters import TaxonomyResult, taxonomy_results_to_flat_keys

BCR_VIABILITY_THRESHOLD = 1.0

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Utility functions (kept from legacy)
# ---------------------------------------------------------------------------

def safe_divide(numerator: float, denominator: float) -> float:
    """Safely divide, returning 0 if denominator is <= 0."""
    return numerator / denominator if denominator > 0 else 0.0

def format_bcr_viability(bcr_value: float) -> Tuple[str, str]:
    """Return (symbol, text) tuple for BCR viability display."""
    if bcr_value >= BCR_VIABILITY_THRESHOLD:
        return ("✅", ">= 1.0: economically viable")
    else:
        return ("❌", "< 1.0: not economically viable")

# ---------------------------------------------------------------------------
# Precomputed taxonomy ID sets for denominator/numerator resolution
# ---------------------------------------------------------------------------

_ALL_COST_IDS = frozenset(
    tid for tid, item in TAXONOMY.items() if item.side == "cost"
)
_ALL_BENEFIT_IDS = frozenset(
    tid for tid, item in TAXONOMY.items() if item.side == "benefit"
)
def _cost_ids(*, category: str, subgroup: str | None = None) -> frozenset[str]:
    return frozenset(
        tid for tid in _ALL_COST_IDS
        if TAXONOMY[tid].category == category
        and (subgroup is None or TAXONOMY[tid].subgroup == subgroup)
    )


def _benefit_ids(*, category: str) -> frozenset[str]:
    return frozenset(
        tid for tid in _ALL_BENEFIT_IDS if TAXONOMY[tid].category == category
    )


_CAPITAL_IDS = _cost_ids(category="capital")
_DELAY_PERIOD_IDS = _cost_ids(category="delay_period")
_OPERATING_IDS = _cost_ids(category="operating")
_EXTERNAL_COST_IDS = _cost_ids(category="external")
_EXTERNAL_RISK_IDS = _cost_ids(category="external", subgroup="risk")
_EXTERNAL_EMISSIONS_IDS = _cost_ids(category="external", subgroup="emissions")
_MARKET_IDS = _benefit_ids(category="market")
_EXTERNAL_BENEFIT_IDS = _benefit_ids(category="external")
_OPERATIONAL_IDS = _OPERATING_IDS - get_excluded_taxonomy_ids(["line_losses"])
_ENERGY_EMISSIONS_IDS = (
    get_excluded_taxonomy_ids(["line_losses"]) | _EXTERNAL_EMISSIONS_IDS
)
_DELAY_IDS = frozenset({"base_delay"})
_ATRR_IDS = frozenset({"capital_recovery", "row_rent"}) | OANDM_IDS | INSURANCE_IDS

_DENOM_SETS: dict[str, frozenset[str]] = {
    "all_costs": _ALL_COST_IDS,
    "atrr_delay": _ATRR_IDS | _DELAY_PERIOD_IDS,
    "revenue_requirement_loss": _ATRR_IDS | frozenset({
        "line_loss_conductor", "line_loss_converter",
    }),
}
_NUMER_SETS: dict[str, frozenset[str]] = {
    "all_benefits": _ALL_BENEFIT_IDS,
    "market": _MARKET_IDS,
    "capital_recovery": frozenset({"capital_recovery"}),
    "revenue_requirement": _ATRR_IDS,
}

# Output key generation for exclusion BCR variants
_EXCL_KEY_ORDER = ["avoided_emissions", "emissions", "line_losses", "wildfire", "outage"]
_GROUP_TO_SUFFIX: dict[str, str] = {
    "avoided_emissions": "avoided_emissions",
    "emissions": "emissions",
    "line_losses": "linelosses",
    "wildfire": "wildfire_risk",
    "outage": "outage_risk",
}

# Canonical output keys included in the BCR results dict
_BCR_OUTPUT_KEYS = frozenset({
    "build_cost_pv",
    "row_cost_pv", "acquisition_pv", "acquisition_nominal_total",
    "holding_pv", "holding_nominal",
    "row_rent_pv", "row_rent_nominal",
    "env_mitigation_pv",
    "oandm_pv", "insurance_pv",
    "oandm_line_pv", "oandm_converter_pv",
    "insurance_line_pv", "insurance_converter_pv",
    "energy_losses_pv", "conductor_loss_pv", "converter_loss_pv",
    "emissions_comp_cost_pv",
    "displacement_avoided_benefit_pv",
    "wildfire_pv", "outage_pv",
    "delay_cost_pv",
    "congestion_benefit_pv",
    "delivered_benefit_pv", "delivered_benefit_nominal",
    "capacity_value_benefit_pv",
    "capital_recovery_pv",
    "capital_recovery_pv_wacc",
})

_BUILD_IDS = frozenset({"build_conductor", "build_structure", "build_converter"})
_ROW_ACQUISITION_IDS = frozenset({"row_acquisition"})
_ROW_HOLDING_IDS = frozenset({"row_holding"})
_LINE_LOSS_IDS = frozenset({"line_loss_conductor", "line_loss_converter"})
# Flat-key sums add these directly. A null on one of them has to be bridged
# so that call returns; the sums below then apply the availability rule.
_BRIDGE_IDS = _BUILD_IDS | _ROW_ACQUISITION_IDS | _ROW_HOLDING_IDS | _LINE_LOSS_IDS

def _excl_output_suffix(exclude_groups: frozenset[str]) -> str:
    """Generate the legacy output key suffix for an exclusion variant."""
    parts = [_GROUP_TO_SUFFIX[g] for g in _EXCL_KEY_ORDER if g in exclude_groups]
    return "_and_".join(parts)

# ---------------------------------------------------------------------------
# Main BCR computation (replaces calculate_benefits + calculate_costs +
# calculate_bcr_metrics from the pre-taxonomy codebase)
# ---------------------------------------------------------------------------

def compute_all_bcrs(results: list[TaxonomyResult]) -> dict:
    """Compute all BCR metrics from taxonomy-tagged results.

    An item with ``applies is False`` counts as absent from every sum. Sums
    skip items with ``available is False``. A sum is 0.0 when no item of the
    set applies, and null when every applying item is not available. ``omitted`` names those ids
    for every key except the item keys in ``_BCR_OUTPUT_KEYS``.
    """
    by_id: dict[str, TaxonomyResult] = {r.taxonomy_id: r for r in results}

    def _sum_attr(ids: frozenset[str] | set[str], attr: str, *, wacc: bool = False):
        present = [by_id[tid] for tid in ids if tid in by_id and by_id[tid].applies]
        if not present:
            return 0.0
        available = [row for row in present if row.available]
        if not available:
            return None
        total = 0.0
        for row in available:
            value = getattr(row, attr)
            if wacc and value is None:
                raise ValueError(f"{row.taxonomy_id} has no WACC present value")
            total += value
        return total

    def _sum_pv(ids: frozenset[str] | set[str]):
        return _sum_attr(ids, "value_pv")

    def _sum_wacc(ids: frozenset[str] | set[str]):
        return _sum_attr(ids, "value_pv_wacc", wacc=True)

    def _sum_nom(ids: frozenset[str] | set[str]):
        return _sum_attr(ids, "value_nominal")

    def _omitted(ids: frozenset[str] | set[str]) -> list[str]:
        return sorted(
            tid for tid in ids
            if tid in by_id and by_id[tid].available is False
        )

    def _ratio(numerator, denominator):
        if numerator is None or denominator is None:
            return None
        return safe_divide(numerator, denominator)

    def _net(numerator, denominator):
        if numerator is None or denominator is None:
            return None
        return numerator - denominator

    bridged: list[TaxonomyResult] = []
    for row in results:
        if row.taxonomy_id in _BRIDGE_IDS and (
            row.value_pv is None or row.value_nominal is None
        ):
            bridged.append(replace(
                row,
                value_pv=0.0 if row.value_pv is None else row.value_pv,
                value_nominal=0.0 if row.value_nominal is None else row.value_nominal,
            ))
        else:
            bridged.append(row)
    flat = taxonomy_results_to_flat_keys(bridged)
    out: dict = {k: v for k, v in flat.items() if k in _BCR_OUTPUT_KEYS}
    out["oandm_pv"] = _sum_pv(OANDM_IDS)
    out["insurance_pv"] = _sum_pv(INSURANCE_IDS)
    for tid in OANDM_IDS | INSURANCE_IDS:
        key = f"{tid}_pv"
        if tid in by_id:
            row = by_id[tid]
            out[key] = row.value_pv if row.applies else None
        else:
            out[key] = 0.0
    components: dict[str, frozenset[str] | set[str]] = {}

    def put(key: str, value, ids: frozenset[str] | set[str]) -> None:
        out[key] = value
        if key not in _BCR_OUTPUT_KEYS:
            components[key] = ids

    # Aggregate item keys follow the same sum rule and stay out of omitted.
    out["build_cost_pv"] = _sum_pv(_BUILD_IDS)
    out["row_cost_pv"] = _sum_pv(_ROW_ACQUISITION_IDS)
    out["acquisition_pv"] = out["row_cost_pv"]
    out["holding_pv"] = _sum_pv(_ROW_HOLDING_IDS)
    out["acquisition_nominal_total"] = _sum_nom(_ROW_ACQUISITION_IDS)
    out["holding_nominal"] = _sum_nom(_ROW_HOLDING_IDS)
    out["energy_losses_pv"] = _sum_pv(_LINE_LOSS_IDS)
    out["conductor_loss_pv"] = _sum_pv(frozenset({"line_loss_conductor"}))
    out["converter_loss_pv"] = _sum_pv(frozenset({"line_loss_converter"}))
    put("energy_losses_nominal", _sum_nom(_LINE_LOSS_IDS), _LINE_LOSS_IDS)

    total_costs_pv = _sum_pv(_ALL_COST_IDS)
    total_costs_nominal = _sum_nom(_ALL_COST_IDS)
    total_benefits_pv = _sum_pv(_ALL_BENEFIT_IDS)
    total_benefits_nominal = _sum_nom(_ALL_BENEFIT_IDS)
    societal_ids = _ALL_BENEFIT_IDS | _ALL_COST_IDS

    put("total_costs_pv", total_costs_pv, _ALL_COST_IDS)
    put("total_costs_nominal", total_costs_nominal, _ALL_COST_IDS)
    put("total_benefits_pv", total_benefits_pv, _ALL_BENEFIT_IDS)
    put("total_benefits_nominal", total_benefits_nominal, _ALL_BENEFIT_IDS)
    put("capital_costs_pv", _sum_pv(_CAPITAL_IDS), _CAPITAL_IDS)
    put("capital_costs_nominal", _sum_nom(_CAPITAL_IDS), _CAPITAL_IDS)
    put("delay_period_costs_pv", _sum_pv(_DELAY_PERIOD_IDS), _DELAY_PERIOD_IDS)
    put("delay_period_costs_nominal", _sum_nom(_DELAY_PERIOD_IDS), _DELAY_PERIOD_IDS)
    put("operating_costs_pv", _sum_pv(_OPERATING_IDS), _OPERATING_IDS)
    put("operating_costs_nominal", _sum_nom(_OPERATING_IDS), _OPERATING_IDS)
    put("operational_costs_pv", _sum_pv(_OPERATIONAL_IDS), _OPERATIONAL_IDS)
    put("operational_costs_nominal", _sum_nom(_OPERATIONAL_IDS), _OPERATIONAL_IDS)
    put("delay_costs_pv", _sum_pv(_DELAY_IDS), _DELAY_IDS)
    put("delay_costs_nominal", _sum_nom(_DELAY_IDS), _DELAY_IDS)
    put("energy_emissions_costs_pv", _sum_pv(_ENERGY_EMISSIONS_IDS), _ENERGY_EMISSIONS_IDS)
    put(
        "energy_emissions_costs_nominal",
        _sum_nom(_ENERGY_EMISSIONS_IDS),
        _ENERGY_EMISSIONS_IDS,
    )
    put("external_costs_pv", _sum_pv(_EXTERNAL_COST_IDS), _EXTERNAL_COST_IDS)
    put("external_risk_costs_pv", _sum_pv(_EXTERNAL_RISK_IDS), _EXTERNAL_RISK_IDS)
    put("external_risk_costs_nominal", _sum_nom(_EXTERNAL_RISK_IDS), _EXTERNAL_RISK_IDS)
    put(
        "external_emissions_costs_pv",
        _sum_pv(_EXTERNAL_EMISSIONS_IDS),
        _EXTERNAL_EMISSIONS_IDS,
    )
    put("benefits_market_pv", _sum_pv(_MARKET_IDS), _MARKET_IDS)
    put("benefits_external_pv", _sum_pv(_EXTERNAL_BENEFIT_IDS), _EXTERNAL_BENEFIT_IDS)
    put("line_loss_benefit_pv", 0, frozenset())

    for bcr_def in ALL_BCR_DEFINITIONS.values():
        excluded_ids = (
            get_excluded_taxonomy_ids(list(bcr_def.exclude_groups))
            if bcr_def.exclude_groups
            else set()
        )

        # Societal ratios and exclusion variants sum value_pv. Utility and
        # ratepayer ratios, and their subtotals, sum value_pv_wacc.
        use_wacc = bcr_def.id in ("bcr_utility", "bcr_ratepayer")
        summer = _sum_wacc if use_wacc else _sum_pv
        numer_ids = _NUMER_SETS[bcr_def.numerator_rule] - excluded_ids
        denom_ids = _DENOM_SETS[bcr_def.denominator_rule] - excluded_ids
        numerator = summer(numer_ids)
        denominator = summer(denom_ids)
        bcr_value = _ratio(numerator, denominator)
        net_benefit = _net(numerator, denominator)
        ratio_ids = numer_ids | denom_ids

        if bcr_def.exclude_groups:
            suffix = _excl_output_suffix(bcr_def.exclude_groups)
            put(f"bcr_excluding_{suffix}", bcr_value, ratio_ids)
            put(f"net_benefit_excluding_{suffix}_pv", net_benefit, ratio_ids)
            put(f"total_costs_excluding_{suffix}_pv", denominator, denom_ids)
            put(f"total_benefits_excluding_{suffix}_pv", numerator, numer_ids)
        elif bcr_def.id == "bcr_societal":
            put("bcr_societal", bcr_value, ratio_ids)
            put("net_benefit_pv", net_benefit, ratio_ids)
            put(
                "net_benefit_nominal",
                _net(total_benefits_nominal, total_costs_nominal),
                societal_ids,
            )
        elif bcr_def.id == "bcr_utility":
            put("bcr_utility", bcr_value, ratio_ids)
            put("net_benefit_utility_pv", net_benefit, ratio_ids)
            put("utility_costs_pv", denominator, denom_ids)
            put("utility_benefits_pv", numerator, numer_ids)
        elif bcr_def.id == "bcr_ratepayer":
            put("bcr_ratepayer", bcr_value, ratio_ids)
            put("net_benefit_ratepayer_pv", net_benefit, ratio_ids)
            put("ratepayer_costs_pv", denominator, denom_ids)
            put("ratepayer_benefits_pv", numerator, numer_ids)

    out["omitted"] = {key: _omitted(components[key]) for key in components}
    return out


# ---------------------------------------------------------------------------
# Print summary
# ---------------------------------------------------------------------------

def print_bcr_summary(results: Dict[str, float]) -> None:
    """Print formatted BCR summary to terminal.

    A missing key prints as 0. A present None prints ``not available`` and is
    not coerced to 0 first.
    """
    def _raw(key: str):
        if key not in results:
            return 0
        return results[key]

    def _money(value) -> str:
        if value is None:
            return "not available"
        return f"${value:>15,.0f}"

    def _bcr_text(value) -> str:
        if value is None:
            return "not available"
        symbol, text = format_bcr_viability(value)
        return f"{value:>6.3f}  {symbol} ({text})"

    def _positive(key: str) -> bool:
        value = _raw(key)
        return value is not None and value > 0

    logger.info("")
    logger.info("=" * 80)
    logger.info("BENEFIT-COST RATIO ANALYSIS")
    logger.info("=" * 80)
    logger.info("")

    logger.info("BENEFITS (Present Value):")
    logger.info(f"  Congestion Reduction:        {_money(_raw('congestion_benefit_pv'))}")

    if _positive("capital_recovery_pv"):
        logger.info(f"  Capital Recovery (Rate-Based): {_money(_raw('capital_recovery_pv'))}")

    logger.info("  " + "-" * 78)
    logger.info(f"  Total Benefits:              {_money(_raw('total_benefits_pv'))}")
    logger.info("  (societal; excludes revenue transfer)")
    logger.info("")

    logger.info("COSTS (Present Value):")
    logger.info("  Capital costs:")
    logger.info(f"    Build:                     {_money(_raw('build_cost_pv'))}")
    logger.info(f"    Right-of-Way (acquisition): {_money(_raw('acquisition_pv'))}")
    logger.info(f"    Environmental:             {_money(_raw('env_mitigation_pv'))}")
    logger.info(f"    Subtotal:                  {_money(_raw('capital_costs_pv'))}")
    logger.info("")
    logger.info("  Operating costs:")
    logger.info(f"    O&M:                       {_money(_raw('oandm_pv'))}")
    logger.info(f"    Insurance (operational):  {_money(_raw('insurance_pv'))}")
    if _positive("row_rent_pv"):
        logger.info(f"    ROW rent (operational):    {_money(_raw('row_rent_pv'))}")
    if _positive("converter_loss_pv"):
        logger.info(f"    Converter Losses:          {_money(_raw('converter_loss_pv'))}")
        logger.info(f"    Conductor Losses:          {_money(_raw('conductor_loss_pv'))}")
    else:
        logger.info(f"    Energy Losses:             {_money(_raw('energy_losses_pv'))}")
    logger.info(f"    Subtotal:                  {_money(_raw('operating_costs_pv'))}")
    logger.info("")
    logger.info("  Emissions:")
    logger.info(f"    Loss-Comp. Emissions:      {_money(_raw('emissions_comp_cost_pv'))}")
    logger.info(f"    Subtotal:                  {_money(_raw('external_emissions_costs_pv'))}")
    logger.info("")
    logger.info("  Risk:")
    logger.info(f"    Wildfire:                  {_money(_raw('wildfire_pv'))}")
    logger.info(f"    Outage:                    {_money(_raw('outage_pv'))}")
    logger.info(f"    Subtotal:                  {_money(_raw('external_risk_costs_pv'))}")
    logger.info("")
    logger.info("  Delay-period costs:")
    logger.info(f"    Direct delay:              {_money(_raw('delay_cost_pv'))}")
    logger.info(f"    ROW holding:               {_money(_raw('holding_pv'))}")
    logger.info(f"    Subtotal:                  {_money(_raw('delay_period_costs_pv'))}")
    logger.info("")
    logger.info("  " + "-" * 78)
    logger.info(f"  Total Costs:                 {_money(_raw('total_costs_pv'))}")
    logger.info("")

    logger.info("BENEFIT-COST RATIOS:")
    logger.info(f"  Societal BCR:                {_bcr_text(_raw('bcr_societal'))}")
    logger.info("")
    logger.info(f"  Utility/TSP BCR:             {_bcr_text(_raw('bcr_utility'))}")
    logger.info(f"  Ratepayer BCR:               {_bcr_text(_raw('bcr_ratepayer'))}")
    logger.info("")

    logger.info("NET BENEFITS:")
    nb = _raw("net_benefit_pv")
    if nb is None:
        logger.info("  Net Benefit (PV):            not available")
    else:
        ns = "✅" if nb >= 0 else "❌"
        nt = "positive: benefits exceed costs" if nb >= 0 else "negative: costs exceed benefits"
        logger.info(f"  Net Benefit (PV):            ${nb:>15,.0f}  {ns} ({nt})")
    logger.info("")
    logger.info("=" * 80)
    logger.info("")
