"""Pydantic models for request/response payloads."""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


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
