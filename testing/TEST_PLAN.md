# FORGE Testing Plan

## Overview
This plan covers testing all major functions of the Framework for Open Reproducible Grid Economics (FORGE), including CLI flags, calculation modules, API endpoints, and integration scenarios. The calculator is YAML-in, JSON-out.

---

## 1. CLI Mode Testing

### 1.1 Default run

**Test 1.1.1: Default Mode (YAML → JSON)**
- Command: `venv/bin/python3 forge.py`
- Expected Input: YAML files from `yamls/`
- Expected Output: `outputs/forge_results_<scenario_id>.json`
- Validation: JSON file exists, is valid, contains `scenario_id`, `costs`, `technical_parameters`

**Test 1.1.2: Simple Mode**
- Command: `venv/bin/python3 forge.py --simple`
- Validation: Console output suppressed except BCR analysis; JSON output still written

**Test 1.1.3: Custom Scenario ID**
- Command: `FORGE_SCENARIO_ID=custom_test_123 venv/bin/python3 forge.py --simple`
- Validation: Output file named `forge_results_custom_test_123.json`

### 1.2 Command-Line Flags
Test calculation control flags:

**Test 1.2.1: Skip Wildfire**
- Command: `venv/bin/python3 forge.py --no_wildfire --simple`
- Validation: `wildfire_costs` skipped

**Test 1.2.2: Skip Outages**
- Command: `venv/bin/python3 forge.py --no_outages --simple`
- Validation: `outage_costs` skipped

**Test 1.2.3: Skip Emissions**
- Command: `venv/bin/python3 forge.py --no_emissions --simple`
- Validation: `emissions`, `facilitated_emissions`, and `displacement_delay_cost` skipped

**Test 1.2.4: Skip Line Losses**
- Command: `venv/bin/python3 forge.py --no_linelosses --simple`
- Validation: `line_loss_costs` skipped

**Test 1.2.5: Capital Only Mode**
- Command: `venv/bin/python3 forge.py --capital_only --simple`
- Validation: Only `weighted_miles`, `build_costs`, `row_costs`, `environmental_mitigation` run

**Test 1.2.6: Other `--no_*` flags**
- Commands:
  - `venv/bin/python3 forge.py --no_oandm --simple`
  - `venv/bin/python3 forge.py --no_insurance --simple`
  - `venv/bin/python3 forge.py --no_delay_costs --simple`
  - `venv/bin/python3 forge.py --no_congestion --simple`
- Validation: Matching module skipped (O&M, insurance, delay, congestion)

---

## 2. Calculation Module Testing

### 2.1 Individual Module Testing
Test each of the 17 calculator modules in `scripts/calc/`, plus preprocessing in `scripts/utils/`:

**Test 2.1.1: Weighted Miles (Preprocessing)**
```bash
venv/bin/python3 -m scripts.utils.weighted_miles
```
- Validation: Terrain multiplier calculated correctly

**Test 2.1.2: Build Costs**
```bash
venv/bin/python3 -m scripts.calc.build_costs
```
- Validation: Nominal, AFUDC, and PV costs calculated

**Test 2.1.3–2.1.17: Remaining modules**
Run individually via `python -m`:
- `scripts.calc.row_costs`
- `scripts.calc.environmental_mitigation`
- `scripts.calc.revenue`
- `scripts.calc.insurance_costs`
- `scripts.calc.delay_costs`
- `scripts.calc.wildfire_costs`
- `scripts.calc.outage_costs`
- `scripts.calc.congestion_reduction`
- `scripts.calc.energy_losses`
- `scripts.calc.oandm`
- `scripts.calc.emissions`
- `scripts.calc.facilitated_emissions`
- `scripts.calc.displacement_delay_cost`
- `scripts.calc.line_loss_costs`
- `scripts.calc.bcr_calculator`
- `scripts.calc.bcr_trajectory`

**Test 2.1.18: BCR Calculator**
```bash
venv/bin/python3 -m scripts.calc.bcr_calculator
```
- Validation: Perspective BCRs present (`bcr_societal`, `bcr_utility`, `bcr_ratepayer`) and exclusion variants

