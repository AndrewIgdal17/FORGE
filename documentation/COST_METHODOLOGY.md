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

### Environmental mitigation (1.c)

Environmental mitigation has **base** costs (construction/restoration per effective acre by terrain and construction type) and **credit** costs (wetland and habitat off-site mitigation). For **reconductoring** projects, wetland and habitat credits are set to zero (existing ROW, no new permanent impacts).

| Variable | Meaning / Units | Notes |
| -------- | ----------------- | ----- |
| $M_{terrain}$ | Miles of a specific terrain type | Terrains: 1. Forested 2. Scrubbed Flat 3. Wetland 4. Farmland 5. Desert/Barren 6. Urban 7. Rolling Hills 8. Mountain 9. Subsea. Source: `02_project_physical_details.yaml` → `terrain.terrain_miles`. Only terrains with $M_{terrain} > 0$ are used. |
| $W_{ROW}$ | ROW width | ft. Contingent on project category. |
| $A_{terrain}$ | Base ROW area in terrain | acres. $A_{terrain} = (M_{terrain} \times 5280 \times W_{ROW})/43560$. |
| $u_{mitigation}$ | Mitigation uplift factor | Dimensionless (e.g. 1.25). Accounts for construction width beyond ROW (TCE). Source: `mitigation_uplift_factor`. |
| $A^{effective}_{terrain}$ | Effective acres for mitigation in terrain | acres. $A^{effective}_{terrain} = A_{terrain} \times u_{mitigation}$. |
| $CT$ | Construction type | From project category (overhead, underground direct buried, underground tunnel, subsea). |
| $c_{base,peracre}(terrain, CT)$ | Base mitigation cost per acre for terrain ($/acre) | Depends on terrain and construction type. Source: `09_environmental_mitigation.yaml` → `base_mitigation_cost_per_acre.<CT>.<terrain>`. |
| $C_{base,total}$ | Total base mitigation/restoration cost | $. Sum over terrains (with $M_{terrain} > 0$) of $c_{base,peracre}(terrain, CT) \times A^{effective}_{terrain}$. |
| $A^{effective impact}_{wetland}$ | Wetland impact acres (effective) | acres. Wetland terrain only: $A^{effective impact}_{wetland} = A_{wetland} \times u_{mitigation}$. |
| $A^{effective impact}_{habitat}$ | Habitat impact acres (effective), total | acres. Sum over habitat terrains: $A^{effective impact}_{habitat} = \bigl(\sum_{terrain \in habitat} A_{terrain}\bigr) \times u_{mitigation}$. Habitat = forested, scrubbed flat, desert barren, rolling hills, mountain. |
| $A^{effective impact}_{terrain,habitat}$ | Effective acres of habitat impacted for that terrain | acres. For a given habitat terrain: $A^{effective impact}_{terrain,habitat} = A_{terrain} \times u_{mitigation}$ (that terrain only, not the total). Used per term in $C_{credits,habitat}$. |
| $p_{wetland}$ | Wetland credit cost per acre | $/acre. Source: `credit_cost_per_acre.wetlands` (e.g. subtype "other"). |
| $r_{wetland}$ | Wetland credit ratio | acres of credits required per acre impacted. Source: `credit_ratios.wetlands`. |
| $p_{habitat}(terrain)$ | Habitat credit cost per acre, by terrain | $/acre. Per habitat terrain; fallback to `default` if terrain not listed. |
| $r_{habitat}(terrain)$ | Habitat credit ratio, by terrain | acres of credits required per acre impacted. Per habitat terrain; fallback to `default`. |
| $C_{credits,wetlands}$ | Wetland credit cost | $. |
| $C_{credits,habitat}$ | Habitat credit cost | $. Sum over habitat terrains (with $M_{terrain} > 0$) of $p_{habitat}(terrain) \times r_{habitat}(terrain) \times A^{effective impact}_{terrain,habitat}$. |
| $\xi_{reconductoring}$ | Binary: project is not reconductoring | 1 if not reconductoring, 0 if reconductoring. When 0, wetland and habitat credits are set to zero. |
| $C_{credits,total}$ | Total credit cost (wetland + habitat) | $. After reconductoring rule. |
| $T_{delay}$ | Delay years | years. |
| $T_{construction}$ | Construction years | years. |
| $t_{start}$ | Construction start year | $t_{start} = T_{delay} + 1$ (first year after delay; 1-based year indexing). |
| $r_{WACC,real}$ | Real WACC | decimal. Societal discount rate. |
| $C_{env.mit,nominal}$ | Total environmental mitigation cost (nominal) | $. |
| $B_{env.mit,annual}$ | Annual base for env. mitigation (PV calculation) | $/year over construction years. |
| $C_{credits,real}$ | Real (present) value of credits | $. |
| $C_{env.mit,real}$ | Total environmental mitigation cost (real / present value) | $. |

