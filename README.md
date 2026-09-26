# FORGE - Framework for Open Reproducible Grid Economics

A cost-benefit analysis tool for transmission line projects.

## Quick Start

```bash
# Default run (YAML inputs → JSON output)
python -m forge

# BCR-only console output (suppress intermediate module output)
python -m forge --simple

# Skip selected cost or benefit categories
python -m forge --no_wildfire --no_outages

# Get help
python -m forge --help
```

`python -m forge` loads calculator modules in-process via `importlib.import_module()` and calls `mod.main()`. Output is JSON only: `outputs/forge_results_{scenario_id}.json`.

## Installation

```bash
# Navigate to directory
cd FORGE

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

## Command-Line Flags

| Flag | Description |
|------|-------------|
| `--simple` | Only show BCR analysis (suppress intermediate outputs) |
| `--no_emissions` | Skip emissions cost calculations |
| `--no_linelosses` | Skip line loss cost calculations |
| `--capital_only` | Run only capital cost modules (build, ROW, environmental mitigation) plus prerequisites |
| `--no_oandm` | Skip O&M cost calculations |
| `--no_insurance` | Skip general insurance cost calculations |
| `--no_delay_costs` | Skip delay cost calculations |
| `--no_wildfire` | Skip wildfire risk costs |
| `--no_outages` | Skip outage risk costs |
| `--no_congestion` | Skip congestion benefit calculations |

## Cost Modules

FORGE runs 17 calculator modules:

**Capital Costs:**
1. **Build Costs** (`build_costs`) — Conductors, structures, converters with AFUDC
2. **ROW** (`row_costs`) — Right-of-way acquisition or rental
3. **Environmental** (`environmental_mitigation`) — Mitigation and compliance

**Transfers:**
4. **Revenue** (`revenue`) — Rate-based ATRR (utility–ratepayer transfer)

**Operational Costs:**
5. **O&M** (`oandm`) — Operations, maintenance, vegetation management
6. **Insurance** (`insurance_costs`) — Operational insurance premiums
7. **Energy Losses** (`energy_losses`) — Physical conductor and converter losses
8. **Line Loss Costs** (`line_loss_costs`) — Valued energy-loss costs
9. **Emissions** (`emissions`) — Loss-compensation carbon emissions costs
10. **Facilitated Emissions** (`facilitated_emissions`) — Project-path vs. no-line emissions (feeds avoided-emissions benefit)
11. **Displacement Delay** (`displacement_delay_cost`) — Foregone displacement benefit during delay

**Risk Costs:**
12. **Wildfire** (`wildfire_costs`) — Wildfire risk assessment
13. **Outage** (`outage_costs`) — Outage risk by terrain type

**Other Costs:**
14. **Delays** (`delay_costs`) — Construction delay impacts

**Benefits:**
15. **Congestion Reduction** (`congestion_reduction`) — Congestion relief, delivered energy, and capacity value

**Analysis:**
16. **BCR** (`bcr_calculator`) — Benefit-cost ratio calculations
17. **BCR Trajectory** (`bcr_trajectory`) — Year-by-year BCR/NPV trajectory

## Common Workflows

### Workflow 1: Quick Analysis
```bash
# Edit configuration
vim yamls/01_project_technical_details.yaml

# Run calculations
python -m forge

# Results written to outputs/forge_results_{scenario_id}.json
```

### Workflow 2: Category Exclusions
```bash
# Omit wildfire and outage risk
python -m forge --no_wildfire --no_outages

# Capital costs only
python -m forge --capital_only
```

### Workflow 3: BCR-Only Console Output
```bash
python -m forge --simple
```

## Web Interface

FORGE includes a FastAPI web server with browser UI. Server code lives in `server/app/main.py`. The workspace entry point is `/app/workspace` (`server/static/workspace.html`).

```bash
# Start server (from this directory)
./run_calc_server.command

# Open workspace
open http://localhost:8000/app/workspace
```

**Features:**
- Browser-based UI for editing configuration
- In-process calculations
- JSON results
- API endpoints for integration

## API Usage

### Start Server
```bash
./run_calc_server.command
```

### API Endpoints

**Get taxonomy (cost/benefit structure):**
```bash
curl http://localhost:8000/api/taxonomy
```

**Get input-field metadata (taxonomy-driven forms):**
```bash
curl http://localhost:8000/api/input_metadata
```

**Get combined YAML-derived configuration:**
```bash
curl http://localhost:8000/api/final_combined
```

**Run calculation:**
```bash
curl -X POST http://localhost:8000/api/forge/calculate \
  -H "Content-Type: application/json" \
  -d '{
    "combined_data": { ... },
    "scenario_id": "test"
  }'
```

## Project Structure

```
forge/                        # Python package
├── __init__.py               # Public API re-exports
├── __main__.py               # CLI entry (python -m forge)
├── core.py                   # Main calculator (was forge.py)
├── data.py                   # Data accessors (get_yamls_path, etc.)
├── scripts/                  # Calculation modules
│   ├── calc/                 # Individual cost/benefit calculators
│   ├── io/                   # Input/output processing
│   └── utils/                # Shared utilities
├── yamls/                    # YAML input templates (package data)
└── scenarios/                # Case study scenarios (package data)
server/
  app/                      # FastAPI web server
  static/                   # Web app frontend (entry: workspace.html)
  json/                     # Pre-generated JSON for web app
test/                       # pytest test suite
testing/                    # Integration test runner
docs/                       # Documentation
documentation/              # Methodology description
```

## Troubleshooting

### "PyYAML is required"
Use the virtual environment:
```bash
python -m forge
```

### "No such file or directory: yamls/"
Make sure you're in the FORGE directory:
```bash
cd /path/to/FORGE
python -m forge
```

## Development

### Adding a New Cost Module

1. Create module file: `forge/scripts/calc/new_module.py`
2. Use smart loaders:
   ```python
   from forge.scripts.utils.smart_loaders import load_project_technical_details
   from forge.scripts.utils.smart_output import SmartOutputManager
   ```
3. Add to the script list in `forge/core.py`
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
- **BCR_CHEAT_SHEET.md** - BCR perspectives and exclusion variants
- **testing/** - Automated test suite
  - **testing/README.md** - Testing quick start
  - **testing/TESTING.md** - Complete testing guide
  - **testing/TEST_PLAN.md** - Full test plan
- **server/COMMAND_FILES_GUIDE.md** - Server command documentation

## Version History

- **v2.0** - In-process JSON calculator, web UI, API integration
- **v1.0** - Original YAML-driven implementation

## License

University of Texas at Austin
