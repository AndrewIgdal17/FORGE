"""FastAPI application that accepts JSON, delegates to a processor, and returns JSON."""

from __future__ import annotations

import json
import yaml
from json import JSONDecodeError
from pathlib import Path
from typing import Any, Dict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .ctcc_processor import run_ctcc_calculation
from .models import CTCCInputPayload, CTCCOutputPayload, InputPayload, OutputPayload
from .processor import generate_result

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"
JSON_DIR = BASE_DIR / "json"
OUTPUTS_DIR = BASE_DIR.parent / "outputs"  # CTCC/outputs directory
YAMLS_DIR = BASE_DIR.parent / "yamls"
INDEX_FILE = STATIC_DIR / "index.html"
FINAL_COMBINED_FILE = JSON_DIR / "final_combined.json"
SKIP_BASENAME = "project_category_template"

app = FastAPI(title="CTCC API Server")

# Allow frontend apps to reach the API locally or across origins.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def _refresh_final_combined() -> None:
    """Regenerate final_combined.json from current YAML inputs."""
    if not YAMLS_DIR.exists():
        return

    JSON_DIR.mkdir(parents=True, exist_ok=True)
    combined: Dict[str, Any] = {}

    yaml_files = sorted(list(YAMLS_DIR.glob("*.yaml")) + list(YAMLS_DIR.glob("*.yml")))
    yaml_stems = {yaml_file.stem for yaml_file in yaml_files}

    # Remove stale JSON files that no longer have YAML sources.
    for json_file in JSON_DIR.glob("*.json"):
        if json_file.name == FINAL_COMBINED_FILE.name:
            continue
        if json_file.stem not in yaml_stems:
            json_file.unlink()

    for yaml_file in yaml_files:
        with yaml_file.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle)

        json_path = JSON_DIR / f"{yaml_file.stem}.json"
        with json_path.open("w", encoding="utf-8") as json_handle:
            json.dump(data, json_handle, indent=2)
            json_handle.write("\n")

        if yaml_file.stem != SKIP_BASENAME:
            combined[yaml_file.stem] = data

    with FINAL_COMBINED_FILE.open("w", encoding="utf-8") as handle:
        json.dump(combined, handle, separators=(",", ":"))
        handle.write("\n")


@app.get("/", response_class=FileResponse)
async def serve_index() -> FileResponse:
    """Serve the template HTML page."""
    return FileResponse(INDEX_FILE)


@app.get("/api/final_combined", response_class=JSONResponse)
async def get_final_combined() -> JSONResponse:
    """Return the combined JSON payload generated from YAML files."""
    try:
        _refresh_final_combined()
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to regenerate final_combined.json: {exc}",
        ) from exc

    if not FINAL_COMBINED_FILE.exists():
        raise HTTPException(status_code=404, detail="final_combined.json not found")

    try:
        content = json.loads(FINAL_COMBINED_FILE.read_text(encoding="utf-8"))
        # Convert infinity and NaN values to strings for JSON compliance
        content = _sanitize_for_json(content)
    except JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail="final_combined.json is invalid JSON") from exc

    return JSONResponse(content)


def _sanitize_for_json(obj):
    """Recursively convert inf/nan values to JSON-compliant strings."""
    import math

    if isinstance(obj, dict):
        return {k: _sanitize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_sanitize_for_json(item) for item in obj]
    elif isinstance(obj, float):
        if math.isinf(obj):
            return "Infinity" if obj > 0 else "-Infinity"
        elif math.isnan(obj):
            return "NaN"
    return obj


@app.post("/api/process", response_model=OutputPayload)
async def process_payload(payload: InputPayload) -> OutputPayload:
    """Receive JSON payload, invoke processor, and return the generated result."""
    payload_dict = payload.model_dump()
    result = generate_result(payload_dict)
    return OutputPayload.model_validate(result)


@app.post("/api/ctcc/calculate", response_model=CTCCOutputPayload)
async def calculate_ctcc(payload: CTCCInputPayload) -> CTCCOutputPayload:
    """
    Run CTCC calculations with JSON input and configurable output.

    Supports dual input modes (json/yaml) and dual output modes (json/csv).
    When output_mode='json', returns calculation results as JSON.
    When output_mode='csv', writes CSV files to local folder and returns file list.
    """
    payload_dict = payload.model_dump()
    if payload_dict.get("input_mode") == "json" and not payload_dict.get("combined_data"):
        try:
            _refresh_final_combined()
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to regenerate final_combined.json: {exc}",
            ) from exc

        if not FINAL_COMBINED_FILE.exists():
            raise HTTPException(status_code=404, detail="final_combined.json not found")

        try:
            payload_dict["combined_data"] = json.loads(
                FINAL_COMBINED_FILE.read_text(encoding="utf-8")
            )
        except JSONDecodeError as exc:
            raise HTTPException(
                status_code=500, detail="final_combined.json is invalid JSON"
            ) from exc

    result = run_ctcc_calculation(payload_dict)
    return CTCCOutputPayload.model_validate(_sanitize_for_json(result))


@app.get("/api/outputs/{filename}")
async def get_output_file(filename: str, download: bool = False):
    """
    Serve CSV output files from the outputs directory.

    Args:
        filename: Name of the CSV file to retrieve
        download: If True, forces download; if False, displays inline (default)

    Returns:
        FileResponse with CSV content
    """
    # Security: only allow CSV files and prevent directory traversal
    if not filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed")

    if '/' in filename or '\\' in filename or '..' in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    file_path = OUTPUTS_DIR / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {filename}")

    if not file_path.is_file():
        raise HTTPException(status_code=400, detail="Invalid file")

    # Return file with appropriate headers
    # When download=True, browser will download the file
    # When download=False, browser will display inline (for preview)
    headers = {}
    if download:
        headers["Content-Disposition"] = f'attachment; filename="{filename}"'

    return FileResponse(
        path=file_path,
        media_type="text/csv",
        filename=filename,
        headers=headers
    )


if __name__ == "__main__":
    try:
        import uvicorn
    except ModuleNotFoundError as exc:  # pragma: no cover - convenience only
        raise SystemExit("Install uvicorn to run with `python -m app.main`.") from exc

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