**Equations**

Base area per terrain (only terrains with $M_{terrain} > 0$):
$$A_{terrain} = \frac{M_{terrain} \times 5280 \times W_{ROW}}{43560}.$$

Effective acres (uplift for TCE):
$$A^{effective}_{terrain} = A_{terrain} \times u_{mitigation}.$$

Total base mitigation cost:
$$C_{base,total} = \sum_{terrain \,:\, M_{terrain} > 0} c_{base,peracre}(terrain, CT) \times A^{effective}_{terrain}.$$

Wetland impact acres (wetland terrain only):
$$A^{effective impact}_{wetland} = A_{wetland} \times u_{mitigation}.$$

Habitat impact acres, total (habitat = forested, scrubbed flat, desert barren, rolling hills, mountain):
$$A^{effective impact}_{habitat} = \left( \sum_{terrain \in habitat} A_{terrain} \right) \times u_{mitigation}.$$

Wetland credit cost:
$$C_{credits,wetlands} = p_{wetland} \times r_{wetland} \times A^{effective impact}_{wetland}.$$

Habitat credit cost (per-terrain effective acres $A^{effective impact}_{terrain,habitat}$ for that habitat terrain):
$$C_{credits,habitat} = \sum_{\substack{terrain \in habitat \\ M_{terrain} > 0}} p_{habitat}(terrain) \times r_{habitat}(terrain) \times A^{effective impact}_{terrain,habitat}.$$
(For each habitat terrain, $A^{effective impact}_{terrain,habitat} = A_{terrain} \times u_{mitigation}$.)

Total credit cost (reconductoring zeros out credits when $\xi_{reconductoring} = 0$):
$$C_{credits,total} = \xi_{reconductoring} \times (C_{credits,wetlands} + C_{credits,habitat}).$$

Total nominal environmental mitigation cost:
$$C_{env.mit,nominal} = C_{base,total} + C_{credits,total}.$$

**Regulatory perspective (AFUDC)**  
- Base mitigation: AFUDC-eligible; timing in `19_cost_timing_patterns.yaml` → `environmental_mitigation_base` (e.g. 0% during delay, 100% during construction).  
- Credits: AFUDC-eligible; timing → `environmental_mitigation_credits` (e.g. 20% during delay, 80% during construction).  
- Same capitalization logic as other capital costs (compound to COD). Total capitalized = base capitalized + credits capitalized.

**Societal perspective (real / present value)**  
Base mitigation spread evenly over $T_{construction}$ starting at $t_{start}$. For $T_{construction} > 0$:
$$B_{env.mit,annual} = \frac{C_{base,total}}{T_{construction}}, \qquad
C_{base,real} = \sum_{t=t_{start}}^{t_{start}+T_{construction}-1} \frac{B_{env.mit,annual}}{(1+r_{WACC,real})^t}.$$
If $T_{construction} = 0$, base is one-time at $t_{start}$: $C_{base,real} = C_{base,total} / (1+r_{WACC,real})^{t_{start}}$.

Credits one-time at construction start (year $t_{start}$):
$$C_{credits,real} = \frac{C_{credits,total}}{(1+r_{WACC,real})^{t_{start}}}.$$

