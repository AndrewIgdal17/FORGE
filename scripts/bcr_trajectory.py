# Author: Andrew Igdal
# Date: 2026-07-10
# Description: Year-by-year BCR/NPV trajectory. Post-processes a finished CTCC
#              `results` dict (after all cost/benefit modules + bcr_calculator
#              have run) into a list of per-year rows covering the delay,
#              construction, and operational phases. Enables payback-period
#              analysis, web app charts, and paper figures.
#
#              Design doc: Projects/CTCC/docs/design/2026-07-10__bcr-trajectory-spec.md
#              Plan: Projects/CTCC/docs/plans/2026-07-10__row-rent-escalation-and-bcr-trajectory.md

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from financial_utils import calculate_real_wacc

FIDELITY_TOLERANCE = 0.01  # $0.01 — IEEE 754 floating-point accumulation only; no formula disagreement

# Buckets used internally to route each stream's PV contribution.
_OUTPUT_COST_BUCKETS = ("C_hard", "C_soft", "C_risk", "C_emissions")
_OUTPUT_BENEFIT_BUCKETS = ("B_remedial", "B_enabling", "B_displacement")


@dataclass
class StreamSpec:
    """Geometric-growth operational stream: base_annual * (1+g)^(k-1), discounted.

    All streams in STREAM_REGISTRY start at COD (year D+C+1) and run for
    `project_lifetime` years — this is the "operational" phase.
    """
    key: str
    annual: float
    growth_rate: float
    discount_rate: float
    bucket: str  # "C_soft_op" | "C_risk_wf" | "C_risk_out" | "B_remedial" | "B_enabling"


@dataclass
class ArrayStreamSpec:
    """Full-fidelity stream: a module-exported year-by-year nominal array.

    Values are nominal (undiscounted), length == project_lifetime, and are
    discounted year-by-year here rather than approximated with a geometric
    formula (grid-mix evolution and SCC escalation are not simple geometric
    series).
    """
    key: str
    values: list[float]
    discount_rate: float
    bucket: str  # "C_emissions" | "B_displacement"


def _dig(d: dict, *keys: str, default: float = 0.0) -> Any:
    """Nested dict.get() that tolerates missing intermediate keys."""
    cur: Any = d
    for k in keys:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(k)
    return cur if cur is not None else default


def _growing_term(
    annual: float, growth_rate: float, discount_rate: float,
    k: int, delay_years: int, construction_years: int,
) -> float:
    """PV contribution of an operational-year-k payment from a geometric-growth
    stream, discounted back to the analysis start (year 1).

    This is the k-th term of the sum that `calculate_growing_annuity_pv()`
    computes in closed form; summing this over k=1..project_lifetime
    reproduces that function's output exactly.
    """
    if annual == 0:
        return 0.0
    exponent = delay_years + construction_years + k
    return annual * (1 + growth_rate) ** (k - 1) / (1 + discount_rate) ** exponent


def _back_calc_annual(nominal_total: float, growth_rate: float, years: int) -> float:
    """Invert calculate_nominal_growing_series() to recover the base annual amount."""
    if nominal_total == 0 or years <= 0:
        return 0.0
    if abs(growth_rate) < 1e-12:
        return nominal_total / years
    return nominal_total * growth_rate / ((1 + growth_rate) ** years - 1)


