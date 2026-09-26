#!/bin/bash
# Launch FastAPI server, ensure dependencies are installed, and report public URL.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SERVER_DIR="$SCRIPT_DIR/server"
CODE_ROOT="$SCRIPT_DIR"
VENV_DIR="$CODE_ROOT/.venv"

PORT="${PORT:-8000}"
HOST="${HOST:-127.0.0.1}"

LOG_DIR="$SERVER_DIR/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/fastapi_$(date +%Y%m%d_%H%M%S).log"

if ! command -v uv >/dev/null 2>&1; then
  echo "uv not found. Install: curl -LsSf https://astral.sh/uv/install.sh | sh" >&2
  exit 1
fi
cd "$CODE_ROOT"
uv sync --quiet
VENV_PYTHON="$CODE_ROOT/.venv/bin/python"

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

_public_ip_file=$(mktemp)
(curl -fs --connect-timeout 2 https://api.ipify.org 2>/dev/null || true) > "$_public_ip_file" &
_public_ip_pid=$!

LAN_ADDRESS="http://${LOCAL_IP:-127.0.0.1}:$PORT"
LOCAL_ADDRESS="http://127.0.0.1:$PORT"

# Print large title
cat << 'EOF'
  _____ ___  ____   ____ _____      _    ____ ___   ____  _____ ______     _______ ____
 |  ___/ _ \|  _ \ / ___| ____|    / \  |  _ \_ _| / ___|| ____|  _ \ \   / | ____|  _ \
 | |_ | | | | |_) | |  _|  _|     / _ \ | |_) | |  \___ \|  _| | |_) \ \ / /|  _| | |_) |
 |  _|| |_| |  _ <| |_| | |___   / ___ \|  __/| |   ___) | |___|  _ < \ V / | |___|  _ <
 |_|   \___/|_| \_\\____|_____| /_/   \_|_|  |___| |____/|_____|_| \_\ \_/  |_____|_| \_\

 _____ _    ____ _____  _    ____ ___   ____  _____ ______     _______ ____
|  ___/ \  / ___|_   _|/ \  |  _ \_ _| / ___|| ____|  _ \ \   / | ____|  _ \
| |_ / _ \ \___ \ | | / _ \ | |_) | |  \___ \|  _| | |_) \ \ / /|  _| | |_) |
|  _/ ___ \ ___) || |/ ___ \|  __/| |   ___) | |___|  _ < \ V / | |___|  _ <
|_|/_/   \_|____/ |_/_/   \_|_|  |___| |____/|_____|_| \_\ \_/  |_____|_| \_\

EOF

wait "$_public_ip_pid" 2>/dev/null || true
PUBLIC_IP="$(cat "$_public_ip_file" | tr -d '[:space:]')"
rm -f "$_public_ip_file"
PUBLIC_ADDRESS="http://${PUBLIC_IP:-unavailable}:$PORT"

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
