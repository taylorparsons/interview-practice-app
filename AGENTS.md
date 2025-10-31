---
name: interview-practice-agent
description: FastAPI-based interview rehearsal assistant with realtime voice coaching.
---

# Interview Practice Agent Playbook

Use this playbook when operating or extending the interview-practice application in this repository. It blends the reusable refactoring guidance from the shared skill library with the architecture that powers the FastAPI app, async coaching flows, and realtime voice sessions.

## Mission
- Deliver realistic interview rehearsal experiences across web UI, asynchronous text feedback, and realtime voice coaching.
- Keep agent prompts, state management, and knowledge retrieval well-structured for rapid iteration.
- Ensure refactors remain deliberate, reversible, and validated by automated tests plus manual session QA.

## When to Engage
- Coaching prompts, personas, or evaluation rubrics need to evolve.
- Voice/WebRTC behavior requires tuning (model/voice swaps, instruction tweaks, transcript capture).
- Knowledge-store ingestion or retrieval quality must improve before a release.
- Technical debt inside `app/` is slowing feature delivery or causing regressions.
- A new contributor needs a single reference for how sessions, storage, and agents interact.

## Required Inputs
- Python 3.9+ (use the repo’s `venv` or create a fresh virtual environment; install `requirements.txt`).
- `.env` with `OPENAI_API_KEY`, plus optional overrides (`OPENAI_MODEL`, `OPENAI_REALTIME_MODEL`, `OPENAI_REALTIME_VOICE`, `OPENAI_EMBEDDING_MODEL`).
- Access to `app/knowledge_store/` (FAISS index + metadata) and permission to persist uploads in `app/uploads/`.
- When developing voice features: browser microphone access and a secure tunnel if testing from remote machines.
- Refactoring toolkit already vendored: `scripts/`, `references/`, and `templates/` from the skill library.

## Startup Checklist
1. Activate `venv/` (`source venv/bin/activate`) or create one, then `pip install -r requirements.txt`.
2. Populate `.env` (repo root or `app/.env`) with OpenAI credentials and optional realtime tuning flags.
3. Run `./run.sh` to boot FastAPI once; confirm the UI loads, static assets serve, and logs stream.
4. Execute `pytest` to baseline API/UI tests; resolve failures before refactoring.
5. Run `python scripts/analyze_code.py app --recursive` to surface long or complex flows (notably within `app/main.py`).
6. Review `README.md`, this playbook, and `app/main.py` to understand session lifecycle, knowledge storage, and voice endpoints.

## Core Workflow
1. **Discover**
   - Inspect `app/main.py` for session routes, knowledge-store orchestration, and realtime voice handlers.
   - Review `app/models/interview_agent.py` for persona prompts, question generation, and feedback loops.
   - Examine utilities in `app/utils/` (`document_processor`, `embedding_store`, `session_store`, `prompt_loader`) for shared logic.
   - Use analyzer output to highlight hotspots (long functions, broad exception handling, duplicate logging).
2. **Plan**
   - Capture scope in `templates/refactoring_plan.md` (goals, risks, test plan, rollback strategy).
   - Map smells to patterns from `references/patterns.md` (Extract Method for monolithic handlers, Introduce Parameter Object for voice config, etc.).
   - Confirm safety prerequisites from `references/best_practices.md` (clean working tree, tests, rollback options).
3. **Execute**
   - Apply automated quick wins via `python scripts/refactor_code.py app/main.py --in-place` before manual edits.
   - Refactor incrementally: split lengthy request handlers, encapsulate voice payload construction, tighten logging helpers.
   - Keep persona prompts and knowledge-store interactions behaviorally identical; update tests if signatures shift.
4. **Verify**
   - Run targeted suites (`pytest tests/api`, `pytest tests/ui`) then the full `pytest` run.
   - Manually validate UI flows: upload resume/JD, generate questions, run a coaching session, start realtime voice via `./run_voice.sh`.
   - Capture before/after metrics (function length, complexity, logging coverage) when meaningful.
5. **Document & Handoff**
   - Update this playbook, `README.md`, and relevant docs in `docs/` for new flows or dependencies.
   - Summarize refactors, tests, and known follow-ups in PR descriptions or release notes.

## Agent Composition
- **Text Coach** (`app/models/interview_agent.py`)
  - Class: `InterviewPracticeAgent` built on `AsyncOpenAI` for question generation, answer grading, and iterative feedback.
  - Personas (`ruthless`, `helpful`, `discovery`) supplied via `get_coach_prompt` or persona-specific templates in `app/prompts/`.
  - Maintains session state: generated questions, answers, feedback history, current index, persona.
