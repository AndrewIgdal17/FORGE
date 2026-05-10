# CTCC Methodology

**Purpose (for editors and readers):** This document captures only the **logic and method** of the CTCC—variables, equations, and procedural logic. It is written to be **paper-ready**: the same content can be transferred into the LaTeX paper as the method section. It is **pen-and-paper reproducible**: a reader should be able to replicate every cost and benefit from this document alone, with no reference to code or implementation. Do not add code, config, or software-specific references; keep the doc self-contained and method-only.

---

This document is the **complete methodology** for the Comprehensive Transmission Cost Calculator (CTCC): variables, parameters, equations, and notation for preprocessing (weighted miles), financial parameters, all cost categories (capital, operational, energy/emissions, risk, delay), benefits (congestion and curtailment reduction, and benefit of delivered energy), and revenue. It is the single source of truth for the method so that the entirety can be transferred consistently into the LaTeX paper. **This methodology takes precedence** for categorization and notation.

---

## Table of contents

- [Weighted miles](#weighted-miles)
- [Financial parameters](#financial-parameters)
- [Capital Costs](#capital-costs)
  - [Build Costs](#build-costs)
  - [Capital ROW costs (acquisition, holding)](#capital-row-costs-acquisition-holding)
  - [Environmental mitigation (1.c)](#environmental-mitigation-1c)
- [Operational Costs](#operational-costs)
  - [O&M (2.a)](#om-2a)
  - [Operational insurance (2.b)](#operational-insurance-2b)
  - [Operational ROW rent (2.c)](#operational-row-rent-2c)
- [Energy/Emissions](#energyemissions)
  - [Energy losses](#energy-losses)
  - [Thermal line loss costs (3.a)](#thermal-line-loss-costs-3a)
  - [Emissions costs (3.b)](#emissions-costs-3b)
  - [Residual exceedance costs (3.c)](#residual-exceedance-costs-3c)
- [Risk costs](#risk-costs)
  - [Expected cost of wildfires (4.a)](#expected-cost-of-wildfires-4a)
  - [Expected cost of outages (4.b)](#expected-cost-of-outages-4b)
- [Delay costs](#delay-costs)
  - [Base delay costs (5.a)](#base-delay-costs-5a)
  - [Congestion delay costs (5.b)](#congestion-delay-costs-5b)
  - [Curtailment delay costs (5.c)](#curtailment-delay-costs-5c)
- [Benefits](#benefits)
  - [Congestion and Curtailment Reduction Benefits](#congestion-and-curtailment-reduction-benefits)
  - [Benefit of Delivered Energy](#benefit-of-delivered-energy)
- [Revenue (Benefit to Utility / Cost to Ratepayers)](#revenue-benefit-to-utility--cost-to-ratepayers)

---

## Weighted miles

Weighted miles are difficulty-adjusted line miles used for build costs (and other modules that use terrain-adjusted distance). Each terrain type has a cost multiplier $\lambda_{terrain} \ge 1$; weighted miles for that terrain are terrain miles × multiplier. Total weighted miles is the sum across terrains. (In this section $\lambda_{terrain}$ denotes the terrain cost multiplier; in Risk costs, $\lambda$ denotes event rates.)

**Variables**

| Variable               | Meaning / units                                      | Notes                                                                                                           |
| ---------------------- | ---------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| $M_{terrain}$          | Miles of a specific terrain type, miles              | Terrains: Forested, Scrubbed Flat, Wetland, Farmland, Desert/Barren, Urban, Rolling Hills, Mountain, Subsea.    |
| $\lambda_{terrain}$    | Cost multiplier by terrain type, $\ge 1$              | Same terrain list as $M_{terrain}$. |
| $M_{total}$            | Total (raw) miles, miles                             | Sum of $M_{terrain}$ over all terrains.                                                                          |
| $M_{weighted,terrain}$ | Weighted miles for that terrain type, miles          | $M_{weighted,terrain} = M_{terrain} \times \lambda_{terrain}$ for that terrain.                                 |
| $M_{weighted,total}$   | Total weighted miles across all terrain types, miles | Used in Build costs (1.a) for conductor/structure/converter variable costs.                                     |
| $\lambda_{average}$    | Average terrain multiplier for the project           | $\lambda_{average} = M_{weighted,total} / M_{total}$ when $M_{total} > 0$.                                      |

**Equations**

1. Weighted miles for each terrain type

$$
M_{weighted,terrain} = M_{terrain} \times \lambda_{terrain} \quad \text{for that terrain type}.


$$

2. Total weighted miles

$$
M_{weighted,total} = \sum_{terrain} M_{weighted,terrain}.


$$

3. Total (raw) miles

$$
M_{total} = \sum_{terrain} M_{terrain}.


$$

4. Average terrain multiplier

$$
\lambda_{average} = \frac{M_{weighted,total}}{M_{total}} \quad (M_{total} > 0).


$$

---

## Financial parameters

This section defines discount rates, inflation, base year, and capital structure used across CTCC. It also summarizes the link to real WACC (Fisher).

**Variables**

| Symbol             | Meaning / units                                   | Notes                                                                                 |
| ------------------ | ------------------------------------------------- | ------------------------------------------------------------------------------------- |
| $\pi$              | Annual inflation rate, decimal                    | Used in Fisher link for real WACC.                                                    |
| $Y_{base}$         | Base (reference) year                             | Reference year for all present values; PV is in base-year dollars.                    |
| $r_{WACC,nom}$     | Nominal weighted average cost of capital, decimal | From capital structure or default. Used for AFUDC/utility perspective.                  |
| $r_{WACC,real}$    | Real weighted average cost of capital, decimal    | Used for societal PV of costs and benefits. Calculated via Fisher link.             |
| $r_{social}$       | Social discount rate, decimal                     | Used for externality costs (emissions, expected wildfire cost, expected outage cost). |
| $w_{equity}$       | Fraction of funding from equity, decimal          | $w_{equity} + w_{debt} = 1$.                                                          |
| $w_{debt}$         | Fraction of funding from debt, decimal            |                                                                                       |
| $r_{equity}$       | Cost of equity, decimal                           |                                                                                       |
| $r_{debt}$         | Cost of debt, decimal                             |                                                                                       |

**Equations**

1. Nominal WACC from capital structure

$$
r_{WACC,nom} = w_{equity} \times r_{equity} + w_{debt} \times r_{debt}, \qquad w_{equity} + w_{debt} = 1.


$$

2. Real WACC (Fisher link)

$$
r_{WACC,real} = \frac{1 + r_{WACC,nom}}{1 + \pi} - 1.


$$

**When each rate is used**

- **$r_{WACC,nom}$:** Utility/regulatory perspective (e.g. AFUDC rate when applicable).
- **$r_{WACC,real}$:** Societal PV of capital, O&M, insurance, ROW rent, line loss cost, residual exceedance, benefits, revenue; delay and congestion/curtailment delay costs.
- **$r_{social}$:** Societal PV of externality costs: emissions (3.b), expected cost of wildfires (4.a), expected cost of outages (4.b).

**Alignment with Paper 1 Methods (discounting).** The split above—real WACC for market-valued project cash flows versus the social discount rate for externality streams—is the same structure described in the paper’s Methods (discounting subsection). This file remains the implementation reference for symbols and module boundaries; the paper remains the public-facing statement of scope.

---

## Capital Costs

### Build Costs

| Variable                    | Meaning / units                                                 | Notes                                                                                     |
| --------------------------- | --------------------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| $C_{conductor}$             | Conductor cost ($)                                              | Not terrain adjusted, no contingency applied                                              |
| $C_{structure}$             | Structure cost ($)                                              | Not terrain adjusted, no contingency applied                                              |
| $C_{converter}$             | Converter cost (if DC) ($)                                      | Not terrain adjusted, no contingency applied                                              |
| $C_{adj,conductor}$         | Conductor cost ($)                                              | Terrain adjusted, no contingency applied                                                  |
| $C_{adj,structure}$         | Structure cost ($)                                              | Terrain adjusted, no contingency applied                                                  |
| $C_{adj,converter}$         | Converter cost (if DC) ($)                                      | Terrain adjusted, no contingency applied                                                  |
| $C_{adj,cont,conductor}$    | Conductor cost ($)                                              | Terrain adjusted, contingency applied                                                     |
| $C_{adj,cont,structure}$    | Structure cost ($)                                              | Terrain adjusted, contingency applied                                                     |
| $C_{adj,cont,converter}$    | Converter cost (if DC) ($)                                      | Terrain adjusted, contingency applied                                                     |
| $F_{conductor}$             | Fixed conductor costs ($)                                       | Conductors have both fixed and variable costs                                             |
| $F_{structure}$             | Fixed structure costs ($)                                       | Currently, structures have no fixed costs in the CTCC                                     |
| $F_{converter}$             | Fixed converter costs ($)                                       | Converters only have fixed costs                                                          |
| $V_{conductor}$             | Variable conductor costs ($/mi)                                 | Conductors have both fixed and variable costs. The miles used are terrain adjusted miles. |
| $V_{structure}$             | Variable structure costs ($/mi)                                 | Structures only have variable costs currently. The miles used are terrain adjusted miles. |
| $V_{converter}$             | Variable converter costs ($/mi)                                 | Converters currently have no variable costs — only fixed costs.                           |
| $M_{weighted,total}$        | Total weighted miles across all terrain types (miles)           | From terrain miles × terrain multipliers.                                                 |
| $r_{contingency,conductor}$ | Contingency multiplier for conductors [0,1]                     |                                                                                           |
| $r_{contingency,structure}$ | Contingency multiplier for structures [0,1]                     |                                                                                           |
| $r_{contingency,converter}$ | Contingency multiplier for converter [0,1] (if DC)              |                                                                                           |
| $C_{build}$                 | Terrain adjusted, contingency applied, total build cost         |                                                                                           |
| $\xi_{DC}$                  | Binary for DC projects (1 if DC, 0 if not)                      |                                                                                           |
| $\xi_{reconductoring}$      | Binary for reconductoring projects (0 if reconductor, 1 if not) |                                                                                           |

Technically

$$
C_{conductor} = V_{conductor} \cdot M_{total} + F_{conductor},\quad C_{structure} = V_{structure} \cdot M_{total} + F_{structure},\quad C_{converter} = V_{converter} \cdot M_{total} + F_{converter}.


$$

As of 2026-02-17, $F_{structure} = 0$ and $V_{converter} = 0$. The CTCC uses difficulty-adjusted terrain miles (weighted miles) rather than raw miles:

$$
C_{adj,conductor} = V_{conductor} \cdot M_{weighted,total} + F_{conductor},\quad C_{adj,structure} = V_{structure} \cdot M_{weighted,total},\quad C_{adj,converter} = F_{converter}.


$$

Contingencies:

$$
C_{adj,cont,conductor} = (1 + r_{contingency,conductor}) \cdot C_{adj,conductor},


$$

$$
C_{adj,cont,structure} = (1 + r_{contingency,structure}) \cdot C_{adj,structure},


$$

$$
C_{adj,cont,converter} = (1 + r_{contingency,converter}) \cdot C_{adj,converter}.


$$

Total build cost:

$$
C_{build} = C_{adj,cont,conductor} + \xi_{reconductoring} \cdot C_{adj,cont,structure} + \xi_{reconductoring} \cdot \xi_{DC} \cdot C_{adj,cont,converter}.


$$

(When $\xi_{reconductoring} = 0$ the project is reconductoring and structure/converter costs are excluded; when $\xi_{reconductoring} = 1$ they are included. Converter cost is included only when $\xi_{DC} = 1$ (DC); $\xi_{DC}$ encodes DC vs AC in the formalism so that AC projects do not include converter cost.)

---

### Capital ROW costs (acquisition, holding)

**NOTE:** ROW rent costs are not a capital cost! They are an operational cost (see 2.c).

| Variable                  | Meaning / units                                     | Notes                                                                           |
| ------------------------- | --------------------------------------------------- | ------------------------------------------------------------------------------- |
| $z$                       | Zone index                                          | ROW split into zones (1–15). In calculations we use only zones where $M_z > 0$.  |
| $M_z$                     | Miles in zone $z$                                    | miles.                                                                          |
| $W_{ROW}$                 | ROW width                                           | ft. Contingent on the selected tech (project category).                         |
| $A_z$                     | Area of ROW of zone $z$                              | acres.                                                                          |
| $p_{acquisition,z}$       | Acquisition cost per acre, zone $z$                  | $/acre (one-time).                                                              |
| $p_{hold,z}$              | Holding (option fee) per acre per year, zone $z$     | $/acre/year.                                                                    |
| $p_{rent,z}$              | Rent per acre per year, zone $z$                     | $/acre/year. Operational only (2.c).                                            |
| $C_{acquisition}$         | Total one-time acquisition cost ($)                 | From zone sum; see equations below.                                             |
| $C_{hold,annual}$         | Total annual holding cost ($/year)                  | The years here are the permitting/delay years.                                  |
| $T_{delay}$               | Delay years                                         | years. Used for holding.                                                        |
| $C_{hold,total}$          | Total holding cost over delay ($)                   | Option fee over full delay period.                                              |
| $\xi_{acquisition}$       | Binary: acquisition counts toward capital ROW       | 1 if acquisition applies, 0 if not (e.g. lease/license). Set by agreement type. |
| $\xi_{holding}$           | Binary: holding counts toward capital ROW           | 1 if holding applies, 0 if not. Set by agreement type.                          |
| $C_{acquisition,real}$    | Real (present) value of acquisition cost ($)        | Societal perspective; discounted at $r_{WACC,real}$.                             |
| $C_{hold,real}$           | Real (present) value of holding cost ($)            | Societal perspective; discounted at $r_{WACC,real}$.                             |
| $r_{WACC,real}$           | Real weighted average cost of capital               | decimal. Societal discount rate.                                                |
| $C_{ROW,capital,nominal}$ | Total ROW capital costs in nominal terms ($)        |                                                                                 |
| $C_{ROW,capital,real}$    | Total real (present) value of ROW capital costs ($) | Societal perspective.                                                           |

**Agreement type table**

| Agreement type         | Acquisition                 | Holding                 | Rent (operational) |
| ---------------------- | --------------------------- | ----------------------- | ------------------ |
| New Permanent Easement | Yes ($\xi_{acquisition}=1$) | Yes ($\xi_{holding}=1$) | No                 |
| Simple Fee             | Yes ($\xi_{acquisition}=1$) | Yes ($\xi_{holding}=1$) | No                 |
| Existing Lease/License | No ($\xi_{acquisition}=0$)  | No ($\xi_{holding}=0$)  | Yes                |
| Federal Hybrid         | Yes ($\xi_{acquisition}=1$) | Yes ($\xi_{holding}=1$) | Yes                |

NOTE: Reconductoring or existing ROW → Existing Lease/License; else New Permanent Easement.

**Equations**

Area of ROW per zone:

$$
A_z = \frac{M_z \times 5280 \times W_{ROW}}{43560}.


$$

Total acquisition cost:

$$
C_{acquisition} = \sum_{z \,:\, M_z > 0} A_z \, p_{acquisition,z}.


$$

Annual holding cost (for each delay year):

$$
C_{hold,annual} = \sum_{z \,:\, M_z > 0} A_z \, p_{hold,z}.


$$

Total holding cost over the delay:

$$
C_{hold,total} = C_{hold,annual} \times T_{delay}.


$$

Total nominal ROW capital cost:

$$
C_{ROW,capital,nominal} = \xi_{acquisition}\, C_{acquisition} + \xi_{holding}\, C_{hold,total}.


$$

**Regulatory perspective (AFUDC)**
A timing pattern is applied and AFUDC capitalization logic is applied as for other capital costs (timing for row acquisition and row holding).

**Societal perspective**
Discount at real WACC (real = present value):

$$
C_{acquisition,real} = \frac{C_{acquisition}}{(1+r_{WACC,real})^{T_{delay}}},


$$

$$
C_{hold,real} = \sum_{t=1}^{T_{delay}} \frac{C_{hold,annual}}{(1+r_{WACC,real})^t}.


$$

Total real (present) value of ROW capital costs:

$$
C_{ROW,capital,real} = \xi_{acquisition}\, C_{acquisition,real} + \xi_{holding}\, C_{hold,real}.


$$

---

### Environmental mitigation (1.c)

Environmental mitigation has **base** costs (construction/restoration per effective acre by terrain and construction type) and **credit** costs (wetland and habitat off-site mitigation). For **reconductoring** projects, wetland and habitat credits are set to zero (existing ROW, no new permanent impacts).

| Variable                                 | Meaning / units                                            | Notes                                                                                                                                                                                                                                               |
| ---------------------------------------- | ---------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| $M_{terrain}$                            | Miles of a specific terrain type                           | Terrains: Forested, Scrubbed Flat, Wetland, Farmland, Desert/Barren, Urban, Rolling Hills, Mountain, Subsea. Only terrains with $M_{terrain} > 0$ are used. |
| $W_{ROW}$                                | ROW width                                                  | ft. Contingent on project category.                                                                                                                                                                                                                 |
| $A_{terrain}$                            | Base ROW area in terrain                                   | acres. $A_{terrain} = (M_{terrain} \times 5280 \times W_{ROW})/43560$.                                                                                                                                                                               |
| $u_{mitigation}$                         | Mitigation uplift factor                                   | Dimensionless (e.g. 1.25). Accounts for construction width beyond ROW (TCE).                                                                                                                                                                        |
| $A^{effective}_{terrain}$                | Effective acres for mitigation in terrain                  | acres. $A^{effective}_{terrain} = A_{terrain} \times u_{mitigation}$.                                                                                                                                                                                |
| $CT$                                     | Construction type                                          | From project category (overhead, underground direct buried, underground tunnel, subsea).                                                                                                                                                            |
| $c_{base,peracre}(terrain, CT)$          | Base mitigation cost per acre for terrain ($/acre)         | Depends on terrain and construction type.                                                                                                                                                                                                            |
| $C_{base,total}$                         | Total base mitigation/restoration cost                     | $. Sum over terrains (with $M_{terrain} > 0$) of $c_{base,peracre}(terrain, CT) \times A^{effective}_{terrain}$.                                                                                                                                    |
| $A^{effective impact}_{wetland}$         | Wetland impact acres (effective)                           | acres. Wetland terrain only: $A^{effective impact}_{wetland} = A_{wetland} \times u_{mitigation}$.                                                                                                                                                   |
| $A^{effective impact}_{habitat}$         | Habitat impact acres (effective), total                    | acres. Sum over habitat terrains: $A^{effective impact}_{habitat} = \bigl(\sum_{terrain \in habitat} A_{terrain}\bigr) \times u_{mitigation}$. Habitat = forested, scrubbed flat, desert barren, rolling hills, mountain.                            |
| $A^{effective impact}_{terrain,habitat}$ | Effective acres of habitat impacted for that terrain       | acres. For a given habitat terrain: $A^{effective impact}_{terrain,habitat} = A_{terrain} \times u_{mitigation}$ (that terrain only, not the total). Used per term in $C_{credits,habitat}$.                                                         |
| $p_{wetland}$                            | Wetland credit cost per acre                               | $/acre. |
| $r_{wetland}$                            | Wetland credit ratio                                       | Acres of credits required per acre impacted. |
| $p_{habitat}(terrain)$                   | Habitat credit cost per acre, by terrain                   | $/acre. Per habitat terrain; fallback to default if terrain not listed. |
| $r_{habitat}(terrain)$                   | Habitat credit ratio, by terrain                           | Acres of credits required per acre impacted. Per habitat terrain; fallback to default. |
| $C_{credits,wetlands}$                   | Wetland credit cost                                        | $.                                                                                                                                                                                                                                                  |
| $C_{credits,habitat}$                    | Habitat credit cost                                        | $. Sum over habitat terrains (with $M_{terrain} > 0$) of $p_{habitat}(terrain) \times r_{habitat}(terrain) \times A^{effective impact}_{terrain,habitat}$.                                                                                          |
| $\xi_{reconductoring}$                   | Binary: project is not reconductoring                      | 1 if not reconductoring, 0 if reconductoring. When 0, wetland and habitat credits are set to zero.                                                                                                                                                  |
| $C_{credits,total}$                      | Total credit cost (wetland + habitat)                      | $. After reconductoring rule.                                                                                                                                                                                                                       |
| $T_{delay}$                              | Delay years                                                | years.                                                                                                                                                                                                                                              |
| $T_{construction}$                       | Construction years                                         | years.                                                                                                                                                                                                                                              |
| $t_{start}$                              | Construction start year                                    | $t_{start} = T_{delay} + 1$ (first year after delay; 1-based year indexing).                                                                                                                                                                        |
| $r_{WACC,real}$                          | Real WACC                                                  | decimal. Societal discount rate.                                                                                                                                                                                                                    |
| $C_{env.mit,nominal}$                    | Total environmental mitigation cost (nominal)              | $.                                                                                                                                                                                                                                                  |
| $B_{env.mit,annual}$                     | Annual base for env. mitigation (PV calculation)           | $/year over construction years.                                                                                                                                                                                                                     |
| $C_{credits,real}$                       | Real (present) value of credits                            | $.                                                                                                                                                                                                                                                  |
| $C_{env.mit,real}$                       | Total environmental mitigation cost (real / present value) | $.                                                                                                                                                                                                                                                  |

**Equations**

Base area per terrain (only terrains with $M_{terrain} > 0$):

$$
A_{terrain} = \frac{M_{terrain} \times 5280 \times W_{ROW}}{43560}.


$$

Effective acres (uplift for TCE):

$$
A^{effective}_{terrain} = A_{terrain} \times u_{mitigation}.


$$

Total base mitigation cost:

$$
C_{base,total} = \sum_{terrain \,:\, M_{terrain} > 0} c_{base,peracre}(terrain, CT) \times A^{effective}_{terrain}.


$$

Wetland impact acres (wetland terrain only):

$$
A^{effective impact}_{wetland} = A_{wetland} \times u_{mitigation}.


$$

Habitat impact acres, total (habitat = forested, scrubbed flat, desert barren, rolling hills, mountain):

$$
A^{effective impact}_{habitat} = \left( \sum_{terrain \in habitat} A_{terrain} \right) \times u_{mitigation}.


$$

Wetland credit cost:

$$
C_{credits,wetlands} = p_{wetland} \times r_{wetland} \times A^{effective impact}_{wetland}.


$$

Habitat credit cost (per-terrain effective acres $A^{effective impact}_{terrain,habitat}$ for that habitat terrain):

$$
C_{credits,habitat} = \sum_{\substack{terrain \in habitat \\ M_{terrain} > 0}} p_{habitat}(terrain) \times r_{habitat}(terrain) \times A^{effective impact}_{terrain,habitat}.


$$

(For each habitat terrain, $A^{effective impact}_{terrain,habitat} = A_{terrain} \times u_{mitigation}$.)

Total credit cost (reconductoring zeros out credits when $\xi_{reconductoring} = 0$):

$$
C_{credits,total} = \xi_{reconductoring} \times (C_{credits,wetlands} + C_{credits,habitat}).


$$

Total nominal environmental mitigation cost:

$$
C_{env.mit,nominal} = C_{base,total} + C_{credits,total}.


$$

**Regulatory perspective (AFUDC)**

- Base mitigation: AFUDC-eligible; timing for environmental_mitigation_base (e.g. 0% during delay, 100% during construction).
- Credits: AFUDC-eligible; timing for environmental_mitigation_credits (e.g. 20% during delay, 80% during construction).
- Same capitalization logic as other capital costs (compound to COD). Total capitalized = base capitalized + credits capitalized.

**Societal perspective**
Base mitigation spread evenly over $T_{construction}$ starting at $t_{start}$. For $T_{construction} > 0$:

$$
B_{env.mit,annual} = \frac{C_{base,total}}{T_{construction}}, \qquad
C_{base,real} = \sum_{t=t_{start}}^{t_{start}+T_{construction}-1} \frac{B_{env.mit,annual}}{(1+r_{WACC,real})^t}.


$$

If $T_{construction} = 0$, base is one-time at $t_{start}$: $C_{base,real} = C_{base,total} / (1+r_{WACC,real})^{t_{start}}$.

Credits one-time at construction start (year $t_{start}$):

$$
C_{credits,real} = \frac{C_{credits,total}}{(1+r_{WACC,real})^{t_{start}}}.


$$

Total real (present) value of environmental mitigation:

$$
C_{env.mit,real} = C_{base,real} + C_{credits,real}.


$$

---

## Operational Costs

### O&M (2.a)

O&M is operational only: it is not AFUDC-eligible (no regulatory capitalization). It is:

- **Nominal:** undiscounted sum of annual O&M over project lifetime.
- **Real (societal):** present value of that annual stream from COD to end of life, discounted at real WACC.

| Variable                 | Meaning / units                  | Notes                                                                                                                                                    |
| ------------------------ | -------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| $M_{total}$              | Total line length                | miles. From physical details.                                                                                                                            |
| $M_{terrain}$            | Miles in terrain type            | forested, scrubbed_flat, wetland, farmland, desert_barren, urban, rolling_hills, mountain, subsea.                                                       |
| $T_{delay}$              | Delay years                      | before construction.                                                                                                                                     |
| $T_{construction}$       | Construction years               |                                                                                                                                                          |
| $T_{lifetime}$           | Project lifetime                 | years of operation (O&M accrues over this).                                                                                                              |
| $T_{COD}$                | Commercial operation date (year) | $T_{COD} = T_{delay} + T_{construction} + 1$ (1-based; first year of O&M).                                                                               |
| $r_{WACC,real}$          | Real WACC                        | decimal; used to discount O&M.                                                                                                                           |
| $CT$                     | Construction type                | Overhead, Underground direct-buried, Underground tunnel, Subsea.                                                                                         |
| $c_{conductor}$          | Conductor O&M                    | $/mile/year. By category (construction, AC/DC, capacity, conductor, converter). |
| $c_{converter}$          | Converter O&M                    | $/mile/year. By category. |
| $\xi_{DC}$               | Binary for DC projects           | 1 if DC, 0 if AC. Gates converter O&M (Build costs). |
| $n_{structure}(terrain)$ | Structures per mile              | By terrain. Overhead only. |
| $N_{structure}$          | Total structures                 | Overhead: $N_{structure} = \sum_{terrain} M_{terrain} \times n_{structure}(terrain)$. Non-overhead: not used (see $c_{structure,mi}$). |
| $c_{structure}$          | Cost per structure per year      | $/structure/year. Overhead only. |
| $c_{structure,mi}$       | Structure O&M per mile per year  | $/mile/year. Non-overhead only; one value per construction type (often 0). |
| $c_{veg}(terrain)$       | Vegetation management            | $/mile/year by terrain. Overhead only. |
| $C_{O\&M,annual}$        | Total annual O&M                 | $/year. Sum of conductor + converter + structure + vegetation.                                                                                           |
| $C_{O\&M,nominal}$       | O&M cost (nominal)               | Undiscounted lifetime O&M.                                                                                                                               |
| $C_{O\&M,real}$          | O&M cost (real / PV)             | Present value of O&M from $T_{COD}$ over $T_{lifetime}$.                                                                                                  |

**Equations**

1. COD (first year of O&M)

$$
T_{COD} = T_{delay} + T_{construction} + 1


$$

(1-based; first year of operation.)

2. Conductor (annual)

$$
C_{conductor,annual} = c_{conductor} \times M_{total}


$$

3. Converter (annual; DC only)

$$
C_{converter,annual} = \xi_{DC} \times c_{converter} \times M_{total}


$$

($\xi_{DC}$ encodes DC vs AC in the formalism; converter O&M is included only when $\xi_{DC} = 1$ (DC).)

4. Structure (annual, structure-only — piecewise)

$$
C_{structure,annual} = \begin{cases}
c_{structure} \times N_{structure} & \text{if overhead} \\
c_{structure,mi} \times M_{total} & \text{if non-overhead}
\end{cases}


$$

Note: Currently $c_{structure,mi} = 0$ for non-overhead (underground direct-buried, underground tunnel, subsea).

Overhead: total structures

$$
N_{structure} = \sum_{terrain} M_{terrain} \times n_{structure}(terrain)


$$

5. Vegetation management (annual)

$$
C_{veg,annual} = \sum_{terrain} M_{terrain} \times c_{veg}(terrain)


$$

Overhead only in practice (non-overhead construction types have $c_{veg}(terrain) = 0$). For non-overhead, $C_{veg,annual} = 0$.

6. Total annual O&M

$$
C_{O\&M,annual} = C_{conductor,annual} + C_{converter,annual} + C_{structure,annual} + C_{veg,annual}


$$

7. Nominal (undiscounted) lifetime O&M

$$
C_{O\&M,nominal} = C_{O\&M,annual} \times T_{lifetime}


$$

8. Real (present value) O&M

$$
C_{O\&M,real} = \sum_{t=T_{COD}}^{T_{COD}+T_{lifetime}-1} \frac{C_{O\&M,annual}}{(1+r_{WACC,real})^t}


$$

**Regulatory perspective (AFUDC)**
O&M is not capitalized; there is no $C_{O\&M,AFUDC}$. O&M does not enter rate base.

---

### Operational insurance (2.b)

Operational insurance is operational only: not AFUDC-eligible. Premiums are paid annually on insurable asset value from COD to end of life.

| Variable                 | Meaning / units                        | Notes                                                                    |
| ------------------------ | -------------------------------------- | ------------------------------------------------------------------------ |
| $C_{adj,cont,conductor}$ | Conductor build cost ($)               | Terrain-adjusted, contingency applied. From Build (1.a).                 |
| $C_{adj,cont,structure}$ | Structure build cost ($)               | Terrain-adjusted, contingency applied. From Build (1.a).                 |
| $C_{adj,cont,converter}$ | Converter build cost ($)               | Terrain-adjusted, contingency applied; 0 for AC. From Build (1.a).       |
| $\xi_{ins,conductor}$    | Include conductors in insurable value  | 1 if insured, 0 if not.                                                  |
| $\xi_{ins,structure}$    | Include structures in insurable value  | 1 if insured, 0 if not.                                                  |
| $\xi_{ins,converter}$    | Include converters in insurable value  | 1 if insured, 0 if not.                                                  |
| $V_{insurable}$          | Insurable asset value ($)              | Sum of included build-cost components (with contingencies).              |
| $CT$                     | Construction type                      | Overhead, Underground direct-buried, Underground tunnel, Subsea.         |
| $r_{premium}(CT)$        | Premium rate (decimal)                 | Annual premium as fraction of insurable value. Can depend on $CT$.        |
| $r_{premium,default}$    | Default premium rate                   | Used when no type-specific rate is defined for $CT$.                      |
| $C_{insurance,annual}$   | Annual operational insurance premium   | $/year.                                                                  |
| $T_{lifetime}$           | Project lifetime                       | years.                                                                   |
| $T_{COD}$                | Commercial operation date (year)       | First year premium is paid. $T_{COD} = T_{delay} + T_{construction} + 1$. |
| $r_{WACC,real}$          | Real WACC                              | decimal; used to discount premiums.                                      |
| $C_{insurance,nominal}$  | Operational insurance cost (nominal)   | Undiscounted sum of premiums over project lifetime.                      |
| $C_{insurance,real}$     | Operational insurance cost (real / PV) | Present value of premium stream from $T_{COD}$ over $T_{lifetime}$.       |

**Equations**

1. Insurable asset value (only components with $\xi = 1$ are included):

$$
V_{insurable} = \xi_{ins,conductor}\, C_{adj,cont,conductor} + \xi_{ins,structure}\, C_{adj,cont,structure} + \xi_{ins,converter}\, C_{adj,cont,converter}


$$

2. Premium rate (can depend on construction type; otherwise use default):

$$
r_{premium}(CT) = \begin{cases}
r_{premium,CT} & \text{if a rate is specified for construction type } CT \\
r_{premium,default} & \text{otherwise}
\end{cases}


$$

Here $r_{premium,CT}$ denotes the type-specific rate when defined.

3. Annual premium:

$$
C_{insurance,annual} = V_{insurable} \times r_{premium}(CT)


$$

4. Nominal (undiscounted) lifetime cost:

$$
C_{insurance,nominal} = C_{insurance,annual} \times T_{lifetime}


$$

5. Real (present value) cost. Premiums at the start of each year from $T_{COD}$ for $T_{lifetime}$ years, discounted at $r_{WACC,real}$:

$$
C_{insurance,real} = \sum_{t=T_{COD}}^{T_{COD}+T_{lifetime}-1} \frac{C_{insurance,annual}}{(1+r_{WACC,real})^t}


$$

**Regulatory perspective (AFUDC)**
Operational insurance is not capitalized; there is no $C_{insurance,AFUDC}$. It does not enter rate base.

---

### Operational ROW rent (2.c)

ROW rent is operational only: not AFUDC-eligible. It is the annual payment for use of the right-of-way in zones where the line is built. Same zones, areas, and per-acre rent as in Capital ROW; agreement type determines whether rent applies and over which years it is paid.

| Variable                 | Meaning / units                 | Notes                                                                                                             |
| ------------------------ | ------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| $z$                      | Zone index                      | Same zones as Capital ROW; only $M_z \gt 0$ used.                                                                  |
| $M_z$                    | Miles in zone $z$                | miles.                                                                                                            |
| $W_{ROW}$                | ROW width                       | ft. Same as Capital ROW (project category).                                                                       |
| $A_z$                    | Area of ROW of zone $z$          | acres. $A_z = (M_z \times 5280 \times W_{ROW})/43560$.                                                             |
| $p_{rent,z}$             | Rent per acre per year, zone $z$ | $/acre/year.                                                                                                      |
| $C_{rent,annual}$        | Total annual ROW rent           | $/year. Sum over zones with $M_z \gt 0$.                                                                          |
| $\xi_{rent}$             | Binary: rent applies            | 1 for Existing Lease/License or Federal Hybrid; 0 for New Permanent Easement or Simple Fee (see agreement table). |
| $T_{delay}$              | Delay years                     | years.                                                                                                            |
| $T_{construction}$       | Construction years              | years.                                                                                                            |
| $T_{lifetime}$           | Project lifetime                | years of operation.                                                                                               |
| $t_{rent,start}$         | First year rent is paid         | Agreement-dependent (see below).                                                                                  |
| $T_{rent}$               | Number of years rent is paid    | Agreement-dependent (see below).                                                                                  |
| $r_{WACC,real}$          | Real WACC                       | decimal; used to discount rent.                                                                                   |
| $C_{rent,total,nominal}$ | ROW rent cost (nominal)         | Undiscounted sum of rent over all years it is paid.                                                               |
| $C_{rent,total,real}$    | ROW rent cost (real / PV)       | Present value of rent stream.                                                                                     |

**When rent applies (from agreement type)**

| Agreement type         | Rent?                | $t_{rent,start}$ | $T_{rent}$                                    |
| ---------------------- | -------------------- | ---------------- | --------------------------------------------- |
| New Permanent Easement | No ($\xi_{rent}=0$)  | —                | —                                             |
| Simple Fee             | No ($\xi_{rent}=0$)  | —                | —                                             |
| Existing Lease/License | Yes ($\xi_{rent}=1$) | 1                | $T_{delay} + T_{construction} + T_{lifetime}$ |
| Federal Hybrid         | Yes ($\xi_{rent}=1$) | $T_{delay} + 1$  | $T_{construction} + T_{lifetime}$             |

Lease/License: rent from year 1 through delay, construction, and lifetime. Federal Hybrid: rent from start of construction ($T_{delay}+1$) through construction and lifetime only.

**Equations**

1. Area of ROW per zone (same as Capital ROW)

$$
A_z = \frac{M_z \times 5280 \times W_{ROW}}{43560}


$$

Only zones with $M_z \gt 0$ are included in sums.

2. Annual ROW rent

$$
C_{rent,annual} = \sum_{z \,:\, M_z \gt 0} A_z \, p_{rent,z}


$$

3. Nominal (undiscounted) ROW rent cost

Rent is paid only when $\xi_{rent}=1$, over $T_{rent}$ years:

$$
C_{rent,total,nominal} = \xi_{rent} \times C_{rent,annual} \times T_{rent}


$$

With $T_{rent}$ and $t_{rent,start}$ as in the table above (by agreement type).

4. Real (present value) ROW rent cost

Rent stream from $t_{rent,start}$ for $T_{rent}$ years, discounted at $r_{WACC,real}$:

$$
C_{rent,total,real} = \xi_{rent} \times \sum_{t=t_{rent,start}}^{t_{rent,start} + T_{rent} - 1} \frac{C_{rent,annual}}{(1+r_{WACC,real})^t}


$$

**Regulatory perspective (AFUDC)**
ROW rent is not capitalized; there is no $C_{rent,AFUDC}$. It does not enter rate base.

**Agreement type (reminder)**
Same as Capital ROW: Reconductoring or existing ROW → Existing Lease/License (rent only); otherwise New Permanent Easement (or Simple Fee / Federal Hybrid per project). Rent is the operational row in the Capital ROW agreement table.

---

## Energy/Emissions

The CTCC calculates the thermal losses on a line. Energy losses are the physical quantity of energy lost on the transmission path (line and, for DC, converters). We calculate it to estimate energy loss costs and emissions costs.

### Energy losses

**Variables**

| Variable                      | Meaning / units                    | Notes                                                                                                                       |
| ----------------------------- | ---------------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| $C_{new}$                     | New line capacity                  | MW. Nameplate capacity. (Applies for both reconductoring and greenfield.)                                                   |
| $V$                           | Line voltage                       | kV. For reconductoring, voltage from existing (old) configuration; for greenfield, from new configuration.                  |
| $L$                           | Line length                        | miles. Total line length.                                                                                                   |
| $u$                           | Line utilization                   | Dimensionless,$0 \le u \le 1$. Average fraction of capacity used (annual or representative).                                |
| $n_{phases}$                  | Number of phases                   | 3 for AC; 2 for DC (poles).                                                                                                 |
| $n_{circuits}$                | Number of circuits / poles         | Number of parallel circuits (AC) or poles (DC).                                                                             |
| $n_{conductorsperphase}$      | Conductors per phase (or per pole) | Conductors in parallel per phase/pole.                                                                                      |
| $R_{mi}$                      | Resistance per mile                | $\Omega$/mile. AC: resistance at 75°C; DC: resistance at 20°C. Depends on conductor and circuit.                            |
| $I$                           | Phase current                      | A. RMS phase current at full capacity and nominal voltage.                                                                  |
| $\phi_{AC}$                   | AC power factor                    | Dimensionless (e.g. 0.95). Used only for AC. NOT THE SAME AS THE FLOW FACTOR FOR CONGESTION AND CURTAILMENT CONSIDERATIONS. |
| $f_{load}$                    | Full-load adjustment factor        | Dimensionless. Converts “full-load” loss to an average over the utilization profile; function of $u$.                        |
| $H$                           | Hours per year                     | h/year (e.g. 8760).                                                                                                         |
| $T_{lifetime}$                | Project lifetime                   | years.                                                                                                                      |
| $\xi_{DC}$                    | DC indicator                       | 1 if DC, 0 if AC.                                                                                                           |
| $N_{conv}$                    | Number of converter stations       | 0 for AC; typically 2 for DC (rectifier + inverter).                                                                        |
| $\lambda_{conv}$              | Converter loss fraction            | Dimensionless (e.g. 0.0075 LCC, 0.01 VSC). Fraction of through-power lost per station.                                      |
| $P_{lineloss,MW}$             | Line loss (power)                  | MW. Total resistive line loss (average power).                                                                              |
| $E_{lineloss,MW,annual}$      | Line energy losses (annual)        | MWh/year.                                                                                                                   |
| $E_{lineloss,lifetime}$       | Line energy losses (lifetime)      | MWh.                                                                                                                        |
| $P_{converterloss,MW}$        | Converter loss (power)             | MW. Total converter loss (DC only).                                                                                         |
| $E_{converterloss,MW,annual}$ | Converter energy losses (annual)   | MWh/year.                                                                                                                   |
| $E_{loss}$                    | Total energy losses (annual)       | MWh/year. Line + converter.                                                                                                 |
| $E_{totalloss,lifetime}$      | Total energy losses (lifetime)     | MWh.                                                                                                                        |

**Equations**

1. Phase current (from capacity and voltage)

AC (three-phase, with power factor):

$$
I = \frac{C_{new} \times 1000}{\phi_{AC} \times V \times \sqrt{n_{phases}} \times n_{circuits}} \quad \text{(AC)}


$$

DC:

$$
I = \frac{C_{new} \times 1000}{V \times \sqrt{n_{phases}} \times n_{circuits}} \quad \text{(DC)}


$$

($C_{new}$ in MW, $V$ in kV; factor 1000 for kW/kV → A.)

2. Full-load adjustment (utilization)

$$
f_{load} = \frac{u + u^2}{2}


$$

3. Line loss (power)

Total resistive (I²R) line loss, average power in MW:

$$
P_{lineloss,MW} = \left( \frac{I}{n_{conductorsperphase}} \right)^2 \times \bigl( n_{conductorsperphase} \times n_{phases} \times n_{circuits} \bigr) \times R_{mi} \times L \times \frac{f_{load}}{10^6}


$$

The factor $10^6$ converts watts to MW.

4. Line energy losses (annual and lifetime)

$$
E_{lineloss,MW,annual} = P_{lineloss,MW} \times H


$$

$$
E_{lineloss,lifetime} = E_{lineloss,MW,annual} \times T_{lifetime}


$$

5. Converter loss (DC only)

$$
P_{converterloss,MW} = \xi_{DC} \times N_{conv} \times \lambda_{conv} \times u \times C_{new}


$$

$$
E_{converterloss,MW,annual} = P_{converterloss,MW} \times H


$$

For AC, $\xi_{DC}=0$ (or $N_{conv}=0$), so $P_{converterloss,MW}=0$ and $E_{converterloss,MW,annual}=0$.

6. Total energy losses

$$
E_{loss} = E_{lineloss,MW,annual} + E_{converterloss,MW,annual}


$$

$$
E_{totalloss,lifetime} = E_{loss} \times T_{lifetime} = E_{lineloss,lifetime} + E_{converterloss,MW,annual} \times T_{lifetime}


$$

**Reconductoring**
For reconductoring: voltage $V$ from existing (old) configuration; resistance $R_{mi}$ from new conductors. $C_{new}$ is the new line capacity in both cases.

**Conceptual note**
$P_{lineloss,MW}$ and $P_{converterloss,MW}$ are average power losses (MW) over the year. Annual energy loss (MWh) = that average MW × 8760 h.

---

### Thermal line loss costs (3.a)

Thermal line loss cost is the cost of the energy lost on the transmission path (line and, for DC, converters). It takes the energy losses from the Energy losses section and values them at an electricity price. It is an operational/societal cost (no AFUDC): incurred each year over the project's operating life and discounted at the real WACC.

**Variables**

| Variable                      | Meaning / units                           | Notes                                                  |
| ----------------------------- | ----------------------------------------- | ------------------------------------------------------ |
| $E_{loss}$                    | Total energy losses (annual), MWh/yr      | From Energy losses (line + converter).                 |
| $E_{lineloss,MW,annual}$      | Line energy losses (annual), MWh/yr       | Conductor only.                                        |
| $E_{converterloss,MW,annual}$ | Converter energy losses (annual), MWh/yr  | DC only; 0 for AC.                                     |
| $\gamma_{electricity}$        | Electricity price, $/MWh                  | e.g. baseline or market price.                         |
| $T_{lifetime}$                | Project lifetime, years                   |                                                        |
| $T_{COD}$                     | Commercial operation date, year           | First year of operation.                               |
| $r_{WACC,real}$               | Real WACC, decimal                        | Used to discount this cost (market-tracked).           |
| $C_{loss,annual}$             | Total thermal loss cost (annual), $/yr    | Line + converter.                                      |
| $C_{loss,nominal}$            | Total thermal loss cost (nominal), $      | Undiscounted sum over lifetime.                        |
| $C_{loss,real}$               | Total thermal loss cost (real / PV), $    | PV of annual stream from $T_{COD}$ over $T_{lifetime}$. |
| $C_{lineloss,annual}$         | Line (conductor) loss cost (annual), $/yr | Cost of line losses only.                              |
| $C_{converterloss,annual}$    | Converter loss cost (annual), $/yr        | Cost of converter losses only; 0 for AC.               |

**Equations**

1. Component costs (line and converter)

$$
C_{lineloss,annual} = E_{lineloss,MW,annual} \times \gamma_{electricity}


$$

$$
C_{converterloss,annual} = E_{converterloss,MW,annual} \times \gamma_{electricity}


$$

2. Total annual thermal loss cost

$$
C_{loss,annual} = E_{loss} \times \gamma_{electricity} = C_{lineloss,annual} + C_{converterloss,annual}


$$

3. Nominal (undiscounted) lifetime cost

$$
C_{loss,nominal} = C_{loss,annual} \times T_{lifetime}


$$

4. Real (present value) cost

Annual costs at the start of each year from $T_{COD}$ for $T_{lifetime}$ years, discounted at real WACC:

$$
C_{loss,real} = \sum_{t=T_{COD}}^{T_{COD} + T_{lifetime} - 1} \frac{C_{loss,annual}}{(1 + r_{WACC,real})^t}


$$

---

**Regulatory perspective (AFUDC)**
Thermal loss cost is not capitalized; there is no AFUDC term. It does not enter rate base.

**Societal perspective**
The relevant measure is real (present value) total thermal loss cost, $C_{loss,real}$, using $r_{WACC,real}$. Externality-related costs (e.g. emissions, wildfire risk, outage) use the social discount rate; this cost does not.

**Link to Energy losses**
$E_{loss}$, $E_{lineloss,MW,annual}$, and $E_{converterloss,MW,annual}$ are defined in the Energy losses section. Thermal line loss cost (3.a) is the monetary value of those losses at $\gamma_{electricity}$: total $C_{loss,annual} = E_{loss} \times \gamma_{electricity}$, with line and converter components $C_{lineloss,annual}$ and $C_{converterloss,annual}$.

---

### Emissions costs (3.b)

Emissions cost is the societal cost of emissions (CO₂, SOₓ, NOₓ) from the extra generation used to compensate for transmission energy losses. Only a fraction of losses may be assumed to be met by additional generation; that energy is allocated across sources via an energy source mix (with optional growth/decay by year). **Configuration:** the mix is stored in **`18_energy_source_mix.yaml`** (top-level key `18_energy_source_mix` in merged JSON / `combined_data`); it is **merged at load** with `16_emissions_reductions.yaml` in `yaml_loaders` / `json_loaders` so `emissions.py` still consumes one in-memory `energy_source_mix` dict. Legacy files may still carry mix under `16_emissions_reductions`; loaders fall back there if `18` is absent. Emissions are computed from emission intensities by source and pollutant, then valued at societal cost per kg. It is an externality/societal cost (no AFUDC): incurred each year over the project's operating life and discounted at the social discount rate.

**Variables**

| Variable                | Meaning / units                                                            | Notes                                                                                              |
| ----------------------- | -------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| $E_{loss}$              | Total energy losses (annual), MWh/yr                                       | From Energy losses (line + converter).                                                             |
| $\alpha$                | Compensation share, dimensionless                                          | Fraction of $E_{loss}$ assumed compensated by additional generation; in [0, 1].                     |
| $TEC$                   | Total energy compensated (annual), MWh/yr                                  | $TEC = \alpha \times E_{loss}$.                                                                    |
| $j$                     | Energy source index                                                        | e.g. coal, oil, natural gas, solar, wind, hydro, nuclear, other.                                   |
| $p_{j}(\tau)$           | Share of generation from source $j$ in operating year $\tau$, dimensionless | From initial mix and per-source growth/decay rates; normalized so $\sum_j p_j(\tau) = 1$ each year. |
| $I_{j,k}$               | Emission intensity, kg/MWh                                                 | Emissions of pollutant $k$ per MWh from source $j$.                                                 |
| $k$                     | Pollutant index                                                            | CO₂, SOₓ, NOₓ.                                                                                     |
| $E_{k,\tau}$            | Emissions of pollutant $k$ in operating year $\tau$, kg                     | From compensated energy and mix in that year.                                                      |
| $c_k$                   | Societal cost per kg of pollutant $k$, $/kg                                 | Externality value.                                                                                 |
| $C_{k,\tau}$            | Cost of pollutant $k$ in operating year $\tau$, $                           | Monetization of $E_{k,\tau}$.                                                                       |
| $C_{\tau}$              | Total emissions cost in operating year $\tau$, $/yr                         | Sum over pollutants.                                                                               |
| $T_{lifetime}$          | Project lifetime, years                                                    |                                                                                                    |
| $T_{COD}$               | Commercial operation date, year                                            | First year of operation.                                                                           |
| $r_{social}$            | Social discount rate, decimal                                              | Used to discount this externality cost.                                                            |
| $C_{emissions,nominal}$ | Total emissions cost (nominal), $                                          | Undiscounted sum over lifetime.                                                                    |
| $C_{emissions,real}$    | Total emissions cost (real / PV), $                                        | PV of annual cost stream from $T_{COD}$ over $T_{lifetime}$.                                        |

**Equations**

1. Total energy compensated (annual)

$$
TEC = \alpha \times E_{loss}


$$

2. Energy mix by operating year

For each operating year $\tau = 1, \ldots, T_{lifetime}$, the share $p_j(\tau)$ for each source $j$ is obtained from the initial mix and per-source growth/decay rates, then normalized so that $\sum_j p_j(\tau) = 1$.

3. Emissions in operating year $\tau$ (by pollutant)

$$
E_{k,\tau} = TEC \times \sum_j p_j(\tau) \times I_{j,k}


$$

4. Cost in operating year $\tau$ (by pollutant)

$$
C_{k,\tau} = E_{k,\tau} \times c_k


$$

5. Total emissions cost in operating year $\tau$

$$
C_{\tau} = \sum_k C_{k,\tau}


$$

6. Nominal (undiscounted) lifetime cost

$$
C_{emissions,nominal} = \sum_{\tau=1}^{T_{lifetime}} C_{\tau}


$$

7. Real (present value) cost

Annual costs at the start of each operating year from $T_{COD}$ for $T_{lifetime}$ years, discounted at the social discount rate:

$$
C_{emissions,real} = \sum_{\tau=1}^{T_{lifetime}} \frac{C_{\tau}}{(1 + r_{social})^{T_{COD} + \tau - 1}}


$$

---

**Regulatory perspective (AFUDC)**
Emissions cost is not capitalized; there is no AFUDC term. It does not enter rate base.

**Societal perspective**
The relevant measure is real (present value) total emissions cost, $C_{emissions,real}$, using $r_{social}$. This is an externality cost; unlike market-tracked costs (e.g. thermal line loss cost 3.a), it is discounted at the social discount rate.

**Link to Energy losses**
$E_{loss}$ is defined in the Energy losses section. Emissions cost (3.b) uses the share $\alpha$ of that loss assumed to be compensated by additional generation ($TEC = \alpha \times E_{loss}$), then applies the energy mix, emission intensities, and societal costs per kg to obtain $C_{\tau}$ and hence $C_{emissions,nominal}$ and $C_{emissions,real}$.

**Limitation**
Emissions from line-loss compensation are calculated using an average energy source mix. Incremental emissions could in principle use a marginal emission factor. This is something to be improved after the first paper.

---

### Residual exceedance costs (3.c)

Residual exceedance cost is the societal cost of the constraint that remains after the project: the part of congestion and/or curtailment that the project does not relieve because effective capacity relief is less than the exceedance or curtailment level. It uses the same inputs as the Congestion and Curtailment Reduction Benefits (effective relief, binding hours, curtailment hours, exceedance, curtailment MW). One value per MWh (e.g. average congestion price or a user-set residual value) is applied to total residual energy. It is an operational/societal cost (no AFUDC): incurred each year over the project's operating life and discounted at the real WACC. It is grouped under Energy/Emissions and is a system/societal cost only (not in utility or ratepayer cost perspectives).

**Variables**

| Variable               | Meaning / units                                   | Notes                                                  |
| ---------------------- | ------------------------------------------------- | ------------------------------------------------------ |
| $\Delta C_{effective}$ | Effective capacity relief, MW                     | From Congestion and Curtailment Reduction Benefits section.      |
| $H_{congestion}$       | Hours of congestion per year, h/yr                | Total binding hours.                                   |
| $H_{curtailment}$      | Hours of curtailment per year, h/yr               |                                                        |
| $X_{congestion}$       | MW of congestion (exceedance), MW                 | Average exceedance during binding hours.               |
| $MW_{curtailment}$     | MW of curtailed resources, MW                     | Average curtailed MW during curtailment hours.         |
| $E_{res,cong}$         | Residual congestion energy (annual), MWh/yr       | Unrelieved exceedance over binding hours.              |
| $E_{res,curt}$         | Residual curtailment energy (annual), MWh/yr      | Unrelieved curtailment over curtailment hours.         |
| $E_{residual}$         | Total residual exceedance energy (annual), MWh/yr | $E_{res,cong} + E_{res,curt}$.                         |
| $\gamma_{residual}$    | Value of residual exceedance, $/MWh               | User-set or default to$\gamma_{congestion}$.           |
| $C_{residual,annual}$  | Residual exceedance cost (annual), $/yr           |                                                        |
| $C_{residual,nominal}$ | Residual exceedance cost (nominal), $             | Undiscounted sum over lifetime.                        |
| $C_{residual,real}$    | Residual exceedance cost (real / PV), $           | PV of annual stream from $T_{COD}$ over $T_{lifetime}$. |
| $T_{lifetime}$         | Project lifetime, years                           |                                                        |
| $T_{COD}$              | Commercial operation date (year index), years     |                                                        |
| $r_{WACC,real}$        | Real WACC, decimal                                | Used to discount this cost.                            |

**Equations**

1. Residual congestion energy (annual)

Binding hours × unrelieved exceedance when relief is less than exceedance:

$$
E_{res,cong} = H_{congestion} \times \max(0,\, X_{congestion} - \Delta C_{effective})


$$

2. Residual curtailment energy (annual)

Curtailment hours × unrelieved curtailment when relief is less than curtailment MW:

$$
E_{res,curt} = H_{curtailment} \times \max(0,\, MW_{curtailment} - \Delta C_{effective})


$$

3. Total residual exceedance energy (annual)

$$
E_{residual} = E_{res,cong} + E_{res,curt}


$$

4. Annual cost

One price $\gamma_{residual}$ ($/MWh) is applied (user may set a residual value; otherwise default is $\gamma_{congestion}$):

$$
C_{residual,annual} = E_{residual} \times \gamma_{residual}


$$

5. Nominal (undiscounted) lifetime cost

$$
C_{residual,nominal} = C_{residual,annual} \times T_{lifetime}


$$

6. Real (present value) cost

Annual costs at the start of each year from $T_{COD}$ for $T_{lifetime}$ years, discounted at real WACC:

$$
C_{residual,real} = \sum_{t=0}^{T_{lifetime}-1} \frac{C_{residual,annual}}{(1 + r_{WACC,real})^{T_{COD}+t}}


$$

---

**Regulatory perspective (AFUDC)**
Residual exceedance cost is not capitalized; there is no AFUDC term. It does not enter rate base.

**Societal perspective**
The relevant measure is real (present value) total residual exceedance cost, $C_{residual,real}$, using $r_{WACC,real}$. It is a system/societal cost and is included in total costs and in Energy/Emissions; it is not included in utility or ratepayer cost perspectives.

**Link to Congestion and Curtailment Reduction Benefits**
$\Delta C_{effective}$, $H_{congestion}$, $H_{curtailment}$, $X_{congestion}$, and $MW_{curtailment}$ are defined in the Congestion and Curtailment Reduction Benefits section. Residual exceedance (3.c) is the unrelieved part: when $\Delta C_{effective}$ is less than $X_{congestion}$ or $MW_{curtailment}$, the remaining MWh (binding hours × residual exceedance MW and curtailment hours × residual curtailment MW) are valued at $\gamma_{residual}$ to give $C_{residual,annual}$, hence $C_{residual,nominal}$ and $C_{residual,real}$.

---

## Risk costs

### Expected cost of wildfires (4.a)

Expected cost of wildfires is the expected annual loss (EAL) from wildfire events over the project's operating life, valued at expected loss per event (severity). It uses ignition rates by terrain and construction type, multiplies by severity ($ per event), and can apply risk growth over the lifetime. It is an externality/societal cost (no AFUDC): not capitalized, not in rate base. Present value is a growing annuity from COD, typically discounted at the social discount rate. The cost stream starts at COD (after delay and construction).

**Variables**

| Variable            | Meaning / units                                                 | Notes                                                                                              |
| ------------------- | --------------------------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| terrain             | Terrain index                                                   | e.g. forested, wetland, urban.                                                                     |
| $L_{terrain}$       | Line length in terrain, miles                                   | From physical details.                                                                             |
| $f_{base,terrain}$  | Base ignition rate for terrain, events/(mi·yr)                  | Overhead baseline.                                                                                 |
| $k_t$               | Construction-type multiplier, dimensionless                     | Overhead 1; underground&lt; 1; subsea 0.                                                           |
| $f_{terrain,t}$     | Effective ignition rate for terrain and type $t$, events/(mi·yr) | $f_{terrain,t}=f_{base,terrain} \times k_t$.                                                       |
| $\lambda_{terrain}$ | Annual event rate for terrain, events/yr                        | $\lambda_{terrain} = L_{terrain} \times f_{terrain,t}$.                                            |
| $\lambda$           | Total annual event rate, events/yr                              | $\lambda = \sum_{terrain} \lambda_{terrain}$.                                                      |
| $S$                 | Severity (expected loss per event), $                           | Expected loss per wildfire event.                                                                  |
| $EAL$               | Expected annual loss, $/yr                                      | $EAL=\lambda \times S$.                                                                            |
| $g_{wf}$            | Wildfire risk growth rate, decimal                              | Annual increase in expected loss (e.g. escalation of risk).                                        |
| $T_{lifetime}$      | Project lifetime, years                                         |                                                                                                    |
| $T_{COD}$           | Commercial operation date (year index), years                   | First year of operation; cost stream starts here.                                                  |
| $r_{social}$        | Social discount rate, decimal                                   | Used to discount this externality cost (societal perspective).                                     |
| $C_{wf,nominal}$    | Expected wildfire cost (nominal), $                             | Sum of growing annual EAL over lifetime; undiscounted.                                             |
| $C_{wf,real}$       | Expected wildfire cost (real / PV), $                           | PV of growing EAL stream from $T_{COD}$ over $T_{lifetime}$; discounted for delay and construction. |

**Equations**

1. Effective ignition rate (terrain and construction type)

$$
f_{terrain,t} = f_{base,terrain} \times k_t


$$

2. Segment and total annual event rate

$$
\lambda_{terrain} = L_{terrain} \times f_{terrain,t}, \qquad \lambda = \sum_{terrain} \lambda_{terrain}


$$

3. Expected annual loss

$$
EAL = \lambda \times S


$$

4. Nominal (undiscounted) total cost

Growing annual loss at rate $g_{wf}$ over $T_{lifetime}$ years (first year EAL, then EAL$(1+g_{wf})$, …):

$$
C_{wf,nominal} = EAL \times \frac{(1+g_{wf})^{T_{lifetime}} - 1}{g_{wf}} \quad (g_{wf} \neq 0); \qquad C_{wf,nominal} = EAL \times T_{lifetime} \quad (g_{wf} = 0)


$$

5. Real (present value) cost

Growing annuity: amounts at start of each year from $T_{COD}$ for $T_{lifetime}$ years, discounted at $r_{social}$. With delay and construction, the annuity is discounted so it starts at COD:

$$
C_{wf,real} = \frac{EAL \times \frac{1 - \left(\frac{1+g_{wf}}{1+r_{social}}\right)^{T_{lifetime}}}{r_{social} - g_{wf}}}{(1+r_{social})^{T_{delay} + T_{construction}}} \quad (r_{social} \neq g_{wf})


$$

(If $r_{social} = g_{wf}$, the growing-annuity factor is $T_{lifetime}$; if $g_{wf} = 0$, it reduces to a level annuity.)

---

**Regulatory perspective (AFUDC)**
Expected wildfire cost is not capitalized; there is no AFUDC term. It does not enter rate base. It is an expected future loss (societal/externality).

**Societal perspective**
The relevant measure is real (present value) expected wildfire cost, $C_{wf,real}$, using $r_{social}$. This is an externality cost; the discount rate is typically the social discount rate.

---

### Expected cost of outages (4.b)

Expected cost of outages is the expected annual cost (EAC) from transmission outages over the project's operating life. It uses outage rates by terrain and construction type, effective duration (hours per event) by terrain and type, capacity at risk (fraction of line capacity lost per event), and value of lost load (VoLL)—piecewise by duration (e.g. 0–4 h, 4–24 h, 24+ h). It is an externality/societal cost (no AFUDC): not capitalized, not in rate base. Present value is a growing annuity from COD, typically discounted at the social discount rate. The cost stream starts at COD (after delay and construction).

**Variables**

| Variable             | Meaning / units                                              | Notes                                                                                              |
| -------------------- | ------------------------------------------------------------ | -------------------------------------------------------------------------------------------------- |
| terrain              | Terrain index                                                | e.g. forested, wetland, urban.                                                                     |
| $t$                  | Construction type index                                      | e.g. overhead, underground, subsea.                                                                |
| $L_{terrain}$        | Line length in terrain, miles                                | From physical details.                                                                             |
| $r_{terrain,t}$      | Outage rate for terrain and type $t$, events/(mi·yr)          | Direct outages per mile per year.                                                                  |
| $\lambda_{terrain}$  | Annual outage rate for terrain, events/yr                    | $\lambda_{terrain} = L_{terrain} \times r_{terrain,t}$.                                            |
| $\lambda$            | Total annual outage rate, events/yr                          | $\lambda = \sum_{terrain} \lambda_{terrain}$.                                                      |
| $H_{base,terrain}$   | Base outage duration for terrain, h/event                    | Hours per outage event (by terrain).                                                               |
| $k_t$                | Duration multiplier for construction type $t$, dimensionless  | Overhead 1; underground, subsea can be&gt; 1.                                                      |
| $H_{eff,terrain}$    | Effective outage duration for terrain (and type $t$), h/event | $H_{eff,terrain} = H_{base,terrain} \times k_t$.                                                   |
| $\phi$               | Capacity-at-risk factor, dimensionless                       | Fraction of line capacity lost per event; e.g. 1 = radial.                                         |
| $C$                  | Line capacity, MW                                            | Project capacity.                                                                                  |
| $MW_{lost}$          | MW lost per event, MW                                        | $MW_{lost} = \phi \times C$.                                                                       |
| $U_{terrain}$        | Unserved energy per event (terrain), MWh/event               | $U_{terrain} = H_{eff,terrain} \times MW_{lost}$.                                                  |
| $v(h)$               | Value of lost load (VoLL), $/MWh                             | Piecewise by duration (e.g. tier 1: 0–4 h, tier 2: 4–24 h, tier 3: 24+ h).                         |
| $C_{event,terrain}$  | Cost per outage event (terrain), $/event                     | Piecewise VoLL over $U_{terrain}$ (unserved MWh valued at $v(h)$ by duration tier).                 |
| $EAC$                | Expected annual cost, $/yr                                   | $EAC = \sum_{terrain} \lambda_{terrain} \times C_{event,terrain}$.                                 |
| $g_{outages}$        | Outage risk growth rate, decimal                             | Annual increase in expected cost (optional).                                                       |
| $T_{lifetime}$       | Project lifetime, years                                      |                                                                                                    |
| $T_{COD}$            | Commercial operation date (year index), years                | First year of operation; cost stream starts here.                                                  |
| $r_{social}$         | Social discount rate, decimal                                | Used to discount this externality cost (societal perspective).                                     |
| $C_{outage,nominal}$ | Expected outage cost (nominal), $                            | Sum of growing annual EAC over lifetime; undiscounted.                                             |
| $C_{outage,real}$    | Expected outage cost (real / PV), $                          | PV of growing EAC stream from $T_{COD}$ over $T_{lifetime}$; discounted for delay and construction. |

**Equations**

1. Outage rate and effective duration (by terrain and construction type)

$$
\lambda_{terrain} = L_{terrain} \times r_{terrain,t}, \qquad H_{eff,terrain} = H_{base,terrain} \times k_t


$$

2. Total annual outage rate

$$
\lambda = \sum_{terrain} \lambda_{terrain}


$$

3. MW lost and unserved energy per event (terrain)

$$
MW_{lost} = \phi \times C, \qquad U_{terrain} = H_{eff,terrain} \times MW_{lost}


$$

4. Cost per event (piecewise VoLL)

Cost per event for a given terrain is the piecewise VoLL applied to unserved energy: duration is split into tiers (e.g. 0–4 h at $v_1$ $/MWh$, 4–24 h at $v_2$ $/MWh$, 24+ h at $v_3$ $/MWh$). Total cost = $\sum_{tiers} (\text{hours in tier}) \times MW_{lost} \times v_{tier}$. Denote this $C_{event,terrain}$.

5. Expected annual cost

$$
EAC = \sum_{terrain} \lambda_{terrain} \times C_{event,terrain}


$$

6. Nominal (undiscounted) total cost

Growing annual cost at rate $g_{outages}$ over $T_{lifetime}$ years:

$$
C_{outage,nominal} = EAC \times \frac{(1+g_{outages})^{T_{lifetime}} - 1}{g_{outages}} \quad (g_{outages} \neq 0); \qquad C_{outage,nominal} = EAC \times T_{lifetime} \quad (g_{outages} = 0)


$$

7. Real (present value) cost

Growing annuity from $T_{COD}$ for $T_{lifetime}$ years, discounted at $r_{social}$, with delay and construction period discounting:

$$
C_{outage,real} = \frac{EAC \times \frac{1 - \left(\frac{1+g_{outages}}{1+r_{social}}\right)^{T_{lifetime}}}{r_{social} - g_{outages}}}{(1+r_{social})^{T_{delay} + T_{construction}}} \quad (r_{social} \neq g_{outages})


$$

(If $r_{social} = g_{outages}$, the growing-annuity factor is $T_{lifetime}$; if $g_{outages} = 0$, it reduces to a level annuity.)

---

**Regulatory perspective (AFUDC)**
Expected outage cost is not capitalized; there is no AFUDC term. It does not enter rate base. It is an expected future loss (societal/externality).

**Societal perspective**
The relevant measure is real (present value) expected outage cost, $C_{outage,real}$, using $r_{social}$. This is an externality cost; the discount rate is typically the social discount rate.

**Note on VoLL**
Value of lost load (VoLL) is the economic value placed on unserved energy ($/MWh). Tiered VoLL reflects higher marginal value for longer outages (e.g. short 0–4 h, medium 4–24 h, long 24+ h). Capacity at risk $\phi$ (e.g. 1 for radial, &lt; 1 for meshed/redundant) is the fraction of line capacity assumed lost per outage event.

---

## Delay costs

### Base delay costs (5.a)

Base delay costs are the annual costs incurred during the delay (permitting and pre-construction) period—legal, administrative, labor, materials and equipment, regulatory, public relations, project management, and miscellaneous. They are expressed as a constant annual cost for each delay year. Total nominal cost is that annual cost times the number of delay years. Present value is a level annuity over the delay period, discounted at real WACC. Base delay costs are not AFUDC-eligible and do not enter rate base; they are expensed (societal/regulatory perspective uses PV).

**Variables**

| Variable                                                                                    | Meaning / units                      | Notes                                                                                                         |
| ------------------------------------------------------------------------------------------- | ------------------------------------ | ------------------------------------------------------------------------------------------------------------- |
| $C_{legal}$, $C_{admin}$, $C_{labor}$, $C_{mat}$, $C_{reg}$, $C_{PR}$, $C_{PM}$, $C_{misc}$ | Annual delay cost by category, $/yr  | Legal, admin, labor, material and equipment, regulatory, public relations, project management, miscellaneous. |
| $C_{delay,annual}$                                                                          | Total annual delay cost, $/yr        | $C_{delay,annual} = \sum \text{(categories above)}$.                                                          |
| $T_{delay}$                                                                                 | Delay years                          | From project technical details; permitting/pre-construction period.                                           |
| $r_{WACC,real}$                                                                             | Real WACC, decimal                   | Used to discount the delay cost stream (societal/regulatory).                                                 |
| $C_{delay,nominal}$                                                                         | Total base delay cost (nominal), $   | $C_{delay,nominal} = C_{delay,annual} \times T_{delay}$.                                                      |
| $C_{delay,real}$                                                                            | Total base delay cost (real / PV), $ | PV of level annuity over $T_{delay}$ years at $r_{WACC,real}$.                                                 |

**Equations**

1. Total annual delay cost

$$
C_{delay,annual} = C_{legal} + C_{admin} + C_{labor} + C_{mat} + C_{reg} + C_{PR} + C_{PM} + C_{misc}


$$

2. Nominal total base delay cost

$$
C_{delay,nominal} = C_{delay,annual} \times T_{delay}


$$

3. Real (present value) base delay cost

Level annuity: payments at the start of each year $t = 1, \ldots, T_{delay}$, discounted at real WACC $r_{WACC,real}$:

$$
C_{delay,real} = \sum_{t=1}^{T_{delay}} \frac{C_{delay,annual}}{(1+r_{WACC,real})^t} = C_{delay,annual} \times \frac{1 - (1+r_{WACC,real})^{-T_{delay}}}{r_{WACC,real}} \quad (r_{WACC,real} \neq 0)


$$

(If $r_{WACC,real} = 0$, $C_{delay,real} = C_{delay,annual} \times T_{delay}$.)

---

**Regulatory perspective (AFUDC)**
Base delay costs are not capitalized; there is no AFUDC term. They do not enter rate base. They are expensed during the delay period.

**Societal perspective**
The relevant measure is real (present value) base delay cost, $C_{delay,real}$, using $r_{WACC,real}$ (from financing details). This aligns with the PV of capital and other cost streams in CTCC.

**Link to other delay cost categories**
5.b (congestion delay costs) and 5.c (curtailment delay costs) are opportunity costs of foregone congestion/curtailment relief during delay and construction; see those sections.

---

### Congestion delay costs (5.b)

Congestion delay costs are the **opportunity cost** of congestion that is not relieved while the project is in the delay and construction period. In each of those years, the same congestion relief (MWh/yr) that the project would provide once in service is valued at the same price ($/MWh); that annual value is the cost of delay. So the **annual** congestion delay cost equals the **annual congestion reduction benefit** (raw, before any benefit haircut). The cost stream runs over $T_{delay} + T_{construction}$ years (years 1 through $T_{delay} + T_{construction}$). Present value is a level annuity over that period, discounted at real WACC. Congestion delay costs are not AFUDC-eligible and do not enter rate base; they are societal/opportunity costs.

**Conceptually**
This cost answers: "What congestion benefit do we give up each year we are delayed?" Capacity relief and allocation (curtailment first, then congestion; overlap handled) are the same as in the Congestion and Curtailment Reduction Benefits section. The same annual $ amount is used as the raw congestion benefit, so there is no double-count with post-COD benefits.

**Variables**

| Variable                      | Meaning / units                                 | Notes                                                                                                                                                   |
| ----------------------------- | ----------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| $B_{congestion,annual}$ (raw) | Annual congestion reduction benefit (raw), $/yr | Same formula as in Congestion and Curtailment Reduction Benefits: allocated congestion relief MWh/yr × $\gamma_{congestion}$. No haircut for delay cost. |
| $C_{cong,delay,annual}$       | Congestion delay cost (annual), $/yr            | $C_{cong,delay,annual} = B_{congestion,annual}\text{ (raw)}$.                                                                                           |
| $T_{delay}$                   | Delay years                                     | From project technical details.                                                                                                                         |
| $T_{construction}$            | Construction years                              | From project technical details.                                                                                                                         |
| $r_{WACC,real}$               | Real WACC, decimal                              | Used to discount the delay cost stream.                                                                                                                 |
| $C_{cong,delay,nominal}$      | Congestion delay cost (nominal), $              | Total over delay + construction; undiscounted.                                                                                                          |
| $C_{cong,delay,real}$         | Congestion delay cost (real / PV), $            | PV of level annuity over $T_{delay} + T_{construction}$ years at $r_{WACC,real}$, starting at year 1.                                                    |

**Equations**

1. Annual congestion delay cost

The annual opportunity cost is the same as the raw annual congestion reduction benefit (allocated congestion relief × $\gamma_{congestion}$; see Congestion and Curtailment Reduction Benefits for allocation and overlap):

$$
C_{cong,delay,annual} = B_{congestion,annual}\text{ (raw)}.


$$

2. Nominal total congestion delay cost

$$
C_{cong,delay,nominal} = C_{cong,delay,annual} \times (T_{delay} + T_{construction}).


$$

3. Real (present value) congestion delay cost

Level annuity over years $t = 1, \ldots, T_{delay} + T_{construction}$, discounted at $r_{WACC,real}$:

$$
C_{cong,delay,real} = \sum_{t=1}^{T_{delay} + T_{construction}} \frac{C_{cong,delay,annual}}{(1+r_{WACC,real})^t} = C_{cong,delay,annual} \times \frac{1 - (1+r_{WACC,real})^{-(T_{delay} + T_{construction})}}{r_{WACC,real}} \quad (r_{WACC,real} \neq 0).


$$

(If $r_{WACC,real} = 0$, $C_{cong,delay,real} = C_{cong,delay,annual} \times (T_{delay} + T_{construction})$.)

---

**Regulatory perspective (AFUDC)**
Congestion delay costs are not capitalized; there is no AFUDC term. They do not enter rate base.

**Societal perspective**
The relevant measure is real (present value) congestion delay cost, $C_{cong,delay,real}$, using $r_{WACC,real}$. This is the PV of foregone congestion relief during delay and construction.

**Link to Congestion and Curtailment Reduction Benefits**
The same effective capacity relief, curtailment-then-congestion allocation, and overlap logic define $B_{congestion,annual}$. 5.b uses that annual value (raw) as the cost per year of delay/construction, so benefits (post-COD) and congestion delay cost (during delay/construction) are consistent and not double-counted.

**Link to Base delay costs (5.a)**
5.a is out-of-pocket delay costs (legal, admin, etc.). 5.b is the opportunity cost of foregone congestion relief during the same period. Both use $T_{delay}$; 5.b uses $T_{delay} + T_{construction}$ as the cost duration and $r_{WACC,real}$ for PV.

---

### Curtailment delay costs (5.c)

Curtailment delay costs are the **opportunity cost** of curtailment that is not relieved while the project is in the delay and construction period. In each of those years, the same curtailment relief (MWh/yr) that the project would provide once in service is valued at the same price ($/MWh); that annual value is the cost of delay. So the **annual** curtailment delay cost equals the **annual curtailment reduction benefit** (same formula as the benefit; the un-haircut benefit is used). The cost stream runs over $T_{delay} + T_{construction}$ years (years 1 through $T_{delay} + T_{construction}$). Present value is a level annuity over that period, discounted at real WACC. Curtailment delay costs are not AFUDC-eligible and do not enter rate base; they are societal/opportunity costs.

**Conceptually**
This cost answers: "What curtailment benefit do we give up each year we are delayed?" Capacity relief and allocation (curtailment first, then congestion) are the same as in the Congestion and Curtailment Reduction Benefits section. The same annual $ amount is used as the curtailment benefit, so there is no double-count with post-COD benefits.

**Variables**

| Variable                 | Meaning / units                            | Notes                                                                                                                                                                        |
| ------------------------ | ------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| $B_{curtailment,annual}$ | Annual curtailment reduction benefit, $/yr | Same formula as in Congestion and Curtailment Reduction Benefits: allocated curtailment relief MWh/yr × $\gamma_{curtailment}$ (un-haircut benefit is used for delay cost). |
| $C_{curt,delay,annual}$  | Curtailment delay cost (annual), $/yr      | $C_{curt,delay,annual} = B_{curtailment,annual}$.                                                                                                                            |
| $T_{delay}$              | Delay years                                | From project technical details.                                                                                                                                              |
| $T_{construction}$       | Construction years                         | From project technical details.                                                                                                                                              |
| $r_{WACC,real}$          | Real WACC, decimal                         | Used to discount the delay cost stream.                                                                                                                                      |
| $C_{curt,delay,nominal}$ | Curtailment delay cost (nominal), $        | Total over delay + construction; undiscounted.                                                                                                                               |
| $C_{curt,delay,real}$    | Curtailment delay cost (real / PV), $      | PV of level annuity over $T_{delay} + T_{construction}$ years at $r_{WACC,real}$, starting at year 1.                                                                         |

**Equations**

1. Annual curtailment delay cost

The annual opportunity cost is the same as the annual curtailment reduction benefit (allocated curtailment relief × $\gamma_{curtailment}$; see Congestion and Curtailment Reduction Benefits for allocation):

$$
C_{curt,delay,annual} = B_{curtailment,annual}.


$$

2. Nominal total curtailment delay cost

$$
C_{curt,delay,nominal} = C_{curt,delay,annual} \times (T_{delay} + T_{construction}).


$$

3. Real (present value) curtailment delay cost

Level annuity over years $t = 1, \ldots, T_{delay} + T_{construction}$, discounted at $r_{WACC,real}$:

$$
C_{curt,delay,real} = \sum_{t=1}^{T_{delay} + T_{construction}} \frac{C_{curt,delay,annual}}{(1+r_{WACC,real})^t} = C_{curt,delay,annual} \times \frac{1 - (1+r_{WACC,real})^{-(T_{delay} + T_{construction})}}{r_{WACC,real}} \quad (r_{WACC,real} \neq 0).


$$

(If $r_{WACC,real} = 0$, $C_{curt,delay,real} = C_{curt,delay,annual} \times (T_{delay} + T_{construction})$.)

---

**Regulatory perspective (AFUDC)**
Curtailment delay costs are not capitalized; there is no AFUDC term. They do not enter rate base.

**Societal perspective**
The relevant measure is real (present value) curtailment delay cost, $C_{curt,delay,real}$, using $r_{WACC,real}$. This is the PV of foregone curtailment relief during delay and construction.

**Link to Congestion and Curtailment Reduction Benefits**
The same effective capacity relief and curtailment-then-congestion allocation define $B_{curtailment,annual}$. 5.c uses that annual value as the cost per year of delay/construction, so benefits (post-COD) and curtailment delay cost (during delay/construction) are consistent and not double-counted.

**Link to Congestion delay costs (5.b)**
5.b and 5.c use the same period ($T_{delay} + T_{construction}$) and discounting ($r_{WACC,real}$). Allocation is curtailment first, then congestion, so the two delay costs are consistent and not double-counted.

**Link to Base delay costs (5.a)**
5.a is out-of-pocket delay costs (legal, admin, etc.). 5.c is the opportunity cost of foregone curtailment relief during the same delay and construction period.

## Reporting framework

Total costs are organized into **four reporting buckets** for the appendix and results presentation:

| Bucket | Definition | Components |
|--------|-----------|-----------|
| $C_{\text{hard}}$ | Capital | Build + ROW capital + environmental mitigation |
| $C_{\text{soft}}$ | Operational + energy/emissions losses + delay | O&M + insurance + rent + line losses + residual exceedance + all delay |
| $C_{\text{risk}}$ | Expected losses from uncertain events | $C_{\text{wf}} + C_{\text{outage}}$ |
| $C_{\text{emissions}}$ | Social cost of emissions | Loss-compensation emissions (+ facilitated, when implemented) |

$$C^P = C_{\text{hard}}^P + C_{\text{soft}}^P + C_{\text{risk}}^P + C_{\text{emissions}}^P$$

Total benefits are organized into **two buckets**:

| Bucket | Definition | Components |
|--------|-----------|-----------|
| $B_{\text{remedial}}$ | Relief of existing system inefficiencies | Congestion relief + curtailment relief (each with conservative haircut) |
| $B_{\text{enabling}}$ | New productive value the line creates | Delivered energy benefit ($B_{\text{delivered,lifetime}}$) |

$$B^P = B_{\text{remedial}}^P + B_{\text{enabling}}^P$$

$$NB^P = B^P - C^P$$

Revenue ($R_{\text{PV}}$) is a transfer (utility benefit = ratepayer cost); excluded from societal net benefit and BCR.

---

## Benefits

### Congestion and Curtailment Reduction Benefits

Transmission congestion is when the grid is short of capacity and can't deliver all the power that's wanted, so some value is lost (e.g. higher prices, redispatch). Curtailment is when generators (often renewables) must cut output because the wires can't take it. The CTCC treats both as constraints that a new or upgraded line can partly relieve. The benefits are the monetary value of that relief: less congestion and less curtailment thanks to the project.

**Effective relief**
The project doesn't necessarily relieve capacity equal to its nameplate. For a greenfield line, only a fraction of nameplate effectively relieves the constraint (flow factor $\phi$). For reconductoring, relief is the increase in capacity (new minus old). That effective relief, $\Delta C_{effective}$, is the MW available each hour to reduce congestion and/or curtailment.

**Curtailment first**
The same MW of relief can't count twice. The CTCC assigns relief first to curtailment, then what's left ($\Delta C_{remaining}$) to congestion. So you get curtailment benefit from up to $\min(\Delta C_{effective}, MW_{curtailment})$ over curtailment hours, and congestion benefit from the remaining capacity over congestion hours.

**Overlap**
Congestion hours and curtailment hours can overlap. An overlap fraction $\theta$ splits congestion hours into overlap and non-overlap. On overlap hours, congestion relief is capped by $\Delta C_{remaining}$ (because curtailment already used some of $\Delta C_{effective}$). On non-overlap hours, the full $\Delta C_{effective}$ is available for congestion relief (capped by exceedance $X_{congestion}$). So: overlap congestion relief uses $\Delta C_{remaining}$; non-overlap congestion relief uses $\Delta C_{effective}$.

**Monetization**
Curtailment relief (MWh/yr) is valued at $\gamma_{curtailment}$ ($/MWh); congestion relief at $\gamma_{congestion}$ ($/MWh). Conservative haircuts ($\sigma*{curtailment}$, $\sigma*{congestion}$) can be applied so benefits are $(1 - \sigma) \times \text{energy} \times \text{price}$. Annual benefits are then summed over the project lifetime in nominal terms, or discounted to present value at real WACC from the commercial operation date ($T_{COD}$).

**Summary**
Benefits = value of the congestion and curtailment that the project removes, plus the benefit of delivered energy (see below). Effective capacity relief is computed (greenfield vs reconductoring); curtailment is relieved first, then congestion, with overlap handled so the same MW isn't double-counted. Total benefits in the calculator sum congestion, curtailment, and delivered-energy benefits, in nominal or real (PV) terms. The ratepayer perspective includes all three benefits (congestion, curtailment, and delivered energy) in ratepayer benefits for `bcr_ratepayer` and `net_benefit_ratepayer_pv`.

**Variables**

| Variable                           | Meaning / units                                                     | Notes                                                                       |
| ---------------------------------- | ------------------------------------------------------------------- | --------------------------------------------------------------------------- |
| $\Delta C_{effective}$             | Effective capacity relief, MW                                       |                                                                             |
| $\phi$                             | Flow factor, dimensionless [0,1]                                    |                                                                             |
| $\theta$                           | Binding hours and curtailment overlap                               | 0 = no overlap, 1 = full overlap; 0 if only congestion or only curtailment. |
| $H_{congestion}$                   | Hours of congestion per year, h/yr                                  |                                                                             |
| $H_{curtailment}$                  | Hours of curtailment per year, h/yr                                 |                                                                             |
| $H_{congestion,overlap}$           | Hours of congestion that overlap with curtailment, h/yr             |                                                                             |
| $H_{congestion,nonoverlap}$        | Hours of congestion that do not overlap with curtailment, h/yr      |                                                                             |
| $\gamma_{congestion}$              | Value of congestion, $/MWh                                          |                                                                             |
| $\gamma_{curtailment}$             | Value of curtailed energy, $/MWh                                    |                                                                             |
| $\sigma_{congestion}$              | Haircut to value of congestion reduction                            | Conservative estimate of congestion benefits.                               |
| $\sigma_{curtailment}$             | Haircut to value of curtailment reduction                           | Conservative estimate of curtailment benefits.                              |
| $R_{curtailment,annual}$           | Average curtailment relief due to project, MWh/yr                   |                                                                             |
| $R_{congestion,annual}$            | Average congestion relief due to project, MWh/yr                    | Sum of overlap and non-overlap relief.                                      |
| $R_{congestion,overlap,annual}$    | Overlap-hours congestion relief due to project, MWh/yr              |                                                                             |
| $R_{congestion,nonoverlap,annual}$ | Non-overlap-hours congestion relief due to project, MWh/yr          |                                                                             |
| $C_{new}$                          | New line capacity, MW                                               | Greenfield and reconductoring.                                              |
| $C_{old}$                          | Old line capacity, MW                                               | Reconductoring only.                                                        |
| $\Delta C_{remaining}$             | Capacity remaining to address congestion after curtailment, MW      | Curtailment is addressed first in CTCC.                                     |
| $B_{congestion,annual}$            | Annual benefit from congestion reduction, $/yr                      |                                                                             |
| $B_{curtailment,annual}$           | Annual benefit from curtailment reduction, $/yr                     |                                                                             |
| $B_{congestion,lifetime,nominal}$  | Nominal lifetime benefit from congestion reduction, $               |                                                                             |
| $B_{curtailment,lifetime,nominal}$ | Nominal lifetime benefit from curtailment reduction, $              |                                                                             |
| $B_{total,nominal}$                | Nominal total benefit from congestion and curtailment reductions, $ |                                                                             |
| $B_{congestion,lifetime,real}$     | Real (PV) lifetime benefit from congestion reduction, $             |                                                                             |
| $B_{curtailment,lifetime,real}$    | Real (PV) lifetime benefit from curtailment reduction, $            |                                                                             |
| $B_{total,real}$                   | Real total benefit from congestion and curtailment reductions, $    |                                                                             |
| $MW_{curtailment}$                 | MW of curtailed resources, MW                                       |                                                                             |
| $X_{congestion}$                   | MW of congestion (exceedance), MW                                   |                                                                             |
| $T_{lifetime}$                     | Project lifetime, years                                             |                                                                             |
| $T_{COD}$                          | Commercial operation date (year index), years                       | Sum of delay and construction years.                                        |
| $r_{WACC,real}$                    | Real WACC, decimal                                                  | Used to discount benefits.                                                  |

**Equations**

1. Effective relief

$$
\Delta C_{effective} = \begin{cases} \phi \times C_{new} & \text{if greenfield} \\ C_{new} - C_{old} & \text{otherwise} \end{cases}


$$

2. Capacity remaining to address congestion (curtailment first)

$$
\Delta C_{remaining} = \max\left(0,\, \Delta C_{effective} - \min(\Delta C_{effective},\, MW_{curtailment})\right)


$$

3. Overlap of congestion and curtailment hours

$$
\theta = \begin{cases} \min\!\left(1,\,\frac{H_{curtailment}}{H_{congestion}}\right) & \text{if } H_{curtailment}>0 \text{ and } H_{congestion}>0 \\ 0 & \text{otherwise} \end{cases}


$$

$$
H_{congestion,overlap} = \theta \times H_{congestion}


$$

$$
H_{congestion,nonoverlap} = (1 - \theta) \times H_{congestion}


$$

4. Curtailment relief and benefit

$$
R_{curtailment,annual} = H_{curtailment} \times \min(\Delta C_{effective},\, MW_{curtailment})


$$

$$
B_{curtailment,annual} = R_{curtailment,annual} \times \gamma_{curtailment} \times (1 - \sigma_{curtailment})


$$

5. Congestion relief (overlap uses remaining capacity; non-overlap uses full effective relief)

$$
R_{congestion,annual} = R_{congestion,overlap,annual} + R_{congestion,nonoverlap,annual}


$$

where

$$
R_{congestion,overlap,annual} = H_{congestion,overlap} \times \min(\Delta C_{remaining},\, X_{congestion})


$$

$$
R_{congestion,nonoverlap,annual} = H_{congestion,nonoverlap} \times \min(\Delta C_{effective},\, X_{congestion})


$$

$$
B_{congestion,annual} = R_{congestion,annual} \times \gamma_{congestion} \times (1 - \sigma_{congestion})


$$

6. Nominal lifetime benefits

$$
B_{curtailment,lifetime,nominal} = B_{curtailment,annual} \times T_{lifetime}


$$

$$
B_{congestion,lifetime,nominal} = B_{congestion,annual} \times T_{lifetime}


$$

7. Present value (real) lifetime benefits

$$
B_{curtailment,lifetime,PV} = \sum_{t=0}^{T_{lifetime}-1} \frac{B_{curtailment,annual}}{(1+r_{WACC,real})^{T_{COD}+t}}


$$

$$
B_{congestion,lifetime,PV} = \sum_{t=0}^{T_{lifetime}-1} \frac{B_{congestion,annual}}{(1+r_{WACC,real})^{T_{COD}+t}}


$$

### Benefit of Delivered Energy

The benefit of delivered energy is the societal value of the energy the project enables to be delivered each year. For greenfield, deliverable capacity equals effective capacity ($\Delta C_{effective} = \phi \times C_{new}$). For reconductoring, deliverable capacity is the additional capacity the upgrade enables ($C_{new} - C_{old}$, same as $\Delta C_{effective}$ for reconductoring), including any headroom beyond clearing the constraint. Deliverable energy per year is deliverable capacity × line utilization × hours per year (MWh/year), valued at electricity price $\gamma_{electricity}$ (\$/MWh). Level annual benefit from COD, discounted at real WACC. This benefit is not double-counted with congestion or curtailment (those value constraint relief; this values throughput). The appendix is the source of truth for notation and full definitions.

**Variables**

| Variable | Meaning / units | Notes |
| -------- | --------------- | ----- |
| $\Delta C_{effective}$ | Effective capacity relief, MW | From system constraints. Greenfield: $\phi C_{new}$; reconductoring: $C_{new} - C_{old}$. |
| $u$ | Line utilization, dimensionless | $0 \le u \le 1$. |
| $H$ | Hours per year, h/yr | e.g. 8760. |
| $\gamma_{electricity}$ | Electricity price, \$/MWh | e.g. baseline or market price. |
| $E_{delivered,annual}$ | Deliverable energy per year, MWh/yr | |
| $B_{delivered,annual}$ | Annual benefit from delivered energy, \$/yr | |
| $T_{lifetime}$ | Project lifetime, years | |
| $T_{COD}$ | Commercial operation date (year index), years | First year of operation; benefit stream starts here. |
| $r_{WACC,real}$ | Real WACC, decimal | Used to discount benefits. |
| $B_{delivered,lifetime,nominal}$ | Nominal lifetime benefit from delivered energy, $ | |
| $B_{delivered,lifetime,real}$ | Real (PV) lifetime benefit from delivered energy, $ | |

**Equations**

1. Deliverable energy (annual): $E_{delivered,annual} = \Delta C_{effective} \times u \times H$.

2. Annual benefit: $B_{delivered,annual} = E_{delivered,annual} \times \gamma_{electricity}$.

3. Nominal lifetime benefit: $B_{delivered,lifetime,nominal} = B_{delivered,annual} \times T_{lifetime}$.

4. Real (PV) lifetime benefit: level annual benefit from $T_{COD}$ for $T_{lifetime}$ years, discounted at $r_{WACC,real}$:
$$
B_{delivered,lifetime,real} = \sum_{t=0}^{T_{lifetime}-1} \frac{B_{delivered,annual}}{(1+r_{WACC,real})^{T_{COD}+t}}.
$$

---

## Revenue (Benefit to Utility / Cost to Ratepayers)

Revenue to the utility from rate base is a transfer: benefit to the utility = cost to ratepayers. It is not a cost or benefit to society.

**Variables**

| Variable           | Meaning / units                                    | Notes                                                                                                                   |
| ------------------ | -------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| $RB_{nominal}$     | Nominal rate base at COD, $                        | AFUDC capital at COD. Sum of build, ROW capital, env. mitigation.                                                       |
| $C^{cap}$          | Total capital in rate base at COD, $               | $RB_{nominal} = C^{cap}$. Same as rate base.                                                                            |
| $C^{cap}_{build}$  | Capitalized build cost, $                          | Nominal spending capitalized to COD via AFUDC.                                                                          |
| $C^{cap}_{ROW}$    | Capitalized ROW capital cost, $                    | Nominal spending capitalized to COD via AFUDC.                                                                          |
| $C^{cap}_{envmit}$ | Capitalized environmental mitigation cost, $       | Nominal spending capitalized to COD via AFUDC.                                                                          |
| $C^{nom}_i$        | Nominal spending (pre-AFUDC) for component $i$, $   | Same timing as for AFUDC. $C^{cap}_i = C^{nom}_i + AFUDC_i$.                                                             |
| $\pi$              | Inflation rate, decimal                            |                                                                                                                         |
| $RB_{real}$        | Real rate base in base-year dollars, $             | $RB_{real} = RB_{nominal}/(1+\pi)^{T_{COD}}$.                                                                           |
| $\rho$             | Allowed return rate (real), decimal                |                                                                                                                         |
| $R_{annual,real}$  | Annual revenue in real terms, $/yr                 |                                                                                                                         |
| $T_{lifetime}$     | Project lifetime, years                            |                                                                                                                         |
| $R_{total,real}$   | Total revenue over lifetime, undiscounted, real, $ | Sum of real revenue over lifetime, ignoring timing. Use for communication; not for economic comparison (no time value). |
| $r_{WACC,real}$    | Real WACC, decimal                                 | Used to discount the revenue stream.                                                                                    |
| $R_{PV}$           | Present value of revenue, $                        | Benefit to utility and cost to ratepayers in PV terms. Use when comparing to other PV amounts (e.g. BCR).               |
| $T_{COD}$          | Commercial operation date (year index), years      | Years from base year to first year of operation.                                                                        |

**Equations**

1. Rate base (nominal at COD)

$$
RB_{nominal} = C^{cap} = C^{cap}_{build} + C^{cap}_{ROW} + C^{cap}_{envmit}.


$$

Each $C^{cap}_i$ is AFUDC capital at COD: $C^{cap}_i = C^{nom}_i + AFUDC_i$, so the sum is the rate base.

2. COD (year index from base year)

$$
T_{COD} = T_{delay} + T_{construction} + 1.


$$

3. Real rate base (deflate to base year)

$$
RB_{real} = \frac{RB_{nominal}}{(1+\pi)^{T_{COD}}}.


$$

4. Real annual revenue (constant in base-year $/yr)

$$
R_{annual,real} = RB_{real} \times \rho.


$$

5. Total revenue over lifetime (real, undiscounted)

$$
R_{total,real} = R_{annual,real} \times T_{lifetime}.


$$

6. Present value of revenue (benefit to utility / cost to ratepayers)

Revenue starts at $T_{COD}$ and runs for $T_{lifetime}$ years; discount at real WACC:

$$
R_{PV} = \sum_{t=0}^{T_{lifetime}-1} \frac{R_{annual,real}}{(1 + r_{WACC,real})^{T_{COD} + t}}.


$$

So $B_{utility} = R_{PV}$ and $C_{ratepayers} = B_{utility} = R_{PV}$.

**Capital: utility vs society**

Both use the same capital spending: same nominal amounts ($C^{nom}$ for build, ROW capital, environmental mitigation) and same timing over delay and construction.

- **Utility (regulatory):** "What goes in rate base at COD?" Nominal spending is in CWIP; cost of capital on CWIP is capitalized as AFUDC (compound at nominal AFUDC rate to COD). So $C^{cap}_i = C^{nom}_i + AFUDC_i$ at COD for each of build, ROW, and env. mitigation. Rate base is $RB_{nominal} = C^{cap}_{build} + C^{cap}_{ROW} + C^{cap}_{envmit}$ — one number, at COD, in nominal (COD-year) dollars.
- **Society:** "What is the opportunity cost in today's dollars?" Same nominal spending stream, discounted to base year at real WACC. Result: PV of capital = build_cost_pv + row_capital_pv + env_mitigation_pv. AFUDC does not appear in the societal capital cost.

**Why they're consistent**

1. Same inputs: same $C^{nom}_i$ and same timing for each component (build, ROW, env. mitigation).
2. Same idea of time value: utility compounds to COD (AFUDC); society discounts to base year (real WACC).
3. Different purpose: utility number = rate base $RB_{nominal}$; society number = PV of spending.

AFUDC only affects the utility view: it is the allowance that, added to $C^{nom}_i$, gives $C^{cap}_i$ and thus $RB_{nominal}$. Same underlying spending; two consistent views.

---

## Related (Andy’s Workshop vault)

- [[Projects/CTCC/CTCC MOC]] — project hub
- [[Projects/CTCC/PROJECT_MEMORY]] — CTCC state and key files
- [[Projects/CTCC/ctcc_method_webapp_alignment_audit]] — paper vs app alignment audit

---
