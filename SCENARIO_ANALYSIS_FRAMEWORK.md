# CTCC Scenario Analysis Framework

**Comprehensive Transmission Cost Calculator - Sensitivity Analysis Plan**

---

## 📋 Executive Summary

This document outlines a comprehensive scenario analysis framework for the CTCC that includes:

- **5 baseline scenarios** representing different transmission project types
- **Two-phase sensitivity analysis approach:**
  - **Phase 1 (LHS):** Latin Hypercube Sampling across **35 parameters** (300 samples per scenario)
  - **Phase 2 (OAT):** One-at-a-time analysis on **top 6 parameters** (selected by PRCC ranking)
- **~301 runs per scenario** (1 baseline + 300 LHS sensitivity runs)
- **Additional OAT runs:** ~120 runs per scenario (20 values × 6 top parameters)

The goal is to understand how transmission project economics vary with key technical and financial parameters, and to identify the primary cost and benefit drivers for different project types.

### Sensitivity Analysis Workflow

1. **LHS Sensitivity Analysis:** Run Latin Hypercube Sampling (LHS) to systematically vary all 35 parameters simultaneously across 300 samples. This provides efficient coverage of the parameter space while maintaining statistical properties.

2. **PRCC Calculation:** Calculate Partial Rank Correlation Coefficients (PRCC) for all 35 parameters against each BCR metric. PRCC measures the monotonic relationship between parameters and outputs while controlling for the effects of all other parameters.

3. **Top Parameter Selection:** Identify the top 6 parameters (by absolute PRCC value) for each BCR metric. Parameters with high absolute PRCC values (typically |PRCC| > 0.3) are considered influential.

4. **OAT Analysis:** Perform one-at-a-time parameter sweeps on the top 6 parameters. Each parameter is systematically varied across a range of values (typically 20 values) while holding all other parameters at baseline. This produces response curves showing how each BCR metric changes as a function of the parameter of interest.

---

## 🎯 Baseline Scenarios

### Scenario 1: Greenfield Rural Overhead AC - Medium Capacity

**Use Case:** Typical new rural transmission line connecting generation to load centers

**Configuration:**

```yaml
project:
  name: "S1_Rural_Overhead_AC_500MW"
  construction_type: "Overhead"
  ac_dc: "AC"
  capacity_mw: 460
  conductor_type: "Standard Aluminum Conductor"
  line_utilization: 0.70
  baseline_electricity_price_per_mwh: 50.0
  social_discount_rate: 0.03
  reconductoring: False

timeline:
  construction_years: 1
  delay_years: 4
  project_lifetime: 50

terrain:
  # Mix of low-cost rural terrain (100 miles total)
  forested: 20
  scrubbed_flat: 40
  wetland: 5
  farmland: 25
  rolling_hills: 10
```

**Expected Characteristics:**

- Moderate build costs
- Lower ROW costs (rural land)
- Significant line losses (medium capacity, long distance)
- Moderate congestion benefits

---

### Scenario 2: Greenfield Urban Underground AC - Low Capacity

**Use Case:** Urban congestion relief, densely populated area

**Configuration:**

```yaml
project:
  name: "S2_Urban_Underground_AC_200MW"
  construction_type: "Underground Direct-Buried"
  ac_dc: "AC"
  capacity_mw: 200
  conductor_type: "Advanced Aluminum Conductor"
  line_utilization: 0.70
  baseline_electricity_price_per_mwh: 75.0 # Higher urban prices
  social_discount_rate: 0.03
  reconductoring: False

timeline:
  construction_years: 2 # Longer construction for underground
  delay_years: 2.5 # More permitting challenges
  project_lifetime: 50

terrain:
  # Mostly urban terrain (20 miles total - shorter urban line)
  urban: 15
  farmland: 5
```

**Expected Characteristics:**

- Very high build costs (underground + urban)
- Very high ROW costs (urban land)
- Lower line losses (shorter distance)
- High congestion benefits (urban congestion relief)
- Higher electricity prices increase line loss costs and congestion benefits

---

