# scripts/utils/

Shared utilities imported by almost every calculator module.

Includes path configuration, run context, YAML-backed smart loaders, JSON output wrapping, financial math, calculation helpers, constants, weighted-miles, and scenario helpers. Two circular import chains (`yaml_loaders` ↔ `calculation_utils`, and `financial_utils` → `smart_loaders` → `yaml_loaders` → `financial_utils`) stay lazy on purpose.