Total real (present) value of environmental mitigation:
$$C_{env.mit,real} = C_{base,real} + C_{credits,real}.$$

**Outputs**  
- `total_nominal`: $C_{env.mit,nominal}$.  
- `total_afudc`: Environmental mitigation capitalized to COD (base + credits).  
- `total_pv`: $C_{env.mit,real}$.  
- `base_cost_nominal`: $C_{base,total}$.  
- `credits_nominal`: $C_{credits,total}$.  
- `credits_pv`: $C_{credits,real}$.

**Data sources**  
- `02_project_physical_details.yaml`: $M_{terrain}$.  
- `09_environmental_mitigation.yaml`: $u_{mitigation}$, $c_{base,peracre}(terrain, CT)$, $p_{wetland}$, $r_{wetland}$, $p_{habitat}(terrain)$, $r_{habitat}(terrain)$.  
- `20_project_category_row_widths.yaml`: $W_{ROW}$.  
- `19_cost_timing_patterns.yaml`: `environmental_mitigation_base`, `environmental_mitigation_credits`.  
- Project: $CT$, $\xi_{reconductoring}$, $T_{delay}$, $T_{construction}$.

---

## Operational Costs

### O&M (2.a)

O&M is operational only: it is not AFUDC-eligible (no regulatory capitalization). In CTCC it is:

- **Nominal:** undiscounted sum of annual O&M over project lifetime.
- **Real (societal):** present value of that annual stream from COD to end of life, discounted at real WACC.

| Variable | Meaning / Units | Notes |
| -------- | ----------------- | ----- |
| $M_{total}$ | Total line length | miles. From physical details. |
| $M_{terrain}$ | Miles in terrain type | forested, scrubbed_flat, wetland, farmland, desert_barren, urban, rolling_hills, mountain, subsea. |
| $T_{delay}$ | Delay years | before construction. |
| $T_{construction}$ | Construction years | |
| $T_{lifetime}$ | Project lifetime | years of operation (O&M accrues over this). |
| $t_{COD}$ | Commercial operation date (year) | $t_{COD} = T_{delay} + T_{construction} + 1$ (1-based; first year of O&M). |
| $r_{WACC,real}$ | Real WACC | decimal; used to discount O&M. |
| $CT$ | Construction type | Overhead, Underground direct-buried, Underground tunnel, Subsea. |
| $c_{conductor}$ | Conductor O&M | $/mile/year. By category (construction, AC/DC, capacity, conductor, converter). Source: `13_category_om_conductors.yaml` → `variable_cost_per_mile_year`. |
| $c_{converter}$ | Converter O&M | $/mile/year. By category; 0 for AC. Source: `15_category_om_converters.yaml` → `converter_om_cost_per_mile_year`. |
| $n_{structure}(terrain)$ | Structures per mile | By terrain. Overhead only. Source: `14_category_om_structures.yaml` (e.g. structures_per_mile_forested, …). |
| $N_{structure}$ | Total structures | Overhead: $N_{structure} = \sum_{terrain} M_{terrain} \times n_{structure}(terrain)$. Non-overhead: not used (see $c_{structure,mi}$). |
| $c_{structure}$ | Cost per structure per year | $/structure/year. Overhead only. Source: `14_category_om_structures.yaml` → `cost_per_structure_per_year`. |
| $c_{structure,mi}$ | Structure O&M per mile per year | $/mile/year. Non-overhead only; one value per construction type (often 0). Source: `14_category_om_structures.yaml` → `variable_cost_per_mile_year`. |
| $c_{veg}(terrain)$ | Vegetation management | $/mile/year by terrain. Overhead only. Source: `12_project_om_vegetation_management.yaml` → vegetation_management_om_costs\[CT\]\[terrain\]. |
| $C_{O\&M,annual}$ | Total annual O&M | $/year. Sum of conductor + converter + structure + vegetation. |
| $C_{O\&M,nominal}$ | O&M cost (nominal) | Undiscounted lifetime O&M. |
| $C_{O\&M,real}$ | O&M cost (real / PV) | Present value of O&M from $t_{COD}$ over $T_{lifetime}$. |

