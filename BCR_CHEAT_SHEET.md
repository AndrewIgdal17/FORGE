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

### `bcr_excluding_wildfire_risk_and_outage_risk`
**Equation:** `Total Benefits (haircut) / (Total Costs - Wildfire Risk - Outage Risk)`

**Perspective:** Societal perspective excluding both wildfire and outage risk costs

**Includes:**
- **Benefits:** All benefits (congestion + curtailment + revenue)
- **Costs:** Capital + Operational + Energy/Emissions + Delay (excludes wildfire + wildfire liability + outage)

**Use Case:** Analysis when both wildfire and outage risk costs may be insured, managed separately, or contextually inappropriate. This is the renamed version of the previous `bcr_excluding_risk` metric.

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

### `bcr_excluding_wildfire_risk`
**Equation:** `Total Benefits (haircut) / (Total Costs - Wildfire Risk Costs)`

**Perspective:** Societal perspective excluding wildfire risk costs only (includes outage risk)

**Includes:**
- **Benefits:** All benefits (congestion + curtailment + revenue)
- **Costs:** Capital + Operational + Energy/Emissions + Delay + Outage Risk (excludes wildfire + wildfire liability)

**Use Case:** Analysis for regions where wildfire risk is contextually inappropriate (e.g., Virginia scenarios with California-calibrated wildfire parameters), but outage risk should be included

---

### `bcr_excluding_outage_risk`
**Equation:** `Total Benefits (haircut) / (Total Costs - Outage Risk Costs)`

**Perspective:** Societal perspective excluding outage risk costs only (includes wildfire risk)

**Includes:**
- **Benefits:** All benefits (congestion + curtailment + revenue)
- **Costs:** Capital + Operational + Energy/Emissions + Delay + Wildfire Risk (excludes outage)

**Use Case:** Analysis when outage risk may be insured or managed separately, but wildfire risk should be included

---

### `bcr_excluding_emissions_and_wildfire_risk`
**Equation:** `Total Benefits (haircut) / (Total Costs - Emissions Costs - Wildfire Risk Costs)`

**Perspective:** Societal perspective excluding emissions and wildfire risk costs

**Includes:**
- **Benefits:** All benefits (congestion + curtailment + revenue)
- **Costs:** Capital + Operational + Delay + Line Losses + Outage Risk (excludes emissions + wildfire)

**Use Case:** Core project economics excluding emissions externalities and wildfire risk, but including line losses and outage risk

---

### `bcr_excluding_emissions_and_outage_risk`
**Equation:** `Total Benefits (haircut) / (Total Costs - Emissions Costs - Outage Risk Costs)`

**Perspective:** Societal perspective excluding emissions and outage risk costs

**Includes:**
- **Benefits:** All benefits (congestion + curtailment + revenue)
- **Costs:** Capital + Operational + Delay + Line Losses + Wildfire Risk (excludes emissions + outage)

**Use Case:** Core project economics excluding emissions externalities and outage risk, but including line losses and wildfire risk

---

### `bcr_excluding_linelosses_and_wildfire_risk`
**Equation:** `Total Benefits (haircut) / (Total Costs - Line Loss Costs - Wildfire Risk Costs)`

**Perspective:** Societal perspective excluding line losses and wildfire risk costs

**Includes:**
- **Benefits:** All benefits (congestion + curtailment + revenue)
- **Costs:** Capital + Operational + Delay + Emissions + Outage Risk (excludes line losses + wildfire)

**Use Case:** Core project economics excluding line losses and wildfire risk, but including emissions and outage risk

---

### `bcr_excluding_linelosses_and_outage_risk`
**Equation:** `Total Benefits (haircut) / (Total Costs - Line Loss Costs - Outage Risk Costs)`

**Perspective:** Societal perspective excluding line losses and outage risk costs

**Includes:**
- **Benefits:** All benefits (congestion + curtailment + revenue)
- **Costs:** Capital + Operational + Delay + Emissions + Wildfire Risk (excludes line losses + outage)