### Scenario 3: Greenfield Long-Distance HVDC - High Capacity

**Use Case:** Interstate/regional bulk power transfer, renewable integration

**Configuration:**

```yaml
project:
  name: "S3_LongDistance_HVDC_1000MW"
  construction_type: "Overhead"
  ac_dc: "DC"
  capacity_mw: 1000
  conductor_type: "Advanced Aluminum Conductor"
  converter_type: "VSC Converter"
  number_of_converters: 2
  line_utilization: 0.80 # High utilization for major corridor
  baseline_electricity_price_per_mwh: 50.0
  social_discount_rate: 0.03
  reconductoring: False

timeline:
  construction_years: 3 # Longer for converters
  delay_years: 2.0
  project_lifetime: 50

terrain:
  # Long distance, varied terrain (300 miles total)
  forested: 80
  scrubbed_flat: 100
  wetland: 20
  farmland: 60
  rolling_hills: 30
  mountain: 10
```

**Expected Characteristics:**

- Very high build costs (converters + long distance)
- Lower line losses per mile (DC efficiency)
- High total line losses (long distance)
- Very high congestion benefits (bulk transfer)
- Significant curtailment reduction benefits (renewable integration)

---

### Scenario 4: Reconductoring Existing Line - Capacity Upgrade

**Use Case:** Upgrading congested existing corridor, avoiding new ROW

**Configuration:**

```yaml
project:
  name: "S4_Reconductoring_200to500MW"
  construction_type: "Overhead"
  ac_dc: "AC"
  reconductoring: True
  old_capacity_mw: 200
  old_conductor_type: "Standard Aluminum Conductor"
  old_ac_dc: "AC"
  capacity_mw: 500
  conductor_type: "Advanced Aluminum Conductor"
  line_utilization: 0.70
  baseline_electricity_price_per_mwh: 50.0
  social_discount_rate: 0.03

timeline:
  construction_years: 1
  delay_years: 0.5 # Shorter delay (existing ROW)
  project_lifetime: 50

terrain:
  # Mix of terrain (150 miles total)
  forested: 30
  scrubbed_flat: 50
  wetland: 10
  farmland: 40
  rolling_hills: 20
```

**Expected Characteristics:**

- Moderate build costs (conductor only, no new structures)
- Minimal ROW costs (existing ROW)
- **Line loss benefits** (reduced losses vs. baseline)
- High congestion benefits (expanding bottleneck)
- Faster permitting/construction

---

### Scenario 5: Greenfield Subsea AC - Island/Offshore Connection

**Use Case:** Island connection, offshore wind integration

**Configuration:**

```yaml
project:
  name: "S5_Subsea_AC_300MW"
  construction_type: "Subsea"
  ac_dc: "AC"
  capacity_mw: 300
  conductor_type: "Advanced Aluminum Conductor"
  line_utilization: 0.60 # Lower utilization, reliability-focused
  baseline_electricity_price_per_mwh: 60.0 # Higher island prices
  social_discount_rate: 0.03
  reconductoring: False

timeline:
  construction_years: 2
  delay_years: 2.0
  project_lifetime: 50

terrain:
  # Mostly subsea (60 miles total)
  subsea: 50
  scrubbed_flat: 10 # Coastal landing
```

**Expected Characteristics:**

- Very high build costs (subsea construction)
- High O&M costs (subsea maintenance)
- Moderate line losses
- High curtailment benefits (offshore wind integration)
- Lower wildfire/outage risks (subsea)

---

## 🔬 Sensitivity Analysis Methodology

### Phase 1: LHS Sensitivity Analysis (35 Parameters)

The first phase uses Latin Hypercube Sampling (LHS) to systematically explore the parameter space across **35 parameters** simultaneously. This approach is more efficient than one-at-a-time analysis because it:

- Captures parameter interactions and correlations
- Provides better coverage of the parameter space with fewer samples
- Enables robust statistical analysis (PRCC calculation)

#### Parameter Categories

The 35 parameters are organized into the following categories:

