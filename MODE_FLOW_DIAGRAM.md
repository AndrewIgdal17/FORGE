# CTCC Mode Flow Diagram

## Overview
CTCC has 2 entry points with different mode support:
- **ctcc.py** (CLI) - YAML→CSV ONLY (hardcoded)
- **ctcc_processor.py** (API) - Supports YAML→CSV and JSON→JSON modes

---

## Entry Point 1: ctcc.py (Command Line Interface)

```
┌─────────────────────────────────────────────────────────────────────┐
│                            ctcc.py                                  │
│                       (CLI Entry Point)                             │
│                                                                     │
│  ⚠️  FIXED MODE - NO ENVIRONMENT VARIABLE SUPPORT                  │
│     Input:  YAML ONLY (hardcoded)                                  │
│     Output: CSV ONLY (hardcoded)                                   │
└─────────────────────────────────────────────────────────────────────┘
                                 │
                                 │ Runs directly from command line
                                 │ Generates: CTCC_SCENARIO_ID (timestamp)
                                 ▼
                    ┌────────────────────────┐
                    │  FIXED CONFIGURATION   │
                    │  Input:  YAML          │
                    │  Output: CSV           │
                    │  (Cannot be changed)   │
                    └────────────────────────┘
                                 │
                                 ▼
        ┌────────────────────────────────────────────┐
        │         DATA LOADING LAYER                 │
        │  Scripts use smart_loaders.py              │
        │  BUT ctcc.py doesn't set env vars         │
        │  → Defaults to YAML mode                   │
        └────────────────────────────────────────────┘
                                 │
                                 ▼
                          ┌──────────────────┐
                          │  yaml_loaders.py │
                          │                  │
                          │  Loads from:     │
                          │  yamls/*.yaml    │
                          └──────────────────┘
                                 │
                                 ▼
        ┌────────────────────────────────────────────┐
        │      13 CALCULATION SCRIPTS                │
        │                                            │
        │  1. weighted_miles.py                      │
        │  2. build_costs.py                         │
        │  3. row_costs.py                           │
        │  4. environmental_mitigation.py            │
        │  5. delay_costs.py                         │
        │  6. insurance_costs.py                     │
        │  7. wildfire_costs.py                      │
        │  8. outage_costs.py                        │
        │  9. congestion_curtailment_reduction.py    │
        │  10. energy_losses.py                      │
        │  11. emissions.py                          │
        │  12. line_loss_costs.py                    │
        │  13. oandm.py                              │
        └────────────────────────────────────────────┘
                                 │
                                 ▼
        ┌────────────────────────────────────────────┐
        │         OUTPUT WRITING LAYER               │
        │  Scripts use smart_output.py               │
        │  BUT ctcc.py doesn't set env vars         │
        │  → Defaults to CSV mode                    │
        └────────────────────────────────────────────┘
                                 │
                                 ▼
                    ┌───────────────────────┐
                    │ csv_output_manager.py │
                    │                       │
                    │ Writes to:            │
                    │ outputs/*.csv         │
                    │ • batch_summary.csv   │
                    │ • build_costs.csv     │
                    │ • row_costs.csv       │
                    │ • etc.                │
                    └───────────────────────┘
                                 │
                                 ▼
                    ┌────────────────────────┐
                    │   bcr_calculator.py    │
                    │  (Final BCR Analysis)  │
                    └────────────────────────┘
                                 │
                                 ▼
                        ┌────────────────┐
                        │  Terminal      │
                        │  Output        │
                        │  (stdout)      │
                        └────────────────┘
```

### ctcc.py Mode Support

```python
# ctcc.py DOES NOT support environment variable mode switching
# It is HARDCODED to YAML → CSV mode

# Only environment variable used:
CTCC_SCENARIO_ID  = "<custom_id>"       # Generated internally (timestamp)
                                        # Set as env var for subprocesses
```

**⚠️ IMPORTANT:** ctcc.py is hardcoded to YAML→CSV mode and CANNOT be changed via environment variables. It does not read `CTCC_INPUT_MODE` or `CTCC_OUTPUT_MODE`.

**Technical Details:**
- Line 14: Imports `csv_output_manager` directly (not smart_output)
- Line 29: Runs scripts via subprocess without passing env vars for mode
- Lines 102-104: Hardcoded to use `CTCCOutputManager` (CSV mode)

