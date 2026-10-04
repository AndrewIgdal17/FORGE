# FORGE - Framework for Open Reproducible Grid Economics

Cost-benefit calculator for transmission line projects. Package name: `forge-calc` 2.0.0.

The browser app lives in a separate repository: [github.com/AndrewIgdal17/FORGE_WebApp](https://github.com/AndrewIgdal17/FORGE_WebApp).

## Quick Start

```bash
uv sync
python -m forge
```

`python -m forge` loads the bundled YAML defaults and runs the calculator in-process. With the shipped defaults, `capacity_mw` is 0, so the CLI exits 1 and reports invalid inputs. Set `capacity_mw` in the project technical details (or pass a scenario through the Python API) before expecting a full result.

```bash
# BCR-only console output (suppress intermediate module output)
python -m forge --simple

# Skip selected cost categories
python -m forge --no_wildfire --no_outages

# Show DEBUG-level diagnostics
python -m forge --verbose

# Get help
python -m forge --help
```

Output is JSON: `outputs/forge_results_{scenario_id}.json`.

## Installation

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
```

`uv sync` installs `forge-calc` and its runtime dependencies (`pyyaml`, `pandas`, `numpy`) from `uv.lock`. Pytest is the `dev` extra; install it before running the test suite (`uv sync --extra dev`).

## Command-Line Flags

| Flag | Description |
|------|-------------|
| `--simple` | Suppress intermediate outputs |
| `--verbose` | Show DEBUG-level diagnostics |
| `--capital_only` | Run only capital cost modules (build, ROW, environmental mitigation) plus prerequisites |
| `--no_emissions` | Skip emissions cost calculations |
| `--no_linelosses` | Skip line loss cost calculations |
| `--no_oandm` | Skip O&M cost calculations |
| `--no_insurance` | Skip general insurance cost calculations |
| `--no_delay_costs` | Skip delay cost calculations |
| `--no_wildfire` | Skip wildfire risk costs |
| `--no_outages` | Skip outage risk costs |

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

### Quick analysis

```bash
# Edit configuration
vim forge/yamls/01_project_technical_details.yaml

# Run calculations
python -m forge
```

Results are written to `outputs/forge_results_{scenario_id}.json`.

### Category exclusions

```bash
python -m forge --no_wildfire --no_outages
python -m forge --capital_only
```

### BCR-only console output

```bash
python -m forge --simple
```

## Project Structure

```
forge/                        # Python package (forge-calc)
├── __init__.py               # Public API re-exports
├── __main__.py               # CLI entry (python -m forge)
├── core.py                   # Main calculator
├── contract.py               # Input contract (resolve, diff, validate)
├── errors.py                 # InvalidInputs, CalculationError
├── presets.py                # Grid-mix presets
├── data.py                   # Data accessors (defaults template, paths)
├── scripts/                  # Calculation modules
│   ├── calc/                 # Individual cost/benefit calculators
│   ├── io/                   # Input/output processing
│   ├── utils/                # Shared utilities
│   ├── sensitivity/          # Sensitivity runners
│   └── tests/                # Facilitated-emissions unit tests
├── yamls/                    # YAML input templates (package data)
├── scenarios/                # Case study scenarios (package data)
└── presets/                  # Bundled presets (package data)
test/                         # pytest suite
scripts/                      # benchmark.py, record_golden.py
docs/                         # Workflow notes and YAML explorer
documentation/                # Methodology description
BCR_CHEAT_SHEET.md            # BCR perspectives and exclusion variants
generate_yaml_docs.py         # YAML documentation generator
pyproject.toml                # Package metadata and pytest config
uv.lock                       # Locked dependencies
```

## Testing

```bash
uv sync --extra dev
uv run pytest
```

Pytest collects `test/` and `forge/scripts/tests/`.

## Documentation

- **README.md** (this file) — Quick start
- **BCR_CHEAT_SHEET.md** — BCR perspectives and exclusion variants
- **docs/** — Execution workflow notes and the YAML input explorer
- **documentation/FORGE_METHODOLOGY.md** — Methodology description
- **generate_yaml_docs.py** — Regenerates YAML documentation

## Version

- **2.0.0** — In-process JSON calculator (`forge-calc`). The web app is [FORGE_WebApp](https://github.com/AndrewIgdal17/FORGE_WebApp).

## License

University of Texas at Austin