1. **Core Economic/Technical (18 parameters):**
   - `real_wacc_mult`, `wacc_nominal_mult`, `social_discount_rate_mult`, `inflation_rate_mult`
   - `delay_years`, `construction_years`, `project_lifetime`
   - `line_utilization_mult`, `electricity_price_mult`
   - `wildfire_ignition_rate_mult`
   - `congestion_price_mult`, `congestion_flow_factor_mult`, `congestion_binding_hours_mult`
   - `congestion_average_exceedance_mult`, `congestion_near_binding_hours_mult`
   - `congestion_near_binding_relief_factor_mult`, `congestion_saturation_factor_mult`
   - `environmental_mitigation_cost_mult`

2. **ROW Cost Multipliers (3 parameters):**
   - `row_acquisition_cost_mult`, `row_rent_cost_mult`, `row_hold_cost_mult`

3. **Terrain Multipliers (9 parameters):**
   - `terrain_mult_forested`, `terrain_mult_scrubbed_flat`, `terrain_mult_wetland`
   - `terrain_mult_farmland`, `terrain_mult_desert_barren`, `terrain_mult_urban`
   - `terrain_mult_rolling_hills`, `terrain_mult_mountain`, `terrain_mult_subsea`

4. **Operational/Risk (5 parameters):**
   - `outage_rate_mult`, `outage_growth_rate_mult`
   - `veg_om_per_mile_mult`
   - `labor_cost_mult`, `materials_cost_mult`

#### LHS Sampling Details

- **Samples per scenario:** 300 LHS samples
- **Total runs per scenario:** 301 (1 baseline + 300 LHS)
- **Parameter ranges:** Each parameter has a defined range (see `sensitivity_analysis.py` for details)
- **Sampling strategy:** Latin Hypercube ensures efficient coverage while maintaining statistical properties

### Phase 2: OAT Analysis (Top 6 Parameters)

After PRCC calculation identifies the most influential parameters, one-at-a-time (OAT) analysis is performed on the **top 6 parameters** (by absolute PRCC) for each BCR metric. This provides:

- Intuitive visualization of parameter impacts
- Identification of critical thresholds or non-linear relationships
- Response curves showing BCR sensitivity to each parameter

#### OAT Analysis Details

- **Parameters analyzed:** Top 6 per BCR metric (selected by PRCC ranking)
- **Values per parameter:** Typically 20 values across the parameter's range
- **Total OAT runs per scenario:** ~120 runs (20 values × 6 parameters)
- **Output:** Response curves showing BCR vs. parameter value

### Example: Traditional OAT Parameters (Historical Reference)

The following parameters were historically considered for one-at-a-time analysis. In the current implementation, the top parameters are selected dynamically based on PRCC results, but these remain important parameters that often appear in the top rankings:

### 1. Capacity Sensitivity

**Parameter:** `capacity_mw`

**Values:** [baseline × 0.5, baseline × 0.75, baseline, baseline × 1.25, baseline × 1.5]

**Examples by Scenario:**

- S1 (500 MW): 250, 375, 500, 625, 750 MW
- S2 (200 MW): 100, 150, 200, 250, 300 MW
- S3 (1000 MW): 500, 750, 1000, 1250, 1500 MW
- S4 (500 MW): 250, 375, 500, 625, 750 MW
- S5 (300 MW): 150, 225, 300, 375, 450 MW

**Expected Insights:**

- How do build costs scale with capacity? (Linear? Sublinear? Superlinear?)
- At what capacity do economies of scale diminish?
- Line loss cost vs. capacity relationship
- Congestion benefit vs. capacity trade-off
- Optimal capacity for each scenario type

**Key Metrics to Track:**

- Build cost per MW
- Line loss cost per MWh delivered
- Congestion benefit per MW
- Total NPV per MW

---

### 2. Line Utilization Sensitivity

**Parameter:** `line_utilization`

**Values:** [0.50, 0.60, 0.70, 0.80, 0.90]

**Expected Insights:**

- Impact on line losses (quadratic relationship with current)
- Effect on congestion/curtailment benefits
- Trade-off between utilization and losses
- Optimal utilization level for economic efficiency
- Spare capacity value

