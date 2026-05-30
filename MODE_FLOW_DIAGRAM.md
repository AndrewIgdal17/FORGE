# CTCC Architecture & Flow Diagram

Single input/output contract (YAML in, JSON out) and API boundary. Technical documentation of CTCC's architecture and data flow after the pre-DuckDB refactor (audit item 3).

**Last Updated:** 2026-03-11
**Version:** 3.0

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Single Flow](#single-flow)
4. [Data Flow](#data-flow)
5. [Entry Points](#entry-points)
6. [Smart Loaders & Output](#smart-loaders--output)
7. [File Structure](#file-structure)
8. [Environment Variables](#environment-variables)
9. [Example Flows](#example-flows)
10. [API Boundary Conversion](#api-boundary-conversion)
11. [Key Implementation Details](#key-implementation-details)
12. [Troubleshooting](#troubleshooting)
13. [Future Enhancements](#future-enhancements)
14. [Related](#related)

---

## Overview

CTCC has a single calculator contract and two entry points:

- **Calculator:** YAML in (directory: `yamls/` or `CTCC_YAMLS_DIR`), JSON out (`ctcc_results_{scenario_id}.json` in `outputs/`).
- **API:** Accepts JSON, returns JSON; the server converts the request to a temp YAML directory, runs the calculator, and returns the calculator's JSON.
- **Entry points:** CLI (`ctcc.py`) or API (`server/app/ctcc_processor.py`).

### Key Design Principles

1. **Single input path** — Calculator reads only from a YAML directory (no JSON input mode).
2. **Single output path** — Calculator writes only one JSON result file (no CSV output mode).
3. **Server converts at boundary** — API receives JSON; server writes temp YAML dir, sets `CTCC_YAMLS_DIR`, invokes ctcc, returns JSON.
4. **Single source of truth** — Server delegates to `ctcc.py`; no duplicated calculation logic.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                         USER INTERFACES                      │
├──────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌────────────────┐  ┌─────────────────┐   │
│  │   CLI        │  │   Web UI       │  │   API Client    │   │
│  │   (Terminal) │  │   (Browser)    │  │   (Python/HTTP) │   │
│  └──────┬───────┘  └────────┬───────┘  └────────┬────────┘   │
└─────────┼──────────────────┼──────────────────┼─────────────┘
          │                  │                    │
          ▼                  ▼                    ▼
┌─────────────────┐  ┌────────────────────────────────────────┐
│   ctcc.py       │  │   server/app/main.py (FastAPI)          │
│   (CLI Entry)   │  │   server/app/ctcc_processor.py         │
│                 │  │   Merge → temp YAML dir → invoke ctcc   │
│  Delegates to → │  │   → read ctcc_results JSON → response  │
│  14 scripts     │  └────────────────┬───────────────────────┘
│  (in-process    │                    │
│   by default)   │  ← Delegates to ctcc.py via subprocess
└─────────┬───────┘                    │
          │                            │
          └────────────┬──────────────┘
                        ▼
         ┌─────────────────────────────┐
         │   Environment Variables      │
         │   • CTCC_YAMLS_DIR (optional)│
         │   • CTCC_SCENARIO_ID         │
         └─────────────┬────────────────┘
                       ▼
         ┌─────────────────────────────┐
         │   14 Calculation Scripts     │
         │   (in-process or --subprocess)│
         └─────────────┬────────────────┘
                       ▼
         ┌─────────────────────────────┐
         │   smart_loaders.py            │
         │   → yaml_loaders only         │
         └─────────────┬────────────────┘
                       ▼
         ┌─────────────────────────────┐
         │   yaml_loaders.py            │
         │   (reads from YAMLS_DIR)     │
         └─────────────┬────────────────┘
                       ▼
         ┌─────────────────────────────┐
         │   Calculation Logic          │
         └─────────────┬────────────────┘
                       ▼
         ┌─────────────────────────────┐
         │   smart_output.py            │
         │   → json_output_manager only │
         └─────────────┬────────────────┘
                       ▼
         ┌─────────────────────────────┐
         │   json_output_manager        │
         │   (shared aggregator or file)│
         └─────────────┬────────────────┘
                       ▼
         ┌─────────────────────────────┐
         │   outputs/                   │
         │   ctcc_results_[id].json     │
         └─────────────────────────────┘
```

**API path:** Server writes merged request to a temp YAML dir, sets `CTCC_YAMLS_DIR`, invokes ctcc, reads `ctcc_results_{scenario_id}.json`, cleans up temp dir, returns JSON.

---

## Single Flow

The calculator has one input path and one output path. There are no mode combinations.

| Entry point | Input to calculator | Output from calculator |
|-------------|---------------------|-------------------------|
| CLI        | YAML directory (`yamls/` or `CTCC_YAMLS_DIR`) | `outputs/ctcc_results_{scenario_id}.json` |
| API        | Same (server provides temp YAML dir via `CTCC_YAMLS_DIR`) | Same; server reads file and returns JSON response |

The API still accepts JSON in the request body and returns JSON; conversion from client JSON to YAML happens only at the server boundary before invoking the calculator.

---

## Data Flow

### CLI Flow

```
yamls/ (or CTCC_YAMLS_DIR)
         │
         ▼
    [ctcc.py]
  Sets CTCC_SCENARIO_ID if not set
  Creates JSON output manager (shared aggregator when in-process)
         │
         ▼
  [14 scripts: in-process by default]
     │
     ├─ smart_loaders → yaml_loaders (read from YAMLS_DIR)
     ├─ Calculation logic
     └─ smart_output → json_output_manager (write to aggregator or temp JSON files)
         │
         ▼
  [ctcc.py aggregates results, computes BCR]
         │
         ▼
  outputs/ctcc_results_{scenario_id}.json
```

No CSV output. No JSON input to the calculator.

### API Flow

```
POST /api/ctcc/calculate
  Body: { "scenario_id": "...", "combined_data": { ... } }
         │
         ▼
  [ctcc_processor.py]
  Merge combined_data with template (if simplified format)
         │
         ▼
  Create temp directory (e.g. tempfile.mkdtemp())
  For each key in merged_data: write {key}.yaml
         │
         ▼
  Set env["CTCC_YAMLS_DIR"] = temp_dir (absolute path)
  Set env["CTCC_SCENARIO_ID"] = scenario_id
  Do NOT set CTCC_JSON_DATA_FILE or CTCC_INPUT_MODE
         │
         ▼
  Invoke: python ctcc.py (subprocess, cwd=CTCC_ROOT)
         │
         ▼
  [ctcc reads from CTCC_YAMLS_DIR, writes ctcc_results_{scenario_id}.json]
         │
         ▼
  Server reads CTCC_ROOT/outputs/ctcc_results_{scenario_id}.json
  Remove temp YAML dir
         │
         ▼
  Return JSON response { "success", "scenario_id", "results", ... }
```

---

## Entry Points

### 1. CLI Entry Point: `ctcc.py`

**Purpose:** Command-line interface for batch calculations.

**Features:**
- No input/output mode flags; calculator is always YAML in, JSON out.
- Scenario ID from environment `CTCC_SCENARIO_ID` or auto-generated (timestamp).
- Optional input directory override: `CTCC_YAMLS_DIR`.
- Runs 14 calculation scripts in-process by default (import and call `main()`); use `--subprocess` for legacy subprocess-per-script behavior.
- Aggregates JSON results, computes BCR, writes `ctcc_results_{scenario_id}.json`.

**Usage:**
```bash
python ctcc.py
# Or with env overrides:
CTCC_YAMLS_DIR=/path/to/yamls CTCC_SCENARIO_ID=my_id python ctcc.py
# Legacy: run each script as subprocess
python ctcc.py --subprocess
```

**Flow:**
1. Parse arguments (e.g. `--simple`, `--subprocess`, feature toggles).
2. Load BCR config from YAML (yaml_loaders).
3. Set or generate `CTCC_SCENARIO_ID`; set `CTCC_OUTPUT_MODE=json` for scripts.
4. Create JSON output manager (shared when in-process).
5. Run 14 scripts (in-process or subprocess).
6. Aggregate JSON, compute BCR, call `write_final_json_output`.
7. Write `outputs/ctcc_results_{scenario_id}.json`.

### 2. API Entry Point: `server/app/ctcc_processor.py`

**Purpose:** FastAPI backend for web UI and programmatic access.

**Function:** `run_ctcc_calculation(payload)`

**Features:**
- Accepts JSON payload with `combined_data` (and optional `scenario_id`, `input_mode`, `output_mode`; latter two ignored for calculator behavior).
- Writes merged data to a **temp YAML directory** (one file per key: `01_project_technical_details.yaml`, etc.), not a temp JSON file.
- Sets `CTCC_YAMLS_DIR` to that directory; does not set `CTCC_JSON_DATA_FILE` or `CTCC_INPUT_MODE`.
- Invokes `ctcc.py` via subprocess; reads `ctcc_results_{scenario_id}.json`; returns it in the response.
- Removes temp YAML dir after reading results.
- 10-minute timeout for long calculations.

**Payload structure (request):**
```json
{
  "scenario_id": "my_scenario",
  "combined_data": {
    "01_project_technical_details": { ... },
    "02_project_physical_details": { ... },
    ...
  }
}
```

**Response structure:** Always JSON results (no CSV path).
```json
{
  "success": true,
  "scenario_id": "my_scenario",
  "timestamp": "...",
  "output_mode": "json",
  "results": { ... },
  "error": null
}
```

**Why delegate to ctcc.py?** Single source of truth for calculations; server only converts JSON to YAML and invokes the calculator.

---

## Smart Loaders & Output

### Smart Loaders (`smart_loaders.py`)

**Purpose:** Provide a single loader API to calculation scripts. The calculator uses only YAML input.

**How it works:** Always imports and re-exports `yaml_loaders`. Scripts call e.g. `load_project_technical_details()` from `smart_loaders`; data is read from `YAMLS_DIR` (from `path_config`; overridable via `CTCC_YAMLS_DIR`). There is no conditional branch on input mode and no use of `json_loaders` in the calculator path.

### Smart Output (`smart_output.py`)

**Purpose:** Provide a single output API to calculation scripts. The calculator uses only JSON output.

**How it works:** Always uses `JSONOutputManager` (or the shared aggregator when the orchestrator has set one via `run_context`). There is no CSV branch and no `CTCC_OUTPUT_MODE` branching; scripts always write to the JSON aggregator or to per-module JSON files for aggregation later.

---

## File Structure

### Calculation Scripts (14)

Located in `scripts/`:

1. **weighted_miles.py** — Terrain-weighted miles (preprocessing)
2. **build_costs.py** — Construction costs with AFUDC
3. **row_costs.py** — Right-of-way costs
4. **environmental_mitigation.py** — Environmental compliance
5. **revenue.py** — Rate-based revenue (if enabled)
6. **insurance_costs.py** — Insurance premiums
7. **delay_costs.py** — Project delay impacts
8. **wildfire_costs.py** — Wildfire risk assessment
9. **outage_costs.py** — Expected outage costs
10. **congestion_curtailment_reduction.py** — Transmission benefits
11. **energy_losses.py** — I²R and converter losses (preprocessing)
12. **oandm.py** — Operations & maintenance
13. **emissions.py** — Emissions from line losses
14. **line_loss_costs.py** — Economic cost of losses

Plus BCR aggregation and `write_final_json_output` in `ctcc.py`.

### Input

- **YAML:** `yamls/` (default) or the directory given by `CTCC_YAMLS_DIR`. One file per section (e.g. `01_project_technical_details.yaml`). Defined in `path_config.py`; `YAMLS_DIR` can be overridden by the environment.

### Output

- **JSON only:** `outputs/ctcc_results_{scenario_id}.json`. Produced by `ctcc.py` after aggregating per-module results and computing BCR.

### Run commands

- **CLI:** From repo root, `python ctcc.py` (see README).
- **Web app:** `run_calc_server.command` (FastAPI on port 8000).

---

## Environment Variables

### CTCC_YAMLS_DIR

**Values:** Optional; absolute path to a directory containing YAML input files (same naming as `yamls/`: e.g. `01_project_technical_details.yaml`).

**Purpose:** Override the default YAML input directory. When not set, the calculator uses `yamls/` (from `path_config.PROJECT_ROOT / "yamls"`).

**Set by:** Server when handling API requests (temp directory with merged request data written as one YAML file per key). CLI users can set it to point at an alternate config directory.

### CTCC_SCENARIO_ID

**Values:** Any string (default: generated timestamp if not set).

**Purpose:** Identifies the run; used for the output filename `ctcc_results_{scenario_id}.json`.

**Set by:** `ctcc.py` sets it in the environment if not already set. The server sets it from the request payload or generates one.

**Used by:** Output manager for file naming; BCR and aggregation.

---

## Example Flows

### Example 1: CLI (YAML dir → JSON)

```bash
$ python ctcc.py

# Flow:
# 1. ctcc.py loads BCR config from YAML
# 2. Sets CTCC_SCENARIO_ID (e.g. from env or timestamp)
# 3. Runs 14 scripts in-process; each uses yaml_loaders (from yamls/)
#    and json_output_manager (shared aggregator)
# 4. Aggregates results, computes BCR, writes outputs/ctcc_results_{scenario_id}.json
```

With custom scenario ID and input dir:

```bash
$ CTCC_SCENARIO_ID=my_run CTCC_YAMLS_DIR=/path/to/my/yamls python ctcc.py
```

### Example 2: API (JSON request → JSON response)

```bash
$ curl -X POST http://localhost:8000/api/ctcc/calculate \
  -H "Content-Type: application/json" \
  -d '{"scenario_id": "api_test", "combined_data": { ... }}'

# Flow:
# 1. ctcc_processor merges combined_data with template if simplified format
# 2. Writes merged data to temp dir as 01_*.yaml, 02_*.yaml, ...
# 3. Sets CTCC_YAMLS_DIR=temp_dir, CTCC_SCENARIO_ID=api_test
# 4. Runs ctcc.py (subprocess)
# 5. ctcc reads from temp YAML dir, writes ctcc_results_api_test.json
# 6. Server reads that file, deletes temp dir, returns JSON response
```

---

## API Boundary Conversion

The only place where "JSON input" is converted to something the calculator uses is at the **API boundary**. The server receives JSON (`combined_data`), merges it with the template if needed, then writes the merged structure to a **temporary YAML directory** (one file per key). The calculator never reads JSON input; it only reads from a YAML directory. So from the calculator's perspective there is no "JSON mode"—only YAML in, JSON out. The API still accepts and returns JSON for the client.

---

## Key Implementation Details

### Why two entry points?

- **ctcc.py (CLI):** Direct execution, batch use, no server required.
- **ctcc_processor.py (API):** Web UI, programmatic access, concurrent users.

### Why delegate to ctcc.py?

The server does not duplicate calculation logic. It converts client JSON to YAML, invokes ctcc, and returns the calculator's JSON. Single source of truth for all calculations.

### How scripts communicate

- **In-process (default):** One shared `JSONOutputManager` (aggregator) set in `run_context`; scripts write to it; no per-script JSON files; ctcc aggregates in memory and writes the final JSON file.
- **Subprocess (legacy):** Each script runs in a subprocess and may write `json_output_{scenario_id}_{module}.json`; ctcc globs and aggregates those files, then writes `ctcc_results_{scenario_id}.json`.
- **Environment:** `CTCC_YAMLS_DIR` and `CTCC_SCENARIO_ID` (and optionally `CTCC_OUTPUT_MODE=json`) are passed to subprocesses when used.

---

## Troubleshooting

### YAML directory not found

**Symptom:** FileNotFoundError or missing section when loading YAML.

**Solution:** Ensure `yamls/` exists and contains the expected files (e.g. `01_project_technical_details.yaml`), or set `CTCC_YAMLS_DIR` to a directory that does. When using the API, the server creates the temp YAML dir; if the merge fails, check the request payload and template.

### Environment variables

**Symptom:** Wrong scenario ID or wrong input directory.

**Solution:**
```bash
env | grep CTCC
# Relevant: CTCC_YAMLS_DIR, CTCC_SCENARIO_ID
```

### Temp files in outputs/

**Symptom:** `json_output_*.json` files remain (e.g. after a subprocess run).

**Solution:** These are intermediate files when using `--subprocess`. They can be deleted manually or by a cleanup script; the final result is `ctcc_results_{scenario_id}.json`.

---

## Future Enhancements

- **Database (e.g. DuckDB):** The calculator's only input is "read config from a directory." A future step can introduce an input adapter that reads from a DB for the current run instead of from a YAML dir, without adding a second input path.
- **Optional CSV export:** If needed, a separate step could read `ctcc_results_*.json` and write CSV as a derived export; the pipeline would remain YAML in, JSON out.

---

## Related

- [README](README.md) — Quick start and overview.
- [VENV_SETUP](VENV_SETUP.md) — Virtual environment setup.

---

**End of Documentation**
