# Voice & Session MVP TODOs

Checklist derived from the technical design in `prd_new_features.md`. Each section enumerates implementation, validation, and rollout work required to satisfy the defined GIVEN/WHEN/THEN scenarios.

## MVP 1 — Dual-Sided Voice Transcripts
- [x] Schema: extend session loader/saver to initialize and persist `voice_messages` with both coach and candidate roles; confirm defaults for legacy sessions.
- [x] Backend: add `/session/{id}/voice-messages` to append candidate/coach transcript packets with timestamps while updating aggregated `voice_transcripts` / `voice_agent_text`.
- [x] Backend: update `app/main.py` helpers to populate default voice fields and include `voice_messages` in session payloads without logging raw text.
- [x] Frontend: adjust `app/static/js/app.js` to relay interim/final transcript events, persist them via the new endpoint, and reconcile with persisted history on reload.
- [x] Frontend: update the voice timeline renderer to normalize coach/candidate roles and display dual-sided transcripts within 150 ms.
- [x] QA: create automated integration covering “GIVEN voice session active WHEN candidate speaks THEN timeline/session JSON include candidate entry” plus manual smoke test for reconnection.
- [x] Analytics: instrument transcript completeness metric (95% target) via counters in existing logging pipeline.

## MVP 2 — Coach Formatting Preservation
- Schema: store raw Markdown in `voice_messages` while caching sanitized HTML for render/export to avoid recomputation.
- Backend: update `InterviewPracticeAgent` to stop flattening guidance and pass Markdown through; integrate python-markdown + bleach sanitizer.
- Frontend: ensure timeline renderer consumes sanitized HTML while preventing XSS; adjust CSS to support lists and headers.
- Backend/Export: update PDF generator template to use sanitized HTML blocks so formatting matches web view.
- QA: validate acceptance (“GIVEN Markdown feedback WHEN rendered THEN formatting preserved”) via unit tests for sanitizer and visual regression spot-checks.
- Documentation: note Markdown support limits (e.g., tables) in internal runbook.

## MVP 3 — Practice Again for Voice/Text Sessions
- Schema: add `practice_history` collection storing `{run_id, completed_at, question_ids, model_id, voice_id}`; default to empty list for legacy files.
- Backend: implement `POST /sessions/{id}/practice-again` endpoint that snapshots current questions, applies optional additions, clears transcripts/answers, and returns new run metadata.
- Backend: ensure concurrency control so a running session cannot trigger duplicate practice-again runs.
- Frontend: build modal in `app/static/js/app.js` + template to offer reuse/add question paths and push the proper API payload.
- Frontend: refresh timeline and session state after run reset, surfacing the first question and updated practice history.
- QA: automate scenario “GIVEN session complete WHEN Practice Again invoked THEN new run created, prior run recorded” plus regression on text-only sessions.
- Analytics: log practice-again triggers to measure 60% reuse goal.

## MVP 4 — Runtime Model Selection
- Schema: expand `voice_settings` with `model_id`, `thinking_effort`, and `verbosity` defaults (`gpt-4o-mini`, `medium`, `balanced`) and ensure serialization/backfill.
- Backend: add `PATCH /sessions/{id}/settings` with validation against the approved model matrix; persist changes and emit structured log events.
- Backend: update `InterviewPracticeAgent` to consume session-specific settings and apply them to the next prompt only (no retroactive changes).
- Frontend: implement settings drawer controls for model, effort, verbosity; disable unsupported combinations and surface “applies to upcoming questions” confirmation.
- Frontend: maintain optimistic UI state pending API response and gracefully handle validation errors.
- QA: cover acceptance (“GIVEN active session WHEN model changes THEN next prompt uses new config”) via integration tests and manual check that prior transcripts remain intact.
- Telemetry: extend metrics/logging to capture adoption of each model/effort/verbosity trio.

## MVP 5 — Voice Selection with Preview
- Schema: persist `voice_settings.voice_id` alongside existing settings with backward-compatible defaults.
- Backend: create `voice_catalog.json` (or similar) and expose `GET /voices` endpoint returning available voices, labels, and preview URLs.
- Backend: update session start/realtime handshake to send the selected `voice_id`.
- Frontend: build selector UI with preview playback (local audio element) and confirmation flow tied to the settings API.
- Frontend: cache preview clips client-side and guard against starting a new prompt while previewing.
- QA: test acceptance (“GIVEN selector WHEN previewed and saved THEN active session unaffected until next prompt uses new voice”) plus fallbacks when catalog fetch fails.
- Telemetry: log voice selection frequency for future catalog tuning.

## MVP 6 — PDF Study Guide Export
- Schema: add `pdf_exports` metadata (timestamp, filename, size) to session store; ensure defaults for legacy sessions.
- Backend: implement `POST /sessions/{id}/exports/pdf` using FastAPI `BackgroundTasks`, Jinja2 template, and WeasyPrint renderer with temp file cleanup.
- Backend: ensure export endpoint enforces ≤5 s SLA for ≤15 questions and returns streaming response on success with error handling/logging otherwise.
- Frontend: add Export CTA with progress indicator and download handling; support multiple exports per session.
- QA: verify acceptance (“GIVEN completed session WHEN export requested THEN PDF matches timeline content and metadata recorded”) via automated test harness and manual layout review.
- Operations: document new dependency (WeasyPrint) in README/requirements and update deployment steps to include system packages if required.
- Telemetry: record PDF export attempts/successes to measure 40% usage goal.
