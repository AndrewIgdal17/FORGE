"""Post-Tier-2-Batch-1 validation: compare current .forge outputs to pre-change reference values.

Reference values from published case studies
(the last iteration before Tier 1 + Tier 2 methodology changes).

Methodology changes that affect values:
- Tier 1: contingency 10%→20%, social DR 3%→2%, allowed return 10%→7.5%, wildfire UG 0.02→0.01,
  hydro 4→24, SOx/NOx inflation, ROW rents updated to CY2026, wetland credit $25K→$51K
- Tier 2 Batch 1: outage overhead rate 0.025→0.015, UG duration 2→80, subsea rate 0.00475→0.0007,
  DC temp correction (+22% DC losses), corona (0/6/25 kW/mi at ≤345/500/765 kV),
  BCR ratepayer numerator (all_benefits → remedial_enabling),
  marine env mitigation (2% subsea CAPEX), O&M escalation (2% growing annuity),
  soft cost multiplier (+10% on build)
"""

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCENARIOS_DIR = REPO_ROOT / "scenarios"

# ============================================================================
# REFERENCE VALUES from real-world-case-studies.tex (pre-Tier-1/Tier-2 values)
# ============================================================================

REFERENCE = {
    "CTT_Actual_Delay2": {
        "label": "CTT CREZ (2-yr delay)",
        "build_cost_pv": 503e6,  # $503M (Table 3, Capital row, 2-yr delay)
        "total_costs_pv": 10.69e9,  # $10.69B (Table 3, Total Costs)
        "total_benefits_pv": 20.08e9,  # $20.08B (Table 3, Total Benefits)
        "net_benefit_pv": 9.39e9,  # $9.39B (Table 3, Net Benefit)
        "bcr_societal": 1.88,  # Table 4
        "bcr_utility": 1.48,  # Table 4
        "bcr_ratepayer": 12.3,  # Table 4
        "outage_pv": 750e6,  # $750M (Table 3, Risk row includes WF+Outage; Table 5 Excl Outage gives $750M)
        "avoided_emissions_pv": 17.16e9,  # $17.16B (Table 3, Benefits row)
        "congestion_benefit_pv": None,  # Part of $797M remedial
        "delivered_benefit_pv": 2.12e9,  # $2.12B (Table 3, Enabling)
        "notes": "240mi AC overhead, 345kV double-circuit, ERCOT Panhandle",
    },
    "SunZia_Delay17": {
        "label": "SunZia (17-yr delay)",
        "build_cost_pv": 1.21e9,  # $1.21B (Table 2, Capital row, 17-yr delay — note: discounted from $2.30B)
        "total_costs_pv": 15.01e9,  # $15.01B (Table 2, Total Costs)
        "total_benefits_pv": 28.09e9,  # $28.09B (Table 2, Total Benefits)
        "net_benefit_pv": 13.08e9,  # $13.08B (Table 2, Net Benefit)
        "bcr_societal": 1.87,  # Table 3
        "bcr_utility": 0.88,  # Table 3
        "bcr_ratepayer": 18.8,  # Table 3
        "outage_pv": 11.8e9,  # $11.8B (Table 4 Excl Outage excluded cost)
        "avoided_emissions_pv": 23.96e9,  # $23.96B (Table 2, Benefits row)
        "congestion_benefit_pv": 0.76e9,  # Part of $0.76B remedial (Table 2)
        "delivered_benefit_pv": 3.37e9,  # $3.37B (Table 2, Enabling)
        "notes": "550mi DC overhead, 2400MW HVDC VSC, 17yr delay",
    },
    "SunZia_Delay2": {
        "label": "SunZia (2-yr delay)",
        "build_cost_pv": 2.30e9,  # $2.30B (Table 1, Hard capital) — note this is the PV at 2yr delay
        "total_costs_pv": 22.19e9,  # $22.19B (Table 2, Total Costs)
        "total_benefits_pv": 45.17e9,  # $45.17B (Table 2, Total Benefits)
        "net_benefit_pv": 22.98e9,  # $22.98B (Table 2, Net Benefit)
        "bcr_societal": 2.04,  # Table 3
        "bcr_utility": 1.49,  # Table 3
        "bcr_ratepayer": 10.7,  # Table 3
        "outage_pv": 18.4e9,  # $18.4B (Table 4 Excl Outage excluded cost for 2-yr)
        "avoided_emissions_pv": 37.32e9,  # $37.32B (Table 2, Benefits row)
        "congestion_benefit_pv": 1.45e9,  # $1.45B remedial (Table 2)
        "delivered_benefit_pv": 6.40e9,  # $6.40B (Table 2, Enabling)
        "notes": "550mi DC overhead, 2400MW HVDC VSC, 2yr counterfactual",
    },
    "TBC_Delay4": {
        "label": "Trans Bay Cable (4-yr delay)",
        "build_cost_pv": 217e6,  # $217M (Table 1, Hard capital)
        "total_costs_pv": 674e6,  # $674M (Table 2, Total Costs)
        "total_benefits_pv": 4.41e9,  # $4,410M (Table 2, Total Benefits)
        "net_benefit_pv": 3.735e9,  # $3,735M (Table 2, Net Benefit)
        "bcr_societal": 6.54,  # Table 3
        "bcr_utility": 1.11,  # Table 3
        "bcr_ratepayer": 13.0,  # Table 3
        "outage_pv": 209e6,  # $209M (Table 4 Excl Outage excluded cost)
        "avoided_emissions_pv": 2.74e9,  # $2,740M (Table 2, Benefits row)
        "congestion_benefit_pv": 134e6,  # $134M (Table 2, Remedial)
        "delivered_benefit_pv": 1.54e9,  # $1,540M (Table 2, Enabling)
        "notes": "53mi subsea HVDC, 500MW (modeled), 4yr delay",
    },
    "AEP_LRGV_ACCC": {
        "label": "AEP LRGV ACCC Reconductoring",
        "build_cost_pv": 109e6,  # $109M (Table costs, Build row)
        "total_costs_pv": 5.203e9,  # $5,203M (Table costs, Total)
        "total_benefits_pv": 8.096e9,  # $8,096M (Table benefits, Total excl revenue)
        "net_benefit_pv": 8.096e9 - 5.203e9,  # ~$2.893B
        "bcr_societal": 1.56,  # Table BCR
        "bcr_utility": 1.05,  # Table BCR
        "bcr_ratepayer": 4.1,  # Table BCR
        "outage_pv": 0,  # Zeroed intentionally
        "avoided_emissions_pv": 4.444e9,  # $4,444M (Table benefits)
        "congestion_benefit_pv": 184e6,  # $184M (Table benefits)
        "delivered_benefit_pv": 3.468e9,  # $3,468M (Table benefits)
        "notes": "240mi AC overhead reconductoring, 2598MW, 1yr delay",
    },
    "AEP_LRGV_Laredo_NewBuild": {
        "label": "AEP LRGV Laredo New Build",
        "build_cost_pv": 186e6,  # $186M (Table costs, Build row)
        "total_costs_pv": 3.681e9,  # $3,681M (Table costs, Total)
        "total_benefits_pv": 11.976e9,  # $11,976M (Table benefits, Total excl revenue)
        "net_benefit_pv": 11.976e9 - 3.681e9,  # ~$8.295B
        "bcr_societal": 3.25,  # Table BCR
        "bcr_utility": 1.09,  # Table BCR
        "bcr_ratepayer": 8.2,  # Table BCR
        "outage_pv": 0,  # Zeroed intentionally
        "avoided_emissions_pv": 7.02e9,  # $7,020M (Table benefits)
        "congestion_benefit_pv": 108e6,  # $108M (Table benefits)
        "delivered_benefit_pv": 4.848e9,  # $4,848M (Table benefits)
        "notes": "~200mi AC overhead greenfield, 1792MW, 7yr delay",
    },
}

