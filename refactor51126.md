# CTCC refactor summary (steps 1–6) — for Dane

This document explains the refactor we have done so far. It is a self-contained overview of all six completed steps: what changed and why.

---

## Step 1: Greek letters as ASCII

**What we did:** Replaced Unicode Greek (and math) symbols in Python code with readable ASCII names.

**Why it mattered:** The codebase had symbols like Δ (Delta), λ (lambda), φ (phi), α (alpha) in variable names, dict keys, and print statements (e.g. in `congestion_curtailment_reduction.py`, `wildfire_costs.py`, `outage_costs.py`, `emissions.py`). Those are valid in Python but cause problems: hard to type, poor search/diff support, and encoding issues in some terminals or tools. Methodology docs (LaTeX, markdown) still use proper math notation; only **code** was changed.

**Concrete changes:** Identifiers like `ΔC_rem` became `delta_C_rem`; `λc` became `lambda_curt` or similar; dict keys like `"ΔC_remain_bc_mw"` became `"delta_C_remain_bc_mw"`. Print strings that showed Greek were updated to words (e.g. "lambda * S", "phi =", "alpha"). Result: code is searchable, portable, and easier to maintain.

---

## Step 2: One Python project, one venv

**What we did:** Unified the project so there is a single virtual environment for both the calculator and the server.

**Why it mattered:** Previously there were two venvs: one at repo root for `ctcc.py` and the calculation scripts, and one under `server/` for the FastAPI app. The server even had logic (`ensure_cli_venv()`) to create or use the root venv when running a calculation. That meant two dependency lists, two places to install, and a brittle bridge between server and CLI. New contributors and deployment had to think about “which venv for which task.”

**Concrete changes:** We merged dependencies into one list at repo root. The server now runs with that same environment (e.g. `run_calc_server.command` activates the root venv and runs uvicorn). When the API runs a calculation, it uses the same Python (e.g. `sys.executable`) to invoke `ctcc.py`; no second venv and no `ensure_cli_venv()`. One place to install, one place to update.

---

## Step 3: YAML in, JSON out

**What we did:** Gave the calculator a single contract: it **only** reads input from a YAML directory and **only** writes one JSON result file. We removed the old “two input modes” (YAML or JSON) and “two output modes” (CSV or JSON).

**Why it mattered:** Before, the calculator could read either YAML files or a temporary JSON file, and could write either CSV (e.g. `batch_summary.csv`) or JSON. That meant branching everywhere: `smart_loaders` chose between `yaml_loaders` and `json_loaders`; the output path chose between CSV and JSON managers; the server set env vars so the calculator read from a temp JSON file. Two code paths for input, two for output, and more edge cases and bugs. Picking one input and one output format simplified the pipeline and set us up for a future move to a database (step 7).

**How it works now:**

- **Calculator:** Always reads from a YAML directory (default `yamls/`, or a directory set by `CTCC_YAMLS_DIR`). Always writes one file: `ctcc_results_{scenario_id}.json`. No CSV path inside the calculator; no JSON input path.
- **Web app / API:** From the user’s perspective nothing changed. The app still sends JSON and receives JSON. Under the hood, the **server** converts the incoming JSON (merged with the template) into a **temporary YAML directory**, sets `CTCC_YAMLS_DIR` to that directory, runs the calculator, then reads `ctcc_results_{scenario_id}.json` and returns it. So the API boundary stays JSON; only the internal calculator contract is YAML in, JSON out.

```mermaid
flowchart LR
  Client[JSON request]
  ServerMerge[Merge with template]
  WriteYaml[Write temp YAML dir]
  InvokeCtcc[Invoke ctcc]
  ReadJson[Read ctcc_results JSON]
  Response[JSON response]
  Client --> ServerMerge --> WriteYaml --> InvokeCtcc --> ReadJson --> Response
```

**Why this helps later:** When we add a database (step 7), we only need one **input adapter**: “read config for this run from the DB” instead of “read from YAML directory.” We do not need to support both YAML and JSON input in the calculator; we swap the source and keep the rest of the pipeline the same.

---

