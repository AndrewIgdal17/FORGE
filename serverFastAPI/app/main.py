"""FastAPI application that accepts JSON, delegates to a processor, and returns JSON."""

from __future__ import annotations

import json
from json import JSONDecodeError
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .processor import generate_result
from .ctcc_processor import run_ctcc_calculation

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"
JSON_DIR = BASE_DIR / "json"
INDEX_FILE = STATIC_DIR / "index.html"
FINAL_COMBINED_FILE = JSON_DIR / "final_combined.json"

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


class InputPayload(BaseModel):
    mode: Literal["simple", "bulk"] = "simple"
    message: str = ""
    values: List[float] = Field(default_factory=list)
    combinedData: Optional[Dict[str, Any]] = None


class OutputPayload(BaseModel):
    mode: Literal["simple", "bulk"]
    originalMessage: Optional[str] = None
    characterCount: Optional[int] = None
    valuesProvided: Optional[int] = None
    sum: Optional[float] = None
    average: Optional[float] = None
    entries: Optional[int] = None
    lines: Optional[List[str]] = None
    text: Optional[str] = None


class CTCCInputPayload(BaseModel):
    mode: Literal["calculate"] = "calculate"
    input_mode: Literal["json", "yaml"] = "json"
    output_mode: Literal["json", "csv"] = "json"
    combined_data: Optional[Dict[str, Any]] = None
    scenario_id: Optional[str] = None


class CTCCOutputPayload(BaseModel):
    success: bool
    scenario_id: str
    timestamp: str
    input_mode: str
    output_mode: str
    error: Optional[str] = None
    results: Optional[Dict[str, Any]] = None
    csv_files: Optional[List[str]] = None


@app.get("/", response_class=FileResponse)
async def serve_index() -> FileResponse:
    """Serve the template HTML page."""
    return FileResponse(INDEX_FILE)


@app.get("/api/final_combined", response_class=JSONResponse)
async def get_final_combined() -> JSONResponse:
    """Return the combined JSON payload generated from YAML files."""
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


@app.post("/api/process", response_class=JSONResponse, response_model=OutputPayload)
async def process_payload(payload: InputPayload) -> JSONResponse:
    """Receive JSON payload, invoke processor, and return the generated JSON result."""
    payload_dict = payload.model_dump()
    result = generate_result(payload_dict)
    return JSONResponse(result)


@app.post("/api/ctcc/calculate", response_class=JSONResponse)
async def calculate_ctcc(payload: CTCCInputPayload) -> JSONResponse:
    """
    Run CTCC calculations with JSON input and configurable output.

    Supports dual input modes (json/yaml) and dual output modes (json/csv).
    When output_mode='json', returns calculation results as JSON.
    When output_mode='csv', writes CSV files to local folder and returns file list.
    """
    payload_dict = payload.model_dump()
    result = run_ctcc_calculation(payload_dict)
    return JSONResponse(result)


if __name__ == "__main__":
    try:
        import uvicorn
    except ModuleNotFoundError as exc:  # pragma: no cover - convenience only
        raise SystemExit("Install uvicorn to run with `python -m app.main`.") from exc

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