**Key Metrics to Track:**

- Line loss cost vs. utilization
- MWh delivered vs. utilization
- Cost per MWh delivered (including losses)
- Benefits per MWh delivered

---

### 3. Electricity Price Sensitivity

**Parameter:** `baseline_electricity_price_per_mwh`

**Values:** [baseline × 0.5, baseline × 0.75, baseline, baseline × 1.25, baseline × 1.5]

**Examples by Scenario:**

- S1 ($50/MWh): $25, $37.50, $50, $62.50, $75
- S2 ($75/MWh): $37.50, $56.25, $75, $93.75, $112.50
- S3 ($50/MWh): $25, $37.50, $50, $62.50, $75
- S4 ($50/MWh): $25, $37.50, $50, $62.50, $75
- S5 ($60/MWh): $30, $45, $60, $75, $90

**Expected Insights:**

- Line loss cost elasticity to electricity price
- Congestion benefit elasticity to electricity price
- At what price do line losses become the dominant cost?
- Break-even price for project viability
- Price scenarios favoring different technologies (AC vs. DC)

**Key Metrics to Track:**

- Line loss cost sensitivity
- Congestion/curtailment benefit sensitivity
- Total benefit-cost ratio vs. price
- Price elasticity of NPV

---

### 4. Social Discount Rate Sensitivity

**Parameter:** `social_discount_rate`

**Values:** [0.02, 0.03, 0.04, 0.05, 0.07]

**Expected Insights:**

- NPV sensitivity to discount rate assumptions
- Impact on long-term costs/benefits (O&M, line losses)
- Comparison with WACC discount rates
- Sensitivity of project ranking to discount rate
- Time value of delay costs

**Key Metrics to Track:**

- Total NPV vs. discount rate
- Benefit-cost ratio vs. discount rate
- PV of long-term costs (O&M, line losses) vs. discount rate
- Delay cost PV vs. discount rate

---

### 5. Construction Delay Sensitivity

**Parameter:** `delay_years`

**Values:** [0, 1, 2, 3, 5] years

**Note:** Baseline delay varies by scenario (see scenario definitions)

**Expected Insights:**

- Cost of permitting/siting delays
- AFUDC accumulation with delay
- Foregone congestion/curtailment benefits
- Break-even delay (when to abandon project?)
- Difference between scenarios (urban vs. rural delays)

**Key Metrics to Track:**

- Delay cost (nominal and PV)
- AFUDC accumulation
- Foregone benefits (NPV)
- Total NPV reduction per year of delay
- % NPV loss per year of delay

---

### 6. Project Lifetime Sensitivity

**Parameter:** `project_lifetime`

**Values:** [30, 40, 50, 60] years

**Expected Insights:**

- Long-term value proposition
- Break-even timeline
- Impact of discount rate on lifetime value
- Difference between capital costs (upfront) and operational costs (long-term)
- Asset life assumptions impact

**Key Metrics to Track:**

- Total NPV vs. lifetime
- Benefit-cost ratio vs. lifetime
- PV of O&M costs vs. lifetime
- PV of line losses vs. lifetime
- Years to NPV break-even

---

## 📊 Analysis Matrix

### Runs per Scenario

**Phase 1: LHS Sensitivity Analysis**
- **1 baseline run**
- **300 LHS samples** (all 35 parameters varied simultaneously)
- **Total Phase 1: 301 runs per scenario**

**Phase 2: OAT Analysis (Top 6 Parameters)**
- **~120 OAT runs** (20 values × 6 top parameters, per BCR metric)
- Note: OAT runs are performed after PRCC identifies top parameters

### Total Analysis

- **5 scenarios** × **301 LHS runs** = **1,505 total LHS runs**
- **5 scenarios** × **~120 OAT runs** = **~600 total OAT runs**
- **Grand total: ~2,105 runs** (including baseline runs)

### Data Output