**Equations**

1. COD (first year of O&M)

$$t_{COD} = T_{delay} + T_{construction} + 1$$

(1-based; first year of operation.)

2. Conductor (annual)

$$C_{conductor,annual} = c_{conductor} \times M_{total}$$

3. Converter (annual; DC only)

$$C_{converter,annual} = c_{converter} \times M_{total}$$

(0 for AC.)

4. Structure (annual, structure-only — piecewise)

$$C_{structure,annual} = \begin{cases}
c_{structure} \times N_{structure} & \text{if overhead} \\
c_{structure,mi} \times M_{total} & \text{if non-overhead}
\end{cases}$$

Note: Currently $c_{structure,mi} = 0$ for non-overhead (underground direct-buried, underground tunnel, subsea).

Overhead: total structures

$$N_{structure} = \sum_{terrain} M_{terrain} \times n_{structure}(terrain)$$

5. Vegetation management (annual)

$$C_{veg,annual} = \sum_{terrain} M_{terrain} \times c_{veg}(terrain)$$

Overhead only in practice (non-overhead construction types have $c_{veg}(terrain) = 0$). For non-overhead, $C_{veg,annual} = 0$.

6. Total annual O&M

$$C_{O\&M,annual} = C_{conductor,annual} + C_{converter,annual} + C_{structure,annual} + C_{veg,annual}$$

7. Nominal (undiscounted) lifetime O&M

$$C_{O\&M,nominal} = C_{O\&M,annual} \times T_{lifetime}$$

8. Real (present value) O&M

$$C_{O\&M,real} = \sum_{t=t_{COD}}^{t_{COD}+T_{lifetime}-1} \frac{C_{O\&M,annual}}{(1+r_{WACC,real})^t}$$

**Regulatory perspective (AFUDC)**  
O&M is not capitalized; there is no $C_{O\&M,AFUDC}$. O&M does not enter rate base.

**Data sources**  
- `01_project_technical_details.yaml`: construction type, AC/DC, capacity, conductor type, converter type, delay_years, construction_years, project_lifetime.  
- `02_project_physical_details.yaml`: terrain miles, total miles.  
- `12_project_om_vegetation_management.yaml`: $c_{veg}(terrain)$ by construction type.  
- `13_category_om_conductors.yaml`: $c_{conductor}$ by category.  
- `14_category_om_structures.yaml`: $n_{structure}(terrain)$, $c_{structure}$, $c_{structure,mi}$.  
- `15_category_om_converters.yaml`: $c_{converter}$ by category (AC → 0).  
- Financing: $r_{WACC,real}$.

---

### Operational insurance (2.b)

Operational insurance is operational only: not AFUDC-eligible. Premiums are paid annually on insurable asset value from COD to end of life.

| Variable | Meaning / units | Notes |
| -------- | ----------------- | ----- |
| $C_{adj,cont,conductor}$ | Conductor build cost ($) | Terrain-adjusted, contingency applied. From Build (1.a). |
| $C_{adj,cont,structure}$ | Structure build cost ($) | Terrain-adjusted, contingency applied. From Build (1.a). |
| $C_{adj,cont,converter}$ | Converter build cost ($) | Terrain-adjusted, contingency applied; 0 for AC. From Build (1.a). |
| $\xi_{ins,conductor}$ | Include conductors in insurable value | 1 if insured, 0 if not. |
| $\xi_{ins,structure}$ | Include structures in insurable value | 1 if insured, 0 if not. |
| $\xi_{ins,converter}$ | Include converters in insurable value | 1 if insured, 0 if not. |
| $V_{insurable}$ | Insurable asset value ($) | Sum of included build-cost components (with contingencies). |
| $CT$ | Construction type | Overhead, Underground direct-buried, Underground tunnel, Subsea. |
| $r_{premium}(CT)$ | Premium rate (decimal) | Annual premium as fraction of insurable value. Can depend on $CT$. |
| $r_{premium,default}$ | Default premium rate | Used when no type-specific rate is defined for $CT$. |
| $C_{insurance,annual}$ | Annual operational insurance premium | $/year. |
| $T_{lifetime}$ | Project lifetime | years. |
| $t_{COD}$ | Commercial operation date (year) | First year premium is paid. $t_{COD} = T_{delay} + T_{construction} + 1$. |
| $r_{WACC,real}$ | Real WACC | decimal; used to discount premiums. |
| $C_{insurance,nominal}$ | Operational insurance cost (nominal) | Undiscounted sum of premiums over project lifetime. |
| $C_{insurance,real}$ | Operational insurance cost (real / PV) | Present value of premium stream from $t_{COD}$ over $T_{lifetime}$. |

