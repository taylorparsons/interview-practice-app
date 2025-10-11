#!/usr/bin/env bash
#
# codex_up.sh — One‑stop local bootstrap for the Interview Practice App
#
# Purpose
# - Creates/activates a Python virtual environment
# - Installs Python dependencies from requirements.txt
# - Ensures runtime folders exist (logs/, app/session_store/)
# - Optionally starts the FastAPI dev server or runs tests
#
# Notes
# - Voice features (realtime + previews) require OPENAI_API_KEY. If the key is
#   missing, the server still starts but voice endpoints will return 5xx when
#   invoked. Set OPENAI_API_KEY in .env to enable them.
# - This script intentionally does not fail on a missing API key so it can be
#   used in CI or constrained review environments.
#
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"
RELOAD="${RELOAD:-1}"
REQUESTED_PYVER="${PYVER:-}"       # e.g., export PYVER=3.11 or pass --python 3.11
ACTION="start"                      # default action: start server

usage() {
  cat <<'EOF'
Usage: scripts/codex_up.sh [--python <ver>] [--no-reload] [--start|--tests|--install|--preseed-previews]

Actions (choose one; default: --start):
  --start              Install deps and run the dev server (uvicorn)
  --tests              Install deps and run pytest
  --install            Only create venv and install dependencies
  --preseed-previews   Generate and cache voice preview MP3s (requires OPENAI_API_KEY)

Options:
  --python <ver>       Prefer a specific Python version (e.g., 3.11)
  --no-reload          Run uvicorn without auto-reload
  -h, --help           Show this help and exit

Environment overrides:
  HOST, PORT           Server bind address (default 0.0.0.0:8000)
  RELOAD=0             Disable auto-reload (same as --no-reload)
  PYTHON_BIN=<path>    Use a specific python interpreter
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --start|--tests|--install|--preseed-previews)
      ACTION="${1#--}"
      shift
      ;;
    --python)
      if [[ $# -lt 2 ]]; then echo "--python requires a version (e.g., 3.11)" >&2; exit 1; fi
      REQUESTED_PYVER="$2"; shift 2 ;;
    --no-reload)
      RELOAD=0; shift ;;
    -h|--help)
      usage; exit 0 ;;
    *)
      echo "Unknown option: $1" >&2; usage; exit 1 ;;
  esac
done

# 1) Choose a Python interpreter (prefer <=3.12 to match binary wheels)
declare -a PY_CANDIDATES=()
[[ -n "${PYTHON_BIN:-}" ]] && PY_CANDIDATES+=("$PYTHON_BIN")
[[ -n "$REQUESTED_PYVER" ]] && PY_CANDIDATES+=("python${REQUESTED_PYVER}")
PY_CANDIDATES+=("python3.11" "python3.12" "python3.10" "python3")

PY=""
for c in "${PY_CANDIDATES[@]}"; do
  if command -v "$c" >/dev/null 2>&1; then PY="$c"; break; fi
done
if [[ -z "$PY" ]]; then
  echo "Error: could not find a Python interpreter (tried: ${PY_CANDIDATES[*]})." >&2
  exit 1
fi

# 2) Create/activate venv
if [[ ! -d venv ]]; then
  echo "Creating virtual environment with $PY ..."
  "$PY" -m venv venv
fi
if [[ ! -x venv/bin/python ]]; then
  echo "Error: venv/bin/python is missing. Remove venv/ and re-run." >&2
  exit 1
fi

# shellcheck disable=SC1091
source venv/bin/activate
python -m pip install --upgrade pip >/dev/null

# 3) Install dependencies
if [[ -f requirements.txt ]]; then
  echo "Installing Python dependencies..."
  python -m pip install -r requirements.txt >/dev/null
fi

# 4) Ensure runtime folders and environment file
mkdir -p logs logs/archive app/session_store app/static/voices
if [[ ! -f .env && -f .env.example ]]; then
  cp .env.example .env
  echo "Created .env from .env.example (set OPENAI_API_KEY to enable voice)."
fi

# 5) Action dispatch
case "$ACTION" in
  start)
    echo "Starting FastAPI server (uvicorn) ..."
    [[ -z "${OPENAI_API_KEY:-}" ]] && echo "Warning: OPENAI_API_KEY not set; voice features will be unavailable." >&2
    RELOAD_FLAG=$([[ "$RELOAD" == 0 ]] && echo "" || echo "--reload")
    exec uvicorn app.main:app --host "$HOST" --port "$PORT" $RELOAD_FLAG
    ;;
  tests)
    echo "Running pytest ..."
    exec pytest -q
    ;;
  install)
    echo "Environment ready. Activate with: source venv/bin/activate"
    ;;
  preseed-previews)
    echo "Generating voice previews via scripts/preseed_voice_previews.py ..."
    if [[ -z "${OPENAI_API_KEY:-}" ]]; then
      echo "Error: OPENAI_API_KEY is required to synthesize previews." >&2
      exit 1
    fi
    exec python scripts/preseed_voice_previews.py
    ;;
  *)
    echo "Unknown action: $ACTION" >&2; exit 1 ;;
esac