**LHS Results:**
- `results.csv`: All LHS runs with input parameters and output metrics
- `prcc_values.csv`: PRCC coefficients for all 35 parameters across all BCR metrics
- `prcc_heatmap.png`: Visualization of PRCC values
- `tornado_*.png`: Tornado diagrams for each BCR metric
- `scatter_top6_*.png`: Scatter plots for top 6 parameters

**OAT Results:**
- `oat_results_*.csv`: OAT sweep results for each BCR metric
- `oat_*_plot1.png`: Response curves for top 6 parameters per BCR metric
- `oat_summary.csv`: Combined OAT results

All runs include:
- **35 input parameters** (from LHS sampling)
- **scenario_id** and **timestamp** for tracking
- **~55 financial metrics** (costs, benefits, NPV values)
- **5 BCR metrics** (bcr_system, bcr_capital, bcr_excluding_risk, bcr_excluding_emissions, bcr_excluding_emissions_and_risk)

---

## 📈 Expected Analyses and Visualizations

### 1. PRCC Sensitivity Analysis Results

**Analysis:** Identify which parameters most significantly influence project economics

**Visualizations:**
- **PRCC Heatmap:** Shows PRCC values for all 35 parameters across all BCR metrics
- **Tornado Diagrams:** Bar charts ranking parameters by absolute PRCC for each BCR metric
- **Scatter Plots:** Parameter vs. BCR relationships for top 6 parameters
- **Parallel Coordinates Plot:** Multi-dimensional visualization of parameter combinations and BCR outcomes

**Key Questions:**
- Which parameters have the highest PRCC values (most influential)?
- Are there parameters with consistently high PRCC across all BCR metrics?
- Which parameters have low PRCC (can be fixed at baseline values)?
- Are there parameter interactions visible in the parallel coordinates plot?

### 2. OAT Response Curves

**Analysis:** Detailed one-at-a-time sensitivity analysis for top 6 parameters

**Visualizations:**
- **OAT Response Curves:** BCR vs. parameter value plots for each top parameter
- **Baseline Reference Lines:** Vertical lines showing baseline parameter values
- **Non-linearity Detection:** Identify thresholds, breakpoints, or non-linear relationships

**Key Questions:**
- How does BCR change as each parameter varies?
- Are there critical thresholds where BCR changes dramatically?
- Which parameters show non-linear relationships?
- What is the sensitivity (slope) of BCR to each parameter?

### 3. Baseline Scenario Comparison

**Analysis:** Compare all 5 baseline scenarios side-by-side

**Visualizations:**

- Bar chart: Total build cost by scenario
- Bar chart: Total NPV (benefits - costs) by scenario
- Bar chart: Build cost per MW by scenario
- Stacked bar: Cost breakdown by category (build, ROW, O&M, line losses, etc.)
- Bar chart: Benefit breakdown (congestion, curtailment)

**Key Questions:**

- Which scenario type has lowest $/MW build cost?
- Which has highest NPV?
- Which has best benefit-cost ratio?
- What are the primary cost drivers for each scenario?

---

### 2. Capacity Sensitivity Curves

**Analysis:** For each scenario, plot key metrics vs. capacity

**Visualizations:**

- Line plot: Build cost vs. capacity (all scenarios)
- Line plot: Build cost per MW vs. capacity (economies of scale?)
- Line plot: Line loss cost vs. capacity
- Line plot: Total NPV vs. capacity
- Line plot: Benefit-cost ratio vs. capacity

**Key Questions:**

- Are there economies of scale in build costs?
- What's the optimal capacity for each scenario type?
- How do line losses scale with capacity?
- At what capacity does NPV maximize?

---

### 3. Utilization Sensitivity Curves

**Analysis:** For each scenario, plot key metrics vs. utilization

**Visualizations:**

- Line plot: Line loss cost vs. utilization (all scenarios)
- Line plot: Cost per MWh delivered vs. utilization
- Line plot: MWh delivered vs. utilization
- Line plot: Total NPV vs. utilization

**Key Questions:**

- What's the optimal utilization level?
- How steep is the line loss penalty at high utilization?
- Does optimal utilization differ by scenario?