**Equations**

1. Insurable asset value (only components with $\xi = 1$ are included):

$$V_{insurable} = \xi_{ins,conductor}\, C_{adj,cont,conductor} + \xi_{ins,structure}\, C_{adj,cont,structure} + \xi_{ins,converter}\, C_{adj,cont,converter}$$

2. Premium rate (can depend on construction type; otherwise use default):

$$r_{premium}(CT) = \begin{cases}
r_{premium,CT} & \text{if a rate is specified for construction type } CT \\
r_{premium,default} & \text{otherwise}
\end{cases}$$

Here $r_{premium,CT}$ denotes the type-specific rate when defined.

3. Annual premium:

$$C_{insurance,annual} = V_{insurable} \times r_{premium}(CT)$$

4. Nominal (undiscounted) lifetime cost:

$$C_{insurance,nominal} = C_{insurance,annual} \times T_{lifetime}$$

5. Real (present value) cost. Premiums at the start of each year from $t_{COD}$ for $T_{lifetime}$ years, discounted at $r_{WACC,real}$:

$$C_{insurance,real} = \sum_{t=t_{COD}}^{t_{COD}+T_{lifetime}-1} \frac{C_{insurance,annual}}{(1+r_{WACC,real})^t}$$

**Regulatory perspective (AFUDC)**  
Operational insurance is not capitalized; there is no $C_{insurance,AFUDC}$. It does not enter rate base.

**Data sources**  
- Build costs (1.a): $C_{adj,cont,conductor}$, $C_{adj,cont,structure}$, $C_{adj,cont,converter}$.  
- Insurance config: $\xi_{ins,*}$, $r_{premium}(CT)$, $r_{premium,default}$.  
- Project: $CT$, $T_{lifetime}$, $T_{delay}$, $T_{construction}$.  
- Financing: $r_{WACC,real}$.

---

### Operational ROW rent (2.c)

ROW rent is operational only: not AFUDC-eligible. It is the annual payment for use of the right-of-way in zones where the line is built. Same zones, areas, and per-acre rent as in Capital ROW; agreement type determines whether rent applies and over which years it is paid.

| Variable | Meaning / Units | Notes |
| -------- | ----------------- | ----- |
| $z$ | Zone index | Same zones as Capital ROW; only $M_z \gt 0$ used. |
| $M_z$ | Miles in zone $z$ | miles. |
| $W_{ROW}$ | ROW width | ft. Same as Capital ROW (project category). |
| $A_z$ | Area of ROW of zone $z$ | acres. $A_z = (M_z \times 5280 \times W_{ROW})/43560$. |
| $p_{rent,z}$ | Rent per acre per year, zone $z$ | $/acre/year. |
| $C_{rent,annual}$ | Total annual ROW rent | $/year. Sum over zones with $M_z \gt 0$. |
| $\xi_{rent}$ | Binary: rent applies | 1 for Existing Lease/License or Federal Hybrid; 0 for New Permanent Easement or Simple Fee (see agreement table). |
| $T_{delay}$ | Delay years | years. |
| $T_{construction}$ | Construction years | years. |
| $T_{lifetime}$ | Project lifetime | years of operation. |
| $t_{rent,start}$ | First year rent is paid | Agreement-dependent (see below). |
| $T_{rent}$ | Number of years rent is paid | Agreement-dependent (see below). |
| $r_{WACC,real}$ | Real WACC | decimal; used to discount rent. |
| $C_{rent,total,nominal}$ | ROW rent cost (nominal) | Undiscounted sum of rent over all years it is paid. |
| $C_{rent,total,real}$ | ROW rent cost (real / PV) | Present value of rent stream. |

