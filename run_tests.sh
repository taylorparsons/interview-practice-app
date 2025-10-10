#!/usr/bin/env bash
set -euo pipefail

if [ ! -d "venv" ]; then
  python3.11 -m venv venv
fi

source venv/bin/activate
pip install -r requirements.txt

echo "Running pytest with verbose output..."
pytest -vv --maxfail=1 --durations=5
