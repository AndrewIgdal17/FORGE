# Batch Summary CSV Column Reference

**Comprehensive Transmission Cost Calculator (CTCC)**  
**Total Columns: 97**

---

## SECTION 1: TECHNICAL PARAMETERS (Columns 1-18)

### Project Identification

1. **project_name** - User-defined project name/identifier
2. **scenario_id** - Unique scenario identifier (timestamp-based)
3. **timestamp** - When the scenario was run (ISO format)

### Core Technical Specifications

4. **construction_type** - Overhead, Underground Direct-Buried, Underground Tunnel, or Subsea
5. **ac_dc** - AC or DC transmission
6. **capacity_mw** - Project capacity in megawatts
7. **conductor_type** - Standard Aluminum Conductor or Advanced Aluminum Conductor
8. **line_length_miles** - Total line length in miles (sum of all terrain)
9. **line_utilization** - Percentage of capacity utilized [0-1]

### Converter Details (DC Projects)

10. **converter_type** - LCC Converter or VSC Converter (NA for AC)
11. **number_of_converters** - 1 or 2 (0 for AC projects)

### Reconductoring Details

12. **reconductoring** - True if upgrading existing line, False if greenfield
13. **old_capacity_mw** - Original capacity before reconductoring (0 if greenfield)
14. **old_conductor_type** - Original conductor type (empty if greenfield)
15. **old_ac_dc** - Original AC/DC type (empty if greenfield)

### Financial Parameters

16. **baseline_electricity_price_per_mwh** - Electricity price in $/MWh
17. **social_discount_rate** - Discount rate for NPV calculations (e.g., 0.03 = 3%)

### Timeline

18. **construction_years** - Years required for construction
19. **delay_years** - Years of delay before construction starts
20. **project_lifetime_years** - Project operational lifetime in years

---

## SECTION 2: BUILD COSTS (Columns 21-26)

### Total Build Costs

21. **build_cost_nominal** - Total construction cost (undiscounted)
22. **build_cost_afudc** - Build cost with AFUDC (financing during construction)
23. **build_cost_pv** - Build cost present value

### Build Cost Components

24. **build_conductor_nominal** - Conductor/cable costs
25. **build_structure_nominal** - Structure costs (towers, poles, foundations)
26. **build_converter_nominal** - Converter station costs (DC projects only)

---

## SECTION 3: INSURANCE COSTS (Columns 27-29)

27. **insurance_annual** - Annual operational insurance premium
28. **insurance_nominal** - Lifetime operational insurance costs (undiscounted)
29. **insurance_pv** - Operational insurance present value

---

## SECTION 3a: WILDFIRE LIABILITY INSURANCE (Columns 30-32)

30. **wildfire_liability_annual** - Annual wildfire liability insurance premium (ROL × Liability Limit)
31. **wildfire_liability_nominal** - Lifetime wildfire liability insurance costs (undiscounted)
32. **wildfire_liability_pv** - Wildfire liability insurance present value

---

## SECTION 4: RIGHT-OF-WAY (ROW) COSTS

### Total ROW Costs

- **row_cost_nominal** - Total ROW costs (undiscounted; capital + rent)
- **row_cost_afudc** - ROW capital with AFUDC (acquisition + holding only; used for rate base)
- **row_cost_pv** - ROW total present value (capital + rent)

### ROW Capital vs. Operational

- **row_capital_pv** - ROW capital PV (acquisition + holding); included in capital costs and rate base
- **row_rent_pv** - ROW rent PV; included in operational costs
- **row_capital_afudc** - ROW capital AFUDC (same as row_cost_afudc)
- **row_capital_nominal** - ROW capital nominal (acquisition + holding)
- **row_rent_nominal** - ROW rent nominal (annual ROW payment)

### ROW Cost Components (diagnostics)

- **row_acquisition_nominal** - Land acquisition costs
- **row_holding_nominal** - Holding costs during development
- **row_rent_nominal** - Annual rent payments (if leasing)

---

## SECTION 5: ENVIRONMENTAL MITIGATION (Columns 39-43)

### Total Environmental Costs

39. **env_mitigation_nominal** - Total environmental mitigation (undiscounted)
40. **env_mitigation_afudc** - Environmental costs with AFUDC
41. **env_mitigation_pv** - Environmental mitigation present value

