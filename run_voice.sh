#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_ROOT"

# Load environment configuration early so we can validate voice settings.
set -a
if [[ -f .env ]]; then
  # shellcheck disable=SC1091
  source .env
fi
set +a

if [[ -z "${OPENAI_API_KEY:-}" ]]; then
  cat <<'EOF' >&2
Error: OPENAI_API_KEY is not set.
Add it to .env or export it in your shell before running run_voice.sh.
EOF
  exit 1
fi

# Ensure the realtime voice defaults exist when not provided via the environment.
export OPENAI_REALTIME_MODEL="${OPENAI_REALTIME_MODEL:-gpt-realtime-mini-2025-10-06}"
export OPENAI_REALTIME_VOICE="${OPENAI_REALTIME_VOICE:-verse}"
export OPENAI_REALTIME_URL="${OPENAI_REALTIME_URL:-https://api.openai.com/v1/realtime}"

# Select a Python interpreter that is known to satisfy binary wheel availability.
declare -a PYTHON_CANDIDATES=()
if [[ -n "${PYTHON_BIN:-}" ]]; then
  PYTHON_CANDIDATES+=("$PYTHON_BIN")
fi
PYTHON_CANDIDATES+=("python3.11" "python3.12" "python3.10" "python3")

PYTHON_BIN=""
for candidate in "${PYTHON_CANDIDATES[@]}"; do
  if command -v "$candidate" >/dev/null 2>&1; then
    version=$("$candidate" -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    major=${version%%.*}
    minor=${version#*.}
    if [[ "$major" -eq 3 && "$minor" -lt 13 ]]; then
      PYTHON_BIN="$candidate"
      break
    fi
  fi
done

if [[ -z "$PYTHON_BIN" ]]; then
  cat <<'EOF' >&2
Error: Could not find a supported Python interpreter (<3.13).
Install Python 3.11 or 3.12 and re-run, or set PYTHON_BIN to a compatible executable.
EOF
  exit 1
fi

# Create a virtual environment when missing.
if [[ ! -d venv ]]; then
  echo "Creating virtual environment with ${PYTHON_BIN}..."
  "$PYTHON_BIN" -m venv venv
fi

if [[ ! -x venv/bin/python ]]; then
  echo "Error: venv/bin/python is missing. Remove venv/ and re-run the script." >&2
  exit 1
fi

VENV_VERSION=$(venv/bin/python -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
VENV_MAJOR=${VENV_VERSION%%.*}
VENV_MINOR=${VENV_VERSION#*.}
if [[ "$VENV_MAJOR" -eq 3 && "$VENV_MINOR" -ge 13 ]]; then
  cat <<'EOF' >&2
Error: Existing virtual environment uses Python 3.13+, which is not yet supported by scikit-learn.
Remove the venv/ directory (rm -rf venv) and rerun this script to build with Python 3.11 or 3.12.
EOF
  exit 1
fi

# Activate the environment and refresh dependencies (idempotent when already installed).
# shellcheck disable=SC1091
source venv/bin/activate

echo "Ensuring pip is up to date..."
python -m pip install --upgrade pip >/dev/null

if [[ -f requirements.txt ]]; then
  echo "Installing project requirements..."
  python -m pip install -r requirements.txt >/dev/null
fi

HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"
RELOAD_FLAG="--reload"

if [[ "${RELOAD:-1}" == "0" ]]; then
  RELOAD_FLAG=""
fi

LOG_DIR="$PROJECT_ROOT/logs"
ARCHIVE_DIR="$LOG_DIR/archive"
mkdir -p "$LOG_DIR" "$ARCHIVE_DIR"

SUPERVISOR_LOG="$LOG_DIR/uvicorn-supervisor.log"
if [[ -s "$SUPERVISOR_LOG" ]]; then
  TS=$(date +"%Y-%m-%d_%H-%M-%S")
  mv "$SUPERVISOR_LOG" "$ARCHIVE_DIR/${TS}_uvicorn-supervisor.log"
fi

echo "Launching Interview Practice App with realtime voice support:"
echo "  http://${HOST}:${PORT} (open via http://localhost:${PORT} for microphone access)"
echo "  Model: ${OPENAI_REALTIME_MODEL}"
echo "  Voice: ${OPENAI_REALTIME_VOICE}"
echo "Logs:    logs/app.log (app+uvicorn), logs/access.log (HTTP access)"
echo "Archive: logs/archive/<YYYY-MM-DD_HH-MM-SS>/ (rotated on each start)"
echo "Supervisor log (stdout/stderr): logs/uvicorn-supervisor.log"

set +e
uvicorn app.main:app --host "$HOST" --port "$PORT" $RELOAD_FLAG 2>&1 | tee "$SUPERVISOR_LOG"
exit_code=${PIPESTATUS[0]}
exit $exit_code
