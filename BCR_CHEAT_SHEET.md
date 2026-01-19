# BCR (Benefit-Cost Ratio) Cheat Sheet

Quick reference guide for all BCR perspectives calculated by CTCC.

---

## System/Societal Perspectives

### `bcr_system`
**Equation:** `Total Benefits (haircut) / Total Costs`

**Perspective:** Full societal/system-wide analysis

**Includes:**
- **Benefits:** Congestion reduction + Curtailment reduction + Revenue (all with conservative haircuts)
- **Costs:** Capital + Operational + Energy/Emissions + Risk + Delay (everything)

**Use Case:** Complete societal cost-benefit analysis including all externalities and risks

---

### `bcr_excluding_risk`
**Equation:** `Total Benefits (haircut) / (Total Costs - Risk Costs)`

**Perspective:** Societal perspective excluding probabilistic risk costs

**Includes:**
- **Benefits:** All benefits (congestion + curtailment + revenue)
- **Costs:** Capital + Operational + Energy/Emissions + Delay (excludes wildfire + outage + liability)

**Use Case:** Analysis when risk costs may be insured, managed separately, or contextually inappropriate (e.g., Texas rural lines with California-style wildfire assumptions)

---

### `bcr_excluding_emissions`
**Equation:** `Total Benefits (haircut) / (Total Costs - Emissions Costs)`

**Perspective:** Societal perspective excluding emissions externalities only

**Includes:**
- **Benefits:** All benefits (congestion + curtailment + revenue)
- **Costs:** Capital + Operational + Risk + Delay + Line Losses (excludes emissions only)

**Use Case:** Analysis focusing on transmission project economics without emissions externalities, but including line losses

---

### `bcr_excluding_linelosses`
**Equation:** `Total Benefits (haircut) / (Total Costs - Line Loss Costs)`

**Perspective:** Societal perspective excluding line loss costs only

**Includes:**
- **Benefits:** All benefits (congestion + curtailment + revenue)
- **Costs:** Capital + Operational + Risk + Delay + Emissions (excludes line losses only)

**Use Case:** Analysis focusing on transmission project economics without line loss costs, but including emissions

---

### `bcr_excluding_emissions_and_linelosses`
**Equation:** `Total Benefits (haircut) / (Total Costs - Emissions Costs - Line Loss Costs)`

**Perspective:** Societal perspective excluding both emissions and line losses

**Includes:**
- **Benefits:** All benefits (congestion + curtailment + revenue)
- **Costs:** Capital + Operational + Risk + Delay (excludes emissions + line losses)

**Use Case:** Analysis focusing on transmission project economics without energy/emissions externalities

---

### `bcr_excluding_emissions_and_risk`
**Equation:** `Total Benefits (haircut) / (Total Costs - Emissions Costs - Risk Costs)`

**Perspective:** Societal perspective excluding emissions and risk costs

**Includes:**
- **Benefits:** All benefits (congestion + curtailment + revenue)
- **Costs:** Capital + Operational + Delay + Line Losses (excludes emissions + risk)

**Use Case:** Core project economics from societal perspective, excluding emissions externalities and probabilistic risks, but including line losses

---

### `bcr_excluding_linelosses_and_risk`
**Equation:** `Total Benefits (haircut) / (Total Costs - Line Loss Costs - Risk Costs)`

**Perspective:** Societal perspective excluding line losses and risk costs

**Includes:**
- **Benefits:** All benefits (congestion + curtailment + revenue)
- **Costs:** Capital + Operational + Delay + Emissions (excludes line losses + risk)

**Use Case:** Core project economics from societal perspective, excluding line losses and probabilistic risks, but including emissions

---

### `bcr_excluding_emissions_and_linelosses_and_risk`
**Equation:** `Total Benefits (haircut) / (Total Costs - Emissions Costs - Line Loss Costs - Risk Costs)`

**Perspective:** Societal perspective excluding emissions, line losses, and risk costs

**Includes:**
- **Benefits:** All benefits (congestion + curtailment + revenue)
- **Costs:** Capital + Operational + Delay only

**Use Case:** Core project economics from societal perspective, excluding all externalities and probabilistic risks