**When rent applies (from agreement type)**

| Agreement type | Rent? | $t_{rent,start}$ | $T_{rent}$ |
| -------------- | ----- | ----------------- | ---------- |
| New Permanent Easement | No ($\xi_{rent}=0$) | — | — |
| Simple Fee | No ($\xi_{rent}=0$) | — | — |
| Existing Lease/License | Yes ($\xi_{rent}=1$) | 1 | $T_{delay} + T_{construction} + T_{lifetime}$ |
| Federal Hybrid | Yes ($\xi_{rent}=1$) | $T_{delay} + 1$ | $T_{construction} + T_{lifetime}$ |

Lease/License: rent from year 1 through delay, construction, and lifetime. Federal Hybrid: rent from start of construction ($T_{delay}+1$) through construction and lifetime only.

**Equations**

1. Area of ROW per zone (same as Capital ROW)

$$A_z = \frac{M_z \times 5280 \times W_{ROW}}{43560}$$

Only zones with $M_z \gt 0$ are included in sums.

2. Annual ROW rent

$$C_{rent,annual} = \sum_{z \,:\, M_z \gt 0} A_z \, p_{rent,z}$$

3. Nominal (undiscounted) ROW rent cost

Rent is paid only when $\xi_{rent}=1$, over $T_{rent}$ years:

$$C_{rent,total,nominal} = \xi_{rent} \times C_{rent,annual} \times T_{rent}$$

With $T_{rent}$ and $t_{rent,start}$ as in the table above (by agreement type).

4. Real (present value) ROW rent cost

Rent stream from $t_{rent,start}$ for $T_{rent}$ years, discounted at $r_{WACC,real}$:

$$C_{rent,total,real} = \xi_{rent} \times \sum_{t=t_{rent,start}}^{t_{rent,start} + T_{rent} - 1} \frac{C_{rent,annual}}{(1+r_{WACC,real})^t}$$

**Regulatory perspective (AFUDC)**  
ROW rent is not capitalized; there is no $C_{rent,AFUDC}$. It does not enter rate base.

**Agreement type (reminder)**  
Same as Capital ROW: Reconductoring or existing ROW → Existing Lease/License (rent only); otherwise New Permanent Easement (or Simple Fee / Federal Hybrid per project). Rent is the operational row in the Capital ROW agreement table.

**Data sources**  
- ROW details by zone: $M_z$, $p_{rent,z}$ (and $p_{acquisition,z}$, $p_{hold,z}$ for capital).  
- Project category: $W_{ROW}$.  
- Project: agreement type (or reconductoring / uses existing ROW), $T_{delay}$, $T_{construction}$, $T_{lifetime}$.  
- Financing: $r_{WACC,real}$.

---

## Energy/Emissions

The CTCC calculates the thermal losses on a line. Energy losses are the physical quantity of energy lost on the transmission path (line and, for DC, converters). We calculate it to estimate energy loss costs and emissions costs.

### Energy losses

**Variables**