## Step 4: FastAPI structure

**What we did:** Gave the server a clearer layout: request/response models moved into a dedicated `models.py`, and endpoints return Pydantic models instead of raw `JSONResponse` wrappers.

**Why it mattered:** Previously, `main.py` mixed everything: models defined inline, routes, and helpers like `_refresh_final_combined` and `_sanitize_for_json`. Endpoints were annotated with `response_model=OutputPayload` but actually returned `JSONResponse(result)`, so the declared shape could drift from what was really returned. Moving models out and returning real Pydantic instances gives a single place for the API shape, better OpenAPI docs, and easier testing.

**Concrete changes:** Models (e.g. `CTCCInputPayload`, `CTCCOutputPayload`) live in `app/models.py`. Route handlers build and return those model instances so FastAPI handles serialization. Optionally, routes were grouped into routers (e.g. `routers/ctcc.py`, `routers/general.py`) so `main.py` stays a thin composition point. Result: conventional FastAPI layout and a clear API surface for the next step (typing).

---

## Step 5: Pydantic instead of Dict[str, Any]

**What we did:** Replaced untyped dicts in the API and in key calculator paths with Pydantic models and sub-models. That gave us validation, clearer types, and centralized handling of things like `inf`/`nan` in JSON.

**Why it mattered:** The API and the BCR/aggregation code used `Dict[str, Any]` (or plain `dict`) for payloads and results. So we had manual checks (`_is_number`, `_sanitize_for_json`), typo-prone key access (`result.get("costs", {}).get("build", {}).get("total_pv", 0)`), and no single place that defined “what does a valid request or result look like?” Pydantic lets us define that shape once and get validation and serialization in one place.

**Concrete changes:** Request and response payloads now use nested Pydantic models where the shape is known (e.g. `combined_data` sections, `costs`/`benefits`/`summary`/`bcr` in results). BCR input is a typed model so we use attribute access instead of `safe_get_numeric`. We added custom serialization for non-finite numbers so we could remove or narrow `_sanitize_for_json`. Result: fewer runtime key errors, better IDE/type-checker support, and one source of truth per shape.

---

## Step 6: In-process pipeline (no subprocess per script)

**What we did:** The calculator no longer runs each script as a separate subprocess. Instead, `ctcc.py` **imports** each calculation module and **calls** its `main()` (or equivalent) in the same process. Data passes in memory through a shared output aggregator.

**Why it mattered:** Previously, for every run we spawned 10–15 Python processes (one per script). Each process started the interpreter, loaded the same libraries, read input from disk, and wrote its output to a file; then the orchestrator aggregated by reading those files. That was slow (many process spawns and repeated I/O) and harder to debug (failures showed up as “script X exited with code 1” instead of a normal Python traceback). Running everything in one process removes the spawn overhead and keeps a single traceback and a single import graph.

**Concrete changes:** In `ctcc.py`, the loop that called `run_script(script_name)` (subprocess) was replaced with a loop that imports the module (e.g. `importlib.import_module`) and calls `module.main()`. The output manager (JSON aggregator) is created once and shared; each step adds its results in memory instead of writing per-script files. We kept a `--subprocess` flag so we can still run the old way for comparison or debugging. Result: faster runs, simpler handoff, and easier debugging and profiling.

---

## Summary

| Step | What we did |
|------|----------------|
| 1 | Greek letters → ASCII in code (searchable, portable). |
| 2 | One venv for CLI and server (one dependency list, no ensure_cli_venv). |
| 3 | Calculator: YAML in, JSON out only; server converts client JSON to temp YAML at the boundary. |
| 4 | FastAPI: models in models.py, endpoints return Pydantic. |
| 5 | Replace Dict[str, Any] with Pydantic models; validation and serialization in one place. |
| 6 | Run calculation scripts in-process (import + call main); shared in-memory aggregator. |

Steps 7 (database instead of filesystem) and 8 (frontend) are planned but not done yet. The refactor through step 6 gives a single contract (YAML in, JSON out), one process, one venv, and a typed API—so adding a DB or moving frontend state to the backend can build on a clean base.