- **Realtime Voice Coach** (assembled in `app/main.py` and frontend assets)
  - `_build_voice_instructions` combines persona prompt, resume/JD excerpts, and retrieved work-history snippets.
  - `POST /voice/session` (`create_voice_session`) calls the OpenAI Realtime Sessions API, configuring model, voice, and server-side VAD thresholds.
  - Frontend (`app/static/js/app.js`) negotiates WebRTC, streams audio, handles transcripts, and updates live UI state.
- **Knowledge & Session Stores**
  - `app/utils/embedding_store.py` manages the FAISS-backed work-history memory in `app/knowledge_store/` (import, search, clear).
  - `app/utils/session_store.py` persists session data (uploads, persona, agent state) under `app/session_store/`.
  - `app/utils/document_processor.py` sanitizes uploads and orchestrates resume/JD ingestion.

## Voice Flow Summary
1. User selects **Start Voice Session**; frontend gathers session ID, persona, and preferred voice.
2. `create_voice_session` prepares realtime instructions and requests a `client_secret` from OpenAI (`OPENAI_REALTIME_URL`).
3. Frontend establishes WebRTC with the realtime model, streaming audio both directions while displaying coach feedback.
4. Voice transcripts and coach responses persist via `/session/{id}/voice-transcript/*` routes for later review.
5. Optional “memorize” actions store notable transcripts in the work-history knowledge base for future prompts.

## Toolset Overview
- **Server launchers**: `./run.sh` (default FastAPI dev server), `./run_voice.sh` (same with realtime-focused logging), `./kill.sh` (cleanup helper).
- **Automation scripts**: `scripts/analyze_code.py` (AST-based smell detection), `scripts/refactor_code.py` (safe auto-fixes).
- **Knowledge tooling**: API endpoints `/work-history/*` wrap embedding store operations; refer to `app/utils/embedding_store.py` for direct use.
- **Logging**: `app/logging_config.py` + `app/logging_context.py` enable structured logs with session IDs (see `LOGGING_SEQUENCE.md`).
- **Frontend assets**: `app/static/js/app.js`, `app/templates/*.html`, `app/static/css/` drive the coaching UI and voice UX.
- **Tests**: `tests/api/` covers REST endpoints; `tests/ui/` houses UI checks; expand coverage when refactoring major flows.

## Safety & Quality Gates
- ✅ `pytest` (and targeted `tests/api` / `tests/ui`) pass locally before and after refactors.
- ✅ `./run.sh` still serves uploads, question generation, and coaching loops without regressions; `./run_voice.sh` negotiates realtime voice successfully.
- ✅ Knowledge store remains consistent (FAISS index + metadata in sync; no orphaned uploads or transcripts).
- ✅ Structured logs keep expected slugs/fields; log volume stays manageable after instrumentation changes.
- ✅ Environment variables and required services (OpenAI APIs, WebRTC access) remain documented for collaborators.
- ✅ Refactors stay behavior-preserving; feature additions land in separate commits or PRs.
- ✅ `python3 scripts/analyze_code.py app --recursive` runs cleanly with no new findings introduced by your change; investigate and resolve any new issues before handoff.
- ✅ Capture analyzer output in version control (commit or PR notes) with a brief explanation of why it was run and any new observations discovered.

## Decision Support
- **Should I Refactor?** Use the decision tree in `templates/refactoring_plan.md`: confirm tests exist, identify concrete pain (performance, readability, defects), and weigh the risk of touching async handlers, WebRTC flows, or FAISS state.
- **Which Pattern Helps?**
  - Long FastAPI handlers (`app/main.py`): Extract helper modules or routers.
  - Repeated logging boilerplate: Introduce helper functions or context managers.
  - Voice payload construction: Encapsulate configuration objects to avoid parameter sprawl.
  - Persona prompt branching: Consider strategy objects or data-driven templates when adding personas.
- **Risk Assessment**: Document high-risk zones (file uploads, knowledge-store mutations, OpenAI realtime session creation) and mitigations before coding.

## Handoff Expectations
- Provide updated tests, environment instructions, and any migrations (knowledge-store rebuilds, config changes).
- Attach analyzer reports or refactor plans when delivering large cleanups; highlight modules touched and metrics improved.
- Document remaining tech debt (legacy session data, UI gaps, pending persona prompts) for future iterations.
- Ensure the working tree is clean, dependencies are pinned, and `.env` guidance stays current before handoff.

Keeping to this playbook keeps the interview-practice agent dependable while making future enhancements smoother and safer.
