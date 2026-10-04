# Date: 2025-11-04
# Description: Calculate benefit-cost ratios (BCR) for transmission projects.
#              Taxonomy-driven aggregation (Phase 2.3 rewrite).

from __future__ import annotations

import logging
from typing import Dict, Tuple

from forge.scripts.io.taxonomy import TAXONOMY, ALL_BCR_DEFINITIONS, get_excluded_taxonomy_ids
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
_SOFT_IDS = frozenset(
    tid for tid in _ALL_COST_IDS if TAXONOMY[tid].category == "soft"
)
_HARD_IDS = frozenset(
    tid for tid in _ALL_COST_IDS if TAXONOMY[tid].category == "hard"
)
_RISK_IDS = frozenset(
    tid for tid in _ALL_COST_IDS if TAXONOMY[tid].category == "risk"
)
_EMISSIONS_IDS = frozenset(
    tid for tid in _ALL_COST_IDS if TAXONOMY[tid].category == "emissions"
)
_OPERATIONAL_IDS = frozenset(
    tid for tid in _ALL_COST_IDS if TAXONOMY[tid].subgroup == "operational"
)
_DELAY_IDS = frozenset(
    tid for tid in _ALL_COST_IDS if TAXONOMY[tid].subgroup == "delay"
)
_BASE_DELAY_IDS = frozenset({"base_delay"})
_ENERGY_EMISSIONS_IDS = frozenset(
    tid for tid in _ALL_COST_IDS
    if TAXONOMY[tid].subgroup == "energy" or TAXONOMY[tid].category == "emissions"
)
_REMEDIAL_IDS = frozenset(
    tid for tid in _ALL_BENEFIT_IDS if TAXONOMY[tid].category == "remedial"
)
_ENABLING_IDS = frozenset(
    tid for tid in _ALL_BENEFIT_IDS if TAXONOMY[tid].category == "enabling"
)
_AVOIDED_EMISSIONS_IDS = frozenset(
    tid for tid in _ALL_BENEFIT_IDS if TAXONOMY[tid].category == "avoided_emissions"
)

