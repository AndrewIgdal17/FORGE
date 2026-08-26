# BCR (Benefit-Cost Ratio) Cheat Sheet

Quick reference for all BCR perspectives calculated by CTCC.

## Revenue as Transfer

Revenue (the utility's annual transmission revenue requirement, ATRR) is a **transfer** from ratepayers to the utility — zero-sum from society's perspective. Societal BCRs exclude revenue. Revenue appears only in the Utility BCR (numerator) and Ratepayer BCR (denominator).

## Cost and Benefit Categories

**Benefits:**
- **Remedial** ($B_{\text{remedial}}$): congestion relief + curtailment relief
- **Enabling** ($B_{\text{enabling}}$): delivered energy benefit
- **Avoided emissions** ($B_{\text{avoided,emissions}}$): displacement of dirtier generation

**Costs:**
- **Hard** ($C_{\text{hard}}$): build + ROW capital + environmental mitigation (AFUDC-eligible, in rate base)
- **Operational** ($C_{\text{operational}}$): O&M + insurance + ROW rent
- **Energy/Emissions** ($C_{\text{loss}} + C_{\text{emissions}}$): line losses (conductor + converter) + loss-compensation emissions
- **Risk** ($C_{\text{risk}}$): expected wildfire cost + expected outage cost
- **Delay** ($C_{\text{delay}}$): base delay + congestion delay + curtailment delay + displacement delay

---

## Core BCRs (3)

### `bcr_societal` — Societal

**Formula:** $B^P / C^P$ (all benefits / all costs)

**Question:** Is this project a net positive for society?

**Audience:** Regulators, planners, policy analysts.

**BCR = 1.0:** Break-even for society. **BCR < 1.0:** Project destroys net societal value (absent unquantified benefits).

---

### `bcr_utility` — Utility / TSP

**Formula:** $\text{ATRR}_{\text{PV}} / (\text{ATRR}_{\text{PV}} + C_{\text{base\ delay}})$

**Question:** Does the revenue the utility collects cover everything the utility pays?

**Audience:** Utility financial planners, transmission service providers.

**Pure utility perspective:** Both numerator and denominator use the utility's own cost basis. ATRR (capital recovery + O&M + insurance + ROW rent) appears on both sides and cancels. What remains is the delay penalty.

**BCR = 1.0:** Structural identity for zero-delay regulated projects — revenue covers all recoverable costs by design. **BCR < 1.0:** The utility bears unrecoverable pre-construction delay costs (legal, admin, permitting) not in rate base.

---

### `bcr_ratepayer` — Ratepayer

**Formula:** $(B_{\text{remedial}} + B_{\text{enabling}}) / (\text{ATRR}_{\text{PV}} + C_{\text{loss}})$

**Question:** Do bill-relevant benefits exceed what ratepayers pay?

**Audience:** Consumer advocates (NASUCA), state PUCs.

**Numerator excludes** avoided emissions — they are a societal externality that does not reduce energy bills absent an embedded carbon price.

**BCR < 1.0:** Ratepayers pay more than they receive in bill-relevant benefits. Expected for emissions-driven or reliability-driven projects.

---

## Exclusion Variants (3)

Three variants of the societal BCR, each answering a specific sensitivity question. Additional exclusion combinations are available interactively via the Custom BCR builder.

### `bcr_excluding_avoided_emissions` — Excl. Avoided Emissions

**Formula:** $(B^P - B_{\text{avoided,emissions}}) / C^P$

**Question:** What is the BCR under the FERC-minimum benefit set (no emissions benefits)?

**Use case:** Jurisdictions that do not recognize a social cost of carbon; alignment with FERC Order 1920's seven required benefits (which exclude emissions).

---

### `bcr_excluding_wildfire_risk` — Excl. Wildfire

**Formula:** $B^P / (C^P - C_{\text{wf}})$

**Question:** What is the BCR for low-wildfire regions?

**Use case:** Projects in the Great Plains, Midwest, or other regions where wildfire risk is geographically inappropriate.

---

### `bcr_excluding_wildfire_risk_and_outage_risk` — Excl. Wildfire + Outage

**Formula:** $B^P / (C^P - C_{\text{wf}} - C_{\text{outage}})$

**Question:** What is the deterministic BCR (no probabilistic risk costs)?

**Use case:** Stakeholders who question probabilistic risk valuation methodology.

---

## Quick Decision Guide

| Question | BCR |
|---|---|
| Is it good for society overall? | `bcr_societal` |
| Should a utility build this? | `bcr_utility` |
| Do ratepayers benefit? | `bcr_ratepayer` |
| What if we exclude emissions benefits? | `bcr_excluding_avoided_emissions` |
| Low-wildfire region? | `bcr_excluding_wildfire_risk` |
| No risk costs at all? | `bcr_excluding_wildfire_risk_and_outage_risk` |

---

## Notes

1. **Present value:** All values are in PV terms, discounted to base year.
2. **AFUDC:** Capital costs use year-by-year S-curve compounding (MISO MTEP25 profiles) from construction spending to COD.
3. **Revenue model:** Declining-balance FERC formula rate (straight-line depreciation + return on declining rate base).
4. **Custom BCR:** The web app's Custom BCR builder lets users toggle any combination of 5 excludable groups (avoided emissions, loss-compensation emissions, line losses, wildfire, outage) for ad-hoc sensitivity.
