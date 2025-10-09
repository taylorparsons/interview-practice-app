#!/usr/bin/env bash
set -euo pipefail

# Simple setup-and-run script for the Interview Practice App
# Usage:
#   ./run.sh                # default: create venv (if missing), install, run with reload
#   ./run.sh --no-reload    # run without auto-reload
#   ./run.sh --python 3.11  # prefer a specific python version (3.11 default)

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_ROOT"

PYVER="3.11"
RELOAD=1
while [[ $# -gt 0 ]]; do
  case "$1" in
    --no-reload)
      RELOAD=0
      shift
      ;;
    --python)
      PYVER="$2"; shift 2
      ;;
    *)
      echo "Unknown option: $1" >&2; exit 1;
      ;;
  esac
done

PYTHON_BIN="python${PYVER}"
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "python${PYVER} not found. Falling back to python3 if available..."
  if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
  else
    echo "No suitable Python found. Please install Python ${PYVER}." >&2
    exit 1
  fi
fi

# Create venv if missing
if [[ ! -d "venv" ]]; then
  echo "Creating virtual environment with ${PYTHON_BIN}..."
  "$PYTHON_BIN" -m venv venv
fi

# Activate venv
source venv/bin/activate

echo "Upgrading pip..."
python -m pip install --upgrade pip

echo "Installing project requirements..."
pip install -r requirements.txt

# Check .env presence
if [[ ! -f .env ]]; then
  cat <<EOF
Note: .env not found at $PROJECT_ROOT/.env
Create one if you need AI features:
  OPENAI_API_KEY=your_key_here
EOF
fi

HOST="0.0.0.0"
PORT="8000"
RELOAD_FLAG="--reload"
[[ "$RELOAD" -eq 0 ]] && RELOAD_FLAG=""

echo "Starting server: http://${HOST}:${PORT}"
exec uvicorn app.main:app --host "$HOST" --port "$PORT" $RELOAD_FLAG
