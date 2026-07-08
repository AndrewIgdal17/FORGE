# Task 3 Report: Displacement Delay Cost Module (#26)

## Status: DONE

## Commits

- Not committed this session — the shell tool became unresponsive after verification completed. All files below are modified/created in the working tree and verified working; a commit still needs to be made (see Concerns).

## Summary

Added a new, purely additive module that computes the foregone emissions displacement benefit during the project delay period, valued at year-specific social cost of carbon (SCC) and discounted at the social discount rate. Wired it into the taxonomy, output managers, and pipeline exactly following the `facilitated_emissions.py` pattern.

### New file

- `scripts/displacement_delay_cost.py` — `calculate_displacement_delay_cost()` evolves both the counterfactual and project-path fuel mixes over the delay period using `calculate_energy_mix_by_year`/`calculate_emissions_by_year` from `emissions.py`, computes the emissions difference (displacement that *would* have occurred) per delay-year, values it at year-`t` SCC (`base_cost * (1+growth)^t`), and discounts each year at `social_discount_rate^(t+1)`. Returns zeros gracefully when `delay_years <= 0` or `energy_delivered_annual_mwh <= 0`. `main()` follows `facilitated_emissions.py`'s exact loading/fallback/output pattern (including the subprocess JSON-on-disk fallback for `energy_delivered_annual_mwh`). Module docstring and a code comment document the known limitation: delay-period and operational-period calculations both start fuel-mix evolution from the YAML initial percentages (no COD handoff) — to be fixed by the future single-trajectory redesign (Task 4).

### Pipeline wiring

