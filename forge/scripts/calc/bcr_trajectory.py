# Date: 2026-07-10
# Description: Year-by-year BCR/NPV trajectory. Reads each TaxonomyResult stream
#              and discounts societal accumulators at the social rate and
#              utility and ratepayer accumulators at real WACC.

from __future__ import annotations

from typing import Any, Optional

from forge.scripts.io.taxonomy import TAXONOMY, get_excluded_taxonomy_ids

FIDELITY_TOLERANCE = 0.01  # $0.01 — IEEE 754 floating-point accumulation only; no formula disagreement
_RATIO_REL_TOLERANCE = 0.01  # 1% relative — per-ratio match vs bcr_calculator

# Taxonomy BCR ids. Exclusion variants are stored on the calculator side as
# legacy `bcr_excluding_{suffix}` keys, not these ids. Trajectory stores
# outage+wildfire as `bcr_excl_wf_out`.
_BCR_RATIO_KEYS = [
    "bcr_societal", "bcr_utility", "bcr_ratepayer",
    "bcr_excl_avoided_emissions", "bcr_excl_emissions_costs",
    "bcr_excl_all_emissions", "bcr_excl_outage",
    "bcr_excl_wildfire", "bcr_excl_outage_wildfire",
]
_BCR_CALC_KEYS = {
    "bcr_societal": "bcr_societal",
    "bcr_utility": "bcr_utility",
    "bcr_ratepayer": "bcr_ratepayer",
    "bcr_excl_avoided_emissions": "bcr_excluding_avoided_emissions",
    "bcr_excl_emissions_costs": "bcr_excluding_emissions",
    "bcr_excl_all_emissions": "bcr_excluding_avoided_emissions_and_emissions",
    "bcr_excl_outage": "bcr_excluding_outage_risk",
    "bcr_excl_wildfire": "bcr_excluding_wildfire_risk",
    "bcr_excl_outage_wildfire": "bcr_excluding_wildfire_risk_and_outage_risk",
}
_TRAJ_RATIO_ALIASES = {
    "bcr_excl_outage_wildfire": "bcr_excl_wf_out",
}

_BUCKETS = (
    "C_hard", "C_soft", "C_risk", "C_emissions",
    "B_remedial", "B_enabling", "B_avoided_emissions",
)
_COST_BUCKET = {
    "hard": "C_hard",
    "soft": "C_soft",
    "risk": "C_risk",
    "emissions": "C_emissions",
}
_BENEFIT_BUCKET = {
    "remedial": "B_remedial",
    "enabling": "B_enabling",
    "avoided_emissions": "B_avoided_emissions",
}

# Utility: revenue requirement over that set plus base delay.
# Ratepayer: remedial and enabling over the revenue requirement plus line losses.
# The four externalities are in neither set.
_UTILITY_NUMERATOR = frozenset({"capital_recovery", "oandm", "insurance", "row_rent"})
_UTILITY_DELAY = frozenset({"base_delay"})
_RATEPAYER_NUMERATOR = frozenset(
    item.id
    for item in TAXONOMY.values()
    if item.side == "benefit" and item.category in ("remedial", "enabling")
)
_RATEPAYER_DENOMINATOR = frozenset({
    "capital_recovery", "oandm", "insurance", "row_rent",
    "line_loss_conductor", "line_loss_converter",
})
_WACC_IDS = _UTILITY_NUMERATOR | _UTILITY_DELAY | _RATEPAYER_NUMERATOR | _RATEPAYER_DENOMINATOR
_WILDFIRE_IDS = get_excluded_taxonomy_ids(["wildfire"])
_OUTAGE_IDS = get_excluded_taxonomy_ids(["outage"])


def _as_float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    return float(value)


def _assert_per_ratio_fidelity(final: dict, bcr: dict) -> None:
    """Assert trajectory final-year BCR ratios match bcr_calculator values.

    Looks up calculator keys via `_BCR_CALC_KEYS` (legacy `bcr_excluding_*`
    names) and trajectory keys via `_TRAJ_RATIO_ALIASES`. Skips a ratio when
    the calculator value is near zero.
    """
    for key in _BCR_RATIO_KEYS:
        traj_key = _TRAJ_RATIO_ALIASES.get(key, key)
        traj_val = _as_float(final.get(traj_key, 0.0))
        bcr_val = _as_float(bcr.get(_BCR_CALC_KEYS[key], 0.0))
        if abs(bcr_val) > FIDELITY_TOLERANCE:
            diff = abs(traj_val - bcr_val)
            rel_diff = diff / abs(bcr_val)
            assert rel_diff < _RATIO_REL_TOLERANCE, (
                f"BCR trajectory fidelity check failed for {key}: "
                f"trajectory={traj_val:.6f}, bcr_calculator={bcr_val:.6f}, "
                f"relative diff={rel_diff:.4%}"
            )


