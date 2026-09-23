# FORGE Testing Plan

## Overview
This plan covers testing all major functions of the Framework for Open Reproducible Grid Economics (FORGE), including CLI modes, calculation modules, API endpoints, and integration scenarios.

---

## 1. CLI Mode Testing

### 1.1 Input/Output Mode Combinations
Test all four mode combinations:

**Test 1.1.1: Default Mode (YAML → CSV)**
- Command: `venv/bin/python3 forge.py`
- Expected Input: 22 YAML files from `yamls/`
- Expected Output: 12 CSV files in `outputs/` + `batch_summary.csv`
- Validation: Check all CSV files exist, contain data, no errors

**Test 1.1.2: JSON Input → CSV Output**
- Command: `venv/bin/python3 forge.py -j`
- Expected Input: Auto-generated `combined_data.json` from YAML
- Expected Output: 12 CSV files in `outputs/`
- Validation: Compare with YAML→CSV results (should be identical)

**Test 1.1.3: JSON Input → JSON Output**
- Command: `venv/bin/python3 forge.py -j -o --id test_scenario`
- Expected Input: `combined_data.json`
- Expected Output: Single `forge_results_test_scenario.json`
- Validation: JSON structure valid, contains all 13 cost modules

**Test 1.1.4: YAML Input → JSON Output (Not supported)**
- Command: `venv/bin/python3 forge.py -o`
- Expected: Should default to YAML input with JSON output
- Validation: Verify mode detection works correctly

### 1.2 Command-Line Flags
Test calculation control flags:

**Test 1.2.1: Skip Risk Calculations**
- Command: `venv/bin/python3 forge.py --norisk --simple`
- Validation: Wildfire and outage scripts skipped (11 scripts run instead of 13)

**Test 1.2.2: Skip Emissions**
- Command: `venv/bin/python3 forge.py --no_emissions --simple`
- Validation: Emissions script skipped (12 scripts run)

**Test 1.2.3: Skip Line Losses**
- Command: `venv/bin/python3 forge.py --no_linelosses --simple`
- Validation: Line loss script skipped (12 scripts run)

**Test 1.2.4: Capital Only Mode**
- Command: `venv/bin/python3 forge.py --capital_only --simple`
- Validation: Only 4 scripts run (weighted_miles, build, ROW, environmental)

**Test 1.2.5: Simple Mode**
- Command: `venv/bin/python3 forge.py --simple`
- Validation: Output suppressed except BCR analysis

**Test 1.2.6: Custom Scenario ID**
- Command: `venv/bin/python3 forge.py -j -o --id custom_test_123`
- Validation: Output file named `forge_results_custom_test_123.json`

---

## 2. Calculation Module Testing

### 2.1 Individual Module Testing
Test each of the 13 calculation scripts independently:

**Test 2.1.1: Weighted Miles (Preprocessing)**
```bash
export FORGE_INPUT_MODE=yaml
export FORGE_OUTPUT_MODE=csv
export FORGE_SCENARIO_ID=test
venv/bin/python3 scripts/weighted_miles.py
```
- Validation: Terrain multiplier calculated correctly

**Test 2.1.2: Build Costs**
```bash
venv/bin/python3 scripts/build_costs.py
```
- Validation: Nominal, AFUDC, and PV costs calculated
- Check: CSV output contains all required columns

**Test 2.1.3-2.1.13: Remaining Modules**
Test individually:
- insurance_costs.py
- row_costs.py
- environmental_mitigation.py
- delay_costs.py
- wildfire_costs.py
- outage_costs.py
- congestion_curtailment_reduction.py
- energy_losses.py
- emissions.py
- line_loss_costs.py
- oandm.py

**Test 2.1.14: BCR Calculator**
```bash
venv/bin/python3 scripts/bcr_calculator.py
```
- Validation: All BCR metrics calculated (system BCR, capital BCR, net benefits)

### 2.2 Module Integration Testing

**Test 2.2.1: Dependencies**
- Validate: weighted_miles runs before all other scripts
- Validate: energy_losses runs before line_loss_costs
- Validate: All cost modules complete before BCR calculation

**Test 2.2.2: Data Flow**
- Test: Data written by one module is correctly read by dependent modules
- Test: batch_summary.csv accumulates results from all modules

---

## 3. Smart Loaders & Output Testing

### 3.1 Smart Loaders

**Test 3.1.1: YAML Loader Selection**
```bash
export FORGE_INPUT_MODE=yaml
python3 -c "from scripts.smart_loaders import load_project_technical_details; print(load_project_technical_details())"
```
- Validation: Loads from YAML files correctly

**Test 3.1.2: JSON Loader Selection**
```bash
export FORGE_INPUT_MODE=json
export FORGE_JSON_DATA_FILE=server/json/final_combined.json
python3 -c "from scripts.smart_loaders import load_project_technical_details; print(load_project_technical_details())"
```
- Validation: Loads from JSON file correctly

**Test 3.1.3: Mode Auto-Detection**
- Test both modes return identical data structures
- Validate all loader functions work (load_project_technical_details, load_financing_details, etc.)

### 3.2 Smart Output

**Test 3.2.1: CSV Output Manager**
```bash
export FORGE_OUTPUT_MODE=csv
python3 -c "from scripts.smart_output import FORGEOutputManager; mgr = FORGEOutputManager(); print(type(mgr._manager))"
```
- Validation: Returns CSVOutputManager instance

**Test 3.2.2: JSON Output Manager**
```bash
export FORGE_OUTPUT_MODE=json
python3 -c "from scripts.smart_output import FORGEOutputManager; mgr = FORGEOutputManager(); print(type(mgr._manager))"
```
- Validation: Returns JSONOutputManager instance

