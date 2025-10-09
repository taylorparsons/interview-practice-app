#!/usr/bin/env bash
set -euo pipefail

# Test runner and optional health check
# Usage:
#   ./test.sh                 # run pytest
#   ./test.sh --health        # run pytest, then quick health check against local server
#   ./test.sh --url http://localhost:8000  # override base URL for health check

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_ROOT"

DO_HEALTH=0
BASE_URL="http://localhost:8000"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --health)
      DO_HEALTH=1; shift ;;
    --url)
      BASE_URL="$2"; shift 2 ;;
    *) echo "Unknown option: $1" >&2; exit 1 ;;
  esac
done

if [[ -d venv ]]; then
  source venv/bin/activate
fi

if ! command -v pytest >/dev/null 2>&1; then
  echo "Installing pytest..."
  pip install pytest >/dev/null
fi

echo "Running tests..."
pytest -q || { echo "Tests failed" >&2; exit 1; }

if [[ "$DO_HEALTH" -eq 1 ]]; then
  echo "Health check: ${BASE_URL}/"
  set +e
  curl -s -o /dev/null -w "%{http_code}\n" "${BASE_URL}/" | grep -E "^(200|302)$" >/dev/null
  STATUS=$?
  set -e
  if [[ $STATUS -ne 0 ]]; then
    echo "Health check failed. Is the server running? Try: ./run_voice.sh" >&2
    exit 1
  fi
  echo "Health check passed."
fi