def _build_stream_registry(results: dict, inputs: dict, wacc_real: float) -> list[StreamSpec]:
    """Build the geometric-growth operational streams (Sec: Stream registry).

    Note: ROW rent is NOT included here — it has its own payment window (which
    varies by ROW agreement type and can start before COD) and is handled
    separately by `_row_rent_stream_params()` / the main loop's `pv_rent` term.
    """
    project_details = inputs["01_project_technical_details"]

    g_benefit = inputs.get("17_congestion_curtailment_reductions", {}).get(
        "benefit_price_escalation_real", 0.0
    )
    g_om = inputs.get("14_category_om_structures", {}).get(
        "om_real_escalation_rate", 0.0
    )
    g_insurance = _dig(inputs, "04_insurance", "insurance", "escalation_rate")

    cc = _dig(results, "benefits", "congestion_curtailment", default={}) or {}
    annual_congestion = cc.get("congestion_benefit_annual", 0.0)
    annual_curtailment = cc.get("curtailment_benefit_annual", 0.0)
    annual_delivered = cc.get("delivered_benefit_annual", 0.0)
    annual_capacity_value = cc.get("capacity_value_annual", 0.0)

    annual_om = _dig(results, "costs", "oandm", "total_annual")
    annual_insurance = _dig(results, "costs", "insurance", "annual_premium")
    annual_energy_losses = _dig(results, "costs", "line_loss", "annual_cost")

    return [
        StreamSpec("annual_congestion_benefit", annual_congestion, g_benefit, wacc_real, "B_remedial"),
        StreamSpec("annual_curtailment_benefit", annual_curtailment, g_benefit, wacc_real, "B_remedial"),
        StreamSpec("delivered_benefit_annual", annual_delivered, g_benefit, wacc_real, "B_enabling"),
        StreamSpec("capacity_value_annual", annual_capacity_value, g_benefit, wacc_real, "B_enabling"),
        StreamSpec("annual_om", annual_om, g_om, wacc_real, "C_soft_op"),
        StreamSpec("annual_insurance", annual_insurance, g_insurance, wacc_real, "C_soft_op"),
        StreamSpec("energy_losses_annual_cost", annual_energy_losses, g_benefit, wacc_real, "C_soft_op"),
    ]


def _row_agreement_type(inputs: dict) -> str:
    """Mirror row_costs.py's agreement-type inference (explicit override, else
    derived from reconductoring / uses_existing_row)."""
    project = inputs["01_project_technical_details"]["project"]
    explicit = project.get("row_agreement_type")
    if explicit:
        return explicit
    return (
        "lease_license_existing"
        if (project.get("project_type", "greenfield") in ("reconductoring", "rebuild")
            or project.get("uses_existing_row"))
        else "permanent_easement_new"
    )


def _row_rent_stream_params(
    results: dict, inputs: dict, delay_years: int, construction_years: int, project_lifetime: int,
) -> tuple[float, float, int, int]:
    """Recover ROW rent's true annual amount and payment window from the nominal
    lifetime total, matching row_costs.py's two timing patterns exactly:

    - `lease_license_existing`: rent starts year 1, runs delay+construction+
      lifetime years (the option/lease payment covers the whole holding period).
    - all other agreement types (permanent_easement_new, fee_simple,
      federal_hybrid): rent starts at construction start (year delay+1), runs
      construction+lifetime years.

    `permanent_easement_new` / `fee_simple` zero `yearly_rent_cost` upstream in
    row_costs.py, so `row_rent_nominal` is 0 and this resolves to a no-op annual
    rent for those cases regardless of window.

    Returns: (annual_rent, growth_rate, start_year, num_years)
    """
    g_rent = inputs.get("11_project_row_details", {}).get("row_rent_escalation_real", 0.0)
    row_rent_nominal = _dig(results, "costs", "row", "row_rent_nominal")
    agreement_type = _row_agreement_type(inputs)
    if agreement_type == "lease_license_existing":
        start_year = 1
        num_years = delay_years + construction_years + project_lifetime
    else:
        start_year = delay_years + 1
        num_years = construction_years + project_lifetime
    annual_rent = _back_calc_annual(row_rent_nominal, g_rent, num_years)
    return annual_rent, g_rent, start_year, num_years


def _build_risk_streams(results: dict, inputs: dict, social_discount_rate: float) -> list[StreamSpec]:
    """Wildfire + outage EAL/EAC streams (social discount rate, own growth rates)."""
    g_wf = _dig(inputs, "06_wildfire_costs", "wildfire", "risk_growth_rate")
    g_out = _dig(inputs, "07_outage_costs", "outage", "risk_growth_rate")
    eal_wf = _dig(results, "costs", "wildfire", "EAL")
    eac_out = _dig(results, "costs", "outage", "EAC")
    return [
        StreamSpec("EAL_wf", eal_wf, g_wf, social_discount_rate, "C_risk_wf"),
        StreamSpec("EAC_out", eac_out, g_out, social_discount_rate, "C_risk_out"),
    ]