| Variable | Meaning / units | Notes |
| -------- | ----------------- | ----- |
| $C_{new}$ | New line capacity | MW. Nameplate capacity. (Applies for both reconductoring and greenfield.) |
| $V$ | Line voltage | kV. For reconductoring, voltage from existing (old) configuration; for greenfield, from new configuration. |
| $L$ | Line length | miles. Total line length. |
| $u$ | Line utilization | Dimensionless, $0 \le u \le 1$. Average fraction of capacity used (annual or representative). |
| $n_{phases}$ | Number of phases | 3 for AC; 2 for DC (poles). |
| $n_{circuits}$ | Number of circuits / poles | Number of parallel circuits (AC) or poles (DC). |
| $n_{conductorsperphase}$ | Conductors per phase (or per pole) | Conductors in parallel per phase/pole. |
| $R_{mi}$ | Resistance per mile | $\Omega$/mile. AC: resistance at 75°C; DC: resistance at 20°C. Depends on conductor and circuit. |
| $I$ | Phase current | A. RMS phase current at full capacity and nominal voltage. |
| $\phi_{AC}$ | AC power factor | Dimensionless (e.g. 0.95). Used only for AC. NOT THE SAME AS THE FLOW FACTOR FOR CONGESTION AND CURTAILMENT CONSIDERATIONS. |
| $f_{load}$ | Full-load adjustment factor | Dimensionless. Converts “full-load” loss to an average over the utilization profile; function of $u$. |
| $H$ | Hours per year | h/year (e.g. 8760). |
| $T_{lifetime}$ | Project lifetime | years. |
| $\xi_{DC}$ | DC indicator | 1 if DC, 0 if AC. |
| $N_{conv}$ | Number of converter stations | 0 for AC; typically 2 for DC (rectifier + inverter). |
| $\lambda_{conv}$ | Converter loss fraction | Dimensionless (e.g. 0.0075 LCC, 0.01 VSC). Fraction of through-power lost per station. |
| $P_{lineloss,MW}$ | Line loss (power) | MW. Total resistive line loss (average power). |
| $E_{lineloss,MW,annual}$ | Line energy losses (annual) | MWh/year. |
| $E_{lineloss,lifetime}$ | Line energy losses (lifetime) | MWh. |
| $P_{converterloss,MW}$ | Converter loss (power) | MW. Total converter loss (DC only). |
| $E_{converterloss,MW,annual}$ | Converter energy losses (annual) | MWh/year. |
| $E_{loss}$ | Total energy losses (annual) | MWh/year. Line + converter. |
| $E_{totalloss,lifetime}$ | Total energy losses (lifetime) | MWh. |

**Equations**

1. Phase current (from capacity and voltage)

AC (three-phase, with power factor):

$$I = \frac{C_{new} \times 1000}{\phi_{AC} \times V \times \sqrt{n_{phases}} \times n_{circuits}} \quad \text{(AC)}$$

DC:

$$I = \frac{C_{new} \times 1000}{V \times \sqrt{n_{phases}} \times n_{circuits}} \quad \text{(DC)}$$

($C_{new}$ in MW, $V$ in kV; factor 1000 for kW/kV → A.)

2. Full-load adjustment (utilization)

$$f_{load} = \frac{u + u^2}{2}$$

3. Line loss (power)

Total resistive (I²R) line loss, average power in MW:

$$P_{lineloss,MW} = \left( \frac{I}{n_{conductorsperphase}} \right)^2 \times \bigl( n_{conductorsperphase} \times n_{phases} \times n_{circuits} \bigr) \times R_{mi} \times L \times \frac{f_{load}}{10^6}$$

The factor $10^6$ converts watts to MW.

4. Line energy losses (annual and lifetime)

$$E_{lineloss,MW,annual} = P_{lineloss,MW} \times H$$

$$E_{lineloss,lifetime} = E_{lineloss,MW,annual} \times T_{lifetime}$$

5. Converter loss (DC only)

$$P_{converterloss,MW} = \xi_{DC} \times N_{conv} \times \lambda_{conv} \times u \times C_{new}$$

$$E_{converterloss,MW,annual} = P_{converterloss,MW} \times H$$

For AC, $\xi_{DC}=0$ (or $N_{conv}=0$), so $P_{converterloss,MW}=0$ and $E_{converterloss,MW,annual}=0$.

6. Total energy losses

$$E_{loss} = E_{lineloss,MW,annual} + E_{converterloss,MW,annual}$$

$$E_{totalloss,lifetime} = E_{loss} \times T_{lifetime} = E_{lineloss,lifetime} + E_{converterloss,MW,annual} \times T_{lifetime}$$

