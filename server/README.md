# FastAPI JSON Template

Minimal example of a front-end page sending JSON to a FastAPI backend, delegating to a
Python helper, and returning the generated JSON result back to the browser.

## Project layout

- `app/main.py` — FastAPI application with routes for `GET /` (serve the demo page),
  `GET /api/final_combined` (serve the aggregated JSON), and `POST /api/process`
  (transform inbound payloads).
- `app/processor.py` — Re-usable Python function that transforms the inbound payload.
- `static/index.html` — Standalone HTML page with a form that uses `fetch()` to call the
  backend and renders the response.

## Getting started

```bash
python -m venv .venv
source .venv/bin/activate        # On Windows use: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open <http://127.0.0.1:8000/> in a browser and use the **Mode** selector:

- **Simple** — send the text + number inputs and receive summary stats.
- **Bulk** — the page fetches `final_combined.json` via `GET /api/final_combined`, sends
  it back to `POST /api/process`, and the server returns a flattened list of keys with
  dotted paths (one line per value).

Because CORS is configured to allow any origin, you can also host the HTML file elsewhere
and point the request at the running FastAPI instance. The **API Base URL** input
autofills with the page's own host but swaps the port to `8000`; update it if your API is
listening elsewhere (e.g. the WAN address printed by `run_fastapi.command`). The form
then appends `/api/process` automatically.

### macOS shortcut

Double-click `run_fastapi.command` (or execute it from Terminal) to launch the server,
print the reachable address on your network, and stream FastAPI request logs. Logs are
also archived in `logs/` for later inspection.

- `run_fastapi.command` — launches the API + HTML app (uses uvicorn), ensures the
  virtual environment + dependencies are ready, and prints detected public/WAN and LAN
  URLs.
- `serve_static.command` — hosts only the `static/` directory via Python's simple HTTP
  server, again reporting both WAN and LAN URLs for sharing `index.html`.

`run_fastapi.command` creates `.venv/` on first run and installs dependencies listed in
`requirements.txt` when needed. WAN detection relies on outbound HTTP; if blocked, the
scripts fall back to LAN/local addresses, and reaching the public URL can still require
port forwarding from your router.

### Utilities

- `yaml_to_json.py` — command-line helper for converting YAML files to JSON.
  ```bash
  python yaml_to_json.py input.yaml output.json
  # or omit output to print to stdout
  python yaml_to_json.py input.yaml
  ```
  When an output file is provided, the script also refreshes `final_combined.json`
  in the same directory, bundling every converted JSON except
  `project_category_template.json` into a minimized aggregate.
  Run this against the YAML sources before using the **Bulk** mode in the demo UI.
