# CTCC Developer Documentation

Comprehensive technical documentation for developers working on CTCC.

**Last Updated:** 2025-11-10
**Version:** 2.0
**Status:** Production-ready

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Quick Start for Developers](#quick-start-for-developers)
3. [Architecture](#architecture)
4. [Development Workflows](#development-workflows)
5. [API Reference](#api-reference)
6. [File Structure](#file-structure)
7. [Testing](#testing)
8. [Known Issues](#known-issues)
9. [Deployment](#deployment)
10. [Troubleshooting](#troubleshooting)

---

## Project Overview

### What is CTCC?

CTCC (Comprehensive Transmission Cost Calculator) is a cost-benefit analysis tool for high-voltage transmission line projects. It calculates 13 different cost and benefit categories to help utilities and regulators make informed decisions about energy infrastructure investments.

### Key Features

- **Flexible I/O:** YAML or JSON input, CSV or JSON output
- **13 Cost Modules:** Build, ROW, environmental, O&M, risk, benefits, etc.
- **3 Financial Perspectives:** Nominal, AFUDC (regulatory), Present Value (societal)
- **Web UI:** Browser-based interface for editing and running calculations
- **REST API:** Programmatic access for integration
- **CLI:** Command-line tool for batch processing

### Technology Stack

- **Language:** Python 3.8+
- **Web Framework:** FastAPI + Uvicorn
- **Data Processing:** Pandas, NumPy
- **Configuration:** YAML (PyYAML), JSON
- **Frontend:** Vanilla JavaScript (no frameworks)

---

## Quick Start for Developers

### Initial Setup

```bash
# Clone and navigate to project
cd CTCC

# Create CLI virtual environment
python3 -m venv venv
source venv/bin/activate
pip install pyyaml pandas numpy

# Create server virtual environment
cd server
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Run Calculations (CLI)

```bash
# Default YAML→CSV
venv/bin/python3 ctcc.py

# JSON→JSON
venv/bin/python3 ctcc.py -j -o --id test

# JSON→CSV
venv/bin/python3 ctcc.py -j
```

### Start Web Server

```bash
cd server
./run_calc_server.command
# Server runs at http://localhost:8000
```

### Convert YAML to JSON

```bash
cd server
./convert_yamls.command
# Select source directory
# Output: server/json/final_combined.json
```

---

## Architecture

### High-Level Design

CTCC follows a **subprocess-based architecture** where:

1. Entry point (`ctcc.py` or `ctcc_processor.py`) receives request
2. Environment variables set to specify modes
3. 13 calculation scripts run as subprocesses
4. Scripts use smart loaders/output to abstract I/O
5. Results aggregated and returned

### Design Principles

1. **Single Responsibility:** Each script calculates one cost category
2. **Mode Abstraction:** Scripts don't know their I/O mode
3. **Environment-Based Configuration:** Modes set via env vars
4. **Delegation Over Duplication:** Server delegates to CLI
5. **Backwards Compatibility:** YAML→CSV mode preserved

### Entry Points

#### 1. CLI: `ctcc.py`

**Purpose:** Direct command-line calculations

**Key Functions:**
- `parse_arguments()` - Parse command-line flags
- `run_script(script, env)` - Run calculation subprocess
- `main()` - Orchestrate entire calculation flow

**Usage:**
```bash
venv/bin/python3 ctcc.py [-j] [-o] [--id SCENARIO_ID]
```

#### 2. API: `server/app/ctcc_processor.py`

**Purpose:** Web API backend

**Key Functions:**
- `run_ctcc_calculation(payload)` - Main calculation function

**How it works:**
1. Receives JSON payload with configuration
2. Writes `combined_data` to temp file (JSON mode)
3. Sets environment variables
4. Calls `ctcc.py` via subprocess
5. Reads output file (JSON or CSV list)
6. Returns structured response
7. Cleans up temp files

**Why delegate to ctcc.py?**
- Single source of truth (fix once, works everywhere)
- Automatic benefit from ctcc.py improvements
- Reduced code: 453 → 189 lines (58% reduction)

### Data Flow

```
Input (YAML/JSON)
    ↓
Environment Variables
    ↓
ctcc.py (sets modes)
    ↓
13 Scripts (subprocesses)
    ↓
smart_loaders → yaml_loaders | json_loaders
    ↓
Calculation Logic
    ↓
smart_output → csv_output_manager | json_output_manager
    ↓
Output (CSV/JSON)
```

### Smart Loaders & Output

**Purpose:** Abstract I/O mode from calculation scripts

**smart_loaders.py:**
```python
import os

input_mode = os.getenv('CTCC_INPUT_MODE', 'yaml')

if input_mode == 'json':
    from json_loaders import *
else:
    from yaml_loaders import *
```

**smart_output.py:**
```python
import os

output_mode = os.getenv('CTCC_OUTPUT_MODE', 'csv')

if output_mode == 'json':
    from json_output_manager import JSONOutputManager as CTCCOutputManager
else:
    from csv_output_manager import CSVOutputManager as CTCCOutputManager
```

**Benefits:**
- Scripts use generic imports: `from smart_loaders import load_...`
- Mode switching transparent to scripts
- Easy to add new I/O formats

---

## Development Workflows

### Adding a New Cost Module

#### Step 1: Create Calculation Script

```python
# scripts/new_module.py
from smart_loaders import load_project_technical_details, load_financing_details
from smart_output import CTCCOutputManager

def calculate_new_costs(project_data, financing_data):
    """Calculate costs for new module."""
    # Perform calculations
    results = {
        'total_nominal': 0,
        'total_pv': 0,
        # ... more fields
    }
    return results

def main():
    # Load data
    project_data = load_project_technical_details()
    financing_data = load_financing_details()

    # Calculate
    results = calculate_new_costs(project_data, financing_data)

    # Write output
    output_manager = CTCCOutputManager()
    output_manager.add_new_module_costs(results)
    output_manager.write_batch_summary()

    print("New module calculation complete")

if __name__ == "__main__":
    main()
```

#### Step 2: Add Output Methods

**csv_output_manager.py:**
```python
def add_new_module_costs(self, results):
    """Add new module results to CSV batch summary."""
    self.new_module_costs = results
    # Update batch_summary fields
```

**json_output_manager.py:**
```python
def add_new_module_costs(self, results):
    """Add new module results to JSON output."""
    self.costs["new_module"] = results
```

#### Step 3: Update ctcc.py

```python
scripts = [
    "weighted_miles.py",
    "build_costs.py",
    # ... existing scripts
    "new_module.py",  # Add here
]
```

#### Step 4: Test

```bash
# Test individual script
export CTCC_INPUT_MODE=json
export CTCC_OUTPUT_MODE=json
export CTCC_JSON_DATA_FILE=server/json/final_combined.json
export CTCC_SCENARIO_ID=test
python3 scripts/new_module.py

# Test via ctcc.py
venv/bin/python3 ctcc.py -j -o --id test

# Test via API
curl -X POST http://localhost:8000/api/ctcc/calculate \
  -H "Content-Type: application/json" \
  -d @test_payload.json
```

### Modifying Existing Calculations

#### Update Calculation Logic

1. Locate script in `scripts/` directory
2. Modify calculation function
3. Test with known inputs
4. Verify outputs match expected

#### Update Tests

1. Add test cases for new logic
2. Run test suite
3. Update documentation

### Adding New Input Format

#### Step 1: Create Loader

```python
# scripts/xml_loaders.py
import xml.etree.ElementTree as ET

def load_project_technical_details():
    """Load from XML file."""
    tree = ET.parse(os.getenv('CTCC_XML_FILE'))
    root = tree.getroot()
    # Parse XML and return dict
    return {...}
```

#### Step 2: Update Smart Loaders

```python
# scripts/smart_loaders.py
input_mode = os.getenv('CTCC_INPUT_MODE', 'yaml')

if input_mode == 'xml':
    from xml_loaders import *
elif input_mode == 'json':
    from json_loaders import *
else:
    from yaml_loaders import *
```

#### Step 3: Update ctcc.py

```python
# Add XML mode handling
if input_mode == 'xml':
    xml_file = os.getenv('CTCC_XML_FILE')
    if not xml_file:
        print("Error: XML mode requires CTCC_XML_FILE")
        sys.exit(1)
```

### Adding New Output Format

Similar process as adding input format, but for `*_output_manager.py` and `smart_output.py`.

---

## API Reference

### FastAPI Endpoints

#### GET `/`

Returns web UI (index.html)

**Response:** HTML page

---

#### GET `/api/final_combined`

Returns combined JSON configuration

**Response:**
```json
{
  "01_project_technical_details": {...},
  "02_project_physical_details": {...},
  ...
}
```

---

#### POST `/api/ctcc/calculate`

Runs CTCC calculations

**Request:**
```json
{
  "input_mode": "json",
  "output_mode": "json",
  "scenario_id": "test",
  "combined_data": {...}
}
```

**Response (JSON output):**
```json
{
  "success": true,
  "scenario_id": "test",
  "timestamp": "2025-11-10T12:00:00",
  "input_mode": "json",
  "output_mode": "json",
  "csv_files": null,
  "results": {
    "scenario_id": "test",
    "technical_parameters": {...},
    "costs": {
      "build": {...},
      "row": {...},
      ...
    },
    "benefits": {
      "congestion_curtailment": {...}
    },
    "summary": {...},
    "bcr": {...}
  },
  "error": null
}
```

**Response (CSV output):**
```json
{
  "success": true,
  "scenario_id": "test",
  "timestamp": "2025-11-10T12:00:00",
  "input_mode": "json",
  "output_mode": "csv",
  "csv_files": [
    "batch_summary.csv",
    "build_costs.csv",
    ...
  ],
  "results": null,
  "output_dir": "/path/to/outputs",
  "error": null
}
```

---

#### GET `/api/outputs/{filename}`

Downloads CSV output file

**Query Parameters:**
- `download` (bool, optional): Force download vs inline preview

**Example:**
```bash
# Preview
curl http://localhost:8000/api/outputs/batch_summary.csv

# Download
curl http://localhost:8000/api/outputs/batch_summary.csv?download=true \
  -o batch_summary.csv
```

**Security:**
- Only .csv files allowed
- Directory traversal prevented
- File existence validated

---

## File Structure

```
CTCC/
├── ctcc.py                       # CLI entry point
├── yaml_to_json.py               # YAML→JSON converter
├── cleanup_ctcc.sh               # Cleanup script
├── run_yaml_csv.command          # YAML→CSV runner
├── run_json_csv.command          # JSON→CSV runner
├── run_json_json.command         # JSON→JSON runner
│
├── scripts/                      # Calculation modules
│   ├── smart_loaders.py          # Input abstraction
│   ├── smart_output.py           # Output abstraction
│   ├── yaml_loaders.py           # YAML input
│   ├── json_loaders.py           # JSON input
│   ├── csv_output_manager.py    # CSV output
│   ├── json_output_manager.py   # JSON output
│   ├── financial_utils.py       # AFUDC, PV calculations
│   ├── bcr_calculator.py        # Benefit-cost ratio
│   │
│   ├── weighted_miles.py        # 1. Preprocessing
│   ├── build_costs.py           # 2. Build costs
│   ├── insurance_costs.py       # 3. Insurance
│   ├── row_costs.py             # 4. Right-of-way
│   ├── environmental_mitigation.py  # 5. Environmental
│   ├── delay_costs.py           # 6. Delays
│   ├── wildfire_costs.py        # 7. Wildfire risk
│   ├── outage_costs.py          # 8. Outage risk
│   ├── congestion_curtailment_reduction.py  # 9. Benefits
│   ├── energy_losses.py         # 10. Preprocessing
│   ├── emissions.py             # 11. Emissions
│   ├── line_loss_costs.py       # 12. Line losses
│   └── oandm.py                 # 13. O&M
│
├── yamls/                        # YAML configuration (22 files)
│   ├── 01_project_technical_details.yaml
│   ├── 02_project_physical_details.yaml
│   └── ...
│
├── outputs/                      # Calculation results
│   ├── *.csv                     # CSV outputs
│   └── ctcc_results_*.json       # JSON outputs
│
├── server/                       # FastAPI web server
│   ├── app/
│   │   ├── main.py               # FastAPI app
│   │   ├── ctcc_processor.py     # Calculation orchestrator
│   │   └── processor.py          # Demo processor
│   │
│   ├── static/
│   │   └── index.html            # Web UI (SPA)
│   │
│   ├── json/                     # JSON configs (21 files)
│   │   ├── 01_project_technical_details.json
│   │   └── final_combined.json   # Combined config
│   │
│   ├── logs/                     # Server logs
│   ├── yaml_to_json.py           # Server YAML converter
│   ├── requirements.txt          # Python dependencies
│   │
│   ├── run_calc_server.command   # Start FastAPI
│   ├── web_ui_server.command     # Start static server
│   └── convert_yamls.command     # YAML→JSON tool
│
├── venv/                         # CLI virtual env
│
├── README.md                     # User documentation
├── Claude.md                     # This file
└── MODE_FLOW_DIAGRAM.md          # Architecture docs
```

---

## Testing

### Manual Testing

#### Test CLI

```bash
# YAML→CSV (default)
venv/bin/python3 ctcc.py

# JSON→CSV
venv/bin/python3 ctcc.py -j

# JSON→JSON
venv/bin/python3 ctcc.py -j -o --id test
```

#### Test API

```bash
# Start server
cd server
./run_calc_server.command

# Test in browser
open http://localhost:8000

# Test with curl
curl -X POST http://localhost:8000/api/ctcc/calculate \
  -H "Content-Type: application/json" \
  -d @test_payload.json
```

#### Test Individual Script

```bash
export CTCC_INPUT_MODE=json
export CTCC_OUTPUT_MODE=json
export CTCC_JSON_DATA_FILE=server/json/final_combined.json
export CTCC_SCENARIO_ID=test
python3 scripts/build_costs.py
```

### Test Scripts

```bash
# API vs CLI comparison
venv/bin/python3 test_api_vs_cli.py

# CTCC processor test
venv/bin/python3 test_ctcc_processor.py

# Mode comparison
venv/bin/python3 test_mode_comparison.py
```

### Unit Testing

*To be implemented*

Planned structure:
```
tests/
├── test_loaders.py
├── test_output_managers.py
├── test_calculations.py
├── test_api.py
└── fixtures/
    ├── sample_yaml/
    └── sample_json/
```

---

## Known Issues

### Issue 1: Missing YAML File Mappings (FIXED)

**Status:** ✅ Resolved in v2.0

**Problem:** `yaml_loaders.py` was missing 5 file mappings, causing YAML mode to fail.

**Solution:** Added all missing entries to `yaml_file_map` dictionary.

### Issue 2: Server Processor Code Duplication (FIXED)

**Status:** ✅ Resolved in v2.0

**Problem:** `ctcc_processor.py` duplicated all calculation logic (453 lines).

**Solution:** Refactored to delegate to `ctcc.py` via subprocess (189 lines, 58% reduction).

### Issue 3: Module-Specific CSV Files Not Generated

**Status:** ⚠️ Known limitation

**Problem:** Only `batch_summary.csv` is generated, not individual module CSVs.

**Root Cause:** Scripts call `write_batch_summary()` but not `write_module_csv()`.

**Workaround:** Use JSON output mode for complete detailed results.

**Fix Required:** Update each script to call `write_module_csv()` with module-specific data.

---

## Deployment

### Production Checklist

- [ ] Set strong SECRET_KEY in FastAPI
- [ ] Configure CORS for production domains
- [ ] Set up reverse proxy (nginx)
- [ ] Enable HTTPS
- [ ] Configure logging
- [ ] Set up monitoring
- [ ] Configure file permissions
- [ ] Set resource limits (timeout, memory)
- [ ] Test all mode combinations
- [ ] Verify CSV downloads work
- [ ] Test with realistic data sizes

### Environment Setup

```bash
# Production environment variables
export CTCC_ENV=production
export CTCC_LOG_LEVEL=INFO
export CTCC_MAX_TIMEOUT=600000
export CTCC_TEMP_DIR=/var/tmp/ctcc
```

### Docker Deployment

*To be implemented*

Planned Dockerfile:
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . /app

RUN pip install -r server/requirements.txt
RUN pip install -r requirements.txt

EXPOSE 8000

CMD ["uvicorn", "server.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## Troubleshooting

### Server Won't Start

**Error:** `Port 8000 already in use`

**Solution:**
```bash
# Find process
lsof -i :8000

# Kill process
kill -9 <PID>

# Or use different port
PORT=8001 ./run_calc_server.command
```

### Calculation Fails with KeyError

**Error:** `KeyError: 'some_field'`

**Cause:** Missing or incorrect configuration data

**Solution:**
```bash
# Verify JSON structure
python3 -c "import json; print(json.load(open('server/json/final_combined.json')))"

# Regenerate from YAML
cd server
./convert_yamls.command
```

### Environment Variables Not Set

**Error:** Scripts use wrong mode

**Solution:**
```bash
# Check environment
env | grep CTCC

# Clear if needed
unset CTCC_INPUT_MODE
unset CTCC_OUTPUT_MODE
unset CTCC_JSON_DATA_FILE
unset CTCC_SCENARIO_ID
```

### Temp Files Not Cleaned Up

**Symptom:** `json_output_*.json` files remain in `outputs/`

**Solution:**
```bash
# Manual cleanup
rm outputs/json_output_*.json

# Or use cleanup script
./cleanup_ctcc.sh
```

### Virtual Environment Issues

**Error:** Module not found

**Solution:**
```bash
# CLI venv
cd CTCC
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install pyyaml pandas numpy

# Server venv
cd server
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## Contributing

### Code Style

- Follow PEP 8 style guide
- Use type hints where appropriate
- Add docstrings to all functions
- Comment complex logic
- Keep functions focused and small

### Git Workflow

1. Create feature branch: `git checkout -b feature/new-module`
2. Make changes and test thoroughly
3. Commit with descriptive messages
4. Push and create pull request
5. Request code review

### Documentation

- Update README.md for user-facing changes
- Update Claude.md for developer changes
- Update MODE_FLOW_DIAGRAM.md for architecture changes
- Add inline comments for complex logic

---

## Version History

### v2.0 (2025-11-10)

**Major Changes:**
- Added JSON input/output modes
- Implemented command-line flags (`-j`, `-o`, `--id`)
- Refactored server processor to delegate to `ctcc.py`
- Fixed YAML loader missing file mappings
- Created comprehensive documentation

**Improvements:**
- Reduced server processor code by 58% (453 → 189 lines)
- Single source of truth for calculations
- Web UI with CSV preview and download
- Automatic temp file cleanup
- Better error handling

### v1.0 (2025-10-31)

**Initial Release:**
- 13 calculation modules
- YAML input, CSV output
- CLI interface (`ctcc.py`)
- BCR calculator
- Financial utilities (AFUDC, PV)

---

## License

University of Texas at Austin

---

## Support

For questions or issues:
- Check README.md for user documentation
- Check MODE_FLOW_DIAGRAM.md for architecture
- Review code comments in calculation scripts
- Test with known-good YAML files

---

**End of Developer Documentation**
