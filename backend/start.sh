#!/usr/bin/env bash
set -euo pipefail

# Defaults
: "${PORT:=8080}"
: "${HOST:=0.0.0.0}"
: "${UVICORN_WORKERS:=1}"

KEY_FILE="${WEBUI_SECRET_KEY_FILE:-.webui_secret_key}"

# Optional: install Playwright deps if requested and not provided via WS
if [[ "${WEB_LOADER_ENGINE:-}" == "playwright" && -z "${PLAYWRIGHT_WS_URL:-}" ]]; then
  echo "[start] Installing Playwright browsers (chromium) and deps..."
  if command -v playwright >/dev/null 2>&1; then
    playwright install chromium || true
    playwright install-deps chromium || true
  fi
  python - <<'PY'
import nltk
try:
    nltk.download('punkt_tab')
except Exception:
    pass
PY
fi

# Ensure WEBUI_SECRET_KEY present
if [[ -z "${WEBUI_SECRET_KEY:-}" && -z "${WEBUI_JWT_SECRET_KEY:-}" ]]; then
  echo "[start] Loading WEBUI_SECRET_KEY from file (${KEY_FILE})"
  if [[ ! -f "${KEY_FILE}" ]]; then
    echo "[start] Generating WEBUI_SECRET_KEY"
    # Generate a random 48-character hex string
    head -c 24 /dev/urandom | hexdump -ve '1/1 "%02x"' > "${KEY_FILE}"
  fi
  export WEBUI_SECRET_KEY="$(cat "${KEY_FILE}")"
fi

echo "[start] Starting CryoTensor UI on ${HOST}:${PORT} (workers=${UVICORN_WORKERS})"

exec uvicorn open_webui.main:app \
  --host "${HOST}" \
  --port "${PORT}" \
  --forwarded-allow-ips '*' \
  --workers "${UVICORN_WORKERS}" \
  --ws auto
