# FORGE - Framework for Open Reproducible Grid Economics

A flexible cost-benefit analysis tool for transmission line projects supporting multiple input/output modes.

## Quick Start

```bash
# Default mode (YAML → CSV)
venv/bin/python3 forge.py

# JSON input with JSON output
venv/bin/python3 forge.py -j -o --id my_scenario

# JSON input with CSV output
venv/bin/python3 forge.py -j

# Get help
venv/bin/python3 forge.py --help
```

## Installation

```bash
# Navigate to directory
cd FORGE

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install pyyaml pandas numpy
```

## Command-Line Flags

| Flag | Description | Example |
|------|-------------|---------|
| `-j`, `--json` | Use JSON input mode | `forge.py -j` |
| `-o`, `--json-out` | Use JSON output mode | `forge.py -j -o` |
| `--id NAME` | Set scenario ID | `forge.py --id baseline` |
| `-h`, `--help` | Show help message | `forge.py --help` |

## Mode Combinations

| Input | Output | Flags | Input Files | Output Files |
|-------|--------|-------|-------------|--------------|
| YAML | CSV | *(default)* | `yamls/*.yaml` (22) | `outputs/*.csv` (12) |
| JSON | CSV | `-j` | `combined_data.json` | `outputs/*.csv` (12) |
| JSON | JSON | `-j -o` | `combined_data.json` | `forge_results_[id].json` |

## Usage Examples

### Example 1: Traditional Analysis (Default)
```bash
venv/bin/python3 forge.py
```
- **Input:** 22 YAML files in `yamls/`
- **Output:** 12 CSV files in `outputs/`
- **Use:** Spreadsheet analysis, detailed breakdowns

### Example 2: JSON Input, CSV Output
```bash
venv/bin/python3 forge.py -j
```
- **Input:** Single `combined_data.json` (auto-generated from YAML)
- **Output:** 12 CSV files in `outputs/`
- **Use:** Single config file, multiple outputs

### Example 3: Full JSON Mode
```bash
venv/bin/python3 forge.py -j -o --id scenario_A
```
- **Input:** Single `combined_data.json`
- **Output:** Single `forge_results_scenario_A.json`
- **Use:** API integration, programmatic processing

## Output Files

**CSV Mode** (default):
- `batch_summary.csv` - Main results with all metrics
- `build_costs.csv` - Construction costs breakdown
- `insurance_costs.csv` - Insurance calculations
- `row_costs.csv` - Right-of-way costs
- `environmental_mitigation.csv` - Environmental costs
- `delay_costs.csv` - Delay impacts
- `wildfire_costs.csv` - Wildfire risk
- `outage_costs.csv` - Outage risk by terrain
- `congestion_curtailment.csv` - Congestion/curtailment benefits
- `emissions_costs.csv` - Emissions calculations
- `line_loss_costs.csv` - Energy loss costs
- `oandm_costs.csv` - Operations & maintenance

**JSON Mode** (`-o` flag):
- `forge_results_[scenario_id].json` - Single aggregated file with all results

## Comparing Scenarios

After running multiple scenarios (e.g. with different `--id` values), use the comparison script to contrast them:

```bash
python3 compare_scenarios.py
# or: ./run_compare_scenarios.command
```

- The script lists all scenarios in `outputs/batch_summary.csv` (numbered and lettered).
- Enter which to compare (e.g. `1 3 5`, `1-4`, or `A C E`), then hit Enter.
- It writes `outputs/scenario_comparison_YYYYMMDD_HHMMSS.csv` (metrics × scenarios) and `.md` (overview tables and a short contrast summary).

## Cost Modules

FORGE calculates 13 cost and benefit categories:

**Capital Costs:**
1. **Build Costs** - Conductors, structures, converters with AFUDC
2. **ROW** - Right-of-way acquisition or rental
3. **Environmental** - Mitigation and compliance

**Operational Costs:**
4. **O&M** - Operations, maintenance, vegetation management
5. **Insurance** - Operational insurance premiums
6. **Line Losses** - Energy loss calculations
7. **Emissions** - Carbon emissions costs

**Risk Costs:**
8. **Wildfire** - Wildfire risk assessment
9. **Outage** - Outage risk by terrain type

**Other Costs:**
10. **Delays** - Construction delay impacts

**Benefits:**
11. **Congestion** - Congestion reduction benefits
12. **Curtailment** - Curtailment reduction benefits

**Analysis:**
13. **BCR** - Benefit-cost ratio calculations

## Common Workflows

### Workflow 1: Quick Analysis
```bash
# Edit configuration
vim yamls/01_project_technical_details.yaml

# Run calculations
venv/bin/python3 forge.py

# View results
open outputs/batch_summary.csv
```