- `ctcc.py`: added `"displacement_delay_cost"` to `_PRELOAD_MODULES` (after `facilitated_emissions`), and `"displacement_delay_cost.py"` to both `_build_scripts_list()` and the CLI `main()` script list (after `facilitated_emissions.py`, under the `no_emissions` guard).
- `scripts/json_output_manager.py`: added `add_displacement_delay_cost()` storing results under `self.costs["displacement_delay"]` (a cost, unlike `facilitated_emissions` which stores under benefits). Also folded the new cost into `calculate_summary()`'s grand-total and `reporting_bucket_soft_pv` fallback (used only if the taxonomy/BCR path throws).
- `scripts/taxonomy.py`: added `TaxonomyItem("emissions_displacement_delay", "cost", "soft", "delay", "Displacement Delay Emissions Cost", "social", None, 9, ...)` (soft/delay bucket, `display_order=9` after `curtailment_delay`, `discount_rate="social"` per the module's discounting). Added `"emissions_displacement_delay": "emissions_displacement_delay_pv"` to `TAXONOMY_TO_CALCULATOR_KEY`. Updated item-count assertions 34→35 (both the module-level and `__main__` checks), calculator-key-count assertion 23→24, and the `_expected_social` set (module discounts at social rate, so it needed adding there too or the `__main__` verification would fail).
- `scripts/taxonomy_adapters.py`: added `adapt_displacement_delay_cost()` reading `costs.get("displacement_delay", {})`, wired into `adapt_all_results()`, and added the `emissions_displacement_delay_pv`/`_nominal` keys to `taxonomy_results_to_flat_keys()`.
- `scripts/bcr_calculator.py`: added `"emissions_displacement_delay_pv"` to `_LEGACY_ITEM_KEYS` so it flows through `compute_all_bcrs()` into the flat BCR/CSV-equivalent output. No BCR-set changes needed — it's automatically picked up by `_ALL_COST_IDS`, `_SOFT_IDS`, and `_DELAY_IDS` (subgroup-based), which feed `soft_costs_pv`, `delay_costs_pv`, `total_costs_pv`, and the existing `hard_delay`/exclusion-variant BCR denominators, exactly like `congestion_delay`/`curtailment_delay`.
- `scripts/csv_output_manager.py`: added `"emissions_displacement_delay_pv"` to `BATCH_SUMMARY_FIELDS` (Delay Costs PV section). Did not touch the legacy (unused) `CTCCOutputManager` class in this file — confirmed via grep that no script imports it anymore (`smart_output.CTCCOutputManager` is the one actually used everywhere); only `BATCH_SUMMARY_FIELDS` is imported from this module by `ctcc.py`.

### Appendix

- `Projects/CTCC/methodology/appendix.tex`: inserted `\subsubsection{Displacement Delay Emissions Cost}\label{sec:app-displacement-delay}` immediately after the "Displacement avoided emissions" pairwise-corollary paragraph (end of `sec:app-displacement`), with the equation, the SCC-growth citation, and the Limitation paragraph exactly per spec. Fixed one citation key typo from the spec (`OMBA42023` → the actual bib key `OMB2023CircularA4`, verified against `references.bib` and already used elsewhere in the appendix for the same OMB Circular A-4 citation).

## Verification

- `python taxonomy.py` → `Taxonomy verification passed: 35 items, 36 BCR definitions, 5 excludable groups` (regenerated `server/json/taxonomy.json`).
- `python -m pytest test_facilitated_emissions.py -q` → 3 passed (no regression).
- `python run_sunzia.py` → ran end-to-end without errors (both delay=17 and delay=2 scenarios).
- Direct Python check via `run_scenario()`:
  - SunZia delay=17: `costs['displacement_delay'] = {'displacement_delay_cost_pv': 27,682,006,651, 'displacement_delay_cost_nominal': 35,467,519,529, ...}` — large and non-zero, as expected for 17 years of foregone 2400 MW wind displacement.
  - Same inputs with `delay_years=0`: `displacement_delay_cost_pv = 0.0` exactly.
- `python run_tbc.py` → ran end-to-end; inspected the saved `.ctcc` files directly:
  - `TBC_Delay4.ctcc` → `displacement_delay_cost_pv = 206,829,926` (> 0).
  - `TBC_NoDelay.ctcc` → `displacement_delay_cost_pv = 0.0` (exactly 0), confirming the delay-vs-no-delay contrast the task asked to verify.
- LaTeX: compiled `appendix.tex` standalone (temp wrapper with `biblatex`/`biber` + methodology's `references.bib`) — 69 pages, no LaTeX errors, no undefined citations after the biber pass (confirms `Rennert2022` and the corrected `OMB2023CircularA4` key both resolve). Did not touch `papers/paper1-energy-policy/p1appendix.tex` (a separate, already-stale copy out of this task's scope).
- Did **not** run the CLI form `python ctcc.py scenarios/SunZia_Delay17.ctcc --quiet` from the task's fallback instructions — `ctcc.py`'s actual CLI has no positional scenario-file argument (it reads from `YAMLS_DIR` / env, verified via `--help`); the `run_sunzia.py`/`run_tbc.py` + direct `run_scenario()` checks above already exercise the identical in-process pipeline path and confirmed correct wiring, so this was a non-issue rather than a blocker.

## Concerns

1. **No commit made.** The shell tool stopped responding (returned no exit status on repeated `echo` sanity checks) after all verification above had already completed successfully. All changes are in the working tree; someone/something with a working shell still needs to `git add`/`git commit` this task's files (the new `scripts/displacement_delay_cost.py` plus the diffs to `ctcc.py`, `scripts/taxonomy.py`, `scripts/taxonomy_adapters.py`, `scripts/json_output_manager.py`, `scripts/csv_output_manager.py`, `scripts/bcr_calculator.py`, and `Projects/CTCC/methodology/appendix.tex`).
2. **Shared working tree, not an isolated worktree.** Other tasks in this batch (see `task-1/2/6/7/9-report.md`) had already made extensive uncommitted changes to several of the same files I touched (`taxonomy.py`, `taxonomy_adapters.py`, `csv_output_manager.py`, `bcr_calculator.py`, `appendix.tex`) — e.g. a `residual_exceedance` taxonomy item was already removed and the congestion/curtailment section of the appendix was already rewritten (Approach B) before I started. My diffs are layered correctly on top of that pre-existing state (confirmed taxonomy assertions and full pipeline runs pass), but if those other tasks get committed separately before this one, watch for interleaved diff noise when reviewing this task's isolated diff.
3. **Task 4 dependency acknowledged, not implemented.** As instructed, this module intentionally does not implement the grid-mix single-trajectory handoff between delay and operational periods — that limitation is documented in both the module docstring/comment and the appendix `\paragraph{Limitation.}`.