**Test 3.2.3: Output Method Consistency**
- Test: All add_* methods exist in both managers
- Test: Methods have consistent signatures

---

## 4. Web Server & API Testing

### 4.1 Server Startup

**Test 4.1.1: Start FastAPI Server**
```bash
cd server
./run_calc_server.command
```
- Validation: Server starts on port 8000
- Validation: No startup errors

**Test 4.1.2: Health Check**
```bash
curl http://localhost:8000/
```
- Expected: Returns HTML (index.html)

### 4.2 API Endpoints

**Test 4.2.1: GET /api/final_combined**
```bash
curl http://localhost:8000/api/final_combined | jq .
```
- Validation: Returns complete JSON configuration (21 sections)
- Validation: JSON is valid and parseable

**Test 4.2.2: POST /api/forge/calculate (JSON→JSON)**
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
- Validation: results object contains all cost modules
- Validation: BCR metrics present

**Test 4.2.3: POST /api/forge/calculate (JSON→CSV)**
```bash
curl -X POST http://localhost:8000/api/forge/calculate \
  -H "Content-Type: application/json" \
  -d '{
    "input_mode": "json",
    "output_mode": "csv",
    "scenario_id": "api_test_csv",
    "combined_data": <final_combined_content>
  }' | jq .
```
- Validation: Returns success=true
- Validation: csv_files array contains 12+ files
- Validation: output_dir path provided

**Test 4.2.4: GET /api/outputs/{filename}**
```bash
# Preview
curl http://localhost:8000/api/outputs/batch_summary.csv

# Download
curl http://localhost:8000/api/outputs/batch_summary.csv?download=true -o test_batch_summary.csv
```
- Validation: CSV content returned
- Validation: Download flag sets proper headers
- Validation: Security checks prevent directory traversal

**Test 4.2.5: Error Handling**
- Test: Invalid scenario_id
- Test: Missing combined_data
- Test: Malformed JSON
- Test: Non-existent output file
- Expected: Appropriate HTTP error codes (400, 404, 500)

---

## 5. YAML ↔ JSON Conversion Testing

### 5.1 YAML to JSON Conversion

**Test 5.1.1: Command-Line Converter**
```bash
venv/bin/python3 yaml_to_json.py yamls/ test_combined.json
```
- Validation: All 21 YAML files converted (1 template skipped)
- Validation: Output JSON has 21 top-level keys
- Validation: No data loss during conversion

**Test 5.1.2: Server Converter**
```bash
cd server
./convert_yamls.command
```
- Validation: Prompts for directory selection
- Validation: Creates final_combined.json
- Validation: File is valid JSON

**Test 5.1.3: Auto-Conversion in CLI**
```bash
venv/bin/python3 forge.py -j
```
- Validation: Auto-converts YAML to JSON if no JSON file provided
- Validation: Creates combined_data.json in project root

### 5.2 Data Integrity

**Test 5.2.1: Round-Trip Comparison**
- Run: YAML→CSV with scenario A
- Convert: YAML→JSON
- Run: JSON→CSV with scenario B
- Compare: Scenario A and B results should be identical

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

**Test 6.3.1: System BCR Calculation**
- Formula: Total Benefits (PV) / Total Costs (PV)
- Test: BCR > 1.0 (economically viable)
- Test: BCR < 1.0 (not viable)

**Test 6.3.2: Capital BCR**
- Formula: Total Benefits / Capital Costs Only
- Validation: Excludes operational and risk costs

**Test 6.3.3: Exclusion BCRs**
- Test: System BCR (excl. risk)
- Test: System BCR (excl. emissions)
- Test: System BCR (excl. both)
- Validation: Exclusions properly subtract from denominator

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
- Expected: 400 error with validation message

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
venv/bin/python3 forge.py -j -o --id scenario1 &
venv/bin/python3 forge.py -j -o --id scenario2 &
venv/bin/python3 forge.py -j -o --id scenario3 &
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
3. View results: Check `outputs/batch_summary.csv`
4. Validation: All 13 modules complete, BCR calculated

**Test 8.1.2: Multi-Scenario Comparison**
1. Run baseline: `venv/bin/python3 forge.py -j -o --id baseline`
2. Modify config (capacity +20%)
3. Run high_capacity: `venv/bin/python3 forge.py -j -o --id high_capacity`
4. Compare: `diff outputs/forge_results_baseline.json outputs/forge_results_high_capacity.json`
5. Validation: Costs increase proportionally

**Test 8.1.3: Web UI Workflow**
1. Start server: `cd server && ./run_calc_server.command`
2. Open browser: `http://localhost:8000`
3. Edit configuration in UI
4. Run calculation via UI
5. Download CSV results
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
- Baseline: YAML→CSV mode
- Compare: JSON modes (should be similar)
- Target: < 30 seconds for 100-mile project

**Test 9.1.2: API Performance**
- Measure: Response time for API calculation
- Target: < 35 seconds (includes subprocess overhead)

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
- Validation: All flags documented
- Validation: Examples provided

**Test 10.2: README Examples**
- Test: Each example in README.md works as described
- Validation: No outdated commands or broken examples

---

## Test Execution Summary

### Priority Levels
- **P0 (Critical)**: CLI mode combinations, API endpoints, calculation modules
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
| 1.1.1   | Default YAML→CSV | ⬜ | |
| 1.1.2   | JSON→CSV | ⬜ | |
| 1.1.3   | JSON→JSON | ⬜ | |
...
```

Status Legend:
- ⬜ Not tested
- ✅ Pass
- ❌ Fail
- ⚠️ Partial/Warning
- 🔄 In progress