**To use other modes, you must use `ctcc_processor.py` instead.**

---

## Entry Point 2: ctcc_processor.py (FastAPI Backend)

```
┌─────────────────────────────────────────────────────────────────────┐
│                   serverFastAPI/app/ctcc_processor.py               │
│                         (API Entry Point)                           │
│                                                                     │
│  Function: run_ctcc_calculation(payload)                           │
│                                                                     │
│  Payload structure:                                                │
│  {                                                                 │
│    "input_mode": "yaml" | "json",                                 │
│    "output_mode": "csv" | "json",                                 │
│    "scenario_id": "custom_id",                                    │
│    "combined_data": { ... }  // if input_mode = "json"           │
│  }                                                                 │
└─────────────────────────────────────────────────────────────────────┘
                                 │
                                 │ Routes based on mode combination
                                 │
            ┌────────────────────┼────────────────────┐
            │                    │                    │
            ▼                    ▼                    ▼
┌───────────────────┐  ┌──────────────────┐  ┌─────────────────────┐
│  JSON → JSON      │  │  YAML → CSV      │  │  Mixed Modes        │
│  (Full API Mode)  │  │  (Traditional)   │  │  (Subprocess)       │
└───────────────────┘  └──────────────────┘  └─────────────────────┘
            │                    │                    │
            │                    │                    │
            ▼                    ▼                    ▼
┌───────────────────────────────────────────────────────────────────┐
│                     MODE ROUTING LOGIC                             │
└───────────────────────────────────────────────────────────────────┘
```

### Mode 1: JSON → JSON (Full API Mode)

```
run_json_to_json(payload, scenario_id)
│
├─ 1. Write combined_data to temp JSON file
│     Location: /tmp/ctcc_data_{scenario_id}_*.json
│     Purpose: Allow subprocess scripts to load JSON data
│
├─ 2. Set environment variables
│     CTCC_SCENARIO_ID = scenario_id
│     CTCC_INPUT_MODE = "json"
│     CTCC_OUTPUT_MODE = "json"
│     CTCC_JSON_DATA_FILE = <temp_file_path>
│
├─ 3. Initialize JSONOutputManager(scenario_id)
│     Purpose: Aggregate results from subprocesses
│
├─ 4. Run 13 calculation scripts via subprocess
│     For each script in scripts list:
│     ├─ subprocess.run([venv/bin/python3, script])
│     │   │
│     │   ├─ Script loads data via json_loaders.py
│     │   │   └─ Reads from temp JSON file (CTCC_JSON_DATA_FILE)
│     │   │
│     │   ├─ Script performs calculations
│     │   │
│     │   └─ Script saves output via smart_output.py
│     │       └─ Writes to outputs/json_output_{scenario}_{script}.json
│     │
│     └─ Collect exit codes and errors
│
├─ 5. Aggregate JSON output files
│     Pattern: outputs/json_output_{scenario}_*.json
│     For each JSON file:
│     └─ output_manager.load_from_file(json_file)
│         └─ Merges data into main output_manager
│
├─ 6. Calculate BCR metrics
│     bcr_calculator.calculate_and_display_bcr()
│     └─ output_manager.add_bcr_metrics(results)
│
├─ 7. Get final JSON results
│     results = output_manager.get_json_results()
│
├─ 8. Cleanup temp files
│     ├─ Delete temp JSON data file
│     └─ Delete all json_output_{scenario}_*.json files
│
└─ 9. Return response
      {
        "success": true/false,
        "scenario_id": "...",
        "timestamp": "...",
        "input_mode": "json",
        "output_mode": "json",
        "results": {
          "costs": { ... },
          "benefits": { ... },
          "summary": { ... },
          "bcr": { ... }
        },
        "scripts_run": 13,
        "total_scripts": 13,
        "error": null
      }
```

### Mode 2: YAML → CSV (Traditional Mode via API)

```
run_yaml_to_csv(scenario_id)
│
├─ 1. Set environment variables
│     CTCC_SCENARIO_ID = scenario_id
│     (No INPUT_MODE or OUTPUT_MODE - uses defaults)
│
├─ 2. Run ctcc.py as subprocess
│     subprocess.run([sys.executable, "ctcc.py"])
│     │
│     └─ ctcc.py runs in default YAML→CSV mode
│         └─ Generates CSV files in outputs/
│
├─ 3. Parse result
│     Check return code
│
└─ 4. Return response
      {
        "success": true/false,
        "scenario_id": "...",
        "input_mode": "yaml",
        "output_mode": "csv",
        "csv_files": [
          "batch_summary.csv",
          "build_costs.csv",
          ...
        ],
        "output_dir": "outputs/"
      }
```