**Use Case:** Core project economics excluding line losses and outage risk, but including emissions and wildfire risk

---

### `bcr_excluding_emissions_and_linelosses_and_wildfire_risk`
**Equation:** `Total Benefits (haircut) / (Total Costs - Emissions Costs - Line Loss Costs - Wildfire Risk Costs)`

**Perspective:** Societal perspective excluding emissions, line losses, and wildfire risk costs

**Includes:**
- **Benefits:** All benefits (congestion + curtailment + revenue)
- **Costs:** Capital + Operational + Delay + Outage Risk only

**Use Case:** Core project economics excluding emissions, line losses, and wildfire risk, but including outage risk

---

### `bcr_excluding_emissions_and_linelosses_and_outage_risk`
**Equation:** `Total Benefits (haircut) / (Total Costs - Emissions Costs - Line Loss Costs - Outage Risk Costs)`

**Perspective:** Societal perspective excluding emissions, line losses, and outage risk costs

**Includes:**
- **Benefits:** All benefits (congestion + curtailment + revenue)
- **Costs:** Capital + Operational + Delay + Wildfire Risk only

**Use Case:** Core project economics excluding emissions, line losses, and outage risk, but including wildfire risk

---

### `bcr_excluding_emissions_and_wildfire_risk_and_outage_risk`
**Equation:** `Total Benefits (haircut) / (Total Costs - Emissions Costs - Wildfire Risk Costs - Outage Risk Costs)`

**Perspective:** Societal perspective excluding emissions and both risk costs

**Includes:**
- **Benefits:** All benefits (congestion + curtailment + revenue)
- **Costs:** Capital + Operational + Delay + Line Losses (excludes emissions + wildfire + outage)

**Use Case:** Core project economics from societal perspective, excluding emissions externalities and both probabilistic risks, but including line losses. This is the renamed version of `bcr_excluding_emissions_and_risk`.

---

### `bcr_excluding_linelosses_and_wildfire_risk_and_outage_risk`
**Equation:** `Total Benefits (haircut) / (Total Costs - Line Loss Costs - Wildfire Risk Costs - Outage Risk Costs)`

**Perspective:** Societal perspective excluding line losses and both risk costs

**Includes:**
- **Benefits:** All benefits (congestion + curtailment + revenue)
- **Costs:** Capital + Operational + Delay + Emissions (excludes line losses + wildfire + outage)

**Use Case:** Core project economics from societal perspective, excluding line losses and both probabilistic risks, but including emissions. This is the renamed version of `bcr_excluding_linelosses_and_risk`.

---

### `bcr_excluding_emissions_and_linelosses_and_wildfire_risk_and_outage_risk`
**Equation:** `Total Benefits (haircut) / (Total Costs - Emissions Costs - Line Loss Costs - Wildfire Risk Costs - Outage Risk Costs)`

**Perspective:** Societal perspective excluding emissions, line losses, and both risk costs

**Includes:**
- **Benefits:** All benefits (congestion + curtailment + revenue)
- **Costs:** Capital + Operational + Delay only

**Use Case:** Core project economics from societal perspective, excluding all externalities and both probabilistic risks. This is the renamed version of `bcr_excluding_emissions_and_linelosses_and_risk`.

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
- `net_benefit_excluding_wildfire_risk_and_outage_risk_pv = Total Benefits - (Total Costs - Wildfire Risk - Outage Risk)` *(renamed from net_benefit_excluding_risk_pv)*
- `net_benefit_excluding_wildfire_risk_pv = Total Benefits - (Total Costs - Wildfire Risk)` *(new: excludes wildfire only)*
- `net_benefit_excluding_outage_risk_pv = Total Benefits - (Total Costs - Outage Risk)` *(new: excludes outage only)*
- `net_benefit_excluding_emissions_and_linelosses_pv = Total Benefits - (Total Costs - Energy/Emissions Costs)` *(excludes both emissions and line losses)*
- `net_benefit_excluding_emissions_and_linelosses_and_wildfire_risk_and_outage_risk_pv = Total Benefits - (Total Costs - Energy/Emissions - Wildfire Risk - Outage Risk)` *(renamed, excludes all four)*
- `net_benefit_capital_only_pv = Total Benefits - Capital Costs`
- `net_benefit_capital_and_delay_pv = Total Benefits - (Capital Costs + Delay Costs)`

