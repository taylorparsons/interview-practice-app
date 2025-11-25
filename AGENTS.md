# Repository Guidelines
## Superpowers System

<EXTREMELY_IMPORTANT>
You have superpowers. Superpowers teach you new skills and capabilities. RIGHT NOW run: `~/.codex/superpowers/.codex/superpowers-codex bootstrap` and follow the instructions it returns.
</EXTREMELY_IMPORTANT>
## Project Structure & Module Organization
- `app/main.py`: FastAPI entrypoint, routes, and session logic.
- `app/templates/`: Jinja2 templates (UI). Entry: `index.html`.
- `app/static/`: Front-end assets (`css/`, `js/`).
- `app/models/`: Core app logic (e.g., `interview_agent.py`).
- `app/utils/`: Helpers for uploads and document processing.
- `app/uploads/`: Temporary uploaded files (ignored from VCS).
- `requirements.txt`: Python dependencies.

## Build, Test, and Development Commands
- Create venv: `python3.11 -m venv venv && source venv/bin/activate`
- Install deps: `pip install -r requirements.txt && pip install fastapi uvicorn python-multipart jinja2`
- Run dev server: `uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`
- Open API docs: visit `http://localhost:8000/docs`

## Coding Style & Naming Conventions
- Python: PEP 8, 4-space indentation, type hints where practical.
- Naming: modules `snake_case.py`, classes `CamelCase`, functions/vars `snake_case`.
- Routes: RESTful nouns/verbs; prefer JSON models via Pydantic.
- Templates/Static: keep component-specific assets grouped and named consistently.

## Testing Guidelines
- Framework: `pytest` (add if not installed: `pip install pytest`).
- Test layout: mirror `app/` structure under `tests/`.
- Naming: files `test_*.py`; functions `test_*`.
- Run tests: `pytest -q` (use `-k <pattern>` to filter).

### Policy: MVP Features Require Tests
- For every MVP feature added or changed, add at least one automated test that exercises the expected behavior and acceptance criteria.
- Favor API-level tests (FastAPI TestClient) that simulate realistic usage and avoid external network calls by stubbing clients where needed.
- Extend existing suites rather than creating ad-hoc scripts; keep tests fast and deterministic.
- Use `-k` filters for focused iteration and ensure the full suite passes before merging to `main`.

## Commit & Pull Request Guidelines
- Commits: concise, imperative subject (≤72 chars). Example: `feat: add question generation endpoint`.
- Include rationale and scope in body when needed; group related changes.
- PRs: clear description, screenshots of UI changes, steps to reproduce/test, and linked issues.
- Keep PRs focused and small; add checklist items (lint/test pass).

## Security & Configuration Tips
- Create `.env` in repo root. Required: `OPENAI_API_KEY=...`.
- Optional realtime overrides: `OPENAI_REALTIME_MODEL`, `OPENAI_REALTIME_VOICE`, `OPENAI_REALTIME_URL`.
- Never commit secrets or files under `app/uploads/`.

## Architecture Overview
- FastAPI server renders `index.html` and serves static assets.
- Session data tracks uploads, questions, and evaluations in-memory.
- `InterviewPracticeAgent` encapsulates AI interactions; endpoints fall back to heuristics if unavailable.

## Local Logging
- Files: `logs/app.log` (app + uvicorn/error) and `logs/access.log` (HTTP access).
- Rotation on startup: existing non-empty logs are archived under
  `logs/archive/YYYY-MM-DD_HH-MM-SS/` automatically.
- Console: logs also stream to stdout/stderr as before.
- Verbosity: set env vars before starting the app:
  - `APP_LOG_LEVEL` (default `INFO`)
  - `UVICORN_LOG_LEVEL` (default inherits APP_LOG_LEVEL)
  - `UVICORN_ACCESS_LOG_LEVEL` (default `INFO`)
- Format: set `APP_LOG_FORMAT=json` for structured JSON logs (default is text).
- Context: each record includes `request_id` and, when present, `session_id`.
- Headers: every response includes `X-Request-ID` for correlation.
- Request lifecycle: middleware logs `request.start`, `request.end`, and `request.error` with
  method, path, status, duration_ms, client IP, and user-agent (no bodies logged).
- Agent retries: example/evaluation endpoints attempt the agent twice before fallback.
  Look for `example.agent path … attempt=1/2`, `example.retry.start`, `evaluation.retry.start`,
  and `evaluation.agent path … attempt=1/2` to confirm the retry flow.
- Agent initialization logs now include the session id:
  `session=<id> Initialized Interview Agent with OpenAI model: …`.
- Supervisor process (uvicorn reload/parent) stdout/stderr is captured in `logs/uvicorn-supervisor.log`
  (rotated to `logs/archive/<timestamp>_uvicorn-supervisor.log`). Use this when diagnosing errors
  that appear in the terminal but not in `app.log`.

Notes
- Using `uvicorn --reload` restarts the app on file changes; each restart will archive
  non-empty log files into a new timestamped folder.
- To capture everything in one place while developing:
  - `tail -f logs/app.log logs/access.log`
