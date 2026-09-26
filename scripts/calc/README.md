# scripts/calc/

Core cost and benefit calculation modules. `forge.py` loads most of these via `importlib.import_module("scripts.calc.<name>")` and calls `main()`. They share data through `scripts.utils.run_context` and write results through `scripts.utils.smart_output`. `bcr_trajectory` is the exception: it is loaded by direct import (`from scripts.calc.bcr_trajectory import compute_trajectory`), not importlib.

## Modules

- `build_costs` — Terrain-adjusted conductor, structure, and converter CAPEX with contingencies.
- `row_costs` — ROW acquisition, holding, and rent by agreement type.
- `environmental_mitigation` — Base per-acre mitigation plus wetland/habitat credit costs.
- `revenue` — FERC declining-balance rate-based revenue requirement (ATRR).
- `insurance_costs` — Annual operational insurance premium on insurable asset value.
- `delay_costs` — Base pre-construction delay costs (legal, admin, labor, regulatory).
- `wildfire_costs` — Expected annual wildfire loss (ignition × severity × risk growth).
- `outage_costs` — Expected annual outage cost (rate × duration × VoLL × risk growth).
- `congestion_reduction` — Congestion reduction benefit from relieved constraint MWh.
- `energy_losses` — Physical energy losses (conductor resistance + converter stations).
- `oandm` — Conductor, structure, converter, and vegetation-management O&M.
- `emissions` — Loss-compensation emissions social cost (extra generation to cover losses).
- `facilitated_emissions` — Facilitated emissions and avoided-emissions benefit (`B_avoided_emissions`).
- `displacement_delay_cost` — Foregone avoided-emissions benefit during the delay period.
- `line_loss_costs` — Thermal line-loss costs valued at electricity price.
- `bcr_calculator` — Taxonomy-driven BCR aggregation across 9 perspectives.
- `bcr_trajectory` — Year-by-year BCR/NPV trajectory after all modules and BCR aggregation.

## Data flow

Modules share data through `scripts.utils.run_context`. The key pattern: `ctx.build_costs` provides post-contingency/post-soft-cost CAPEX to downstream modules (O&M, insurance, env mitigation).

## Selectors

Several modules use explicit binary selectors (ξ) at the point of use, matching the appendix equations. Examples: `xi_structure` in `build_costs`, `xi_dc` in `oandm`, `xi_credits` in `environmental_mitigation`.
