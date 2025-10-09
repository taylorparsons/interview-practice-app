# Repository Guidelines

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
