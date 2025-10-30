# Testing Guide

## Overview
The project currently includes two testing entry points:
- Python unit/integration tests executed via `pytest` (run with `./test.sh` or `pytest` directly once suites are added).
- Browser-based “user tests” powered by Helium/Selenium that validate critical UI flows.

Both suites expect the FastAPI application dependencies installed from `requirements.txt`. The Helium user tests require additional packages from `requirements-dev.txt`.

## Prerequisites
1. Create and activate the virtual environment (see `README.md`).
2. Install core dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Install UI testing dependencies:
   ```bash
   pip install -r requirements-dev.txt
   ```
4. Launch the FastAPI server in another terminal:
   ```bash
   ./run.sh
   # or
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```
   Adjust `UI_BASE_URL` if the app runs on a different origin.

## Running FastAPI Test Suite
```bash
./test.sh
```
This script executes `pytest -q`. You can pass extra flags by editing the script or running `pytest` directly.

## Running Helium User Tests
```bash
./run_usertests.sh
```
The script installs UI dependencies from `requirements-dev.txt` (if needed) and runs `pytest tests/ui --maxfail=1 --disable-warnings --tb=short`. Results are streamed to the terminal, logged to `tests/ui/__artifacts__/usertests.pytest.log`, and summarized in `tests/ui/__artifacts__/usertests_report.md`.

### Environment Variables
- `UI_BASE_URL`: override the target app URL (default `http://localhost:8000`).
- `HEADFUL_UI_TESTS`: set to `1` or `true` to launch a visible Chrome window instead of headless mode.

### Artifacts
Each run stores per-test flow screenshots in timestamped folders under `tests/ui/__artifacts__/`, alongside HTML dumps on failure. Clean up this directory between runs if necessary.