### 2.2 Module Integration Testing

**Test 2.2.1: Dependencies**
- Validate: weighted_miles runs before all other scripts
- Validate: energy_losses runs before line_loss_costs
- Validate: All cost modules complete before BCR calculation

**Test 2.2.2: Data Flow**
- Test: Data written by one module is correctly read by dependent modules
- Test: Aggregated JSON accumulates results from all modules

---

## 3. Smart Loaders & Output Testing

### 3.1 Smart Loaders

Calculator input is YAML-only. `scripts.utils.smart_loaders` re-exports `scripts.io.yaml_loaders`.

**Test 3.1.1: YAML Loader**
```bash
python3 -c "from scripts.utils.smart_loaders import load_project_technical_details; print(load_project_technical_details())"
```
- Validation: Loads from YAML files correctly

**Test 3.1.2: Loader Coverage**
- Validate loader functions work (`load_project_technical_details`, `load_financing_details`, `get_physical_data_raw`, etc.)

### 3.2 Smart Output

Output is JSON-only (`SmartOutputManager` → `JSONOutputManager`).

**Test 3.2.1: JSON Output Manager**
```bash
python3 -c "from scripts.utils.smart_output import SmartOutputManager; mgr = SmartOutputManager(); print(type(mgr._manager))"
```
- Validation: Delegates to `JSONOutputManager` (or the shared in-process manager)

**Test 3.2.2: Output Methods**
- Test: `add_*` methods exist on the manager
- Test: In-process runs write a single `forge_results_<id>.json`

---

## 4. Web Server & API Testing

### 4.1 Server Startup

**Test 4.1.1: Start FastAPI Server**
```bash
./run_calc_server.command
```
- Validation: Server starts on port 8000 (from repo root)
- Validation: No startup errors

**Test 4.1.2: Health Check**
```bash
curl http://localhost:8000/
```
- Expected: Returns HTML (`landing.html`)

**Test 4.1.3: Workspace UI**
```bash
curl -I http://localhost:8000/app/workspace
```
- Expected: Serves `workspace.html` (main app entry)

### 4.2 API Endpoints

**Test 4.2.1: GET /api/final_combined**
```bash
curl http://localhost:8000/api/final_combined | jq .
```
- Validation: Returns complete JSON configuration
- Validation: JSON is valid and parseable

**Test 4.2.2: POST /api/forge/calculate**
```bash
curl -X POST http://localhost:8000/api/forge/calculate \
  -H "Content-Type: application/json" \
  -d '{
    "input_mode": "json",
    "output_mode": "json",
    "scenario_id": "api_test",
    "combined_data": <final_combined_content>
  }' | jq .
```
- Validation: Returns success=true
- Validation: results object contains cost modules
- Validation: BCR metrics present

**Test 4.2.3: GET /api/outputs/{filename}**
```bash
# Preview (CSV files in outputs/ only)
curl http://localhost:8000/api/outputs/batch_summary.csv

# Download
curl "http://localhost:8000/api/outputs/batch_summary.csv?download=true" -o test_batch_summary.csv
```
- Validation: File returned if it exists under `outputs/`
- Validation: Download flag sets proper headers
- Validation: Security checks prevent directory traversal; non-CSV names rejected

**Test 4.2.4: Other metadata endpoints**
```bash
curl http://localhost:8000/api/taxonomy | jq .
curl http://localhost:8000/api/input_metadata | jq .
curl http://localhost:8000/api/fuel_mix_presets | jq .
```
- Validation: Each returns valid JSON

**Test 4.2.5: Error Handling**
- Test: Missing combined_data (server may fill from `final_combined`)
- Test: Malformed JSON
- Test: Non-existent output file
- Expected: Appropriate HTTP error codes (400, 404, 422, 500)

---

## 5. YAML ↔ JSON Conversion Testing

### 5.1 YAML to JSON Conversion

