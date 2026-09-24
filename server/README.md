# FORGE Web Server

FastAPI server for the Framework for Open Reproducible Grid Economics (FORGE) web app. Serves the browser UI, taxonomy-driven input metadata, and an in-process calculation API. Output is JSON.

## Layout

```
server/
├── app/
│   ├── main.py                 # FastAPI app, page routes, API routes, JWT auth
│   ├── forge_processor.py      # In-process calculator pipeline
│   ├── models.py               # Pydantic request/response models
│   └── fuel_mix_presets.py     # Fuel-mix preset catalog
├── static/                     # Frontend (HTML, JS, CSS, icons, appendix.pdf)
│   ├── workspace.html          # Main app entry (not index.html)
│   ├── landing.html
│   ├── login.html
│   ├── signup.html
│   ├── home.html
│   └── scenarios-manager.html
├── json/                       # Pre-generated JSON from yamls/ (plus final_combined.json)
├── logs/                       # Uvicorn access logs
└── regenerate_json_from_yaml.command
```

Start the server from the **repo root**, not this directory:

```bash
./run_calc_server.command
```

That script runs `uv sync`, then `uvicorn app.main:app` from `server/` (default `http://127.0.0.1:8000`). Override with `HOST` and `PORT`.

Manual equivalent (from this directory, after dependencies are installed):

```bash
../.venv/bin/python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Open the workspace at `http://127.0.0.1:8000/app/workspace`.

## Page routes

| Route | File |
|-------|------|
| `GET /` | `static/landing.html` |
| `GET /signup` | `static/signup.html` |
| `GET /login` | `static/login.html` |
| `GET /app` | `static/home.html` |
| `GET /app/workspace` | `static/workspace.html` (main app) |
| `GET /app/scenarios-manager` | `static/scenarios-manager.html` |
| `/static/*` | Static files |

## API routes

| Route | Method | Purpose |
|-------|--------|---------|
| `/api/final_combined` | GET | Combined default input JSON (regenerated from `yamls/` when YAML files change) |
| `/api/taxonomy` | GET | Cost/benefit taxonomy for the UI |
| `/api/input_metadata` | GET | Per-field metadata for taxonomy-driven forms |
| `/api/fuel_mix_presets` | GET | Fuel-mix preset catalog |
| `/api/forge/calculate` | POST | Run a FORGE calculation in-process; returns JSON |
| `/api/outputs/{filename}` | GET | Serve a `.csv` file from `outputs/` if present |

`POST /api/forge/calculate` accepts `FORGEInputPayload` (`input_mode` and `output_mode` are JSON-only). If `combined_data` is omitted, the server uses the cached `final_combined` payload. Auth: Supabase JWT when `SUPABASE_URL` is set; local runs without that env var skip auth.

## JSON inputs

`server/json/` holds per-YAML JSON files plus `final_combined.json` and `fuel_mix_presets.json`. `GET /api/final_combined` refreshes from `yamls/` when YAML mtimes change. To regenerate all JSON files by hand, run `./regenerate_json_from_yaml.command` (see `COMMAND_FILES_GUIDE.md`).