### Environmental Components

42. **env_base_cost** - Base environmental compliance costs
43. **env_credits_cost** - Environmental offset/credit costs

---

## SECTION 6: DELAY COSTS (Columns 44-46)

44. **delay_cost_nominal** - Cost of construction delays (undiscounted)
45. **delay_cost_afudc** - Delay costs with AFUDC accumulation
46. **delay_cost_pv** - Delay cost present value

_Note: Delay costs include carrying costs during permitting/siting delays_

---

## SECTION 7: WILDFIRE COSTS (Columns 44-47)

44. **wildfire_eal** - Expected Annual Loss from wildfire events
45. **wildfire_nominal** - Lifetime wildfire costs (undiscounted)
46. **wildfire_pv** - Wildfire cost present value
47. **wildfire_events_per_year** - Expected frequency of wildfire events per year

_Note: Probabilistic cost of wildfires sparked by transmission line_

---

## SECTION 8: OUTAGE COSTS (Columns 48-51)

48. **outage_eac** - Expected Annual Cost from outages
49. **outage_nominal** - Lifetime outage costs (undiscounted)
50. **outage_pv** - Outage cost present value
51. **outage_events_per_year** - Expected frequency of outage events per year

_Note: Probabilistic cost of transmission line failures/disruptions_

---

## SECTION 9: CONGESTION BENEFITS (Columns 52-55)

52. **congestion_benefit_annual** - Annual congestion reduction savings
53. **congestion_benefit_nominal** - Lifetime congestion benefits (undiscounted)
54. **congestion_benefit_pv** - Congestion benefit present value
55. **congestion_benefit_haircut_pv** - Conservative congestion benefit (with saturation factor)

_Note: BENEFIT - Cost savings from reduced transmission congestion vs. do-nothing_

---

## SECTION 10: CURTAILMENT BENEFITS (Columns 56-59)

56. **curtailment_benefit_annual** - Annual curtailment reduction savings
57. **curtailment_benefit_nominal** - Lifetime curtailment benefits (undiscounted)
58. **curtailment_benefit_pv** - Curtailment benefit present value
59. **curtailment_benefit_haircut_pv** - Conservative curtailment benefit (with saturation factor)

_Note: BENEFIT - Cost savings from reduced renewable energy curtailment vs. do-nothing_

---

## SECTION 11: CONGESTION/CURTAILMENT DELAY COSTS (Columns 60-66)

### Delay-Related Costs

60. **congestion_delay_cost_nominal** - Cost of foregone congestion benefits during delay
61. **congestion_delay_cost_pv** - Congestion delay cost present value
62. **curtailment_delay_cost_nominal** - Cost of foregone curtailment benefits during delay
63. **curtailment_delay_cost_pv** - Curtailment delay cost present value

### Residual Congestion

64. **residual_congestion_annual** - Annual residual congestion remaining after project
65. **residual_congestion_nominal** - Lifetime residual congestion (undiscounted)
66. **residual_congestion_pv** - Residual congestion present value

_Note: Residual = congestion that project doesn't fully solve_

---

## SECTION 12: EMISSIONS COSTS (Columns 67-69)

67. **emissions_cost_nominal** - Lifetime emissions costs (undiscounted)
68. **emissions_cost_pv** - Emissions cost present value
69. **emissions_annual_cost** - Annual emissions cost

_Note: Cost of emissions from line losses (new generation needed to offset losses)_

---

## SECTION 13: ENERGY LOSS COSTS (Columns 70-74)

70. **energy_losses_pv** - Total energy loss cost present value (conductor + converter for DC; conductor only for AC)
71. **conductor_loss_pv** - Present value of conductor loss costs only; 0 for AC
72. **converter_loss_pv** - Present value of converter loss costs only (DC projects with converters); 0 for AC
73. **energy_losses_nominal** - Lifetime energy loss costs (undiscounted); total = conductor + converter for DC

_Note: "Line loss" is no longer used. Only conductor losses, converter losses, and total energy losses are reported. For greenfield = COST (new losses created). For reconductoring = BENEFIT (losses reduced). energy_losses_pv = conductor_loss_pv + converter_loss_pv. line_loss_costs.csv still has conductor, converter, and total detail rows._

---

## SECTION 14: OPERATIONS & MAINTENANCE (Columns 73-75)