**Test 5.1.1: Command-Line Converter**
```bash
venv/bin/python3 yaml_to_json.py yamls/ test_combined.json
```
- Validation: YAML files converted (template skipped)
- Validation: Output JSON has expected top-level keys
- Validation: No data loss during conversion

**Test 5.1.2: Server Converter**
```bash
cd server
./regenerate_json_from_yaml.command
```
- Validation: Writes per-file JSON under `server/json/`
- Validation: Creates `final_combined.json`
- Validation: File is valid JSON

### 5.2 Data Integrity

**Test 5.2.1: Round-Trip Comparison**
- Run: YAML→JSON with scenario A (`forge.py --simple`)
- Convert: YAML→JSON via `yaml_to_json.py`
- Validation: Calculation JSON is valid and contains required keys

---

## 6. Financial Calculations Testing

### 6.1 AFUDC Calculations

**Test 6.1.1: Verify AFUDC Logic**
- Input: Known build cost, construction period, AFUDC rate
- Expected Output: Capitalized cost = base cost × (1 + rate × time)
- Test with: 1 year, 2 years, 3 years construction periods

**Test 6.1.2: Multi-Year Construction**
- Test: AFUDC applied to costs incurred over multiple years
- Validation: Earlier costs accumulate more interest

### 6.2 Present Value Calculations

**Test 6.2.1: PV Discount Rate**
- Test: Different discount rates (3%, 4.85%, 7%)
- Validation: Higher discount rates = lower PV

**Test 6.2.2: Time-Shifted Costs**
- Test: Costs in year 1, 5, 10, 20, 50
- Validation: Further costs discounted more heavily

### 6.3 BCR Metrics

**Test 6.3.1: Societal BCR**
- Key: `bcr_societal`
- Test: BCR > 1.0 (economically viable)
- Test: BCR < 1.0 (not viable)

**Test 6.3.2: Stakeholder BCRs**
- Keys: `bcr_utility`, `bcr_ratepayer`
- Validation: Present in BCR output

**Test 6.3.3: Exclusion BCRs**
- Test: `bcr_excl_avoided_emissions`, `bcr_excl_emissions_costs`, `bcr_excl_all_emissions`
- Test: `bcr_excl_outage`, `bcr_excl_wildfire`, `bcr_excl_outage_wildfire`
- Validation: Exclusions match taxonomy definitions

---

## 7. Edge Cases & Error Handling

### 7.1 Input Validation

**Test 7.1.1: Missing YAML Files**
- Remove: yamls/01_project_technical_details.yaml
- Expected: Error message indicating missing file

**Test 7.1.2: Invalid YAML Syntax**
- Corrupt: One YAML file with syntax error
- Expected: YAML parsing error with file location

**Test 7.1.3: Invalid JSON**
- Provide: Malformed JSON to API
- Expected: 400/422 error with validation message

**Test 7.1.4: Missing Required Fields**
- Remove: Required field from configuration
- Expected: KeyError with field name

### 7.2 Extreme Values

**Test 7.2.1: Zero Values**
- Test: Line length = 0 miles
- Test: Capacity = 0 MW
- Expected: Graceful handling or clear error

**Test 7.2.2: Very Large Values**
- Test: Line length = 10,000 miles
- Test: Capacity = 10,000 MW
- Validation: Calculations complete without overflow

**Test 7.2.3: Negative Values**
- Test: Negative discount rate
- Test: Negative costs
- Expected: Validation error or warning

### 7.3 Concurrent Execution

**Test 7.3.1: Multiple Scenario IDs**
```bash
FORGE_SCENARIO_ID=scenario1 venv/bin/python3 forge.py --simple &
FORGE_SCENARIO_ID=scenario2 venv/bin/python3 forge.py --simple &
FORGE_SCENARIO_ID=scenario3 venv/bin/python3 forge.py --simple &
wait
```
- Validation: All three complete successfully
- Validation: Output files don't overwrite each other
- Validation: Unique scenario IDs prevent conflicts

---

## 8. Integration & Workflow Testing

### 8.1 Complete Workflows

