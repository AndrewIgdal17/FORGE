# Generally
- We don't need the project parameters at the top of each output tab
- Optional: tooltip or “(i)” linking to the appendix for exact definitions.
- I don't know if we need the Summary Tab. Maybe those values should be in the header?


# Costs
Order

1. **Delay Costs**
   - 1. Normal Delay Costs (base delay)
   - 2. Congestion Delay Costs
   - 3. Curtailment Delay Costs
2. **Capital Costs**
   - 1. Utility Perspective
   - 2. Societal Perspective
3. **Operational Costs**
   - 1. ROW
   - 2. Vegetation Management
   - 3. Maintenance
     - 1. Structure
     - 2. Conductor
     - 3. Converter
   - 4. Operational Insurance Costs
4. **Energy Losses**
   - 1. Line Losses
   - 2. Converter Losses
   - 3. Residual Exceedance
1. **Risk Costs**
   - 1. Wildfire Costs
     - 1. EAL (Expected Annual Loss / expected wildfire cost)
     - 2. Wildfire Liability
   - 2. Outage Costs
6. **Emissions**
   - 1. Costs ($)
   - 2. Amount (kg)


---

## What to provide under each

### 1. Delay Costs

- **1. Normal Delay Costs (base delay)**
  - Total nominal ($), total present value ($). Optionally: annual delay cost ($/yr) and delay years.
  - _Detail (if desired):_ breakdown by category (legal, admin, labor, material_and_equipment, regulatory, public_relations, project_management, miscellaneous); currently the calculator does not export these — only the total is in the API/CSV.
- **2. Congestion Delay Costs**
  - Nominal ($), present value ($). Optional: annual equivalent or years applied.
- **3. Curtailment Delay Costs**
  - Nominal ($), present value ($). Optional: annual equivalent or years applied.
- **Subtotal:** Sum of the three (nominal and PV).

---

### 2. Capital Costs

- **1. Utility Perspective**
  - Rate-base / AFUDC capital at COD (nominal $): Build + ROW capital (acquisition + holding) + Environmental mitigation.
  - Show: total capital at COD; optionally breakdown by Build, ROW capital, Environmental (each nominal and AFUDC at COD).
- **2. Societal Perspective**
  - Present value (real $) of the same capital: Build PV, ROW capital PV, Environmental PV.
  - Show: total capital PV; optionally same breakdown (Build, ROW, Environmental) in PV terms.
- For **Build:** optionally show conductor, structure, converter (nominal and, where applicable, AFUDC/PV).
- For **ROW capital:** acquisition ($) and holding / option fee ($); nominal and PV.
- For **Environmental:** base mitigation and credits (wetlands, habitat); nominal and PV.

---

### 3. Operational Costs

- **1. ROW**
  - ROW rent only (operational): annual ($/yr), nominal lifetime ($), present value ($). Not rate base.
- **2. Vegetation Management**
  - Annual ($/yr), nominal ($), PV ($).
- **3. Maintenance**
  - **Structure:** annual, nominal, PV.
  - **Conductor:** annual, nominal, PV.
  - **Converter:** annual, nominal, PV (DC only; 0 for AC).
  - Subtotal maintenance (structure + conductor + converter): annual, nominal, PV.
- **4. Operational Insurance Costs**
  - Annual premium ($/yr), nominal lifetime ($), PV ($).
  - If wildfire liability is shown here (operational insurance): same metrics; otherwise it can be under Risk.
- **Subtotal:** ROW rent + vegetation + maintenance + operational insurance (nominal and PV).

---

### 4. Energy Losses

- **1. Line Losses**
  - Energy: MWh/yr (and optionally lifetime MWh).
  - Cost: annual ($/yr), nominal ($), PV ($).
- **2. Converter Losses**
  - Energy: MWh/yr (and optionally lifetime MWh); 0 for AC.
  - Cost: annual ($/yr), nominal ($), PV ($).
- **Total energy losses:** MWh/yr and total cost (nominal, PV).
-  **Residual exceedance:** cost only ($/yr, nominal, PV) — unrelieved congestion/curtailment cost; no kg.

---

### 5. Risk Costs

- **1. Wildfire Costs**
  - **EAL (Expected Annual Loss):** annual cost ($/yr), nominal total ($), PV ($).
  - **Wildfire Liability:** annual premium ($/yr), nominal lifetime ($), PV ($).
  - Subtotal wildfire (EAL + liability): nominal, PV.
- **2. Outage Costs**
  - Annual ($/yr), nominal ($), PV ($). Optional: by terrain/segment if the app exposes it.
- **Subtotal risk:** nominal, PV.

---

### 6. Emissions

- **1. Costs ($)**
  - Total: nominal ($), PV ($). Optional: annual ($/yr).
  - By pollutant: CO2, SOx, NOx — each nominal ($) and PV ($).
- **2. Amount (kg)**
  - Total by pollutant: CO2 (kg), SOx (kg), NOx (kg). Optional: annual (kg/yr) and lifetime (kg).
- Optional: societal cost per kg by pollutant ($/kg) for reference.



# BCRs


### 1. Top: Single headline result

- **Net benefit (PV):** Total benefits − total costs ($). 
- Short note: “Benefits = congestion + curtailment (conservative/haircut). Revenue is a transfer and excluded from system benefits.”
- **Capital BCR:** Societal Benefits ÷ societal capital costs only.
- **Capital + delay BCR:** Societal Benefits ÷  societal (capital + delay costs).

### 2. Three perspectives 

Three labeled blocks so “who pays / who benefits” matches the appendix (maybe its an info note or something):

| Perspective | Benefits (PV) | Costs (PV) | BCR | Net benefit (PV) |
|-------------|---------------|------------|-----|-------------------|
| **System (societal)** | Congestion + curtailment (haircut) | All costs (capital + operational + energy/emissions + risk + delay) | System BCR | Benefits − costs |
| **Utility / TSP** | Revenue | Capital (afudc only) + delay + operational | Utility BCR | Revenue − those costs |
| **Ratepayer** | Congestion + curtailment | Revenue + energy losses | Ratepayer BCR | Benefits − those costs |

For each row, show the two totals, the BCR, and net benefit. 

### 4. Sensitivity / exclusions (grouped, not 16 separate rows)

Group by what is excluded; one row per exclusion set:

- Exclude **risk** (wildfire + outage + liability): BCR + optional net benefit; optional: excluded $ (PV) shown.
- Exclude **emissions**: BCR (optional: excluded $).
- Exclude **energy losses**: BCR (optional: excluded $).
- Exclude **emissions + energy losses**: BCR (optional: excluded $).
- Exclude **emissions + risk**: BCR (optional: excluded $).
- Exclude **energy losses + risk**: BCR (optional: excluded $).
- Exclude **emissions + energy losses + risk**: BCR (optional: excluded $).

**Wildfire-only vs outage-only** (the 4+4 variants) can live in a collapsible “More sensitivity” or “By risk type” section so the main view stays simple.

### 5. Optional: Custom BCR

Like we talked about last week. Could the app have toggles (e.g. “Exclude emissions”, “Exclude line losses”, “Exclude wildfire risk”, “Exclude outage risk”):

- One **Custom BCR** and **Custom net benefit (PV)** driven by those toggles 

