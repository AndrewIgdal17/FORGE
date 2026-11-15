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

# Nine ratios and nine NPVs. Each copies one bcr.omitted list.
_TRAJECTORY_OMITTED_SOURCES = (
    ("bcr_societal", "bcr_societal"),
    ("npv_societal", "net_benefit_pv"),
    ("bcr_utility", "bcr_utility"),
    ("npv_utility", "net_benefit_utility_pv"),
    ("bcr_ratepayer", "bcr_ratepayer"),
    ("npv_ratepayer", "net_benefit_ratepayer_pv"),
    ("bcr_excl_avoided_emissions", "bcr_excluding_avoided_emissions"),
    ("npv_excl_avoided_emissions", "net_benefit_excluding_avoided_emissions_pv"),
    ("bcr_excl_emissions_costs", "bcr_excluding_emissions"),
    ("npv_excl_emissions_costs", "net_benefit_excluding_emissions_pv"),
    ("bcr_excl_all_emissions", "bcr_excluding_avoided_emissions_and_emissions"),
    ("npv_excl_all_emissions", "net_benefit_excluding_avoided_emissions_and_emissions_pv"),
    ("bcr_excl_outage", "bcr_excluding_outage_risk"),
    ("npv_excl_outage", "net_benefit_excluding_outage_risk_pv"),
    ("bcr_excl_wildfire", "bcr_excluding_wildfire_risk"),
    ("npv_excl_wildfire", "net_benefit_excluding_wildfire_risk_pv"),
    ("bcr_excl_wf_out", "bcr_excluding_wildfire_risk_and_outage_risk"),
    ("npv_excl_wf_out", "net_benefit_excluding_wildfire_risk_and_outage_risk_pv"),
)

_BUCKETS = (
    "C_hard", "C_soft", "C_risk", "C_emissions",
    "B_remedial", "B_enabling", "B_avoided_emissions",
)

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
_WILDFIRE_IDS = frozenset(get_excluded_taxonomy_ids(["wildfire"]))
_OUTAGE_IDS = frozenset(get_excluded_taxonomy_ids(["outage"]))
_COST_IDS = frozenset(tid for tid, item in TAXONOMY.items() if item.side == "cost")
_BENEFIT_IDS = frozenset(tid for tid, item in TAXONOMY.items() if item.side == "benefit")
_BUCKET_IDS = {
    "C_hard": frozenset(
        tid for tid, item in TAXONOMY.items()
        if item.side == "cost" and item.category == "hard"
    ),
    "C_soft": frozenset(
        tid for tid, item in TAXONOMY.items()
        if item.side == "cost" and item.category == "soft"
    ),
    "C_risk": frozenset(
        tid for tid, item in TAXONOMY.items()
        if item.side == "cost" and item.category == "risk"
    ),
    "C_emissions": frozenset(
        tid for tid, item in TAXONOMY.items()
        if item.side == "cost" and item.category == "emissions"
    ),
    "B_remedial": frozenset(
        tid for tid, item in TAXONOMY.items()
        if item.side == "benefit" and item.category == "remedial"
    ),
    "B_enabling": frozenset(
        tid for tid, item in TAXONOMY.items()
        if item.side == "benefit" and item.category == "enabling"
    ),
    "B_avoided_emissions": frozenset(
        tid for tid, item in TAXONOMY.items()
        if item.side == "benefit" and item.category == "avoided_emissions"
    ),
}


def _assert_per_ratio_fidelity(final: dict, bcr: dict) -> None:
    """Assert trajectory final-year BCR ratios match bcr_calculator values.

    Looks up calculator keys via `_BCR_CALC_KEYS` (legacy `bcr_excluding_*`
    names) and trajectory keys via `_TRAJ_RATIO_ALIASES`. A missing key stays
    0. A present null on either side is a skip. A near-zero calculator value
    is also skipped.
    """
    for key in _BCR_RATIO_KEYS:
        traj_key = _TRAJ_RATIO_ALIASES.get(key, key)
        traj_val = final.get(traj_key, 0.0)
        bcr_val = bcr.get(_BCR_CALC_KEYS[key], 0.0)
        if traj_val is None or bcr_val is None:
            continue
        traj_val = float(traj_val)
        bcr_val = float(bcr_val)
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


