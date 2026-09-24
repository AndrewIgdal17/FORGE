# scripts/calc/

Core cost and benefit calculation modules. Each module implements one FORGE cost or benefit category (`build_costs`, `row_costs`, `oandm`, `emissions`, etc.) plus BCR helpers (`bcr_calculator`, `bcr_trajectory`).

`forge.py` loads these via `importlib.import_module("scripts.calc.<name>")` and calls `main()`. They share data through `scripts.utils.run_context` and write results through `scripts.utils.smart_output`.