**Reconductoring**  
For reconductoring: voltage $V$ from existing (old) configuration; resistance $R_{mi}$ from new conductors. $C_{new}$ is the new line capacity in both cases.

**Conceptual note**  
$P_{lineloss,MW}$ and $P_{converterloss,MW}$ are average power losses (MW) over the year. Annual energy loss (MWh) = that average MW × 8760 h.

---

### Thermal line loss costs (3.a)

Thermal line loss cost is the cost of the energy lost on the transmission path (line and, for DC, converters). It takes the energy losses from the Energy losses section and values them at an electricity price. It is an operational/societal cost (no AFUDC): incurred each year over the project's operating life and discounted at the real WACC.

**Variables**

| Variable | Meaning / units | Notes |
|----------|-----------------|-------|
| $E_{loss}$ | Total energy losses (annual), MWh/yr | From Energy losses (line + converter). |
| $E_{lineloss,MW,annual}$ | Line energy losses (annual), MWh/yr | Conductor only. |
| $E_{converterloss,MW,annual}$ | Converter energy losses (annual), MWh/yr | DC only; 0 for AC. |
| $\gamma_{electricity}$ | Electricity price, $/MWh | e.g. baseline or market price. |
| $T_{lifetime}$ | Project lifetime, years | |
| $t_{COD}$ | Commercial operation date, year | First year of operation. |
| $r_{WACC,real}$ | Real WACC, decimal | Used to discount this cost (market-tracked). |
| $C_{loss,annual}$ | Total thermal loss cost (annual), $/yr | Line + converter. |
| $C_{loss,nominal}$ | Total thermal loss cost (nominal), $ | Undiscounted sum over lifetime. |
| $C_{loss,real}$ | Total thermal loss cost (real / PV), $ | PV of annual stream from $t_{COD}$ over $T_{lifetime}$. |
| $C_{lineloss,annual}$ | Line (conductor) loss cost (annual), $/yr | Cost of line losses only. |
| $C_{converterloss,annual}$ | Converter loss cost (annual), $/yr | Cost of converter losses only; 0 for AC. |

**Equations**

1. Component costs (line and converter)

$$C_{lineloss,annual} = E_{lineloss,MW,annual} \times \gamma_{electricity}$$

$$C_{converterloss,annual} = E_{converterloss,MW,annual} \times \gamma_{electricity}$$

2. Total annual thermal loss cost

$$C_{loss,annual} = E_{loss} \times \gamma_{electricity} = C_{lineloss,annual} + C_{converterloss,annual}$$

3. Nominal (undiscounted) lifetime cost

$$C_{loss,nominal} = C_{loss,annual} \times T_{lifetime}$$

4. Real (present value) cost

Annual costs at the start of each year from $t_{COD}$ for $T_{lifetime}$ years, discounted at real WACC:

$$C_{loss,real} = \sum_{t=t_{COD}}^{t_{COD} + T_{lifetime} - 1} \frac{C_{loss,annual}}{(1 + r_{WACC,real})^t}$$

---

**Regulatory perspective (AFUDC)**  
Thermal loss cost is not capitalized; there is no AFUDC term. It does not enter rate base.

**Societal perspective**  
The relevant measure is real (present value) total thermal loss cost, $C_{loss,real}$, using $r_{WACC,real}$. Externality-related costs (e.g. emissions, wildfire risk, outage) use the social discount rate; this cost does not.

**Link to Energy losses**  
$E_{loss}$, $E_{lineloss,MW,annual}$, and $E_{converterloss,MW,annual}$ are defined in the Energy losses section. Thermal line loss cost (3.a) is the monetary value of those losses at $\gamma_{electricity}$: total $C_{loss,annual} = E_{loss} \times \gamma_{electricity}$, with line and converter components $C_{lineloss,annual}$ and $C_{converterloss,annual}$.

---

*Emissions costs (3.b), Residual exceedance (3.c), Risk (4), and Delay (5) to be documented in the same format.*