### Mode 3: Mixed Modes (JSON→CSV or YAML→JSON)

```
run_via_subprocess(scenario_id, input_mode, output_mode)
│
├─ 1. Set environment variables
│     CTCC_SCENARIO_ID = scenario_id
│     CTCC_INPUT_MODE = input_mode
│     CTCC_OUTPUT_MODE = output_mode
│
├─ 2. Run ctcc.py as subprocess
│     subprocess.run([sys.executable, "ctcc.py"])
│     │
│     └─ ctcc.py respects environment variables
│         └─ Runs in specified mode combination
│
├─ 3. Parse result
│     Check return code
│
└─ 4. Return response
      {
        "success": true/false,
        "scenario_id": "...",
        "input_mode": input_mode,
        "output_mode": output_mode,
        "csv_files": [...] or null,
        "results": {...} or null
      }
```

---

## Mode Combination Matrix

| Input Mode | Output Mode | Entry Point | Implementation | Status |
|------------|-------------|-------------|----------------|--------|
| YAML | CSV | ctcc.py | Direct execution (ONLY mode supported) | ✅ Working |
| YAML | CSV | ctcc_processor.py | `run_yaml_to_csv()` → runs ctcc.py | ✅ Working |
| JSON | JSON | ctcc_processor.py | `run_json_to_json()` → subprocess scripts | ✅ Working |
| JSON | CSV | ctcc_processor.py | `run_via_subprocess()` → runs ctcc.py | ❌ Not supported* |
| YAML | JSON | ctcc_processor.py | `run_via_subprocess()` → runs ctcc.py | ❌ Not supported* |
| JSON | JSON | ctcc.py | N/A | ❌ Not supported* |

**\* These modes require ctcc.py to support environment variables, which it currently does not.**

---

## Smart Loaders and Output Managers

### Smart Loaders (Input Detection)

```
┌────────────────────────────────────────┐
│       smart_loaders.py                 │
│  Detects: CTCC_INPUT_MODE env var     │
└────────────────────────────────────────┘
                  │
     ┌────────────┴────────────┐
     │                         │
     ▼                         ▼
┌──────────────┐        ┌──────────────┐
│yaml_loaders  │        │json_loaders  │
│              │        │              │
│ _data_source │        │ _data_source │
│ ↓            │        │ ↓            │
│ Loads from:  │        │ Loads from:  │
│ yamls/*.yaml │        │ temp JSON    │
└──────────────┘        └──────────────┘
```

**Functions exported by smart_loaders.py:**
- `load_project_technical_details()`
- `load_physical_details()`
- `load_contingencies()`
- `load_financing_details()`
- `load_cost_timing_patterns()`
- `load_afudc_config()`
- `_data_source.get_data(key)` - Direct access for custom loads

### Smart Output (Output Detection)

```
┌────────────────────────────────────────┐
│       smart_output.py                  │
│  Detects: CTCC_OUTPUT_MODE env var    │
└────────────────────────────────────────┘
                  │
     ┌────────────┴────────────┐
     │                         │
     ▼                         ▼
┌──────────────────┐    ┌─────────────────────┐
│csv_output_manager│    │json_output_manager  │
│                  │    │                     │
│ Methods:         │    │ Methods:            │
│ • add_*_costs()  │    │ • add_*_costs()     │
│ • write_batch_   │    │ • save_to_file()    │
│   summary()      │    │ • load_from_file()  │
│                  │    │ • get_json_results()│
│ Writes to:       │    │ Writes to:          │
│ outputs/*.csv    │    │ outputs/json_*_.json│
└──────────────────┘    └─────────────────────┘
```

**API exported by smart_output.py:**
- `CTCCOutputManager()` - Smart wrapper class
- `add_build_costs(results)`
- `add_row_costs(results)`
- `add_environmental_mitigation(results)`
- `add_delay_costs(results)`
- `add_insurance_costs(results)`
- `add_wildfire_costs(results)`
- `add_outage_costs(results)`
- `add_oandm_costs(results)`
- `add_emissions_costs(results)`
- `add_line_loss_costs(results)`
- `add_congestion_curtailment(results)`
- `write_batch_summary()` - CSV: writes file, JSON: saves to file