---

## Capital Investment Perspectives

### `bcr_capital`
**Equation:** `Total Benefits (haircut) / Capital Costs`

**Perspective:** Capital investment return analysis

**Includes:**
- **Benefits:** All benefits (congestion + curtailment + revenue)
- **Costs:** Capital costs only (build + ROW + environmental)

**Use Case:** Quick assessment of capital investment attractiveness (but note: includes benefits utilities don't directly receive)

---

### `bcr_capital_and_delay`
**Equation:** `Total Benefits (haircut) / (Capital Costs + Delay Costs)`

**Perspective:** Capital investment including time value of money

**Includes:**
- **Benefits:** All benefits (congestion + curtailment + revenue)
- **Costs:** Capital + Delay costs (construction delay + congestion/curtailment delay + residual congestion)

**Use Case:** Capital investment analysis accounting for project delays and time value of money

---

## Stakeholder-Specific Perspectives

### `bcr_utility` 
**Equation:** `Revenue / (Capital Costs + Delay Costs + Operational Costs)`

**Perspective:** Utility or Transmission Service Provider (TSP) decision-making

**Includes:**
- **Benefits:** Revenue only (rate base recovery - what utilities actually receive)
- **Costs:** Capital + Delay + Operational (what utilities actually pay)
- **Excludes:** Line losses (socialized), Emissions (externalities), Risk (may be insured/not applicable)

**Use Case:** 
- Utility/TSP investment decisions
- Regulatory rate case analysis
- Understanding why utilities might not build (revenue doesn't cover their costs)

**Key Insight:** Utilities don't receive congestion/curtailment benefits directly - those go to ratepayers. They only get rate base recovery.

---

### `bcr_ratepayer` 
**Equation:** `(Congestion Benefits + Curtailment Benefits) / Line Loss Costs`

**Perspective:** Ratepayer/consumer perspective

**Includes:**
- **Benefits:** Congestion reduction + Curtailment reduction (what ratepayers receive)
- **Costs:** Line losses only (what ratepayers pay through rates)
- **Excludes:** Revenue (utilities get this), Capital costs (recovered through rates separately)

**Use Case:**
- Consumer advocate analysis
- Public utility commission ratepayer impact assessment
- Understanding ratepayer opposition (benefits may not exceed line loss costs they pay)

**Key Insight:** Ratepayers receive congestion/curtailment relief but pay for line losses through rates. They don't directly benefit from utility revenue.

---

### `bcr_primary`
**Equation:** `Primary Benefits / Primary Costs` (customizable via flags)

**Perspective:** Flexible primary analysis with optional exclusions

**Includes:**
- **Benefits:** Revenue (always) + Congestion (optional) + Curtailment (optional)
- **Costs:** Capital + Delay (always) + O&M (optional) + Insurance (optional) + Wildfire (optional) + Outage (optional) + Line Losses (optional) + Emissions (optional)

**Use Case:** Custom analysis with specific module inclusions/exclusions via command-line flags

**Note:** If no flags are set, equals `bcr_system`

---

## Net Benefits

All BCRs have corresponding net benefit calculations (Present Value unless noted):

### System/Societal Net Benefits
- `net_benefit_pv = Total Benefits (haircut) - Total Costs`
- `net_benefit_nominal = Total Benefits (nominal) - Total Costs (nominal)` *(undiscounted)*
- `net_benefit_primary_pv = Primary Benefits - Primary Costs` *(customizable via flags)*
- `net_benefit_excluding_risk_pv = Total Benefits - (Total Costs - Risk Costs)`
- `net_benefit_excluding_emissions_and_linelosses_pv = Total Benefits - (Total Costs - Energy/Emissions Costs)` *(excludes both emissions and line losses)*
- `net_benefit_excluding_emissions_and_linelosses_and_risk_pv = Total Benefits - (Total Costs - Energy/Emissions - Risk)` *(excludes all three)*
- `net_benefit_capital_only_pv = Total Benefits - Capital Costs`
- `net_benefit_capital_and_delay_pv = Total Benefits - (Capital Costs + Delay Costs)`

### Stakeholder-Specific Net Benefits
- `net_benefit_utility_pv = Revenue - (Capital Costs + Delay Costs + Operational Costs)`
- `net_benefit_ratepayer_pv = (Congestion Benefits + Curtailment Benefits) - Line Loss Costs`

### Partial Exclusion Net Benefits (All 8 Combinations)

Systematic exploration of all combinations excluding emissions, risk, and line losses:

| Exclude Risk | Exclude Emissions | Exclude Line Losses | Net Benefit Variable | Equation |
|-------------|-------------------|---------------------|---------------------|----------|
| No | No | No | `net_benefit_pv` | `Total Benefits - Total Costs` |
| Yes | No | No | `net_benefit_excluding_risk_pv` | `Total Benefits - (Total Costs - Risk)` |
| No | Yes | No | `net_benefit_excluding_emissions_pv` | `Total Benefits - (Total Costs - Emissions)` *(keeps line losses)* |
| No | No | Yes | `net_benefit_excluding_linelosses_pv` | `Total Benefits - (Total Costs - Line Losses)` *(keeps emissions)* |
| Yes | Yes | No | `net_benefit_excluding_emissions_and_risk_pv` | `Total Benefits - (Total Costs - Emissions - Risk)` *(keeps line losses)* |
| Yes | No | Yes | `net_benefit_excluding_linelosses_and_risk_pv` | `Total Benefits - (Total Costs - Line Losses - Risk)` *(keeps emissions)* |
| No | Yes | Yes | `net_benefit_excluding_emissions_and_linelosses_pv` | `Total Benefits - (Total Costs - Emissions - Line Losses)` *(excludes both)* |
| Yes | Yes | Yes | `net_benefit_excluding_emissions_and_linelosses_and_risk_pv` | `Total Benefits - (Total Costs - Emissions - Line Losses - Risk)` *(excludes all three)* |

**Note:** All use societal perspective (all benefits: congestion + curtailment + revenue)

**Interpretation:** Positive = benefits exceed costs, Negative = costs exceed benefits

---

## Quick Decision Guide

| Question | Use This BCR |
|----------|-------------|
| Should a utility/TSP build this? | `bcr_utility` |
| Do ratepayers benefit? | `bcr_ratepayer` |
| Is it good for society overall? | `bcr_system` or `bcr_excluding_risk` |
| Is the capital investment attractive? | `bcr_capital` or `bcr_capital_and_delay` |
| What if we ignore wildfire risk? | `bcr_excluding_risk` |
| What if we ignore emissions only? | `bcr_excluding_emissions` |
| What if we ignore line losses only? | `bcr_excluding_linelosses` |
| What if we ignore both emissions and line losses? | `bcr_excluding_emissions_and_linelosses` |
| What if we ignore emissions and risk? | `bcr_excluding_emissions_and_risk` |
| What if we ignore line losses and risk? | `bcr_excluding_linelosses_and_risk` |
| Core project economics only (no externalities, no risk)? | `bcr_excluding_emissions_and_linelosses_and_risk` |

---

## Important Notes

1. **Haircut Benefits:** Most BCRs use conservative "haircut" benefits (saturation factors applied to congestion/curtailment)
2. **Present Value:** All values are in present value (PV) terms, discounted to base year
3. **Context Matters:** 
   - Wildfire costs assume California-style catastrophic events ($5B/event)
   - For Texas rural lines, `bcr_excluding_risk` may be more appropriate
   - Line losses are socialized through rates (not direct utility costs)
   - Emissions are externalities (utilities don't pay unless carbon pricing exists)

---

## Example: Scenario 1 (Rural Overhead AC 657MW)

- `bcr_utility = 0.36` → Utility loses money (revenue doesn't cover costs)
- `bcr_ratepayer = 0.22` → Ratepayers lose money (benefits don't cover line losses)
- `bcr_system = 0.02` → Very poor societal return (wildfire risk dominates)
- `bcr_excluding_risk = 0.24` → Better but still negative (excluding wildfire)

**Interpretation:** This project doesn't make economic sense from utility or ratepayer perspectives, and only marginally from societal perspective if wildfire risk is excluded.

