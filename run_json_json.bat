@echo off
REM Run CTCC in JSON input -> JSON output mode (full JSON mode)

setlocal enabledelayedexpansion

cd /d "%~dp0"

REM Determine Python binary
set PYTHON_BIN=python
where python >nul 2>&1
if errorlevel 1 (
    set PYTHON_BIN=python3
    where python3 >nul 2>&1
    if errorlevel 1 (
        echo Python interpreter not found. Install Python 3 or add to PATH.
        exit /b 1
    )
)

REM Create virtual environment if it doesn't exist
if not exist "venv\" (
    echo Creating virtual environment at venv
    %PYTHON_BIN% -m venv venv
    if errorlevel 1 (
        echo Failed to create virtual environment
        exit /b 1
    )
)

REM Activate virtual environment
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo Failed to activate virtual environment
    exit /b 1
)

REM Install/update dependencies
if exist "requirements.txt" (
    echo Installing/updating dependencies...
    python -m pip install --upgrade pip >nul 2>&1
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo Failed to install dependencies
        exit /b 1
    )
) else (
    echo requirements.txt not found; skipping dependency installation.
)

echo.
echo Starting CTCC: JSON -^> JSON mode...
echo.

REM Run ctcc.py with JSON input and JSON output flags
python ctcc.py -j -o

echo.
echo CTCC execution complete.
echo Input: combined_data.json (auto-generated from YAML)
echo Output: outputs\ctcc_results_[scenario_id].json

endlocal