---

## Environment Variables Reference

| Variable | Values | Default | Purpose |
|----------|--------|---------|---------|
| `CTCC_INPUT_MODE` | "yaml" \| "json" | "yaml" | Data source selection |
| `CTCC_OUTPUT_MODE` | "csv" \| "json" | "csv" | Output format selection |
| `CTCC_SCENARIO_ID` | any string | timestamp | Scenario identifier |
| `CTCC_JSON_DATA_FILE` | file path | N/A | Path to JSON data (JSON mode only) |

---

## Data Flow: JSON Mode (Detailed)

```
┌─────────────────────────────────────────────────────────────┐
│ 1. API receives POST request with combined_data JSON        │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. ctcc_processor.py writes to temp file                    │
│    /tmp/ctcc_data_{scenario}_xyz.json                      │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. For each calculation script (subprocess):                │
│    ┌──────────────────────────────────────────────────┐    │
│    │ a. Script starts with env vars set:              │    │
│    │    CTCC_INPUT_MODE=json                          │    │
│    │    CTCC_OUTPUT_MODE=json                         │    │
│    │    CTCC_JSON_DATA_FILE=/tmp/ctcc_data_...json   │    │
│    │    CTCC_SCENARIO_ID=scenario_id                  │    │
│    └──────────────────────────────────────────────────┘    │
│                         │                                   │
│    ┌──────────────────────────────────────────────────┐    │
│    │ b. Script imports smart_loaders                   │    │
│    │    → smart_loaders detects CTCC_INPUT_MODE=json │    │
│    │    → routes to json_loaders.py                   │    │
│    │    → json_loaders reads CTCC_JSON_DATA_FILE      │    │
│    │    → loads entire JSON into memory               │    │
│    └──────────────────────────────────────────────────┘    │
│                         │                                   │
│    ┌──────────────────────────────────────────────────┐    │
│    │ c. Script performs calculations                   │    │
│    │    Uses data loaded from JSON                     │    │
│    └──────────────────────────────────────────────────┘    │
│                         │                                   │
│    ┌──────────────────────────────────────────────────┐    │
│    │ d. Script imports smart_output                    │    │
│    │    → smart_output detects CTCC_OUTPUT_MODE=json │    │
│    │    → routes to json_output_manager.py            │    │
│    └──────────────────────────────────────────────────┘    │
│                         │                                   │
│    ┌──────────────────────────────────────────────────┐    │
│    │ e. Script calls output_manager.add_*_costs()     │    │
│    │    → Data stored in memory in output_manager     │    │
│    └──────────────────────────────────────────────────┘    │
│                         │                                   │
│    ┌──────────────────────────────────────────────────┐    │
│    │ f. Script calls output_manager.write_batch_      │    │
│    │    summary()                                      │    │
│    │    → smart_output routes to save_to_file()       │    │
│    │    → Writes outputs/json_output_{scenario}_      │    │
│    │      {script_name}.json                           │    │
│    └──────────────────────────────────────────────────┘    │
│                         │                                   │
│    ┌──────────────────────────────────────────────────┐    │
│    │ g. Script exits                                   │    │
│    └──────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. ctcc_processor.py aggregates all JSON files:             │
│    glob("outputs/json_output_{scenario}_*.json")           │
│    → Finds: build_costs.json, row_costs.json, etc.         │
│    → Calls output_manager.load_from_file() for each        │
│    → Merges all cost/benefit data into single structure    │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. Run BCR calculator                                       │
│    → Reads aggregated data                                  │
│    → Calculates benefit-cost ratios                         │
│    → Adds BCR metrics to output_manager                     │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. Generate final JSON response                             │
│    output_manager.get_json_results()                        │
│    → Returns complete structure with:                       │
│      • costs (all modules)                                  │
│      • benefits (congestion, curtailment)                   │
│      • summary (totals)                                     │
│      • bcr (benefit-cost ratios)                            │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ 7. Cleanup                                                   │
│    → Delete temp JSON data file                             │
│    → Delete all json_output_{scenario}_*.json files         │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ 8. Return JSON response to API caller                       │
└─────────────────────────────────────────────────────────────┘
```

---

## File System Structure

