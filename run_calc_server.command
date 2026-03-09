#!/bin/bash
# Launch FastAPI server, ensure dependencies are installed, and report public URL.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SERVER_DIR="$SCRIPT_DIR/server"
CODE_ROOT="$SCRIPT_DIR"
VENV_DIR="$CODE_ROOT/venv"
REQUIREMENTS="$CODE_ROOT/requirements.txt"

PORT="${PORT:-8000}"
HOST="${HOST:-127.0.0.1}"

LOG_DIR="$SERVER_DIR/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/fastapi_$(date +%Y%m%d_%H%M%S).log"

PYTHON_BIN="${PYTHON_BIN:-python3}"
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  if command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
  else
    echo "Python interpreter not found. Install Python 3 or export PYTHON_BIN." >&2
    exit 1
  fi
fi

if [[ ! -d "$VENV_DIR" ]]; then
  echo "Creating virtual environment at $VENV_DIR"
  "$PYTHON_BIN" -m venv "$VENV_DIR"
else
  if ! "$VENV_DIR/bin/python" --version >/dev/null 2>&1; then
    echo "Existing virtual environment is broken, recreating..."
    rm -rf "$VENV_DIR"
    "$PYTHON_BIN" -m venv "$VENV_DIR"
  fi
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
VENV_PYTHON="$(command -v python)"

if [[ -z "$VENV_PYTHON" ]] || ! "$VENV_PYTHON" --version >/dev/null 2>&1; then
  echo "Virtual environment activation failed. Recreating..."
  deactivate 2>/dev/null || true
  rm -rf "$VENV_DIR"
  "$PYTHON_BIN" -m venv "$VENV_DIR"
  source "$VENV_DIR/bin/activate"
  VENV_PYTHON="$(command -v python)"
  if [[ -z "$VENV_PYTHON" ]]; then
    echo "Failed to create working virtual environment" >&2
    exit 1
  fi
fi

if [[ -f "$REQUIREMENTS" ]]; then
  echo "Installing/updating dependencies..."
  "$VENV_PYTHON" -m pip install --upgrade pip >/dev/null 2>&1 || true
  "$VENV_PYTHON" -m pip install -r "$REQUIREMENTS"
else
  echo "requirements.txt not found at $REQUIREMENTS; skipping dependency installation."
fi

if ! "$VENV_PYTHON" -c "import uvicorn" >/dev/null 2>&1; then
  echo "uvicorn is unavailable even after installation. Verify requirements.txt includes uvicorn." >&2
  exit 1
fi

LOCAL_IP=""
for iface in en0 en1; do
  if ip_address=$(ipconfig getifaddr "$iface" 2>/dev/null); then
    LOCAL_IP="$ip_address"
    break
  fi
done
if [[ -z "$LOCAL_IP" ]]; then
  LOCAL_IP="$("$VENV_PYTHON" - <<'PY'
import socket
ip = "127.0.0.1"
try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        ip = sock.getsockname()[0]
    finally:
        sock.close()
except OSError:
    pass
print(ip)
PY
)"
fi

LOCAL_IP="$(printf '%s' "${LOCAL_IP:-}" | tr -d '[:space:]')"

PUBLIC_IP=""
if command -v curl >/dev/null 2>&1; then
  PUBLIC_IP="$(curl -fs https://api.ipify.org 2>/dev/null || curl -fs https://ifconfig.me 2>/dev/null || true)"
fi
if [[ -z "$PUBLIC_IP" ]] && command -v dig >/dev/null 2>&1; then
  PUBLIC_IP="$(dig +short myip.opendns.com @resolver1.opendns.com 2>/dev/null || true)"
fi
if [[ -z "$PUBLIC_IP" ]]; then
  PUBLIC_IP="$("$VENV_PYTHON" - <<'PY'
import urllib.request
for url in ("https://api.ipify.org", "https://ifconfig.me/ip"):
    try:
        with urllib.request.urlopen(url, timeout=2) as response:
            data = response.read().decode().strip()
            if data:
                print(data)
                break
    except Exception:
        pass
else:
    print("")
PY
)"
fi

PUBLIC_IP="$(printf '%s' "${PUBLIC_IP:-}" | tr -d '[:space:]')"

PUBLIC_ADDRESS="http://${PUBLIC_IP:-unavailable}:$PORT"
LAN_ADDRESS="http://${LOCAL_IP:-127.0.0.1}:$PORT"
LOCAL_ADDRESS="http://127.0.0.1:$PORT"

# Print large title
cat << 'EOF'
  ____ _____ ____ ____      _    ____ ___   ____  _____ ______     _______ ____
 / ___|_   _/ ___/ ___|    / \  |  _ \_ _| / ___|| ____|  _ \ \   / | ____|  _ \
| |     | || |  | |       / _ \ | |_) | |  \___ \|  _| | |_) \ \ / /|  _| | |_) |
| |___  | || |__| |___   / ___ \|  __/| |   ___) | |___|  _ < \ V / | |___|  _ <
 \____| |_| \____\____| /_/   \_|_|  |___| |____/|_____|_| \_\ \_/  |_____|_| \_\

 _____ _    ____ _____  _    ____ ___   ____  _____ ______     _______ ____
|  ___/ \  / ___|_   _|/ \  |  _ \_ _| / ___|| ____|  _ \ \   / | ____|  _ \
| |_ / _ \ \___ \ | | / _ \ | |_) | |  \___ \|  _| | |_) \ \ / /|  _| | |_) |
|  _/ ___ \ ___) || |/ ___ \|  __/| |   ___) | |___|  _ < \ V / | |___|  _ <
|_|/_/   \_|____/ |_/_/   \_|_|  |___| |____/|_____|_| \_\ \_/  |_____|_| \_\

EOF

echo "Starting FastAPI server..."
echo "Logging requests to $LOG_FILE"
echo "Accessible URLs:"
if [[ -n "$PUBLIC_IP" ]]; then
  echo "  Public : $PUBLIC_ADDRESS"
else
  echo "  Public : unavailable (check WAN connectivity or allowlist)"
fi
echo "  LAN    : $LAN_ADDRESS"
echo "  Local  : $LOCAL_ADDRESS"
echo "Press Ctrl+C to stop the server."
echo

# Open browser after a short delay
(sleep 2 && open "$LOCAL_ADDRESS") &

# Run uvicorn from server directory so app.main:app resolves
cd "$SERVER_DIR"
"$VENV_PYTHON" -m uvicorn app.main:app --host "$HOST" --port "$PORT" --reload --access-log 2>&1 | tee -a "$LOG_FILE"
