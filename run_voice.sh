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

# Create a virtual environment when missing.
if [[ ! -d venv ]]; then
  echo "Creating virtual environment..."
  python3 -m venv venv
fi

# Activate the environment and refresh dependencies (idempotent when already installed).
# shellcheck disable=SC1091
source venv/bin/activate

if [[ -f requirements.txt ]]; then
  echo "Installing project requirements..."
  pip install -r requirements.txt >/dev/null
fi

HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"
RELOAD_FLAG="--reload"

if [[ "${RELOAD:-1}" == "0" ]]; then
  RELOAD_FLAG=""
fi

echo "Launching Interview Practice App with realtime voice support:"
echo "  http://${HOST}:${PORT} (open via http://localhost:${PORT} for microphone access)"
echo "  Model: ${OPENAI_REALTIME_MODEL}"
echo "  Voice: ${OPENAI_REALTIME_VOICE}"

exec uvicorn app.main:app --host "$HOST" --port "$PORT" $RELOAD_FLAG