---

### 4. Price Sensitivity Curves

**Analysis:** For each scenario, plot key metrics vs. electricity price

**Visualizations:**

- Line plot: Line loss cost vs. electricity price
- Line plot: Congestion benefit vs. electricity price
- Line plot: Total NPV vs. electricity price
- Line plot: Benefit-cost ratio vs. electricity price
- Scatter plot: Price elasticity of NPV by scenario

**Key Questions:**

- How sensitive is project viability to electricity price?
- At what price does the project become NPV-positive?
- Which scenarios are most/least sensitive to price?
- What's the price elasticity of line loss costs?

---

### 5. Discount Rate Sensitivity Curves

**Analysis:** For each scenario, plot NPV vs. discount rate

**Visualizations:**

- Line plot: Total NPV vs. discount rate (all scenarios)
- Line plot: Benefit-cost ratio vs. discount rate
- Line plot: PV of line losses vs. discount rate
- Line plot: PV of O&M vs. discount rate

**Key Questions:**

- How sensitive is NPV to discount rate assumptions?
- Which scenarios are most affected by discount rate?
- At what discount rate does project become unviable?
- Comparison with typical WACC rates?

---

### 6. Delay Sensitivity Analysis

**Analysis:** For each scenario, plot cost of delay

**Visualizations:**

- Bar chart: NPV loss per year of delay (all scenarios)
- Line plot: Total NPV vs. delay years
- Stacked bar: Delay cost components (AFUDC, foregone benefits)
- Bar chart: % NPV loss per year of delay

**Key Questions:**

- What's the cost of delay for each scenario?
- Which scenarios are most/least sensitive to delays?
- At what delay should project be abandoned?
- Urban vs. rural delay sensitivity?

---

### 7. Lifetime Sensitivity Analysis

**Analysis:** For each scenario, plot value vs. project lifetime

**Visualizations:**

- Line plot: Total NPV vs. project lifetime
- Line plot: Benefit-cost ratio vs. lifetime
- Line plot: Years to NPV break-even
- Bar chart: PV of lifetime costs vs. lifetime

**Key Questions:**

- How much value in extending asset life?
- At what lifetime does project break even?
- Diminishing returns to longer lifetimes?

---

### 8. Cross-Parameter Analysis

**Analysis:** Identify interactions between parameters

**Visualizations:**

- Heatmap: NPV by capacity and utilization
- Heatmap: NPV by price and discount rate
- Contour plot: Optimal capacity vs. price
- Tornado diagram: Sensitivity ranking by scenario

**Key Questions:**

- Which parameters have the largest impact on NPV?
- Are there parameter interactions?
- What's the rank order of sensitivities?
- Which parameters should be focused on?

---

## 🎯 Key Success Metrics

For each scenario and sensitivity run, calculate:

### Economic Metrics

1. **Total Build Cost (PV)**: Present value of all construction costs
2. **Total Lifetime Costs (PV)**: Build + O&M + ROW + Insurance + Line Losses
3. **Total Lifetime Benefits (PV)**: Congestion + Curtailment benefits
4. **Net Present Value (NPV)**: Benefits - Costs
5. **Benefit-Cost Ratio**: Benefits / Costs
6. **Levelized Cost per MWh**: Total costs / Total MWh delivered

### Efficiency Metrics

7. **Build Cost per MW**: Build cost / Capacity
8. **Line Loss Rate**: MWh lost / MWh generated
9. **Capacity Factor**: Actual utilization / Capacity
10. **Cost per Mile**: Total cost / Line length

### Sensitivity Metrics

11. **Elasticity**: % change in NPV / % change in parameter
12. **Break-even Point**: Parameter value where NPV = 0
13. **Optimal Value**: Parameter value that maximizes NPV
14. **Sensitivity Rank**: Relative importance of each parameter

---

## 🚀 Implementation Plan

### Phase 1: Baseline Scenario Runs (Week 1)

1. Define all 5 baseline scenarios in YAML format
2. Run CTCC for each baseline
3. Verify outputs and review results
4. Document any issues or adjustments needed

