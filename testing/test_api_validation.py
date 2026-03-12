#!/usr/bin/env python3
"""
Pydantic API validation tests: invalid or partial payloads must return 422.

Run from code/server: python -c \"import sys; sys.path.insert(0, '..'); exec(open('../testing/test_api_validation.py').read())\"
Or from code/: venv/bin/python -m pytest testing/test_api_validation.py -v (if pytest installed)
Or from code/server: python -c \"from pathlib import Path; import sys; sys.path.insert(0, str(Path('..').resolve())); from testing.test_api_validation import *; test_process_invalid_mode(); test_ctcc_calculate_invalid_mode(); test_ctcc_calculate_invalid_input_mode(); print('OK')\"
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure server app is importable (repo_root = code/, server_dir = code/server)
repo_root = Path(__file__).resolve().parent.parent
server_dir = repo_root / "server"
for d in (repo_root, server_dir):
    if str(d) not in sys.path:
        sys.path.insert(0, str(d))

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_process_invalid_mode():
    """POST /api/process with invalid 'mode' should return 422."""
    r = client.post("/api/process", json={"mode": "invalid_mode"})
    assert r.status_code == 422


def test_process_values_not_list():
    """POST /api/process with values as string instead of list should be coerced or 422."""
    r = client.post("/api/process", json={"mode": "simple", "values": "not a list"})
    # InputPayload has field_validator that coerces; if values is not a list it becomes []
    assert r.status_code in (200, 422)


def test_ctcc_calculate_invalid_mode():
    """POST /api/ctcc/calculate with wrong top-level 'mode' should return 422."""
    r = client.post("/api/ctcc/calculate", json={"mode": "wrong"})
    assert r.status_code == 422


def test_ctcc_calculate_invalid_input_mode():
    """POST /api/ctcc/calculate with input_mode not in ['json','yaml'] should return 422."""
    r = client.post(
        "/api/ctcc/calculate",
        json={
            "mode": "calculate",
            "input_mode": "xml",
            "output_mode": "json",
        },
    )
    assert r.status_code == 422


def test_ctcc_calculate_partial_ok():
    """POST /api/ctcc/calculate with minimal valid payload can return 200 or 500 (server may fail on missing data)."""
    r = client.post(
        "/api/ctcc/calculate",
        json={
            "mode": "calculate",
            "input_mode": "yaml",
            "output_mode": "json",
        },
    )
    # Validation passes; server may return 200 or 500 depending on env/files
    assert r.status_code in (200, 500), r.text


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
