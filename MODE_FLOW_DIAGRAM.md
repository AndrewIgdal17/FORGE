# CTCC Architecture & Mode Flow Diagram

Complete technical documentation of CTCC's architecture, data flow, and mode combinations.

**Last Updated:** 2025-11-10
**Version:** 2.0

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
     │         └─> Loads individual YAML files
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

```
combined_data.json
  (or auto-generated from YAML)
           │
           ▼
      [ctcc.py -j -o]
    Sets: CTCC_INPUT_MODE=json
          CTCC_OUTPUT_MODE=json
          CTCC_JSON_DATA_FILE=path/to/data.json
           │
           ▼
  [13 Calculation Scripts]
     │
     ├─ smart_loaders.py
     │    └─> json_loaders.py
     │         └─> Loads from CTCC_JSON_DATA_FILE
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
  [Cleanup temp files]
```

### JSON → CSV (Hybrid Mode)

```
combined_data.json
           │
           ▼
      [ctcc.py -j]
    Sets: CTCC_INPUT_MODE=json
          CTCC_OUTPUT_MODE=csv
           │
           ▼
  [13 Calculation Scripts]
     │
     ├─ smart_loaders.py
     │    └─> json_loaders.py
     │
     ├─ Calculation Logic
     │
     └─ smart_output.py
          └─> csv_output_manager.py
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
- `ctcc.py` from `--id` flag or auto-generated
- `ctcc_processor.py` from API payload or auto-generated

**Used by:**
- Output managers for file naming
- BCR calculator for tracking scenarios

### CTCC_JSON_DATA_FILE

**Values:** Absolute path to JSON file

**Purpose:** Specifies location of combined JSON configuration

**Set by:**
- `ctcc.py` when JSON input mode is used
- `ctcc_processor.py` when writing temp file for API

**Used by:**
- `json_loaders.py` to load configuration data

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

### Example 2: CLI JSON→JSON

```bash
$ venv/bin/python3 ctcc.py -j -o --id test

# Internal flow:
# 1. -j flag → JSON input, -o flag → JSON output
# 2. Runs yaml_to_json.py → combined_data.json
# 3. Sets CTCC_INPUT_MODE=json
# 4. Sets CTCC_OUTPUT_MODE=json
# 5. Sets CTCC_SCENARIO_ID=test
# 6. Sets CTCC_JSON_DATA_FILE=combined_data.json
# 7. Runs 13 scripts
# 8. Each script:
#    - Uses smart_loaders → json_loaders
#    - Calculates
#    - Uses smart_output → json_output_manager
#    - Writes temp JSON: json_output_test_[module].json
# 9. Aggregates temp JSONs → ctcc_results_test.json
# 10. Cleans up temp files
# 11. Calculates BCR (adds to JSON)
# 12. Outputs single JSON file
```

### Example 3: API JSON→JSON

```bash
$ curl -X POST http://localhost:8000/api/ctcc/calculate \
  -H "Content-Type: application/json" \
  -d '{
    "input_mode": "json",
    "output_mode": "json",
    "scenario_id": "api_test",
    "combined_data": { ... }
  }'

# Internal flow:
# 1. FastAPI receives request
# 2. ctcc_processor.run_ctcc_calculation() called
# 3. Writes combined_data to temp file: /tmp/ctcc_api_api_test_*.json
# 4. Sets environment variables:
#    - CTCC_INPUT_MODE=json
#    - CTCC_OUTPUT_MODE=json
#    - CTCC_SCENARIO_ID=api_test
#    - CTCC_JSON_DATA_FILE=/tmp/ctcc_api_api_test_*.json
# 5. Runs: venv/bin/python3 ctcc.py (subprocess)
# 6. ctcc.py runs 13 scripts (same as Example 2)
# 7. Reads outputs/ctcc_results_api_test.json
# 8. Cleans up temp input file
# 9. Cleans up output JSON file
# 10. Returns structured response to API client
```

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
