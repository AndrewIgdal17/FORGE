@echo off
REM Launch FastAPI server, ensure dependencies are installed, and report public URL.

setlocal enabledelayedexpansion

cd /d "%~dp0"

set PORT=8000
if not "%PORT%"=="" set PORT=%PORT%
set HOST=0.0.0.0
if not "%HOST%"=="" set HOST=%HOST%

REM Create logs directory
if not exist "logs\" mkdir logs
set LOG_FILE=logs\fastapi_%date:~-4,4%%date:~-10,2%%date:~-7,2%_%time:~0,2%%time:~3,2%%time:~6,2%.log
set LOG_FILE=%LOG_FILE: =0%

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
if not exist ".venv\" (
    echo Creating virtual environment at .venv
    %PYTHON_BIN% -m venv .venv
    if errorlevel 1 (
        echo Failed to create virtual environment
        exit /b 1
    )
)

REM Activate virtual environment
call .venv\Scripts\activate.bat
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

REM Check if uvicorn is available
where uvicorn >nul 2>&1
if errorlevel 1 (
    echo uvicorn is unavailable even after installation. Verify requirements.txt includes uvicorn.
    exit /b 1
)

REM Get local IP address
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4 Address"') do (
    set LOCAL_IP=%%a
    goto :got_local_ip
)
:got_local_ip
set LOCAL_IP=%LOCAL_IP: =%

REM Try to get public IP
set PUBLIC_IP=
for /f "delims=" %%a in ('curl -fs https://api.ipify.org 2^>nul') do set PUBLIC_IP=%%a
if "%PUBLIC_IP%"=="" (
    for /f "delims=" %%a in ('curl -fs https://ifconfig.me 2^>nul') do set PUBLIC_IP=%%a
)

set PUBLIC_ADDRESS=http://%PUBLIC_IP%:%PORT%
if "%PUBLIC_IP%"=="" set PUBLIC_ADDRESS=unavailable
set LAN_ADDRESS=http://%LOCAL_IP%:%PORT%
if "%LOCAL_IP%"=="" set LAN_ADDRESS=http://127.0.0.1:%PORT%

REM Print large title
echo   ____ _____ ____ ____      _    ____ ___   ____  _____ ______     _______ ____
echo  / ___^|_   _/ ___/ ___^|    / \  ^|  _ \_ _^| / ___^|^| ____^|  _ \ \   / ^| ____^|  _ \
echo ^| ^|     ^| ^|^| ^|  ^| ^|       / _ \ ^| ^|_) ^| ^|  \___ \^|  _^| ^| ^|_) \ \ / /^|  _^| ^| ^|_) ^|
echo ^| ^|___  ^| ^|^| ^|__^| ^|___   / ___ \^|  __/^| ^|   ___) ^| ^|___^|  _ ^< \ V / ^| ^|___^|  _ ^<
echo  \____^| ^|_^| \____\____^| /_/   \_^|_^|  ^|___^| ^|____/^|_____^|_^| \_\ \_/  ^|_____^|_^| \_\
echo.
echo  _____ _    ____ _____  _    ____ ___   ____  _____ ______     _______ ____
echo ^|  ___/ \  / ___^|_   _^|/ \  ^|  _ \_ _^| / ___^|^| ____^|  _ \ \   / ^| ____^|  _ \
echo ^| ^|_ / _ \ \___ \ ^| ^| / _ \ ^| ^|_) ^| ^|  \___ \^|  _^| ^| ^|_) \ \ / /^|  _^| ^| ^|_) ^|
echo ^|  _/ ___ \ ___) ^|^| ^|/ ___ \^|  __/^| ^|   ___) ^| ^|___^|  _ ^< \ V / ^| ^|___^|  _ ^<
echo ^|_^|/_/   \_^|____/ ^|_/_/   \_^|_^|  ^|___^| ^|____/^|_____^|_^| \_\ \_/  ^|_____^|_^| \_\
echo.

echo Starting FastAPI server...
echo Logging requests to %LOG_FILE%
echo Accessible URLs:
if not "%PUBLIC_IP%"=="" (
    echo   Public : %PUBLIC_ADDRESS%
) else (
    echo   Public : unavailable (check WAN connectivity or allowlist^)
)
echo   LAN    : %LAN_ADDRESS%
echo   Local  : http://127.0.0.1:%PORT%
echo Press Ctrl+C to stop the server.
echo.

REM Start uvicorn server
uvicorn app.main:app --host %HOST% --port %PORT% --reload --access-log 2>&1 | tee -a "%LOG_FILE%"

endlocal