def _field(entry: Any, name: str) -> Any:
    if isinstance(entry, dict):
        return entry.get(name)
    return getattr(entry, name, None)


def _year_nominal(stream: Any, year: int) -> float:
    """Nominal dollars in calendar year ``year`` (index ``year - 1``)."""
    if not stream or year < 1 or year > len(stream):
        return 0.0
    value = stream[year - 1]
    if value is None:
        return 0.0
    return float(value)


def _discount(nominal: float, rate: float, year: int) -> float:
    """Year-end discount. Matches ``streams.pv`` for this one year."""
    if nominal == 0.0:
        return 0.0
    return nominal / (1.0 + rate) ** year


def _sum_ids(values: dict[str, float], ids: frozenset[str] | set[str]) -> float:
    return sum(values.get(tid, 0.0) for tid in ids)


def compute_trajectory(results: dict, inputs: dict) -> list[dict]:
    """Build each row from TaxonomyResult streams.

    Societal columns and accumulators discount at ``social_discount_rate``.
    Utility and ratepayer accumulators discount at ``wacc_real``. Both rates
    come from ``results["derived_parameters"]``. Output keys are unchanged.

    Raises:
        AssertionError: if the final row's cumulative costs or benefits differ
        from ``results["bcr"]`` by ``FIDELITY_TOLERANCE`` or more, or if any
        of the nine BCR ratios diverges from the calculator by 1% or more.
    """
    timeline = inputs["01_project_technical_details"]["timeline"]
    delay_years = int(round(timeline["delay_years"]))
    construction_years = int(round(timeline["construction_years"]))
    project_lifetime = int(round(timeline["project_lifetime"]))

    derived = results["derived_parameters"]
    r_social = float(derived["social_discount_rate"])
    r_wacc = float(derived["wacc_real"])
    bcr = results.get("bcr", {}) or {}
    entries = results["taxonomy_results"]

    total_years = delay_years + construction_years + project_lifetime
    cum = {name: 0.0 for name in _BUCKETS}
    cum_wf = 0.0
    cum_out = 0.0
    cum_wacc: dict[str, float] = {}
    trajectory: list[dict] = []

    for t in range(1, total_years + 1):
        year = {name: 0.0 for name in _BUCKETS}
        year_wf = 0.0
        year_out = 0.0
        for entry in entries:
            tid = _field(entry, "taxonomy_id")
            item = TAXONOMY.get(tid)
            if item is None:
                continue
            nominal = _year_nominal(_field(entry, "stream"), t)
            if item.side in ("cost", "benefit"):
                social = _discount(nominal, r_social, t)
                bucket = (
                    _COST_BUCKET.get(item.category)
                    if item.side == "cost"
                    else _BENEFIT_BUCKET.get(item.category)
                )
                if bucket is not None:
                    year[bucket] += social
                if tid in _WILDFIRE_IDS:
                    year_wf += social
                elif tid in _OUTAGE_IDS:
                    year_out += social
            if tid in _WACC_IDS:
                cum_wacc[tid] = cum_wacc.get(tid, 0.0) + _discount(nominal, r_wacc, t)

        for name in _BUCKETS:
            cum[name] += year[name]
        cum_wf += year_wf
        cum_out += year_out

        if t <= delay_years:
            phase = "delay"
            year_operational: Optional[int] = None
        elif t <= delay_years + construction_years:
            phase = "construction"
            year_operational = None
        else:
            phase = "operation"
            year_operational = t - delay_years - construction_years

        cum_C_hard = cum["C_hard"]
        cum_C_soft = cum["C_soft"]
        cum_C_risk = cum["C_risk"]
        cum_C_emissions = cum["C_emissions"]
        cum_B_remedial = cum["B_remedial"]
        cum_B_enabling = cum["B_enabling"]
        cum_B_avoided_emissions = cum["B_avoided_emissions"]
        cum_C_total = cum_C_hard + cum_C_soft + cum_C_risk + cum_C_emissions
        cum_B_total = cum_B_remedial + cum_B_enabling + cum_B_avoided_emissions

        denom_excl_risk = cum_C_total - cum_C_risk
        denom_excl_outage = cum_C_total - cum_out
        atrr = _sum_ids(cum_wacc, _UTILITY_NUMERATOR)
        base_delay = _sum_ids(cum_wacc, _UTILITY_DELAY)
        denom_utility = atrr + base_delay
        ratepayer_benefits = _sum_ids(cum_wacc, _RATEPAYER_NUMERATOR)
        denom_ratepayer = _sum_ids(cum_wacc, _RATEPAYER_DENOMINATOR)

        bcr_societal = cum_B_total / cum_C_total if cum_C_total > 0 else None
        bcr_excl_wf_out = cum_B_total / denom_excl_risk if denom_excl_risk > 0 else None
        bcr_excl_outage = cum_B_total / denom_excl_outage if denom_excl_outage > 0 else None
        bcr_ratepayer = (
            ratepayer_benefits / denom_ratepayer if denom_ratepayer > 0 else None
        )
        bcr_utility = atrr / denom_utility if denom_utility > 0 else None

        npv_societal = cum_B_total - cum_C_total
        npv_excl_wf_out = cum_B_total - denom_excl_risk if bcr_excl_wf_out is not None else None
        npv_excl_outage = cum_B_total - denom_excl_outage if bcr_excl_outage is not None else None
        npv_ratepayer = (
            ratepayer_benefits - denom_ratepayer if bcr_ratepayer is not None else None
        )
        npv_utility = atrr - denom_utility if bcr_utility is not None else None

        denom_excl_emissions = cum_C_total - cum_C_emissions
        num_excl_all_emissions = cum_B_total - cum_B_avoided_emissions
        num_excl_av_em = num_excl_all_emissions
        bcr_excl_emissions_costs = (
            cum_B_total / denom_excl_emissions if denom_excl_emissions > 0 else None
        )
        bcr_excl_all_emissions = (
            num_excl_all_emissions / denom_excl_emissions if denom_excl_emissions > 0 else None
        )
        bcr_excl_avoided_emissions = (
            num_excl_av_em / cum_C_total if cum_C_total > 0 else None
        )
        denom_excl_wf = cum_C_total - cum_wf
        bcr_excl_wildfire = cum_B_total / denom_excl_wf if denom_excl_wf > 0 else None

        npv_excl_emissions_costs = (
            cum_B_total - denom_excl_emissions if bcr_excl_emissions_costs is not None else None
        )
        npv_excl_all_emissions = (
            num_excl_all_emissions - denom_excl_emissions
            if bcr_excl_all_emissions is not None else None
        )
        npv_excl_avoided_emissions = (
            num_excl_av_em - cum_C_total if bcr_excl_avoided_emissions is not None else None
        )
        npv_excl_wildfire = (
            cum_B_total - denom_excl_wf if bcr_excl_wildfire is not None else None
        )

        trajectory.append({
            "year": t,
            "phase": phase,
            "year_operational": year_operational,
            "pv_C_hard": year["C_hard"],
            "pv_C_soft": year["C_soft"],
            "pv_C_risk": year["C_risk"],
            "pv_C_emissions": year["C_emissions"],
            "pv_B_remedial": year["B_remedial"],
            "pv_B_enabling": year["B_enabling"],
            "pv_B_avoided_emissions": year["B_avoided_emissions"],
            "cum_C_hard": cum_C_hard,
            "cum_C_soft": cum_C_soft,
            "cum_C_risk": cum_C_risk,
            "cum_C_emissions": cum_C_emissions,
            "cum_C_total": cum_C_total,
            "cum_B_remedial": cum_B_remedial,
            "cum_B_enabling": cum_B_enabling,
            "cum_B_avoided_emissions": cum_B_avoided_emissions,
            "cum_B_total": cum_B_total,
            "bcr_societal": bcr_societal,
            "bcr_excl_wf_out": bcr_excl_wf_out,
            "bcr_excl_outage": bcr_excl_outage,
            "bcr_excl_emissions_costs": bcr_excl_emissions_costs,
            "bcr_excl_all_emissions": bcr_excl_all_emissions,
            "bcr_ratepayer": bcr_ratepayer,
            "bcr_utility": bcr_utility,
            "bcr_excl_avoided_emissions": bcr_excl_avoided_emissions,
            "bcr_excl_wildfire": bcr_excl_wildfire,
            "npv_societal": npv_societal,
            "npv_excl_wf_out": npv_excl_wf_out,
            "npv_excl_outage": npv_excl_outage,
            "npv_excl_emissions_costs": npv_excl_emissions_costs,
            "npv_excl_all_emissions": npv_excl_all_emissions,
            "npv_ratepayer": npv_ratepayer,
            "npv_utility": npv_utility,
            "npv_excl_avoided_emissions": npv_excl_avoided_emissions,
            "npv_excl_wildfire": npv_excl_wildfire,
        })

    target_total_costs_pv = bcr.get("total_costs_pv", 0.0)
    target_total_benefits_pv = bcr.get("total_benefits_pv", 0.0)
    final = trajectory[-1]
    assert abs(final["cum_C_total"] - target_total_costs_pv) < FIDELITY_TOLERANCE, (
        f"Cost fidelity: {final['cum_C_total']} vs {target_total_costs_pv}"
    )
    assert abs(final["cum_B_total"] - target_total_benefits_pv) < FIDELITY_TOLERANCE, (
        f"Benefit fidelity: {final['cum_B_total']} vs {target_total_benefits_pv}"
    )
    _assert_per_ratio_fidelity(final, bcr)

    return trajectory