### Stakeholder-Specific Net Benefits
- `net_benefit_utility_pv = Revenue - (Capital Costs + Delay Costs + Operational Costs)`
- `net_benefit_ratepayer_pv = (Congestion Benefits + Curtailment Benefits) - Line Loss Costs`

### Partial Exclusion Net Benefits (All 16 Combinations)

Systematic exploration of all combinations excluding emissions, line losses, wildfire risk, and outage risk:

| Exclude Wildfire | Exclude Outage | Exclude Emissions | Exclude Line Losses | Net Benefit Variable | Equation |
|------------------|----------------|-------------------|---------------------|---------------------|----------|
| No | No | No | No | `net_benefit_pv` | `Total Benefits - Total Costs` |
| Yes | No | No | No | `net_benefit_excluding_wildfire_risk_pv` | `Total Benefits - (Total Costs - Wildfire Risk)` |
| No | Yes | No | No | `net_benefit_excluding_outage_risk_pv` | `Total Benefits - (Total Costs - Outage Risk)` |
| Yes | Yes | No | No | `net_benefit_excluding_wildfire_risk_and_outage_risk_pv` | `Total Benefits - (Total Costs - Wildfire Risk - Outage Risk)` |
| No | No | Yes | No | `net_benefit_excluding_emissions_pv` | `Total Benefits - (Total Costs - Emissions)` *(keeps line losses)* |
| Yes | No | Yes | No | `net_benefit_excluding_emissions_and_wildfire_risk_pv` | `Total Benefits - (Total Costs - Emissions - Wildfire Risk)` |
| No | Yes | Yes | No | `net_benefit_excluding_emissions_and_outage_risk_pv` | `Total Benefits - (Total Costs - Emissions - Outage Risk)` |
| Yes | Yes | Yes | No | `net_benefit_excluding_emissions_and_wildfire_risk_and_outage_risk_pv` | `Total Benefits - (Total Costs - Emissions - Wildfire Risk - Outage Risk)` |
| No | No | No | Yes | `net_benefit_excluding_linelosses_pv` | `Total Benefits - (Total Costs - Line Losses)` *(keeps emissions)* |
| Yes | No | No | Yes | `net_benefit_excluding_linelosses_and_wildfire_risk_pv` | `Total Benefits - (Total Costs - Line Losses - Wildfire Risk)` |
| No | Yes | No | Yes | `net_benefit_excluding_linelosses_and_outage_risk_pv` | `Total Benefits - (Total Costs - Line Losses - Outage Risk)` |
| Yes | Yes | No | Yes | `net_benefit_excluding_linelosses_and_wildfire_risk_and_outage_risk_pv` | `Total Benefits - (Total Costs - Line Losses - Wildfire Risk - Outage Risk)` |
| No | No | Yes | Yes | `net_benefit_excluding_emissions_and_linelosses_pv` | `Total Benefits - (Total Costs - Emissions - Line Losses)` *(excludes both)* |
| Yes | No | Yes | Yes | `net_benefit_excluding_emissions_and_linelosses_and_wildfire_risk_pv` | `Total Benefits - (Total Costs - Emissions - Line Losses - Wildfire Risk)` |
| No | Yes | Yes | Yes | `net_benefit_excluding_emissions_and_linelosses_and_outage_risk_pv` | `Total Benefits - (Total Costs - Emissions - Line Losses - Outage Risk)` |
| Yes | Yes | Yes | Yes | `net_benefit_excluding_emissions_and_linelosses_and_wildfire_risk_and_outage_risk_pv` | `Total Benefits - (Total Costs - Emissions - Line Losses - Wildfire Risk - Outage Risk)` *(excludes all four)* |