**Test 8.1.1: Full Analysis Workflow**
1. Edit configuration: `yamls/01_project_technical_details.yaml`
2. Run calculation: `venv/bin/python3 forge.py`
3. View results: Check `outputs/forge_results_*.json`
4. Validation: Modules complete, BCR calculated

**Test 8.1.2: Multi-Scenario Comparison**
1. Run baseline: `FORGE_SCENARIO_ID=baseline venv/bin/python3 forge.py --simple`
2. Modify config (capacity +20%)
3. Run high_capacity: `FORGE_SCENARIO_ID=high_capacity venv/bin/python3 forge.py --simple`
4. Compare: `diff outputs/forge_results_baseline.json outputs/forge_results_high_capacity.json`
5. Validation: Costs increase proportionally

**Test 8.1.3: Web UI Workflow**
1. Start server: `./run_calc_server.command` (repo root)
2. Open browser: `http://localhost:8000/app/workspace`
3. Edit configuration in UI
4. Run calculation via UI
5. Inspect JSON results
6. Validation: UI matches CLI results

### 8.2 API Integration Workflow

**Test 8.2.1: Programmatic Processing**
1. Fetch config: `GET /api/final_combined`
2. Modify parameters programmatically
3. Submit calculation: `POST /api/forge/calculate`
4. Parse JSON results
5. Validation: Automation workflow works end-to-end

---

## 9. Performance Testing

### 9.1 Execution Time

**Test 9.1.1: CLI Performance**
- Measure: Time for complete calculation
- Target: < 30 seconds for 100-mile project

**Test 9.1.2: API Performance**
- Measure: Response time for in-process API calculation
- Target: < 35 seconds

### 9.2 Memory Usage

**Test 9.2.1: Memory Footprint**
- Monitor: Peak memory during calculation
- Validation: No memory leaks
- Target: < 500 MB RAM

---

## 10. Documentation & Help Testing

**Test 10.1: Help Text**
```bash
venv/bin/python3 forge.py --help
```
- Validation: All flags documented (`--simple`, `--capital_only`, `--no_*`)
- Validation: Examples provided

**Test 10.2: README Examples**
- Test: Each example in README.md works as described
- Validation: No outdated commands or broken examples

---

## 11. Pytest Suites

Automated unit and validation tests live outside `run_tests.py`.

```bash
# From repo root: 15 tests
python -m pytest test/ -v
# test/test_capacity_value.py
# test/test_build_costs.py
# test/test_bcr_incremental_comparison.py

python -m pytest scripts/tests/ -v
# scripts/tests/test_facilitated_emissions.py
# scripts/tests/validate_tier2_batch1.py

python -m pytest testing/test_api_validation.py -v
```

---

## Test Execution Summary

### Priority Levels
- **P0 (Critical)**: CLI flags, API endpoints, calculation modules
- **P1 (High)**: Financial calculations, BCR metrics, error handling
- **P2 (Medium)**: Edge cases, performance, documentation
- **P3 (Low)**: Concurrent execution, extreme values

### Recommended Test Order
1. CLI Mode Testing (1.1, 1.2)
2. API Endpoints (4.2)
3. Calculation Modules (2.1)
4. Financial Calculations (6.1-6.3)
5. Integration Workflows (8.1-8.2)
6. Edge Cases (7.1-7.2)
7. Performance (9.1-9.2)
8. Pytest suites (11)

### Success Criteria
- ✅ All P0 tests pass
- ✅ 95%+ P1 tests pass
- ✅ 80%+ P2 tests pass
- ✅ Known issues documented for failing tests

### Test Results Tracking

Create a test results file to track progress:

```markdown
# Test Results

## Date: YYYY-MM-DD
## Tester: [Name]

| Test ID | Description | Status | Notes |
|---------|-------------|--------|-------|
| 1.1.1   | Default YAML→JSON | ⬜ | |
| 1.1.2   | --simple | ⬜ | |
| 1.1.3   | Custom scenario ID | ⬜ | |
...
```

Status Legend:
- ⬜ Not tested
- ✅ Pass
- ❌ Fail
- ⚠️ Partial/Warning
- 🔄 In progress
