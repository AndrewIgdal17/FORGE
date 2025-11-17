# CTCC Architecture & Mode Flow Diagram

Complete technical documentation of CTCC's architecture, data flow, and mode combinations, with detailed JSON conversion behavior.

**Last Updated:** 2025-11-17
**Version:** 2.1

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Mode Combinations](#mode-combinations)
4. [Data Flow](#data-flow)
5. [Entry Points](#entry-points)
6. [Smart Loaders & Output](#smart-loaders--output)
7. [File Structure](#file-structure)
8. [Environment Variables](#environment-variables)

---

## Overview

CTCC supports multiple input/output combinations through a flexible architecture:

- **Input Modes:** YAML or JSON
- **Output Modes:** CSV or JSON
- **Entry Points:** CLI (`ctcc.py`) or API (`server/app/ctcc_processor.py`)

### Key Design Principles

1. **Mode Abstraction** - Scripts don't know their input/output mode
2. **Smart Routing** - Automatic mode detection via environment variables
3. **Single Source of Truth** - Server processor delegates to `ctcc.py`
4. **Backwards Compatibility** - Traditional YAML→CSV mode preserved

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                         USER INTERFACES                       │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐  ┌────────────────┐  ┌─────────────────┐ │
│  │   CLI        │  │   Web UI       │  │   API Client    │ │
│  │   (Terminal) │  │   (Browser)    │  │   (Python/HTTP) │ │
│  └──────┬───────┘  └────────┬───────┘  └────────┬────────┘ │
│         │                   │                    │          │
└─────────┼───────────────────┼────────────────────┼──────────┘
          │                   │                    │
          ▼                   ▼                    ▼
┌─────────────────┐  ┌────────────────────────────────────────┐
│   ctcc.py       │  │   server/app/main.py (FastAPI)         │
│   (CLI Entry)   │  │   server/app/ctcc_processor.py         │
│                 │  └────────────────┬───────────────────────┘
│  Delegates to → │                   │
│  13 scripts     │  ← Delegates to ctcc.py via subprocess
└─────────┬───────┘                   │
          │                           │
          └───────────┬───────────────┘
                      ▼
         ┌─────────────────────────────┐
         │   Environment Variables     │
         │   • CTCC_INPUT_MODE         │
         │   • CTCC_OUTPUT_MODE        │
         │   • CTCC_SCENARIO_ID        │
         │   • CTCC_JSON_DATA_FILE     │
         └─────────────┬───────────────┘
                       ▼
         ┌─────────────────────────────┐
         │   13 Calculation Scripts    │
         │   (run as subprocesses)     │
         └─────────────┬───────────────┘
                       ▼
         ┌─────────────────────────────┐
         │   smart_loaders.py          │
         │   (routes to yaml/json)     │
         └─────────────┬───────────────┘
                       │
          ┌────────────┴────────────┐
          ▼                         ▼
  ┌───────────────┐         ┌──────────────┐
  │ yaml_loaders  │         │ json_loaders │
  └───────┬───────┘         └──────┬───────┘
          │                        │
          └───────────┬────────────┘
                      ▼
          ┌───────────────────────┐
          │   Calculation Logic   │
          └───────────┬───────────┘
                      ▼
         ┌─────────────────────────────┐
         │   smart_output.py           │
         │   (routes to csv/json)      │
         └─────────────┬───────────────┘
                       │
          ┌────────────┴────────────┐
          ▼                         ▼
  ┌─────────────────┐      ┌────────────────────┐
  │ csv_output_mgr  │      │ json_output_mgr    │
  └────────┬────────┘      └─────────┬──────────┘
           │                         │
           ▼                         ▼
   ┌─────────────┐          ┌──────────────────┐
   │ outputs/    │          │ ctcc_results_    │
   │ *.csv       │          │ [id].json        │
   └─────────────┘          └──────────────────┘
```

---

## Mode Combinations

### Supported Modes

| Input | Output | CLI  | API | Status | Use Case |
|-------|--------|------|-----|--------|----------|
| YAML  | CSV    | ✅   | ✅  | ✅ Working | Traditional analysis |
| JSON  | CSV    | ✅   | ✅  | ✅ Working | Single config, multiple outputs |
| JSON  | JSON   | ✅   | ✅  | ✅ Working | API integration |
| YAML  | JSON   | ❌   | ❌  | ⚠️ Unsupported | Not needed |

### Mode Selection

**CLI (ctcc.py):**
```bash
# YAML → CSV (default)
venv/bin/python3 ctcc.py

# JSON → CSV
venv/bin/python3 ctcc.py -j

# JSON → JSON
venv/bin/python3 ctcc.py -j -o
```

**API (POST /api/ctcc/calculate):**
```json
{
  "input_mode": "json",
  "output_mode": "json",
  "scenario_id": "test",
  "combined_data": { ... }
}
```

---

## Data Flow

### JSON Conversion vs Direct Loading

CTCC handles JSON input in two distinct ways depending on the context:

#### When JSON is Auto-Converted from YAML:

1. **CLI with `-j` flag but no `--json-file`:**
   - `ctcc.py` automatically converts YAML→JSON using `yaml_to_json.py`
   - Creates `combined_data.json` in project root
   - Then proceeds with JSON input mode

2. **API with no `combined_data` in payload:**
   - Server returns error (combined_data required)

#### When JSON is Loaded Directly (No Conversion):

1. **CLI with `-j` and `--json-file` flags:**
   - Uses specified JSON file directly
   - No YAML conversion occurs
   - Example: `ctcc.py -j --json-file server/json/final_combined.json`

2. **API with `combined_data` in payload:**
   - Uses JSON from API request directly
   - Writes to temporary file for subprocess
   - No YAML files accessed

3. **Pre-existing `combined_data.json`:**
   - If `ctcc.py -j` finds existing `combined_data.json`, uses it
   - Only converts YAML if file doesn't exist

**Summary Decision Tree:**
```
JSON mode requested?
├─ NO → Load from YAML files directly
└─ YES → Does JSON file exist or was it provided?
    ├─ YES → Load from JSON (no conversion)
    └─ NO → Convert YAML→JSON, then load JSON
```

### YAML → CSV (Traditional Mode)

```
yamls/
  ├─ 01_project_technical_details.yaml
  ├─ 02_project_physical_details.yaml
  └─ ... (22 files)
           │
           ▼
      [ctcc.py]
    Sets: CTCC_INPUT_MODE=yaml
          CTCC_OUTPUT_MODE=csv
           │
           ▼
  [13 Calculation Scripts]
     │
     ├─ smart_loaders.py
     │    └─> yaml_loaders.py
     │         └─> Loads individual YAML files DIRECTLY
     │              (No JSON conversion ever occurs)
     │
     ├─ Calculation Logic
     │
     └─ smart_output.py
          └─> csv_output_manager.py
               └─> Writes batch_summary.csv
           │
           ▼
      outputs/
        ├─ batch_summary.csv
        ├─ build_costs.csv
        └─ ... (12 files)
```

### JSON → JSON (API Mode)

#### Scenario A: JSON Provided (API) - NO CONVERSION

```
API Request
  combined_data: { ... }
           │
           ▼
  [ctcc_processor.py]
  Writes combined_data to temp file:
  /tmp/ctcc_api_[id]_[timestamp].json
           │
           ▼
      [ctcc.py subprocess]
    Sets: CTCC_INPUT_MODE=json
          CTCC_OUTPUT_MODE=json
          CTCC_JSON_DATA_FILE=/tmp/ctcc_api_[id]_*.json
           │
           ▼
  [13 Calculation Scripts]
     │
     ├─ smart_loaders.py
     │    └─> json_loaders.py
     │         └─> Loads from CTCC_JSON_DATA_FILE
     │              (JSON already exists - NO YAML ACCESS)
     │
     ├─ Calculation Logic
     │
     └─ smart_output.py
          └─> json_output_manager.py
               └─> Writes temp JSON: json_output_[id]_[module].json
           │
           ▼
     [ctcc.py aggregates]
           │
           ▼
  outputs/ctcc_results_[scenario_id].json
     (single combined file)
           │
           ▼
  [Cleanup: temp input + temp output files]
```

#### Scenario B: JSON from CLI - AUTO-CONVERTED IF NEEDED

```
User: ctcc.py -j -o

      [ctcc.py checks]
           │
           ▼
   Does combined_data.json exist?
   OR --json-file provided?
           │
    ┌──────┴──────┐
    NO            YES
    │             │
    ▼             ▼
[Convert]    [Use existing]
    │             │
    ▼             │
yaml_to_json.py   │
  yamls/ ─────────┤
  └─> combined_data.json
           │
           └──────┴──────┐
                         ▼
                  [ctcc.py -j -o]
                Sets: CTCC_INPUT_MODE=json
                      CTCC_OUTPUT_MODE=json
                      CTCC_JSON_DATA_FILE=combined_data.json
                         │
                         ▼
                [13 Calculation Scripts]
                   (same as Scenario A)
                         │
                         ▼
                outputs/ctcc_results_[id].json
```

### JSON → CSV (Hybrid Mode)

**Note:** Same conversion logic as JSON→JSON mode applies here.

```
User: ctcc.py -j
(Note: NO -o flag = CSV output)

      [ctcc.py checks]
           │
           ▼
   Does combined_data.json exist?
   OR --json-file provided?
           │
    ┌──────┴──────┐
    NO            YES
    │             │
    ▼             ▼
[Convert]    [Use existing]
yaml_to_json.py   │
  yamls/ ─────────┤
  └─> combined_data.json
           │
           └──────┴──────┐
                         ▼
                  [ctcc.py -j]
                Sets: CTCC_INPUT_MODE=json
                      CTCC_OUTPUT_MODE=csv
                      CTCC_JSON_DATA_FILE=combined_data.json
                         │
                         ▼
                [13 Calculation Scripts]
                   │
                   ├─ smart_loaders.py
                   │    └─> json_loaders.py
                   │         └─> Loads from JSON
                   │              (NO YAML ACCESS after this point)
                   │
                   ├─ Calculation Logic
                   │
                   └─ smart_output.py
                        └─> csv_output_manager.py
                             └─> Writes to batch_summary.csv
                         │
                         ▼
                    outputs/
                      ├─ batch_summary.csv
                      ├─ build_costs.csv
                      └─ ... (12 files)
```

---

## Entry Points

### 1. CLI Entry Point: `ctcc.py`

**Purpose:** Command-line interface for batch calculations

**Features:**
- Accepts command-line flags (`-j`, `-o`, `--id`)
- Sets environment variables for subprocesses
- Runs 13 calculation scripts sequentially
- Aggregates JSON output (if `-o` flag used)
- Calculates and displays BCR metrics

**Usage:**
```bash
venv/bin/python3 ctcc.py [--json] [--json-out] [--id SCENARIO_ID]
```

**Flow:**
1. Parse arguments
2. Determine input/output modes
3. Generate scenario ID (if not provided)
4. Convert YAML→JSON if JSON input mode
5. Set environment variables
6. Run 13 scripts via subprocess
7. Aggregate results (JSON mode)
8. Calculate BCR
9. Clean up temp files

### 2. API Entry Point: `server/app/ctcc_processor.py`

**Purpose:** FastAPI backend for web UI and programmatic access

**Function:** `run_ctcc_calculation(payload)`

**Features:**
- Accepts JSON payload with configuration
- Writes combined_data to temp file (JSON input)
- Delegates to `ctcc.py` via subprocess
- Returns structured response with results
- Automatic cleanup of temp files
- 10-minute timeout for long calculations

**Payload Structure:**
```json
{
  "input_mode": "json",
  "output_mode": "json",
  "scenario_id": "my_scenario",
  "combined_data": {
    "01_project_technical_details": { ... },
    "02_project_physical_details": { ... },
    ... (21 sections)
  }
}
```

**Response Structure:**
```json
{
  "success": true,
  "scenario_id": "my_scenario",
  "timestamp": "2025-11-10T12:00:00",
  "input_mode": "json",
  "output_mode": "json",
  "csv_files": null,
  "results": { ... },
  "error": null
}
```

**Why Delegate to ctcc.py?**

Previously, `ctcc_processor.py` duplicated all script-running logic. Now it simply calls `ctcc.py`, ensuring:
- Single source of truth for calculations
- Automatic benefit from ctcc.py improvements
- Reduced code duplication (453 → 189 lines)
- Consistent behavior between CLI and API

---

## Smart Loaders & Output

### Smart Loaders (`smart_loaders.py`)

**Purpose:** Abstract input source from calculation scripts

**How it works:**
```python
# Calculation script imports
from smart_loaders import load_project_technical_details

# smart_loaders checks CTCC_INPUT_MODE
input_mode = os.getenv('CTCC_INPUT_MODE', 'yaml')

if input_mode == 'json':
    from json_loaders import load_project_technical_details
else:
    from yaml_loaders import load_project_technical_details
```

**Benefits:**
- Scripts don't need to know input mode
- Easy to add new input formats
- Consistent API across modes

### Smart Output (`smart_output.py`)

**Purpose:** Abstract output destination from calculation scripts

**How it works:**
```python
# Calculation script imports
from smart_output import CTCCOutputManager

# smart_output checks CTCC_OUTPUT_MODE
output_mode = os.getenv('CTCC_OUTPUT_MODE', 'csv')

if output_mode == 'json':
    from json_output_manager import JSONOutputManager as CTCCOutputManager
else:
    from csv_output_manager import CSVOutputManager as CTCCOutputManager
```

**Benefits:**
- Scripts don't need to know output mode
- Easy to add new output formats (XML, Excel, etc.)
- Consistent API across modes

---

## File Structure

### Calculation Scripts (13 Total)

Located in `scripts/` directory:

1. **weighted_miles.py** - Calculate terrain-weighted miles (preprocessing)
2. **build_costs.py** - Construction costs with AFUDC
3. **insurance_costs.py** - Insurance premiums
4. **row_costs.py** - Right-of-way costs
5. **environmental_mitigation.py** - Environmental compliance
6. **delay_costs.py** - Project delay impacts
7. **wildfire_costs.py** - Wildfire risk assessment
8. **outage_costs.py** - Expected outage costs
9. **congestion_curtailment_reduction.py** - Transmission benefits
10. **energy_losses.py** - I²R and converter losses (preprocessing)
11. **emissions.py** - Emissions from line losses
12. **line_loss_costs.py** - Economic cost of losses
13. **oandm.py** - Operations & maintenance

**Note:** Scripts 1 and 10 are preprocessing steps that don't generate direct output modules.

### Input/Output Managers

**Input:**
- `yaml_loaders.py` - Loads from 22 individual YAML files
- `json_loaders.py` - Loads from single combined JSON file

**Output:**
- `csv_output_manager.py` - Writes to batch_summary.csv
- `json_output_manager.py` - Writes to temp JSON, aggregated by ctcc.py

**Abstraction:**
- `smart_loaders.py` - Routes to correct input manager
- `smart_output.py` - Routes to correct output manager

### Configuration Files

**YAML Mode:**
- Location: `yamls/`
- Count: 22 files
- Format: Individual YAML files per section

**JSON Mode:**
- Location: `server/json/` or `combined_data.json`
- Count: 1 combined file or 21 individual files
- Format: Single merged JSON object

---

## Environment Variables

### CTCC_INPUT_MODE

**Values:** `yaml` (default) | `json`

**Purpose:** Tells scripts where to load configuration data

**Set by:**
- `ctcc.py` based on `-j` flag
- `ctcc_processor.py` based on API payload

**Used by:**
- `smart_loaders.py` to route to correct loader

### CTCC_OUTPUT_MODE

**Values:** `csv` (default) | `json`

**Purpose:** Tells scripts how to write results

**Set by:**
- `ctcc.py` based on `-o` flag
- `ctcc_processor.py` based on API payload

**Used by:**
- `smart_output.py` to route to correct output manager

### CTCC_SCENARIO_ID

**Values:** Any string (default: timestamp)

**Purpose:** Identifies calculation run for output files

**Set by:**
- `ctcc.py` sets for subprocesses based on `--id` flag or auto-generated timestamp
- `ctcc_processor.py` sets for subprocesses from API payload or auto-generated

**Used by:**
- Subprocess calculation scripts
- Output managers for file naming
- BCR calculator for tracking scenarios

### CTCC_JSON_DATA_FILE

**Values:** Absolute path to JSON file

**Purpose:** Specifies location of combined JSON configuration

**Set by:**
- `ctcc.py` sets for subprocesses when JSON input mode is used
- `ctcc_processor.py` sets for subprocesses when writing temp file for API

**Used by:**
- Subprocess calculation scripts
- `json_loaders.py` to load configuration data

**Note:** Environment variables are used for **subprocess communication only**. The main `ctcc.py` script uses command-line flags exclusively.

---

## Example Flows

### Example 1: CLI YAML→CSV

```bash
$ venv/bin/python3 ctcc.py

# Internal flow:
# 1. No flags, defaults to YAML→CSV
# 2. Sets CTCC_INPUT_MODE=yaml
# 3. Sets CTCC_OUTPUT_MODE=csv
# 4. Sets CTCC_SCENARIO_ID=20251110_134500
# 5. Runs 13 scripts
# 6. Each script:
#    - Uses smart_loaders → yaml_loaders
#    - Calculates
#    - Uses smart_output → csv_output_manager
#    - Writes to batch_summary.csv
# 7. Calculates BCR
# 8. Outputs 12 CSV files
```

### Example 2: CLI JSON→JSON (with auto-conversion)

```bash
$ venv/bin/python3 ctcc.py -j -o --id test
# Assumes NO combined_data.json exists and NO --json-file provided

# Internal flow:
# 1. -j flag → JSON input, -o flag → JSON output
# 2. Checks for combined_data.json or --json-file
# 3. NOT FOUND → Runs yaml_to_json.py to convert yamls/ → combined_data.json
#    (This is the ONLY time YAML files are accessed in JSON mode)
# 4. Sets CTCC_INPUT_MODE=json
# 5. Sets CTCC_OUTPUT_MODE=json
# 6. Sets CTCC_SCENARIO_ID=test
# 7. Sets CTCC_JSON_DATA_FILE=combined_data.json (absolute path)
# 8. Runs 13 scripts as subprocesses
# 9. Each script:
#    - Uses smart_loaders → json_loaders
#    - json_loaders reads ONLY from CTCC_JSON_DATA_FILE
#    - YAML files are NEVER accessed at this point
#    - Calculates
#    - Uses smart_output → json_output_manager
#    - Writes temp JSON: json_output_test_[module].json
# 10. Aggregates temp JSONs → ctcc_results_test.json
# 11. Cleans up temp files
# 12. Calculates BCR (adds to JSON)
# 13. Outputs single JSON file
```

### Example 2b: CLI JSON→JSON (with existing JSON - no conversion)

```bash
$ venv/bin/python3 ctcc.py -j -o --id test --json-file server/json/final_combined.json
# OR: combined_data.json already exists from previous run

# Internal flow:
# 1. -j flag → JSON input, -o flag → JSON output
# 2. Checks for combined_data.json or --json-file
# 3. FOUND → Uses existing JSON file directly
#    (NO yaml_to_json.py call, NO YAML access, FASTER startup)
# 4. Sets CTCC_INPUT_MODE=json
# 5. Sets CTCC_OUTPUT_MODE=json
# 6. Sets CTCC_SCENARIO_ID=test
# 7. Sets CTCC_JSON_DATA_FILE=server/json/final_combined.json (absolute path)
# 8-13. Same as Example 2 (steps 8-13)
```

### Example 3: API JSON→JSON (NO conversion - JSON provided)

```bash
$ curl -X POST http://localhost:8000/api/ctcc/calculate \
  -H "Content-Type: application/json" \
  -d '{
    "input_mode": "json",
    "output_mode": "json",
    "scenario_id": "api_test",
    "combined_data": { ... }  # Client provides JSON directly
  }'

# Internal flow:
# 1. FastAPI receives request with combined_data already in JSON
# 2. ctcc_processor.run_ctcc_calculation() called
# 3. Writes combined_data to temp file: /tmp/ctcc_api_api_test_*.json
#    (NO YAML CONVERSION - JSON is already provided by client)
# 4. Sets environment variables for subprocess:
#    - CTCC_INPUT_MODE=json
#    - CTCC_OUTPUT_MODE=json
#    - CTCC_SCENARIO_ID=api_test
#    - CTCC_JSON_DATA_FILE=/tmp/ctcc_api_api_test_*.json (absolute path)
# 5. Runs: venv/bin/python3 ctcc.py as subprocess
#    (ctcc.py skips YAML check because CTCC_JSON_DATA_FILE is already set)
# 6. ctcc.py runs 13 scripts
# 7. Each script:
#    - smart_loaders → json_loaders
#    - json_loaders reads from CTCC_JSON_DATA_FILE
#    - YAML files are NEVER accessed (not even checked)
#    - Calculates and writes temp JSON
# 8. ctcc.py aggregates → outputs/ctcc_results_api_test.json
# 9. ctcc_processor reads outputs/ctcc_results_api_test.json
# 10. Cleans up temp input file (/tmp/ctcc_api_*.json)
# 11. Cleans up output JSON file (outputs/ctcc_results_*.json)
# 12. Returns structured response to API client with results embedded
```

---

## JSON Conversion Summary

### When Does YAML→JSON Conversion Occur?

| Scenario | Conversion? | Why? |
|----------|-------------|------|
| `ctcc.py` (default, no flags) | ❌ NO | YAML mode - loads YAML files directly |
| `ctcc.py -j` (first time) | ✅ YES | JSON mode but no JSON file exists yet |
| `ctcc.py -j` (subsequent) | ❌ NO | JSON mode and combined_data.json already exists |
| `ctcc.py -j --json-file <path>` | ❌ NO | JSON mode with explicit file - uses provided file |
| API request with `combined_data` | ❌ NO | JSON already provided in request payload |
| API request without `combined_data` | ❌ ERROR | API requires combined_data (no auto-conversion) |

### Key Points

1. **YAML mode NEVER touches JSON:**
   - When `ctcc.py` runs without `-j` flag
   - Scripts use `yaml_loaders.py` exclusively
   - No conversion, no JSON files created or read

2. **JSON mode conversion is LAZY:**
   - Only converts if JSON file doesn't exist
   - Checks in order: `--json-file` flag → existing `combined_data.json` → convert from YAML
   - Once converted, reused for subsequent runs (until deleted)

3. **API mode is JSON-ONLY:**
   - Client must provide `combined_data` in request
   - No YAML conversion available via API
   - Server writes JSON to temp file for subprocess

4. **Conversion is ONE-WAY at runtime:**
   - YAML can be converted to JSON (via `yaml_to_json.py`)
   - JSON is never converted back to YAML during calculations
   - Conversion is a preprocessing step, not part of calculation flow

5. **Subprocess isolation:**
   - Once `CTCC_JSON_DATA_FILE` is set, scripts never look at YAML
   - Environment variables determine behavior, not file presence
   - Clean separation between input modes

### Performance Implications

**Conversion overhead:**
- First JSON mode run: +2-3 seconds (YAML→JSON conversion)
- Subsequent JSON mode runs: 0 seconds (uses cached JSON)
- YAML mode: 0 seconds (no conversion ever)

**Recommendation:**
- For repeated runs: Use `--json-file` or keep `combined_data.json`
- For single runs: YAML or JSON mode have similar performance
- For API: Always provide JSON (no choice)

---

## Key Implementation Details

### Why Two Entry Points?

**ctcc.py (CLI):**
- Direct script execution
- Simpler for command-line users
- No web server needed
- Good for batch processing

**ctcc_processor.py (API):**
- Web UI integration
- Programmatic access
- Real-time calculations
- Multiple concurrent users

### Why Delegate to ctcc.py?

Before v2.0, `ctcc_processor.py` duplicated all calculation logic. This caused:
- Code duplication
- Maintenance burden (update two places)
- Potential inconsistencies

Now `ctcc_processor.py` simply:
1. Writes input to temp file
2. Calls `ctcc.py` via subprocess
3. Reads output file
4. Returns response

Benefits:
- Single source of truth
- Automatic updates (fix once, works everywhere)
- Reduced code (453 → 189 lines)

### How Scripts Communicate

**Via Files:**
- Scripts write to shared output files
- batch_summary.csv accumulates results
- JSON temp files aggregated at end

**Via Environment:**
- CTCC_* variables passed to subprocesses
- Scripts read via `os.getenv()`

**No Direct IPC:**
- Scripts run sequentially (not parallel)
- No pipes or sockets
- Simple subprocess.run()

---

## Troubleshooting

### Wrong Mode Selected

**Symptom:** Scripts fail with import errors or file not found

**Solution:**
```bash
# Check environment
env | grep CTCC

# Clear if needed
unset CTCC_INPUT_MODE
unset CTCC_OUTPUT_MODE
unset CTCC_JSON_DATA_FILE
```

### Missing JSON File

**Symptom:** `FileNotFoundError: combined_data.json`

**Solution:**
```bash
# Generate from YAML
python3 yaml_to_json.py yamls combined_data.json

# Or use server converter
cd server
./convert_yamls.command
```

### Temp Files Not Cleaned

**Symptom:** json_output_*.json files in outputs/

**Solution:**
```bash
# Manual cleanup
rm outputs/json_output_*.json

# Or use cleanup script
./cleanup_ctcc.sh
```

---

## Future Enhancements

### Potential Input Modes

- **Excel** - Read from .xlsx workbooks
- **Database** - Load from SQL database
- **REST API** - Fetch from remote API

### Potential Output Modes

- **Excel** - Write to .xlsx with multiple sheets
- **HTML** - Generate interactive reports
- **PDF** - Create formatted documents
- **Database** - Store results in SQL tables

### Architecture Improvements

- **Parallel Execution** - Run independent scripts concurrently
- **Progress Tracking** - Real-time progress updates
- **Caching** - Cache intermediate results
- **Validation** - Input validation before calculation

---

**End of Documentation**