**Note:** All use societal perspective (all benefits: congestion + curtailment + revenue)

**Interpretation:** Positive = benefits exceed costs, Negative = costs exceed benefits

---

## Quick Decision Guide

| Question | Use This BCR |
|----------|-------------|
| Should a utility/TSP build this? | `bcr_utility` |
| Do ratepayers benefit? | `bcr_ratepayer` |
| Is it good for society overall? | `bcr_system` or `bcr_excluding_wildfire_risk_and_outage_risk` |
| Is the capital investment attractive? | `bcr_capital` or `bcr_capital_and_delay` |
| What if we ignore wildfire risk (but keep outage)? | `bcr_excluding_wildfire_risk` |
| What if we ignore outage risk (but keep wildfire)? | `bcr_excluding_outage_risk` |
| What if we ignore both wildfire and outage risk? | `bcr_excluding_wildfire_risk_and_outage_risk` |
| What if we ignore emissions only? | `bcr_excluding_emissions` |
| What if we ignore line losses only? | `bcr_excluding_linelosses` |
| What if we ignore both emissions and line losses? | `bcr_excluding_emissions_and_linelosses` |
| What if we ignore emissions and both risks? | `bcr_excluding_emissions_and_wildfire_risk_and_outage_risk` |
| What if we ignore line losses and both risks? | `bcr_excluding_linelosses_and_wildfire_risk_and_outage_risk` |
| What if we ignore emissions and wildfire risk (keep outage)? | `bcr_excluding_emissions_and_wildfire_risk` |
| What if we ignore emissions and outage risk (keep wildfire)? | `bcr_excluding_emissions_and_outage_risk` |
| Core project economics only (no externalities, no risks)? | `bcr_excluding_emissions_and_linelosses_and_wildfire_risk_and_outage_risk` |

---

## Important Notes

1. **Haircut Benefits:** Most BCRs use conservative "haircut" benefits (saturation factors applied to congestion/curtailment)
2. **Present Value:** All values are in present value (PV) terms, discounted to base year
3. **Context Matters:** 
   - Wildfire costs assume California-style catastrophic events ($5B/event)
   - For regions with lower wildfire risk (e.g., Virginia, Great Plains), `bcr_excluding_wildfire_risk` may be more appropriate than `bcr_excluding_wildfire_risk_and_outage_risk`
   - Outage risk is more universal (weather, equipment failure) and generally applicable across regions
   - Line losses are socialized through rates (not direct utility costs)
   - Emissions are externalities (utilities don't pay unless carbon pricing exists)
4. **Separating Wildfire and Outage Risk:**
   - Wildfire risk is highly region-specific (California vs. Virginia vs. Great Plains)
   - Outage risk is more universal and applicable across regions
   - Use `bcr_excluding_wildfire_risk` for Virginia scenarios where California-calibrated wildfire parameters would overstate risk
   - Use `bcr_excluding_wildfire_risk_and_outage_risk` when both risks should be excluded
   - Use `bcr_excluding_outage_risk` when only outage risk should be excluded (rare, but possible if outage risk is insured/managed separately)

---

## Example: Scenario 1 (Rural Overhead AC 657MW)

- `bcr_utility = 0.36` → Utility loses money (revenue doesn't cover costs)
- `bcr_ratepayer = 0.22` → Ratepayers lose money (benefits don't cover line losses)
- `bcr_system = 0.02` → Very poor societal return (wildfire risk dominates)
- `bcr_excluding_wildfire_risk_and_outage_risk = 0.24` → Better but still negative (excluding both risks)
- `bcr_excluding_wildfire_risk = 0.XX` → Better if only wildfire risk excluded (keeps outage risk)

**Interpretation:** This project doesn't make economic sense from utility or ratepayer perspectives, and only marginally from societal perspective if wildfire risk (or both risks) is excluded. The separation of wildfire and outage risk allows for more nuanced regional analysis.