def _build_array_streams(results: dict, social_discount_rate: float) -> list[ArrayStreamSpec]:
    """Full-fidelity annual arrays exported by emissions.py / facilitated_emissions.py.

    Note: fac_emissions_{withline,noline}_annual_values are NOT included here.
    Per taxonomy.py, `emissions_fac` is a "reporting_only" item (bucket
    "reporting") — it is diagnostic and is not part of total_costs_pv /
    total_benefits_pv. Only the loss-compensation cost (emissions_comp,
    bucket "emissions") and the displacement benefit (displacement_avoided,
    bucket "avoided_emissions") are counted; including the fac_emissions
    arrays here would break the fidelity assertion.
    """
    emissions_annual = results.get("emissions_comp_annual_values") or []
    displacement_annual = results.get("displacement_annual_values") or []
    return [
        ArrayStreamSpec("emissions_comp_annual_values", emissions_annual, social_discount_rate, "C_emissions"),
        ArrayStreamSpec("displacement_annual_values", displacement_annual, social_discount_rate, "B_displacement"),
    ]


def compute_trajectory(results: dict, inputs: dict) -> list[dict]:
    """Compute a year-by-year BCR/NPV trajectory from finished CTCC results.

    Args:
        results: The full CTCC results dict (post bcr_calculator.compute_all_bcrs()).
        inputs: The combined YAML input data (timing, discount rates, growth rates).

    Returns:
        List of per-year dicts, one row per year from analysis start (year 1
        of the delay phase, or construction if no delay) through the end of
        the operational lifetime. Length = delay_years + construction_years +
        project_lifetime.

    Raises:
        AssertionError: if the final row's cumulative costs/benefits don't
        match results["bcr"]["total_costs_pv"] / total_benefits_pv within $1.
        This is a development assertion, kept intentionally strict — a
        failure means a stream is missing or miscomputed.
    """
    project_details = inputs["01_project_technical_details"]
    timeline = project_details["timeline"]
    delay_years = int(round(timeline["delay_years"]))
    construction_years = int(round(timeline["construction_years"]))
    project_lifetime = int(round(timeline["project_lifetime"]))

    financial = inputs["03_financing"]["financial"]
    wacc_real = calculate_real_wacc(financial["wacc_nominal"], financial["inflation_rate"])
    social_discount_rate = financial["social_discount_rate"]

    bcr = results.get("bcr", {}) or {}

    # --- Hard costs: distributed uniformly across construction years -------
    build_pv = bcr.get("build_cost_pv", 0.0)
    row_capital_pv = bcr.get("row_capital_pv") or bcr.get("row_cost_pv", 0.0)
    env_mit_pv = bcr.get("env_mitigation_pv", 0.0)
    total_hard_pv = build_pv + row_capital_pv + env_mit_pv

    # --- Delay costs: distributed uniformly across delay years -------------
    # (congestion + curtailment delay opportunity cost, construction cost
    # escalation during delay, and displacement-delay emissions cost — all
    # pre-COD costs that land in the soft-cost bucket).
    total_delay_soft_pv = (
        bcr.get("delay_cost_pv", 0.0)
        + bcr.get("congestion_delay_cost_pv", 0.0)
        + bcr.get("curtailment_delay_cost_pv", 0.0)
        + bcr.get("emissions_displacement_delay_pv", 0.0)
    )
    base_delay_pv = bcr.get("delay_cost_pv", 0.0)

    # --- Revenue (ratepayer BCR denominator) --------------------------------
    capital_recovery = _dig(results, "benefits", "capital_recovery", default={}) or {}
    rate_base_real = capital_recovery.get("rate_base_real", 0.0)

    operational_streams = _build_stream_registry(results, inputs, wacc_real)
    risk_streams = _build_risk_streams(results, inputs, social_discount_rate)
    array_streams = _build_array_streams(results, social_discount_rate)
    rent_annual, rent_growth, rent_start_year, rent_num_years = _row_rent_stream_params(
        results, inputs, delay_years, construction_years, project_lifetime
    )

    D, C, L = delay_years, construction_years, project_lifetime
    total_years = D + C + L

    cum_C_hard = 0.0
    cum_C_soft = 0.0
    cum_C_risk = 0.0
    cum_C_risk_wf = 0.0
    cum_C_risk_out = 0.0
    cum_C_emissions = 0.0
    cum_B_remedial = 0.0
    cum_B_enabling = 0.0
    cum_B_displacement = 0.0
    # Internal-only accumulators (not part of the output schema) needed for
    # the ratepayer BCR denominator, which excludes delay costs, risk costs,
    # and emissions costs.
    cum_C_soft_op = 0.0
    cum_revenue = 0.0
    cum_C_delay = 0.0
    cum_base_delay = 0.0

    trajectory: list[dict] = []

    for t in range(1, total_years + 1):
        pv_C_hard = pv_C_soft = pv_C_risk = pv_C_emissions = 0.0
        pv_C_risk_wf = pv_C_risk_out = 0.0
        pv_B_remedial = pv_B_enabling = pv_B_displacement = 0.0
        pv_soft_op_year = 0.0
        pv_revenue_year = 0.0

        # ROW rent: own payment window (may start pre-COD for lease/license
        # agreements), independent of the delay/construction/operation phases
        # below — see `_row_rent_stream_params()`.
        pv_rent = 0.0
        if rent_annual and rent_start_year <= t <= rent_start_year + rent_num_years - 1:
            k_rent = t - rent_start_year + 1
            pv_rent = rent_annual * (1 + rent_growth) ** (k_rent - 1) / (1 + wacc_real) ** t

        if t <= D:
            phase = "delay"
            year_operational: Optional[int] = None
            if D > 0:
                pv_C_soft += total_delay_soft_pv / D
                cum_C_delay += total_delay_soft_pv / D
                cum_base_delay += base_delay_pv / D
        elif t <= D + C:
            phase = "construction"
            year_operational = None
            if C > 0:
                pv_C_hard += total_hard_pv / C
            # Edge case: delay_years == 0 but pre-COD delay costs are
            # nonzero (shouldn't happen in practice — delay costs are driven
            # by delay_years — but guard fidelity regardless).
            if D == 0 and t == D + 1:
                pv_C_soft += total_delay_soft_pv
                cum_C_delay += total_delay_soft_pv
                cum_base_delay += base_delay_pv
        else:
            phase = "operation"
            k = t - D - C
            year_operational = k

            for s in operational_streams:
                val = _growing_term(s.annual, s.growth_rate, s.discount_rate, k, D, C)
                if s.bucket == "B_remedial":
                    pv_B_remedial += val
                elif s.bucket == "B_enabling":
                    pv_B_enabling += val
                elif s.bucket == "C_soft_op":
                    pv_soft_op_year += val

            for s in risk_streams:
                val = _growing_term(s.annual, s.growth_rate, s.discount_rate, k, D, C)
                pv_C_risk += val
                if s.bucket == "C_risk_wf":
                    pv_C_risk_wf += val
                else:
                    pv_C_risk_out += val

            for a in array_streams:
                if 1 <= k <= len(a.values):
                    nominal_val = a.values[k - 1]
                    if nominal_val:
                        pv = nominal_val / (1 + a.discount_rate) ** (D + C + k)
                        if a.bucket == "C_emissions":
                            pv_C_emissions += pv
                        elif a.bucket == "B_displacement":
                            pv_B_displacement += pv

            pv_C_soft += pv_soft_op_year

            if L > 0:
                R_t = rate_base_real / L + rate_base_real * wacc_real * (1 - (k - 1) / L)
                pv_revenue_year = R_t / (1 + wacc_real) ** (D + C + k)

        # ROW rent lands in the soft-cost bucket regardless of phase (it can
        # fall in the delay or construction phase for lease/license
        # agreements) and counts toward the operational-soft-cost
        # accumulator used by the system/ratepayer BCR denominators, same as
        # the other soft-op streams.
        pv_C_soft += pv_rent
        pv_soft_op_year += pv_rent

        cum_C_hard += pv_C_hard
        cum_C_soft += pv_C_soft
        cum_C_risk += pv_C_risk
        cum_C_risk_wf += pv_C_risk_wf if phase == "operation" else 0.0
        cum_C_risk_out += pv_C_risk_out if phase == "operation" else 0.0
        cum_C_emissions += pv_C_emissions
        cum_B_remedial += pv_B_remedial
        cum_B_enabling += pv_B_enabling
        cum_B_displacement += pv_B_displacement
        cum_C_soft_op += pv_soft_op_year
        cum_revenue += pv_revenue_year

        cum_C_total = cum_C_hard + cum_C_soft + cum_C_risk + cum_C_emissions
        cum_B_total = cum_B_remedial + cum_B_enabling + cum_B_displacement

        # BCR perspectives (mirrors bcr_calculator.py's numerator/denominator
        # rules — see taxonomy.py BCR_DEFINITIONS for bcr_ratepayer).
        denom_excl_risk = cum_C_total - cum_C_risk
        denom_excl_outage = cum_C_total - cum_C_risk_out
        denom_ratepayer = cum_revenue + cum_C_soft_op

        bcr_societal = cum_B_total / cum_C_total if cum_C_total > 0 else None
        bcr_excl_wf_out = cum_B_total / denom_excl_risk if denom_excl_risk > 0 else None
        bcr_excl_outage = cum_B_total / denom_excl_outage if denom_excl_outage > 0 else None
        bcr_ratepayer = (
            (cum_B_remedial + cum_B_enabling) / denom_ratepayer if denom_ratepayer > 0 else None
        )

        npv_societal = cum_B_total - cum_C_total
        npv_excl_wf_out = cum_B_total - denom_excl_risk if bcr_excl_wf_out is not None else None
        npv_excl_outage = cum_B_total - denom_excl_outage if bcr_excl_outage is not None else None
        npv_ratepayer = (
            (cum_B_remedial + cum_B_enabling) - denom_ratepayer if bcr_ratepayer is not None else None
        )

        denom_excl_emissions = cum_C_total - cum_C_emissions
        num_excl_all_emissions = cum_B_total - cum_B_displacement
        bcr_excl_emissions_costs = cum_B_total / denom_excl_emissions if denom_excl_emissions > 0 else None
        bcr_excl_all_emissions = num_excl_all_emissions / denom_excl_emissions if denom_excl_emissions > 0 else None
        npv_excl_emissions_costs = cum_B_total - denom_excl_emissions if bcr_excl_emissions_costs is not None else None
        npv_excl_all_emissions = num_excl_all_emissions - denom_excl_emissions if bcr_excl_all_emissions is not None else None

        denom_utility = cum_revenue + cum_base_delay
        bcr_utility = cum_revenue / denom_utility if denom_utility > 0 else None
        num_excl_av_em = cum_B_total - cum_B_displacement
        bcr_excl_avoided_emissions = num_excl_av_em / cum_C_total if cum_C_total > 0 else None
        denom_excl_wf = cum_C_total - cum_C_risk_wf
        bcr_excl_wildfire = cum_B_total / denom_excl_wf if denom_excl_wf > 0 else None

        npv_utility = cum_revenue - denom_utility if bcr_utility is not None else None
        npv_excl_avoided_emissions = num_excl_av_em - cum_C_total if bcr_excl_avoided_emissions is not None else None
        npv_excl_wildfire = cum_B_total - denom_excl_wf if bcr_excl_wildfire is not None else None

        trajectory.append({
            "year": t,
            "phase": phase,
            "year_operational": year_operational,
            "pv_C_hard": pv_C_hard,
            "pv_C_soft": pv_C_soft,
            "pv_C_risk": pv_C_risk,
            "pv_C_emissions": pv_C_emissions,
            "pv_B_remedial": pv_B_remedial,
            "pv_B_enabling": pv_B_enabling,
            "pv_B_displacement": pv_B_displacement,
            "cum_C_hard": cum_C_hard,
            "cum_C_soft": cum_C_soft,
            "cum_C_risk": cum_C_risk,
            "cum_C_emissions": cum_C_emissions,
            "cum_C_total": cum_C_total,
            "cum_B_remedial": cum_B_remedial,
            "cum_B_enabling": cum_B_enabling,
            "cum_B_displacement": cum_B_displacement,
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

    # --- Fidelity assertion --------------------------------------------------
    target_total_costs_pv = bcr.get("total_costs_pv", 0.0)
    target_total_benefits_pv = bcr.get("total_benefits_pv", 0.0)
    final = trajectory[-1]
    assert abs(final["cum_C_total"] - target_total_costs_pv) < FIDELITY_TOLERANCE, (
        f"Cost fidelity: {final['cum_C_total']} vs {target_total_costs_pv}"
    )
    assert abs(final["cum_B_total"] - target_total_benefits_pv) < FIDELITY_TOLERANCE, (
        f"Benefit fidelity: {final['cum_B_total']} vs {target_total_benefits_pv}"
    )

    return trajectory