```
CTCC/
├── ctcc.py                          # CLI entry point (YAML→CSV default)
├── serverFastAPI/
│   └── app/
│       └── ctcc_processor.py        # API entry point (mode routing)
│
├── scripts/
│   ├── smart_loaders.py             # Input mode auto-detection
│   ├── smart_output.py              # Output mode auto-detection
│   │
│   ├── yaml_loaders.py              # YAML data loading
│   ├── json_loaders.py              # JSON data loading
│   │
│   ├── csv_output_manager.py        # CSV output writing
│   ├── json_output_manager.py       # JSON output writing
│   │
│   ├── [13 calculation scripts]     # Use smart_loaders & smart_output
│   └── bcr_calculator.py            # Final BCR analysis
│
├── yamls/                           # YAML input files
│   ├── 01_project_technical_details.yaml
│   ├── 02_project_physical_details.yaml
│   └── ... (15 total)
│
├── outputs/                         # Output directory
│   ├── *.csv                        # CSV outputs (CSV mode)
│   └── json_output_*_.json          # Temp JSON outputs (JSON mode)
│
└── serverFastAPI/json/
    └── final_combined.json          # Example combined JSON input
```

---

## Quick Reference

### Run ctcc.py:

```bash
# ONLY MODE SUPPORTED: YAML → CSV
python3 ctcc.py

# ❌ These do NOT work - ctcc.py ignores environment variables:
# export CTCC_INPUT_MODE=json    # IGNORED
# export CTCC_OUTPUT_MODE=json   # IGNORED
# python3 ctcc.py                # Still runs YAML → CSV

# To use other modes, use ctcc_processor.py instead
```

### Call ctcc_processor.py (API):

```python
from app.ctcc_processor import run_ctcc_calculation

# JSON → JSON (Full API mode)
result = run_ctcc_calculation({
    "input_mode": "json",
    "output_mode": "json",
    "scenario_id": "my_scenario",
    "combined_data": {...}  # Full JSON data
})

# YAML → CSV (Traditional mode)
result = run_ctcc_calculation({
    "input_mode": "yaml",
    "output_mode": "csv",
    "scenario_id": "my_scenario"
})

# Mixed modes
result = run_ctcc_calculation({
    "input_mode": "json",
    "output_mode": "csv",
    "scenario_id": "my_scenario",
    "combined_data": {...}
})
```

---

## Summary

### Supported Mode Combinations

| Input | Output | Via ctcc.py | Via ctcc_processor.py |
|-------|--------|-------------|----------------------|
| YAML | CSV | ✅ YES (only mode) | ✅ YES |
| JSON | JSON | ❌ NO | ✅ YES |
| JSON | CSV | ❌ NO | ❌ NO* |
| YAML | JSON | ❌ NO | ❌ NO* |

**\* Mixed modes would require ctcc.py to support environment variables**

### Key Limitations

1. **ctcc.py is hardcoded to YAML→CSV**
   - Does not read `CTCC_INPUT_MODE` or `CTCC_OUTPUT_MODE`
   - Cannot be configured for other modes
   - Uses `csv_output_manager` directly (not smart_output)

2. **ctcc_processor.py supports 2 modes:**
   - YAML→CSV via `run_yaml_to_csv()` (calls ctcc.py)
   - JSON→JSON via `run_json_to_json()` (subprocess with env vars)

3. **Mixed modes not supported** because:
   - Would require ctcc.py to detect environment variables
   - ctcc.py would need to be refactored to use smart_output
   - Currently ctcc.py hardcodes csv_output_manager

### To Enable Full Mode Support in ctcc.py

If you want ctcc.py to support all 4 modes, you would need to:

1. Replace line 14: `from csv_output_manager import CTCCOutputManager`
   With: `from smart_output import CTCCOutputManager`

2. Add environment variable passing to subprocess.run() on line 28:
   ```python
   env = os.environ.copy()  # Preserve environment variables
   result = subprocess.run(
       [sys.executable, script_name],
       capture_output=True,
       text=True,
       cwd="scripts",
       env=env  # Pass environment to subprocesses
   )
   ```

3. Keep lines 102-104 as-is (already uses CTCCOutputManager which would become smart_output)

---

**Last Updated:** 2025-11-10
**Status:**
- ✅ ctcc.py: YAML→CSV working
- ✅ ctcc_processor.py: YAML→CSV and JSON→JSON working
- ❌ Mixed modes: Not supported (would require ctcc.py refactoring)
