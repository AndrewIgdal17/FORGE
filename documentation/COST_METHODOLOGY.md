# CTCC Cost Methodology

This document lists variables, parameters, equations, and their meanings for the cost categories used in the Comprehensive Transmission Cost Calculator (CTCC). **This methodology takes precedence** for cost categorization and notation.

The CTCC calculates numerous costs that can be broken up into 5 categories:

1. **Capital costs**
   - a. Build costs
   - b. Capital ROW costs (acquisition, holding)
   - c. Environmental Mitigation
2. **Operational costs**
   - a. O&M costs
   - b. Operational Insurance Costs
   - c. Operational ROW costs (rent)
3. **Energy/Emissions costs** (in conjunction with utilities that calculate losses)
   - a. Thermal line loss costs
   - b. Emissions costs (from extra generation due to compensating line losses)
   - c. Residual exceedance costs (exceedance remaining)
4. **Risk costs** (expected costs of risk events and liability insurance)
   - a. Wildfire liability insurance
   - b. Expected cost of wildfires
   - c. Expected cost of outages
5. **Delay costs**
   - a. Delay costs associated with permitting and construction (base delay)
   - b. Congestion delay costs (congestion issues not addressed because project stuck in delay) — while an energy cost, associated with delays to capture benefit of quick projects
   - c. Curtailment delay costs (curtailment issues not addressed because project stuck in delay) — while an energy cost, associated with delays to capture benefit of quick projects

---

## Capital Costs

### Build Costs

| Variable | Meaning / Units | Notes |
| -------- | ----------------- | ----- |
| $C_{conductor}$ | Conductor cost ($) | Not terrain adjusted, no contingency applied |
| $C_{structure}$ | Structure cost ($) | Not terrain adjusted, no contingency applied |
| $C_{converter}$ | Converter cost (if DC) ($) | Not terrain adjusted, no contingency applied |
| $C_{adj,conductor}$ | Conductor cost ($) | Terrain adjusted, no contingency applied |
| $C_{adj,structure}$ | Structure cost ($) | Terrain adjusted, no contingency applied |
| $C_{adj,converter}$ | Converter cost (if DC) ($) | Terrain adjusted, no contingency applied |
| $C_{adj,cont,conductor}$ | Conductor cost ($) | Terrain adjusted, contingency applied |
| $C_{adj,cont,structure}$ | Structure cost ($) | Terrain adjusted, contingency applied |
| $C_{adj,cont,converter}$ | Converter cost (if DC) ($) | Terrain adjusted, contingency applied |
| $F_{conductor}$ | Fixed conductor costs ($) | Conductors have both fixed and variable costs |
| $F_{structure}$ | Fixed structure costs ($) | Currently, structures have no fixed costs in the CTCC |
| $F_{converter}$ | Fixed converter costs ($) | Converters only have fixed costs |
| $V_{conductor}$ | Variable conductor costs ($/mi) | Conductors have both fixed and variable costs. The miles used are terrain adjusted miles. |
| $V_{structure}$ | Variable structure costs ($/mi) | Structures only have variable costs currently. The miles used are terrain adjusted miles. |
| $V_{converter}$ | Variable converter costs ($/mi) | Converters currently have no variable costs — only fixed costs. |
| $M_{weighted,total}$ | Total weighted miles across all terrain types (miles) | From terrain miles × terrain multipliers; see `scripts/weighted_miles.py`. |
| $r_{contingency,conductor}$ | Contingency multiplier for conductors [0,1] | |
| $r_{contingency,structure}$ | Contingency multiplier for structures [0,1] | |
| $r_{contingency,converter}$ | Contingency multiplier for converter [0,1] (if DC) | |
| $C_{build}$ | Terrain adjusted, contingency applied, total build cost | |
| $\xi_{DC}$ | Binary for DC projects (1 if DC, 0 if not) | |
| $\xi_{reconductoring}$ | Binary for reconductoring projects (0 if reconductor, 1 if not) | |

Technically
$$C_{conductor} = V_{conductor} \cdot M_{total} + F_{conductor},\quad C_{structure} = V_{structure} \cdot M_{total} + F_{structure},\quad C_{converter} = V_{converter} \cdot M_{total} + F_{converter}.$$

As of 2026-02-17, $F_{structure} = 0$ and $V_{converter} = 0$. The CTCC uses difficulty-adjusted terrain miles (weighted miles) rather than raw miles:

$$C_{adj,conductor} = V_{conductor} \cdot M_{weighted,total} + F_{conductor},\quad C_{adj,structure} = V_{structure} \cdot M_{weighted,total},\quad C_{adj,converter} = F_{converter}.$$

Contingencies:
$$C_{adj,cont,conductor} = (1 + r_{contingency,conductor}) \cdot C_{adj,conductor},$$
$$C_{adj,cont,structure} = (1 + r_{contingency,structure}) \cdot C_{adj,structure},$$
$$C_{adj,cont,converter} = (1 + r_{contingency,converter}) \cdot C_{adj,converter}.$$

Total build cost:
$$C_{build} = C_{adj,cont,conductor} + \xi_{reconductoring} \cdot C_{adj,cont,structure} + \xi_{reconductoring} \cdot C_{adj,cont,converter}.$$

(When $\xi_{reconductoring} = 0$ the project is reconductoring and structure/converter costs are excluded; when $\xi_{reconductoring} = 1$ they are included.)

---

### Capital ROW costs (acquisition, holding)

**NOTE:** ROW rent costs are not a capital cost! They are an operational cost (see 2.c).

