#!/bin/bash
# Launch FastAPI server, ensure dependencies are installed, and report public URL.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

PORT="${PORT:-8000}"
HOST="${HOST:-0.0.0.0}"

LOG_DIR="$SCRIPT_DIR/logs"
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

if [[ ! -d ".venv" ]]; then
  echo "Creating virtual environment at .venv"
  "$PYTHON_BIN" -m venv .venv
fi

# shellcheck disable=SC1091
source ".venv/bin/activate"
VENV_PYTHON="$(command -v python)"

if [[ -z "$VENV_PYTHON" ]]; then
  echo "Failed to locate python inside .venv" >&2
  exit 1
fi

if [[ -f "requirements.txt" ]]; then
  echo "Installing/updating dependencies..."
  "$VENV_PYTHON" -m pip install --upgrade pip >/dev/null 2>&1 || true
  "$VENV_PYTHON" -m pip install -r requirements.txt
else
  echo "requirements.txt not found; skipping dependency installation."
fi

if ! command -v uvicorn >/dev/null 2>&1; then
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
echo "  Local  : http://127.0.0.1:$PORT"
echo "Press Ctrl+C to stop the server."
echo

uvicorn app.main:app --host "$HOST" --port "$PORT" --reload --access-log 2>&1 | tee -a "$LOG_FILE"
