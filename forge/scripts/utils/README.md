# forge/scripts/utils/

Shared utilities imported by almost every calculator module.

Includes path configuration, run context, YAML-backed smart loaders, JSON output wrapping, financial math, calculation helpers, constants, weighted-miles, and scenario helpers.

`financial_utils.py` includes `calculate_amortized_cost()`, a level-annuity utility that is not the appendix FERC declining-balance method (which lives in `revenue.py`). It has no active callers.

Two circular import chains stay lazy on purpose: `forge.scripts.io.yaml_loaders` ↔ `calculation_utils`, and `financial_utils` → `smart_loaders` → `forge.scripts.io.yaml_loaders` → `financial_utils`. (`yaml_loaders` lives in `forge/scripts/io/`, not `forge/scripts/utils/`.)