# Known methodology changes and their expected directional effects
CHANGE_EFFECTS = """
EXPECTED DIRECTIONAL EFFECTS OF METHODOLOGY CHANGES:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Build cost PV:     ↑ (soft cost +10%, contingency 10%→20% [Tier 1])
O&M PV:            ↑ (escalation 2% growing annuity adds ~25-30%)
Outage PV:         ↓ for overhead (rate 0.025→0.015, -40%)
                   ↓↓ for subsea (rate 0.00475→0.0007, -85%)
                   ↑↑ for underground (duration 2→80, +40x)
DC line losses:    ↑ (+22% from temperature correction)
AC EHV losses:     ↑ (corona at 500kV +6 kW/mi, 765kV +25 kW/mi; 345kV unchanged)
BCR ratepayer:     ↓ (numerator narrowed: excludes avoided emissions)
Social DR effect:  ↑ benefits/costs PV (2% vs 3% — more discounting weight on future)
Insurance PV:      Same rates, but higher base (soft cost multiplier raises insurable value)
Env mitigation:    ↑ for subsea (marine 2% CAPEX added)
                   ↑ for wetland (credit $25K→$51K [Tier 1])
"""

def load_scenario(name: str) -> dict:
    path = SCENARIOS_DIR / f"{name}.forge"
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)