_DENOM_SETS: dict[str, frozenset[str]] = {
    "all_costs": _ALL_COST_IDS,
    "hard": _HARD_IDS,
    "hard_delay": _HARD_IDS | _DELAY_IDS,
    "atrr_delay": frozenset({
        "capital_recovery", "oandm", "insurance", "row_rent", "base_delay",
    }),
    "revenue_requirement_loss": frozenset({
        "capital_recovery", "oandm", "insurance", "row_rent",
        "line_loss_conductor", "line_loss_converter",
    }),
}
_NUMER_SETS: dict[str, frozenset[str]] = {
    "all_benefits": _ALL_BENEFIT_IDS,
    "remedial": _REMEDIAL_IDS,
    "remedial_enabling": _REMEDIAL_IDS | _ENABLING_IDS,
    "capital_recovery": frozenset({"capital_recovery"}),
    "revenue_requirement": frozenset({"capital_recovery", "oandm", "insurance", "row_rent"}),
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
    "row_cost_pv", "row_capital_pv", "row_capital_nominal",
    "row_rent_pv", "row_rent_nominal",
    "env_mitigation_pv",
    "oandm_pv", "insurance_pv",
    "energy_losses_pv", "conductor_loss_pv", "converter_loss_pv",
    "emissions_comp_cost_pv", "fac_emissions_project_pv",
    "displacement_avoided_benefit_pv",
    "wildfire_pv", "outage_pv",
    "delay_cost_pv", "congestion_delay_cost_pv",
    "emissions_displacement_delay_pv",
    "congestion_benefit_pv",
    "delivered_benefit_pv", "delivered_benefit_nominal",
    "capacity_value_benefit_pv",
    "capital_recovery_pv",
})

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

    Returns a flat dict with 102 keys matching the legacy output format:
    individual item PVs, category subtotals, BCR ratios, net benefits,
    and total_costs_excluding variants.
    """
    by_id: dict[str, TaxonomyResult] = {r.taxonomy_id: r for r in results}

    def _sum_pv(ids: frozenset[str]) -> float:
        return sum(by_id[tid].value_pv for tid in ids if tid in by_id)

    def _sum_nom(ids: frozenset[str]) -> float:
        return sum(by_id[tid].value_nominal for tid in ids if tid in by_id)

    # Individual item keys (filtered to legacy BCR output set)
    flat = taxonomy_results_to_flat_keys(results)
    out = {k: v for k, v in flat.items() if k in _BCR_OUTPUT_KEYS}
    # energy_losses_nominal is not in legacy BCR output but is needed by csv_equivalent
    out["energy_losses_nominal"] = flat.get("energy_losses_nominal", 0)

    # Category subtotals
    total_costs_pv = _sum_pv(_ALL_COST_IDS)
    total_costs_nominal = _sum_nom(_ALL_COST_IDS)
    total_benefits_pv = _sum_pv(_ALL_BENEFIT_IDS)
    total_benefits_nominal = _sum_nom(_ALL_BENEFIT_IDS)

    out.update({
        "total_costs_pv": total_costs_pv,
        "total_costs_nominal": total_costs_nominal,
        "total_benefits_pv": total_benefits_pv,
        "total_benefits_nominal": total_benefits_nominal,
        "hard_costs_pv": _sum_pv(_HARD_IDS),
        "soft_costs_pv": _sum_pv(_SOFT_IDS),
        "risk_costs_pv": _sum_pv(_RISK_IDS),
        "risk_costs_nominal": _sum_nom(_RISK_IDS),
        "emissions_costs_pv": _sum_pv(_EMISSIONS_IDS),
        "capital_costs_pv": _sum_pv(_HARD_IDS),
        "capital_costs_nominal": _sum_nom(_HARD_IDS),
        "operational_costs_pv": _sum_pv(_OPERATIONAL_IDS),
        "operational_costs_nominal": _sum_nom(_OPERATIONAL_IDS),
        "delay_costs_pv": _sum_pv(_DELAY_IDS),
        "delay_costs_nominal": _sum_nom(_DELAY_IDS),
        "energy_emissions_costs_pv": _sum_pv(_ENERGY_EMISSIONS_IDS),
        "energy_emissions_costs_nominal": _sum_nom(_ENERGY_EMISSIONS_IDS),
        "benefits_remedial_pv": _sum_pv(_REMEDIAL_IDS),
        "benefits_enabling_pv": _sum_pv(_ENABLING_IDS),
        "benefits_avoided_emissions_pv": _sum_pv(_AVOIDED_EMISSIONS_IDS),
        "line_loss_benefit_pv": 0,
    })

    # BCR ratios, net benefits, total_costs_excluding variants
    for bcr_def in ALL_BCR_DEFINITIONS.values():
        excluded_ids = (
            get_excluded_taxonomy_ids(list(bcr_def.exclude_groups))
            if bcr_def.exclude_groups
            else set()
        )

        numerator = _sum_pv(_NUMER_SETS[bcr_def.numerator_rule] - excluded_ids)
        denominator = _sum_pv(_DENOM_SETS[bcr_def.denominator_rule] - excluded_ids)
        bcr_value = safe_divide(numerator, denominator)
        net_benefit = numerator - denominator

        if bcr_def.exclude_groups:
            suffix = _excl_output_suffix(bcr_def.exclude_groups)
            out[f"bcr_excluding_{suffix}"] = bcr_value
            out[f"net_benefit_excluding_{suffix}_pv"] = net_benefit
            out[f"total_costs_excluding_{suffix}_pv"] = denominator
            out[f"total_benefits_excluding_{suffix}_pv"] = numerator
        elif bcr_def.id == "bcr_societal":
            out["bcr_societal"] = bcr_value
            out["net_benefit_pv"] = net_benefit
            out["net_benefit_nominal"] = total_benefits_nominal - total_costs_nominal
        elif bcr_def.id == "bcr_utility":
            out["bcr_utility"] = bcr_value
            out["net_benefit_utility_pv"] = net_benefit
        elif bcr_def.id == "bcr_ratepayer":
            out["bcr_ratepayer"] = bcr_value
            out["net_benefit_ratepayer_pv"] = net_benefit

    return out


# ---------------------------------------------------------------------------
# Print summary
# ---------------------------------------------------------------------------

def print_bcr_summary(results: Dict[str, float]) -> None:
    """Print formatted BCR summary to terminal.

    Args:
        results: The 102-key dict from compute_all_bcrs().
    """
    def _g(key: str) -> float:
        return results.get(key, 0) or 0

    logger.info("")
    logger.info("=" * 80)
    logger.info("BENEFIT-COST RATIO ANALYSIS")
    logger.info("=" * 80)
    logger.info("")

    logger.info("BENEFITS (Present Value):")
    logger.info(f"  Congestion Reduction:        ${_g('congestion_benefit_pv'):>15,.0f}")

    if _g("capital_recovery_pv") > 0:
        logger.info(f"  Capital Recovery (Rate-Based): ${_g('capital_recovery_pv'):>15,.0f}")

    logger.info("  " + "-" * 78)
    logger.info(f"  Total Benefits:              ${_g('total_benefits_pv'):>15,.0f}")
    logger.info("  (societal; excludes revenue transfer)")
    logger.info("")

    logger.info("COSTS (Present Value):")
    logger.info("  Capital Costs:")
    logger.info(f"    Build:                     ${_g('build_cost_pv'):>15,.0f}")
    logger.info(f"    Right-of-Way (capital):    ${_g('row_capital_pv'):>15,.0f}")
    logger.info(f"    Environmental:             ${_g('env_mitigation_pv'):>15,.0f}")
    logger.info(f"    Subtotal:                  ${_g('capital_costs_pv'):>15,.0f}")
    logger.info("")
    logger.info("  Operational Costs:")
    logger.info(f"    O&M:                       ${_g('oandm_pv'):>15,.0f}")
    logger.info(f"    Insurance (operational):  ${_g('insurance_pv'):>15,.0f}")
    if _g("row_rent_pv") > 0:
        logger.info(f"    ROW rent (operational):    ${_g('row_rent_pv'):>15,.0f}")
    logger.info(f"    Subtotal:                  ${_g('operational_costs_pv'):>15,.0f}")
    logger.info("")
    logger.info("  Energy & Emissions Costs:")
    if _g("converter_loss_pv") > 0:
        logger.info(f"    Converter Losses:          ${_g('converter_loss_pv'):>15,.0f}")
        logger.info(f"    Conductor Losses:          ${_g('conductor_loss_pv'):>15,.0f}")
    else:
        logger.info(f"    Energy Losses:             ${_g('energy_losses_pv'):>15,.0f}")
    logger.info(f"    Loss-Comp. Emissions:      ${_g('emissions_comp_cost_pv'):>15,.0f}")
    logger.info(f"    Subtotal:                  ${_g('energy_emissions_costs_pv'):>15,.0f}")
    logger.info("")
    logger.info("  Risk Costs:")
    logger.info(f"    Wildfire:                  ${_g('wildfire_pv'):>15,.0f}")
    logger.info(f"    Outage:                    ${_g('outage_pv'):>15,.0f}")
    logger.info(f"    Subtotal:                  ${_g('risk_costs_pv'):>15,.0f}")
    logger.info("")
    logger.info("  Delay Costs:")
    logger.info(f"    Construction Delay:        ${_g('delay_cost_pv'):>15,.0f}")
    logger.info(f"    Congestion Delay:          ${_g('congestion_delay_cost_pv'):>15,.0f}")
    logger.info(f"    Subtotal:                  ${_g('delay_costs_pv'):>15,.0f}")
    logger.info("")
    logger.info("  " + "-" * 78)
    logger.info(f"  Total Costs:                 ${_g('total_costs_pv'):>15,.0f}")
    logger.info("")

    logger.info("BENEFIT-COST RATIOS:")
    bcr_societal = _g("bcr_societal")
    viable_symbol, viable_text = format_bcr_viability(bcr_societal)
    logger.info(f"  Societal BCR:                {bcr_societal:>6.3f}  {viable_symbol} ({viable_text})")
    logger.info("")

    bcr_utility = _g("bcr_utility")
    us, ut = format_bcr_viability(bcr_utility)
    logger.info(f"  Utility/TSP BCR:             {bcr_utility:>6.3f}  {us} ({ut})")

    bcr_ratepayer = _g("bcr_ratepayer")
    rs, rt = format_bcr_viability(bcr_ratepayer)
    logger.info(f"  Ratepayer BCR:               {bcr_ratepayer:>6.3f}  {rs} ({rt})")
    logger.info("")

    logger.info("NET BENEFITS:")
    nb = _g("net_benefit_pv")
    ns = "✅" if nb >= 0 else "❌"
    nt = "positive: benefits exceed costs" if nb >= 0 else "negative: costs exceed benefits"
    logger.info(f"  Net Benefit (PV):            ${nb:>15,.0f}  {ns} ({nt})")
    logger.info("")
    logger.info("=" * 80)
    logger.info("")