def _entry_available(entry: Any) -> bool:
    if isinstance(entry, dict):
        if "available" not in entry:
            return True
        return bool(entry["available"])
    return bool(getattr(entry, "available", True))


def _entry_applies(entry: Any) -> bool:
    if isinstance(entry, dict):
        return bool(entry.get("applies", True))
    return bool(getattr(entry, "applies", True))


def _group_sum(
    source: dict[str, float],
    ids: frozenset[str] | set[str],
    present_ids: set[str],
    unavailable_ids: set[str],
):
    """Sum available ids. Null when every present id in the set is not available.

    An id that does not apply is never present, as in ``compute_all_bcrs``.
    """
    included = set(ids) & present_ids
    if not included:
        return 0.0
    if included <= unavailable_ids:
        return None
    return sum(source.get(tid, 0.0) for tid in included if tid not in unavailable_ids)


def _positive_ratio(numerator, denominator):
    if numerator is None or denominator is None or denominator <= 0:
        return None
    return numerator / denominator


def _difference(left, right):
    if left is None or right is None:
        return None
    return left - right


def _trajectory_omitted(bcr: dict) -> dict[str, list]:
    omitted = bcr.get("omitted") or {}
    copied: dict[str, list] = {}
    for traj_key, source_key in _TRAJECTORY_OMITTED_SOURCES:
        value = omitted.get(source_key)
        copied[traj_key] = list(value) if value else []
    return copied