def extract_metrics(data: dict) -> dict:
    """Extract key comparison metrics from a .forge results dict."""
    results = data["results"]
    costs = results.get("costs", {})
    benefits = results.get("benefits", {})
    bcr = results.get("bcr", {})

    build_pv = costs.get("build", {}).get("total_pv", 0)
    total_costs_pv = bcr.get("total_costs_pv", 0)
    total_benefits_pv = bcr.get("total_benefits_pv", 0)
    net_benefit_pv = bcr.get("net_benefit_pv", 0)
    bcr_societal = bcr.get("bcr_societal", 0)
    bcr_utility = bcr.get("bcr_utility", 0)
    bcr_ratepayer = bcr.get("bcr_ratepayer", 0)
    outage_pv = costs.get("outage", {}).get("pv_cost", 0)
    wildfire_pv = costs.get("wildfire", {}).get("pv_cost", 0)

    # Benefits
    cc = benefits.get("congestion", {})
    fac = benefits.get("facilitated_emissions", {})
    congestion_pv = cc.get("congestion_benefit_pv", 0)
    delivered_pv = cc.get("delivered_benefit_pv", 0)
    avoided_emissions_pv = fac.get("displacement_avoided_benefit_pv", 0)

    # O&M and insurance
    oandm_pv = costs.get("oandm", {}).get("total_pv", 0)
    insurance_pv = costs.get("insurance", {}).get("pv_total", 0)
    env_pv = costs.get("environmental", {}).get("total_pv", 0)
    line_loss_pv = costs.get("line_loss", {}).get("total_pv", 0)

    return {
        "build_cost_pv": build_pv,
        "total_costs_pv": total_costs_pv,
        "total_benefits_pv": total_benefits_pv,
        "net_benefit_pv": net_benefit_pv,
        "bcr_societal": bcr_societal,
        "bcr_utility": bcr_utility,
        "bcr_ratepayer": bcr_ratepayer,
        "outage_pv": outage_pv,
        "wildfire_pv": wildfire_pv,
        "avoided_emissions_pv": avoided_emissions_pv,
        "congestion_benefit_pv": congestion_pv,
        "delivered_benefit_pv": delivered_pv,
        "oandm_pv": oandm_pv,
        "insurance_pv": insurance_pv,
        "env_pv": env_pv,
        "line_loss_pv": line_loss_pv,
    }

def fmt_dollar(val):
    if val is None:
        return "N/A"
    if abs(val) >= 1e9:
        return f"${val/1e9:.2f}B"
    elif abs(val) >= 1e6:
        return f"${val/1e6:.0f}M"
    else:
        return f"${val:,.0f}"

def fmt_pct_change(old, new):
    if old is None or old == 0:
        return "N/A (no ref)"
    pct = ((new - old) / abs(old)) * 100
    arrow = "↑" if pct > 0 else "↓" if pct < 0 else "→"
    return f"{arrow} {pct:+.1f}%"

