# forge/scripts/

FORGE calculator modules under the `forge` package. All calculation, I/O, and helper modules live here (`from forge.scripts.utils.smart_output import ...`).

| Subdir | Contents |
|--------|----------|
| `calc/` | Cost and benefit calculation modules |
| `runners/` | Case-study scenario runners |
| `sensitivity/` | Sensitivity-analysis scripts |
| `utils/` | Shared utilities (finance, loaders, run context) |
| `io/` | YAML/JSON I/O, taxonomy, output managers |
| `tests/` | Script-level validation helpers |

Entry point is `python -m forge` (`forge/__main__.py` → `forge.core`), which imports these packages and runs the in-process pipeline.