def _close(actual, expected, label: str) -> None:
    if actual is None or expected is None:
        return
    assert abs(actual - expected) < FIDELITY_TOLERANCE, (
        f"{label}: {actual} vs {expected}"
    )


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
    present_ids: set[str] = set()
    unavailable_ids: set[str] = set()
    for entry in entries:
        tid = _field(entry, "taxonomy_id")
        if tid not in TAXONOMY or not _entry_applies(entry):
            continue
        present_ids.add(tid)
        if not _entry_available(entry):
            unavailable_ids.add(tid)

    def grouped(source: dict[str, float], ids: frozenset[str] | set[str]):
        return _group_sum(source, ids, present_ids, unavailable_ids)

    cum_social: dict[str, float] = {}
    cum_wacc: dict[str, float] = {}
    trajectory: list[dict] = []

    for t in range(1, total_years + 1):
        year_social: dict[str, float] = {}
        for entry in entries:
            if not _entry_available(entry):
                continue
            tid = _field(entry, "taxonomy_id")
            item = TAXONOMY.get(tid)
            if item is None:
                continue
            nominal = _year_nominal(_field(entry, "stream"), t)
            if item.side in ("cost", "benefit"):
                year_social[tid] = year_social.get(tid, 0.0) + _discount(nominal, r_social, t)
            if tid in _WACC_IDS:
                cum_wacc[tid] = cum_wacc.get(tid, 0.0) + _discount(nominal, r_wacc, t)
        for tid, amount in year_social.items():
            cum_social[tid] = cum_social.get(tid, 0.0) + amount

        if t <= delay_years:
            phase = "delay"
            year_operational: Optional[int] = None
        elif t <= delay_years + construction_years:
            phase = "construction"
            year_operational = None
        else:
            phase = "operation"
            year_operational = t - delay_years - construction_years

        year = {name: grouped(year_social, _BUCKET_IDS[name]) for name in _BUCKETS}
        cum = {name: grouped(cum_social, _BUCKET_IDS[name]) for name in _BUCKETS}
        cum_C_total = grouped(cum_social, _COST_IDS)
        cum_B_total = grouped(cum_social, _BENEFIT_IDS)
        denom_excl_risk = grouped(cum_social, _COST_IDS - _WILDFIRE_IDS - _OUTAGE_IDS)
        denom_excl_outage = grouped(cum_social, _COST_IDS - _OUTAGE_IDS)
        denom_excl_wf = grouped(cum_social, _COST_IDS - _WILDFIRE_IDS)
        denom_excl_emissions = grouped(cum_social, _COST_IDS - _BUCKET_IDS["C_emissions"])
        num_excl_av_em = grouped(cum_social, _BENEFIT_IDS - _BUCKET_IDS["B_avoided_emissions"])
        atrr = grouped(cum_wacc, _UTILITY_NUMERATOR)
        denom_utility = grouped(cum_wacc, _UTILITY_NUMERATOR | _UTILITY_DELAY)
        ratepayer_benefits = grouped(cum_wacc, _RATEPAYER_NUMERATOR)
        denom_ratepayer = grouped(cum_wacc, _RATEPAYER_DENOMINATOR)

        bcr_societal = _positive_ratio(cum_B_total, cum_C_total)
        bcr_excl_wf_out = _positive_ratio(cum_B_total, denom_excl_risk)
        bcr_excl_outage = _positive_ratio(cum_B_total, denom_excl_outage)
        bcr_ratepayer = _positive_ratio(ratepayer_benefits, denom_ratepayer)
        bcr_utility = _positive_ratio(atrr, denom_utility)
        bcr_excl_emissions_costs = _positive_ratio(cum_B_total, denom_excl_emissions)
        bcr_excl_all_emissions = _positive_ratio(num_excl_av_em, denom_excl_emissions)
        bcr_excl_avoided_emissions = _positive_ratio(num_excl_av_em, cum_C_total)
        bcr_excl_wildfire = _positive_ratio(cum_B_total, denom_excl_wf)

        npv_societal = _difference(cum_B_total, cum_C_total)
        npv_excl_wf_out = (
            _difference(cum_B_total, denom_excl_risk) if bcr_excl_wf_out is not None else None
        )
        npv_excl_outage = (
            _difference(cum_B_total, denom_excl_outage) if bcr_excl_outage is not None else None
        )
        npv_ratepayer = (
            _difference(ratepayer_benefits, denom_ratepayer) if bcr_ratepayer is not None else None
        )
        npv_utility = _difference(atrr, denom_utility) if bcr_utility is not None else None
        npv_excl_emissions_costs = (
            _difference(cum_B_total, denom_excl_emissions)
            if bcr_excl_emissions_costs is not None else None
        )
        npv_excl_all_emissions = (
            _difference(num_excl_av_em, denom_excl_emissions)
            if bcr_excl_all_emissions is not None else None
        )
        npv_excl_avoided_emissions = (
            _difference(num_excl_av_em, cum_C_total)
            if bcr_excl_avoided_emissions is not None else None
        )
        npv_excl_wildfire = (
            _difference(cum_B_total, denom_excl_wf) if bcr_excl_wildfire is not None else None
        )

        cum_C_hard = cum["C_hard"]
        cum_C_soft = cum["C_soft"]
        cum_C_risk = cum["C_risk"]
        cum_C_emissions = cum["C_emissions"]
        cum_B_remedial = cum["B_remedial"]
        cum_B_enabling = cum["B_enabling"]
        cum_B_avoided_emissions = cum["B_avoided_emissions"]

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

    results["trajectory_omitted"] = _trajectory_omitted(bcr)
    final = trajectory[-1]
    _close(final["cum_C_total"], bcr.get("total_costs_pv", 0.0), "Cost fidelity")
    _close(final["cum_B_total"], bcr.get("total_benefits_pv", 0.0), "Benefit fidelity")
    _assert_per_ratio_fidelity(final, bcr)

    return trajectory