def main():
    print("=" * 90)
    print("POST-TIER-2-BATCH-1 VALIDATION: Current vs. Pre-Change Reference Values")
    print("=" * 90)
    print(CHANGE_EFFECTS)

    all_flags = []

    for scenario_name, ref in REFERENCE.items():
        data = load_scenario(scenario_name)
        if data is None:
            print(f"\n⚠️  {scenario_name}: FILE NOT FOUND — skipping")
            continue

        current = extract_metrics(data)

        print(f"\n{'━' * 90}")
        print(f"  {ref['label']}  ({scenario_name}.forge)")
        print(f"  {ref['notes']}")
        print(f"{'━' * 90}")

        # Comparison table
        metrics = [
            ("Build Cost PV", "build_cost_pv"),
            ("Total Costs PV", "total_costs_pv"),
            ("Total Benefits PV", "total_benefits_pv"),
            ("Net Benefit PV", "net_benefit_pv"),
            ("BCR Societal", "bcr_societal"),
            ("BCR Utility", "bcr_utility"),
            ("BCR Ratepayer", "bcr_ratepayer"),
            ("Outage PV", "outage_pv"),
            ("Avoided Emissions PV", "avoided_emissions_pv"),
            ("Delivered Energy PV", "delivered_benefit_pv"),
            ("O&M PV", "oandm_pv"),
            ("Insurance PV", "insurance_pv"),
            ("Env Mitigation PV", "env_pv"),
            ("Line Loss PV", "line_loss_pv"),
        ]

        print(f"\n  {'Metric':<25} {'Reference':<15} {'Current':<15} {'Change':<12} {'Flag'}")
        print(f"  {'─' * 80}")

        for label, key in metrics:
            ref_val = ref.get(key)
            cur_val = current.get(key, 0)

            if key in ("bcr_societal", "bcr_utility", "bcr_ratepayer"):
                ref_str = f"{ref_val:.2f}" if ref_val is not None else "N/A"
                cur_str = f"{cur_val:.2f}" if cur_val else "0.00"
                if ref_val is not None and ref_val != 0:
                    pct = ((cur_val - ref_val) / abs(ref_val)) * 100
                    change_str = f"{pct:+.1f}%"
                else:
                    change_str = "N/A"
            else:
                ref_str = fmt_dollar(ref_val) if ref_val is not None else "N/A"
                cur_str = fmt_dollar(cur_val)
                change_str = fmt_pct_change(ref_val, cur_val) if ref_val is not None else "—"

            # Flag logic: >50% change or sign flip
            flag = ""
            if ref_val is not None and ref_val != 0:
                if key in ("bcr_societal", "bcr_utility", "bcr_ratepayer"):
                    pct = ((cur_val - ref_val) / abs(ref_val)) * 100
                else:
                    pct = ((cur_val - ref_val) / abs(ref_val)) * 100

                if abs(pct) > 100:
                    flag = "🔴 >2x"
                    all_flags.append(f"{scenario_name}/{label}: {change_str}")
                elif abs(pct) > 50:
                    flag = "⚠️  >50%"
                    all_flags.append(f"{scenario_name}/{label}: {change_str}")

            print(f"  {label:<25} {ref_str:<15} {cur_str:<15} {change_str:<12} {flag}")

    # Summary
    print(f"\n\n{'=' * 90}")
    print("SUMMARY OF FLAGS (>50% change from reference)")
    print(f"{'=' * 90}")
    if all_flags:
        for f in all_flags:
            print(f"  • {f}")
    else:
        print("  ✅ No metrics changed by more than 50% — all within expected range.")

    print(f"\n{'=' * 90}")
    print("INTERPRETATION GUIDE")
    print(f"{'=' * 90}")
    print("""
  Changes EXPECTED to be large (>50%):
  • Build cost: +32% expected (1.10 soft cost × 1.20/1.10 contingency ratio = 1.32× for Tier 1 projects)
  • O&M PV: +25-35% expected (2% growing annuity over 40yr at 5% WACC adds ~28%)
  • Outage PV (overhead): -40% expected (rate 0.025→0.015)
  • Outage PV (subsea): -85% expected (rate 0.00475→0.0007)
  • BCR Ratepayer: LARGE DROP expected (numerator narrowed from all_benefits to remedial_enabling)
  • DC line losses: +22% expected (temperature correction)
  • Benefits PV: ↑ expected (social DR 3%→2% increases PV of long-lived streams)
  • Avoided emissions: ↑ expected (social DR 3%→2%)

  Changes that would indicate a BUG:
  • Build cost decrease (should only go up from soft cost + contingency)
  • Outage PV increase for overhead/subsea (should decrease)
  • BCR societal flip from >1 to <1 without explanation
  • Any NaN or negative value where positive expected
  • Wildfire going non-zero for subsea projects
""")

if __name__ == "__main__":
    main()