### Phase 2: Sensitivity Analysis Automation (Week 2)

1. Create Python script to automate sensitivity runs
2. Test with one scenario across all parameters
3. Debug and refine
4. Run all 155 scenarios

### Phase 3: Data Analysis (Week 3)

1. Load all results into analysis framework
2. Generate all visualizations
3. Calculate all metrics
4. Document findings

### Phase 4: Reporting (Week 4)

1. Create comprehensive report with findings
2. Highlight key insights and recommendations
3. Present trade-offs and optimal configurations
4. Document methodology and assumptions

---

## 📁 File Structure

```
outputs/
├── batch_summary.csv              # All LHS runs (301 per scenario)

sensitivity_results/
├── scenario_<scenario_id>/
│   ├── lhs_samples.csv           # LHS parameter samples
│   ├── results.csv                # All LHS run results
│   ├── prcc_values.csv           # PRCC coefficients for all parameters
│   ├── prcc_heatmap.png          # PRCC visualization
│   ├── tornado_*.png              # Tornado diagrams per BCR metric
│   ├── scatter_top6_*.png        # Scatter plots for top 6 parameters
│   ├── parallel_coordinates_bcr_system.png
│   └── summary_stats.txt          # Summary statistics

oat_results/
├── scenario_<scenario_id>/
│   ├── oat_results_*.csv         # OAT results per BCR metric
│   ├── oat_*_plot1.png           # OAT response curves per BCR metric
│   └── oat_summary.csv           # Combined OAT results

scripts/
├── sensitivity_analysis.py       # LHS sensitivity analysis script
├── oat_analysis.py               # OAT analysis script
└── ctcc.py                       # Main CTCC calculator
```

---

## 🔍 Quality Control

### Validation Checks

**LHS Analysis:**
- [ ] All 301 LHS runs complete successfully (1 baseline + 300 samples)
- [ ] Each scenario has unique scenario_id
- [ ] All 35 parameters correctly sampled across their ranges
- [ ] No missing data in results.csv
- [ ] PRCC values calculated for all parameters and BCR metrics
- [ ] Results are physically reasonable (no negative costs, etc.)

**OAT Analysis:**
- [ ] Top 6 parameters identified from PRCC results
- [ ] All OAT sweeps complete (~120 runs per scenario)
- [ ] Response curves show expected trends
- [ ] Baseline values correctly marked on OAT plots
- [ ] No missing data in OAT results files

### Documentation

- [ ] All assumptions documented
- [ ] Any YAML parameter changes logged
- [ ] Unusual results investigated and explained
- [ ] Methodology clearly described
- [ ] Results reproducible

---

## 📝 Notes and Assumptions

### General Assumptions

1. All scenarios assume same basic financial parameters unless specified
2. Terrain configurations are representative but not specific to any real project
3. Congestion and curtailment benefits based on regional averages
4. Wildfire and outage probabilities based on construction type defaults

### Limitations

1. Does not include transmission rights/PPA considerations
2. Does not model dynamic electricity prices over project lifetime
3. Assumes constant utilization over lifetime
4. Does not include extreme weather/climate change impacts
5. Regulatory and permitting costs estimated, not project-specific

### Future Extensions

1. Monte Carlo simulation with multiple parameters varying simultaneously
2. Time-series electricity price modeling
3. Climate change scenario analysis
4. Regional-specific parameter sets (ERCOT, CAISO, PJM, etc.)
5. Integration with production cost modeling

---

## 📞 Contact and Review

**Document Version:** 1.0  
**Date:** 2025-11-04  
**Author:** CTCC Analysis Team

**Review Needed:**

- [ ] Scenario definitions reasonable and representative?
- [ ] Sensitivity parameter ranges appropriate?
- [ ] Analysis plan addresses key research questions?
- [ ] Implementation timeline feasible?
- [ ] Any scenarios or parameters missing?

---

_This document serves as the planning framework for comprehensive CTCC scenario analysis. It should be reviewed and approved before proceeding with automation script development._
