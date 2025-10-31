#!/bin/bash
# Serve the static HTML page and report the reachable public URL.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
STATIC_DIR="$SCRIPT_DIR/static"

if [[ ! -d "$STATIC_DIR" ]]; then
  echo "Static directory not found at $STATIC_DIR" >&2
  exit 1
fi

cd "$STATIC_DIR"

PORT="${STATIC_PORT:-5500}"

LOG_DIR="$SCRIPT_DIR/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/static_server_$(date +%Y%m%d_%H%M%S).log"

PYTHON_BIN="${PYTHON_BIN:-python3}"
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  if command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
  else
    echo "Python interpreter not found. Install Python 3 or set PYTHON_BIN." >&2
    exit 1
  fi
fi

LOCAL_IP=""
for iface in en0 en1; do
  if ip_address=$(ipconfig getifaddr "$iface" 2>/dev/null); then
    LOCAL_IP="$ip_address"
    break
  fi
done
if [[ -z "$LOCAL_IP" ]]; then
  LOCAL_IP=$("$PYTHON_BIN" - <<'PY'
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
  )
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
  PUBLIC_IP=$("$PYTHON_BIN" - <<'PY'
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
  )
fi

PUBLIC_IP="$(printf '%s' "${PUBLIC_IP:-}" | tr -d '[:space:]')"

PUBLIC_ADDRESS="http://${PUBLIC_IP:-unavailable}:$PORT/index.html"
LAN_ADDRESS="http://${LOCAL_IP:-127.0.0.1}:$PORT/index.html"

# Print large title
cat << 'EOF'
 _____ _     _         _         _   _            
|_   _| |__ (_)___    (_)___    | |_| |__   ___   
  | | | '_ \| / __|   | / __|   | __| '_ \ / _ \  
  | | | | | | \__ \   | \__ \   | |_| | | |  __/  
  |_| |_| |_|_|___/   |_|___/    \__|_| |_|\___|  
                                                  
 __        _____   ____    _   _ ___   ____  _____ ____  _     _ _____ ____  
 \ \      / | ___ | __ )  | | | |_ _| / ___|| ____|  _ \| |      / | ____|  _ \ 
  \ \ /\ / /|  _| |  _ \  | | | || |  \___ \|  _| | |_) |  \    /  |  _| | |_) |
   \ V  V / | |___| |_) | | |_| || |   ___) | |___|  _ <|   \  /   | |___|  _ < 
    \_/\_/  |_____|____/   \___/|___| |____/|_____|_| \_\    \/    |_____|_| \_\
                                                                             
EOF

echo "Serving static files from $STATIC_DIR"
echo "Logging to $LOG_FILE"
echo "Accessible URLs:"
if [[ -n "$PUBLIC_IP" ]]; then
  echo "  Public : $PUBLIC_ADDRESS"
else
  echo "  Public : unavailable (check WAN connectivity or allowlist)"
fi
echo "  LAN    : $LAN_ADDRESS"
echo "  Local  : http://127.0.0.1:$PORT/index.html"
echo "Press Ctrl+C to stop the server."
echo

"$PYTHON_BIN" -m http.server "$PORT" --bind 0.0.0.0 2>&1 | tee -a "$LOG_FILE"