| Variable | Meaning / Units | Notes |
| -------- | ----------------- | ----- |
| $z$ | Zone index | ROW split into zones (1–15). In calculations we use only zones where $M_z > 0$. |
| $M_z$ | Miles in zone $z$ | miles. |
| $W_{ROW}$ | ROW width | ft. Contingent on the selected tech (project category). |
| $A_z$ | Area of ROW of zone $z$ | acres. |
| $p_{acquisition,z}$ | Acquisition cost per acre, zone $z$ | $/acre (one-time). |
| $p_{hold,z}$ | Holding (option fee) per acre per year, zone $z$ | $/acre/year. |
| $p_{rent,z}$ | Rent per acre per year, zone $z$ | $/acre/year. Operational only (2.c). |
| $C_{acquisition}$ | Total one-time acquisition cost ($) | From zone sum; see equations below. |
| $C_{hold,annual}$ | Total annual holding cost ($/year) | The years here are the permitting/delay years. |
| $T_{delay}$ | Delay years | years. Used for holding. |
| $C_{hold,total}$ | Total holding cost over delay ($) | Option fee over full delay period. |
| $\xi_{acquisition}$ | Binary: acquisition counts toward capital ROW | 1 if acquisition applies, 0 if not (e.g. lease/license). Set by agreement type. |
| $\xi_{holding}$ | Binary: holding counts toward capital ROW | 1 if holding applies, 0 if not. Set by agreement type. |
| $C_{acquisition,real}$ | Real (present) value of acquisition cost ($) | Societal perspective; discounted at $r_{WACC,real}$. |
| $C_{hold,real}$ | Real (present) value of holding cost ($) | Societal perspective; discounted at $r_{WACC,real}$. |
| $r_{WACC,real}$ | Real weighted average cost of capital | decimal. Societal discount rate. |
| $C_{ROW,capital,nominal}$ | Total ROW capital costs in nominal terms ($) | |
| $C_{ROW,capital,real}$ | Total real (present) value of ROW capital costs ($) | Societal perspective. |

**Agreement type table**

| Agreement type | Acquisition | Holding | Rent (operational) |
| -------------- | ----------- | ------- | ------------------- |
| New Permanent Easement | Yes ($\xi_{acquisition}=1$) | Yes ($\xi_{holding}=1$) | No |
| Simple Fee | Yes ($\xi_{acquisition}=1$) | Yes ($\xi_{holding}=1$) | No |
| Existing Lease/License | No ($\xi_{acquisition}=0$) | No ($\xi_{holding}=0$) | Yes |
| Federal Hybrid | Yes ($\xi_{acquisition}=1$) | Yes ($\xi_{holding}=1$) | Yes |

NOTE: Reconductoring or existing ROW → Existing Lease/License; else New Permanent Easement. (In code: `permanent_easement_new`, `fee_simple`, `lease_license_existing`, `federal_hybrid`.)

**Equations**

Area of ROW per zone:
$$A_z = \frac{M_z \times 5280 \times W_{ROW}}{43560}.$$

Total acquisition cost:
$$C_{acquisition} = \sum_{z \,:\, M_z > 0} A_z \, p_{acquisition,z}.$$

Annual holding cost (for each delay year):
$$C_{hold,annual} = \sum_{z \,:\, M_z > 0} A_z \, p_{hold,z}.$$

Total holding cost over the delay:
$$C_{hold,total} = C_{hold,annual} \times T_{delay}.$$

Total nominal ROW capital cost:
$$C_{ROW,capital,nominal} = \xi_{acquisition}\, C_{acquisition} + \xi_{holding}\, C_{hold,total}.$$

**Regulatory perspective (AFUDC)**  
A timing pattern is applied and AFUDC capitalization logic is applied as for other capital costs (see `scripts/financial_utils.py` `calculate_afudc_capitalized_cost` and `19_cost_timing_patterns.yaml`: `row_acquisition`, `row_holding`).

**Societal perspective (real / present value)**  
Discount at real WACC (real = present value):
$$C_{acquisition,real} = \frac{C_{acquisition}}{(1+r_{WACC,real})^{T_{delay}}},$$
$$C_{hold,real} = \sum_{t=1}^{T_{delay}} \frac{C_{hold,annual}}{(1+r_{WACC,real})^t}.$$

Total real (present) value of ROW capital costs:
$$C_{ROW,capital,real} = \xi_{acquisition}\, C_{acquisition,real} + \xi_{holding}\, C_{hold,real}.$$

**Outputs (capital ROW)**  
- `row_capital_nominal`: $C_{ROW,capital,nominal}$.  
- `row_capital_afudc`: Capital ROW capitalized to COD (acquisition + holding).  
- `row_capital_pv`: $C_{ROW,capital,real}$ (PV of acquisition + PV of holding).  
- `acquisition_nominal`: $\xi_{acquisition}\, C_{acquisition}$.  
- `holding_nominal`: $\xi_{holding}\, C_{hold,total}$.

**Data sources**  
- `11_project_row_details.yaml`: `right_of_way` — per-zone `miles`, `acquisition_cost`, `rent_cost`, `hold_cost`.  
- `20_project_category_row_widths.yaml`: `row_width_feet` by category ($W_{ROW}$).  
- `19_cost_timing_patterns.yaml`: `row_acquisition`, `row_holding`.  
- Project: `delay_years` ($T_{delay}$), `construction_years`, `project_lifetime`, `row_agreement_type` (or default from reconductoring / uses_existing_row).

---

*Environmental Mitigation (1.c), Operational costs (2), Energy/Emissions (3), Risk (4), and Delay (5) to be documented in the same format.*