73. **oandm_annual** - Annual O&M costs
74. **oandm_nominal** - Lifetime O&M costs (undiscounted)
75. **oandm_pv** - O&M present value

_Note: Includes conductor, structure, converter, and vegetation management costs_

---

## SECTION 15: BCR-CALCULATED BENEFIT/COST AGGREGATES

### Benefits (Column 76-78, 88)

76. **line_loss_benefit_pv** - Energy loss benefit for reconductoring projects (PV)
77. **total_benefits_pv** - Sum of all benefits (PV)
78. **total_benefits_haircut_pv** - Sum of conservative benefits (PV)
79. **total_benefits_nominal** - Sum of all benefits (undiscounted)

_Benefits = Congestion + Curtailment + Energy Loss (if reconductoring)_

### Cost Aggregates by Category (Columns 79-83, 89-93)

#### Present Value (PV)

79. **capital_costs_pv** - Build + ROW + Environmental (PV)
80. **operational_costs_pv** - O&M + Insurance + Energy Losses + Emissions (PV)
81. **risk_costs_pv** - Wildfire + Outage (PV)
82. **delay_costs_pv** - Construction Delay + Foregone Benefits + Residual (PV)
83. **total_costs_pv** - Sum of all costs (PV)

#### Nominal (Undiscounted)

89. **capital_costs_nominal** - Build + ROW + Environmental (nominal)
90. **operational_costs_nominal** - O&M + Insurance + Line Losses + Emissions (nominal)
91. **risk_costs_nominal** - Wildfire + Outage (nominal)
92. **delay_costs_nominal** - Construction Delay + Foregone Benefits + Residual (nominal)
93. **total_costs_nominal** - Sum of all costs (nominal)

---

## SECTION 16: BENEFIT-COST RATIOS & NET BENEFIT (Columns 84-87, 94)

### BCR Metrics

84. **bcr_system** - Conservative Benefits / Total Costs (primary metric for project viability, uses saturation-adjusted benefits)
85. **bcr_capital** - Conservative Benefits / Capital Costs (investor perspective, uses saturation-adjusted benefits)

### Net Benefit/Cost

87. **net_benefit_pv** - Total Benefits - Total Costs (PV)

- Negative = Net Cost (costs exceed benefits)
- Positive = Net Benefit (benefits exceed costs)

94. **net_benefit_nominal** - Total Benefits - Total Costs (nominal/undiscounted)

- Negative = Net Cost (costs exceed benefits)
- Positive = Net Benefit (benefits exceed costs)

---

## COLUMN ORGANIZATION SUMMARY

**Total: 94 columns**

1. **Technical Parameters** (1-20): 20 columns
2. **Build Costs** (21-26): 6 columns
3. **Insurance** (27-29): 3 columns
4. **ROW** (30-35): 6 columns
5. **Environmental** (36-40): 5 columns
6. **Delay Costs** (41-43): 3 columns
7. **Wildfire** (44-47): 4 columns
8. **Outage** (48-51): 4 columns
9. **Congestion Benefits** (52-55): 4 columns
10. **Curtailment Benefits** (56-59): 4 columns
11. **Congestion/Curtailment Delay** (60-66): 7 columns
12. **Emissions** (67-69): 3 columns
13. **Line Losses** (70-72): 3 columns
14. **O&M** (73-75): 3 columns
15. **Benefit/Cost Aggregates** (76-83, 88-93): 14 columns
16. **BCR & Net Benefit** (84-87, 94): 5 columns

---

## NOTES FOR REORDERING

### Current Structure Issues:

- Technical parameters are at the front (good!)
- Individual cost modules are interspersed
- BCR aggregates are at the end (somewhat scattered between PV and nominal)
- Benefits and costs are not clearly grouped

### Potential Improvements:

1. Keep technical parameters first (1-20)
2. Group all BENEFITS together
3. Group all COSTS by category (capital, operational, risk, delay)
4. Put aggregates (totals) together
5. Put BCR metrics at the very end
6. Within each group, order by: annual → nominal → AFUDC → PV

### Questions to Consider:

- Should scenario_id/timestamp be first or after technical params?
- Should benefits come before or after costs?
- Should detail breakdowns (conductor, structure, etc.) be near totals?
- Should PV and nominal be side-by-side or in separate sections?
