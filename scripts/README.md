# scripts/

FORGE calculator Python package. All calculation, I/O, and helper modules live here as a proper package (`from scripts.utils.smart_output import ...`).

| Subdir | Contents |
|--------|----------|
| `calc/` | Cost and benefit calculation modules |
| `runners/` | Case-study scenario runners |
| `sensitivity/` | Sensitivity-analysis scripts |
| `utils/` | Shared utilities (finance, loaders, paths, run context) |
| `io/` | YAML/JSON I/O, taxonomy, output managers |
| `generators/` | Lookup-table JSON generators |
| `tests/` | Script-level validation helpers |

Entry point is `forge.py` at the repo root, which imports these packages and runs the in-process pipeline.
