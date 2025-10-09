#!/usr/bin/env bash
set -euo pipefail

# Kill any running instance of the Interview Practice App (uvicorn app.main:app).

PIDS=$(pgrep -f "uvicorn app.main:app" || true)

if [[ -z "${PIDS}" ]]; then
  echo "No running uvicorn app.main:app process found."
  exit 0
fi

echo "Stopping uvicorn processes: ${PIDS}"
kill ${PIDS}

# Give processes a moment to terminate gracefully
sleep 1

# Force kill if any remain
if pgrep -f "uvicorn app.main:app" >/dev/null; then
  echo "Processes still running; forcing termination."
  pkill -9 -f "uvicorn app.main:app"
else
  echo "All uvicorn processes stopped."
fi