### Workflow 2: Multiple Scenarios
```bash
# Run different scenarios
venv/bin/python3 forge.py -j -o --id high_capacity
venv/bin/python3 forge.py -j -o --id low_cost
venv/bin/python3 forge.py -j -o --id baseline

# Compare results
diff outputs/forge_results_high_capacity.json outputs/forge_results_baseline.json
```

### Workflow 3: Programmatic Processing
```bash
# Run with JSON output
venv/bin/python3 forge.py -j -o --id analysis

# Process with custom script
python analyze_results.py outputs/forge_results_analysis.json
```

## Web Interface

FORGE includes a FastAPI web server with browser UI:

```bash
# Start server
cd server
./run_calc_server.command

# Open browser
open http://localhost:8000
```

**Features:**
- Browser-based UI for editing configuration
- Real-time calculations
- CSV file preview and download
- JSON export
- API endpoints for integration

## API Usage

### Start Server
```bash
cd server
./run_calc_server.command
```

### API Endpoints

**Get configuration:**
```bash
curl http://localhost:8000/api/final_combined
```

**Run calculation:**
```bash
curl -X POST http://localhost:8000/api/forge/calculate \
  -H "Content-Type: application/json" \
  -d '{
    "input_mode": "json",
    "output_mode": "json",
    "scenario_id": "test",
    "combined_data": { ... }
  }'
```

**Download CSV:**
```bash
curl http://localhost:8000/api/outputs/batch_summary.csv?download=true \
  -o batch_summary.csv
```

## Advanced Options

### Command Files
```bash
./run_yaml_csv.command     # YAML → CSV (traditional)
./run_json_csv.command      # JSON → CSV
./run_json_json.command     # JSON → JSON (full JSON mode)
```

**Note:** These convenience scripts use command-line flags internally.

## Project Structure

```
FORGE/
├── forge.py                    # Main CLI script with flags
├── yaml_to_json.py            # YAML → JSON converter
├── README.md                  # This file
├── yamls/                     # Input YAML files (22 files)
├── scripts/                   # Calculation modules
│   ├── smart_loaders.py      # Auto-detects input mode
│   ├── smart_output.py       # Auto-detects output mode
│   ├── json_loaders.py       # JSON input handler
│   ├── json_output_manager.py # JSON output handler
│   ├── yaml_loaders.py       # YAML input handler
│   ├── csv_output_manager.py # CSV output handler
│   ├── build_costs.py        # Build cost calculations
│   ├── oandm.py              # O&M calculations
│   └── ... (13 modules total)
├── outputs/                   # Results directory
├── server/                    # FastAPI web server
│   ├── app/
│   │   ├── main.py           # FastAPI application
│   │   └── forge_processor.py # Calculation orchestrator
│   ├── static/
│   │   └── index.html        # Web UI
│   ├── json/                  # JSON configuration files
│   ├── run_calc_server.command  # Start API server
│   ├── web_ui_server.command    # Start static file server
│   └── convert_yamls.command    # YAML to JSON converter
└── venv/                      # Virtual environment
```

## Troubleshooting

### "PyYAML is required"
Use the virtual environment:
```bash
venv/bin/python3 forge.py
```

### "No such file or directory: yamls/"
Make sure you're in the FORGE directory:
```bash
cd /path/to/FORGE
venv/bin/python3 forge.py
```

### Check Current Mode
The output shows your configuration:
```bash
venv/bin/python3 forge.py -j
# 🔧 Input Mode: JSON
# 🔧 Output Mode: CSV
# 📋 Scenario ID: 20251110_132500
```

### Clean Up Temporary Files
```bash
./cleanup_forge.sh
```

## Development

### Adding a New Cost Module

1. Create module file: `scripts/new_module.py`
2. Use smart loaders:
   ```python
   from smart_loaders import load_project_technical_details
   from smart_output import FORGEOutputManager
   ```
3. Add to `forge.py` script list
4. Update documentation

### Testing

```bash
# Run automated test suite
cd testing
../venv/bin/python3 run_tests.py --quick

# See testing/README.md for more options
```

## Documentation

- **README.md** (this file) - Quick start guide
- **testing/** - Automated test suite
  - **testing/README.md** - Testing quick start
  - **testing/TESTING.md** - Complete testing guide
  - **testing/TEST_PLAN.md** - Full test plan
- **Claude.md** - Comprehensive development documentation
- **MODE_FLOW_DIAGRAM.md** - Architecture and flow diagrams
- **server/COMMAND_FILES_GUIDE.md** - Server command documentation

## Version History

- **v2.0** - Added JSON modes, command-line flags, web UI, API integration, refactored server processor
- **v1.0** - Original YAML → CSV implementation

## License

University of Texas at Austin

## Authors

- Andrew Igdal - Original implementation
- Extended with FastAPI server and flexible mode system
