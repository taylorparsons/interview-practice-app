# Voice Experience Enhancements Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Deliver end-to-end voice UX enhancements: dual-sided transcripts with preserved formatting, Practice Again + runtime model/voice controls, and PDF export.

**Architecture:** FastAPI session API stores additive fields (`voice_messages`, `voice_settings`, `practice_history`, `pdf_exports`) backed by JSON session files; frontend vanilla JS renders combined timeline, selectors, and exports. Streaming/ASR stays on OpenAI Realtime; markdown sanitized on backend; PDF rendered server-side via WeasyPrint.

**Tech Stack:** FastAPI, Python 3.11, Jinja2, python-markdown + bleach, WeasyPrint, vanilla JS/Tailwind, pytest/FastAPI TestClient.

---

## Phase 1 — Dual-sided transcripts + formatting

### Task 1: Schema defaults and loading
- Files:
  - Modify: `app/main.py`
  - Modify: `app/utils/session_store.py` (if present; otherwise add helper)
  - Test: `tests/test_session_defaults.py` (new)
- Step 1: Write failing tests ensuring legacy sessions backfill `voice_messages` as `[]` and `voice_settings` default fields.
- Step 2: Run `pytest tests/test_session_defaults.py -q` (expect FAIL).
- Step 3: Implement defaults when loading/saving session JSON; ensure no logging of raw transcripts.
- Step 4: Run `pytest tests/test_session_defaults.py -q` (expect PASS).
- Step 5: `git add app/main.py app/utils/session_store.py tests/test_session_defaults.py && git commit -m "feat: add voice defaults for legacy sessions"`

### Task 2: Realtime transcription + role packets
- Files:
  - Modify: `app/main.py` (realtime session creation + endpoints)
  - Modify: `app/models/interview_agent.py` (if needed for message plumbing)
  - Test: `tests/test_voice_messages_api.py` (new)
- Step 1: Write failing API test: POST/WS emits candidate/coach packets stored as `{role, text, timestamp, question_index}`; role fidelity enforced.
- Step 2: Run `pytest tests/test_voice_messages_api.py -q` (expect FAIL).
- Step 3: Add `input_audio_transcription` payload (env `OPENAI_INPUT_TRANSCRIPTION_MODEL`, default `gpt-4o-mini-transcribe`), append packets to `voice_messages`, guard cross-role mix-ups.
- Step 4: Run `pytest tests/test_voice_messages_api.py -q` (expect PASS).
- Step 5: `git add app/main.py app/models/interview_agent.py tests/test_voice_messages_api.py && git commit -m "feat: store dual-sided voice messages with transcription"`

### Task 3: Markdown preservation + sanitizer
- Files:
  - Modify: `app/models/interview_agent.py`
  - Add: `app/utils/markdown.py` (sanitizer helper)
  - Modify: `requirements.txt`
  - Test: `tests/test_markdown_sanitizer.py` (new)
- Step 1: Write failing test for sanitizer (bullets, numbered lists, disallow script tags) and for agent passing Markdown through.
- Step 2: Run `pytest tests/test_markdown_sanitizer.py -q` (expect FAIL).
- Step 3: Add `markdown` + `bleach` deps; implement sanitizer helper returning sanitized HTML plus raw text.
- Step 4: Update agent to store raw Markdown in `voice_messages` and cached sanitized HTML for render/export.
- Step 5: Run `pytest tests/test_markdown_sanitizer.py -q` (expect PASS).
- Step 6: `git add app/models/interview_agent.py app/utils/markdown.py requirements.txt tests/test_markdown_sanitizer.py && git commit -m "feat: preserve coach markdown with sanitization"`

### Task 4: Frontend timeline + mic UX
- Files:
  - Modify: `app/static/js/app.js`
  - Modify: `app/templates/index.html` (timeline/mic UI)
  - Test: `tests/test_frontend_placeholder.md` (manual checklist placeholder if no FE test harness)
- Step 1: Update timeline renderer to show coach/user entries from persisted `voice_messages` within 150 ms; render sanitized HTML.
- Step 2: Add mic activity states (idle/listening/speaking/muted/unsupported) and toggles for browser ASR fallback + metadata view.
- Step 3: Add “Export Transcript” (JSON/txt) action.
- Step 4: Smoke-test manually; document steps in `tests/test_frontend_placeholder.md`.
- Step 5: `git add app/static/js/app.js app/templates/index.html tests/test_frontend_placeholder.md && git commit -m "feat: render dual-sided voice timeline with mic UX"`

---

## Phase 2 — Practice Again + model/voice selectors

### Task 5: Practice Again backend + schema
- Files:
  - Modify: `app/main.py`
  - Modify/Add: `app/utils/practice_history.py` (helper)
  - Test: `tests/test_practice_again.py` (new)
- Step 1: Write failing test: `POST /sessions/{id}/practice-again` creates new run, clears answers/transcripts, records prior run in `practice_history`, guards concurrent run.
- Step 2: Run `pytest tests/test_practice_again.py -q` (expect FAIL).
- Step 3: Implement schema additions and endpoint; ensure additive defaults.
- Step 4: Run `pytest tests/test_practice_again.py -q` (expect PASS).
- Step 5: `git add app/main.py app/utils/practice_history.py tests/test_practice_again.py && git commit -m "feat: add practice again with run history"`

### Task 6: Practice Again UI flow
- Files:
  - Modify: `app/static/js/app.js`
  - Modify: `app/templates/index.html`
  - Test: extend `tests/test_frontend_placeholder.md` with manual steps
- Step 1: Add modal/wizard to reuse existing questions or append new ones; call new endpoint.
- Step 2: Refresh timeline/state after reset; surface first question of new run.
- Step 3: Manual regression for text + voice sessions; update checklist doc.
- Step 4: `git add app/static/js/app.js app/templates/index.html tests/test_frontend_placeholder.md && git commit -m "feat: practice again UI for voice/text sessions"`

### Task 7: Model/effort/verbosity settings
- Files:
  - Modify: `app/main.py`
  - Modify: `app/models/interview_agent.py`
  - Modify: `app/static/js/app.js`
  - Test: `tests/test_session_settings.py` (new)
- Step 1: Write failing API test for `PATCH /sessions/{id}/settings` validating model matrix and applying on next prompt only.
- Step 2: Run `pytest tests/test_session_settings.py -q` (expect FAIL).
- Step 3: Implement `voice_settings` fields (model_id, thinking_effort, verbosity) with defaults and validation; agent consumes on next call.
- Step 4: UI drawer to select options; toast “applies to upcoming questions.”
- Step 5: Run `pytest tests/test_session_settings.py -q` and manual UI check (document in frontend checklist).
- Step 6: `git add app/main.py app/models/interview_agent.py app/static/js/app.js tests/test_session_settings.py tests/test_frontend_placeholder.md && git commit -m "feat: runtime model effort verbosity settings"`

### Task 8: Voice selection + preview
- Files:
  - Add: `app/voice_catalog.json`
  - Modify: `app/main.py` (GET /voices, PATCH /session/{id}/voice, preview endpoint)
  - Add: `app/static/voices/` (cached previews)
  - Modify: `app/static/js/app.js`
  - Modify: `app/templates/index.html`
  - Test: `tests/test_voice_catalog.py` (new)
- Step 1: Write failing tests for catalog endpoint, preview generation/caching, and persistence to session.
- Step 2: Run `pytest tests/test_voice_catalog.py -q` (expect FAIL).
- Step 3: Implement catalog read, validation, preview synthesis (OpenAI TTS) with disk cache; handshake uses `voice_id`.
- Step 4: UI dropdown + preview button with loading/disable behavior; save selection.
- Step 5: Run tests and update frontend manual checklist.
- Step 6: `git add app/voice_catalog.json app/main.py app/static/js/app.js app/templates/index.html tests/test_voice_catalog.py tests/test_frontend_placeholder.md && git commit -m "feat: voice selector with preview caching"`

---

## Phase 3 — PDF study guide export

### Task 9: PDF export backend
- Files:
  - Modify: `requirements.txt` (WeasyPrint and deps)
  - Modify: `app/main.py` (POST /sessions/{id}/exports/pdf`)
  - Add: `app/templates/pdf/export.html` (Jinja2)
  - Add: `app/utils/pdf.py`
  - Test: `tests/test_pdf_export.py` (new)
- Step 1: Write failing test for PDF endpoint (<=5s, includes questions/messages/feedback, records `pdf_exports` metadata).
- Step 2: Run `pytest tests/test_pdf_export.py -q` (expect FAIL).
- Step 3: Implement background task rendering via WeasyPrint, temp file cleanup, metadata logging.
- Step 4: Run tests (allow slower timeout for PDF) and fix.
- Step 5: `git add requirements.txt app/main.py app/templates/pdf/export.html app/utils/pdf.py tests/test_pdf_export.py && git commit -m "feat: pdf study guide export endpoint"`

### Task 10: PDF export UI + docs
- Files:
  - Modify: `app/static/js/app.js`
  - Modify: `app/templates/index.html`
  - Modify: `README.md` and `.env.example` (deps/env notes)
  - Test: update `tests/test_frontend_placeholder.md`
- Step 1: Add Export CTA with progress indicator; handle multiple exports; download on success.
- Step 2: Document WeasyPrint/system deps in README and env vars (if any).
- Step 3: Manual layout review; update checklist doc.
- Step 4: `git add app/static/js/app.js app/templates/index.html README.md .env.example tests/test_frontend_placeholder.md && git commit -m "feat: pdf export UI and docs"`
- Step 5: Extend settings UI to expose model/effort/verbosity controls (wired to `PATCH /session/{id}/settings`); persist selection and show “applies to upcoming questions” note.

---

## Verification & rollout
- Run full suite: `pytest -q`
- Manual smoke: voice session with transcripts, Practice Again flow, model/voice switch mid-session (applies next prompt), PDF export <5s for <=15 questions.
- Logging/telemetry: ensure structured logs for model/voice changes, practice-again triggers, PDF attempts.
- Backward compatibility: verify loading legacy session without new fields does not error.
- TODO (post-release): tighten evaluation prompt + JSON schema (Pydantic/JSON schema enforcement) to reduce non-JSON `evaluate_answer` warnings and ensure compliant responses. Validate with a dedicated test that retries are minimal and fallbacks log at INFO or lower.
- DONE 2025-11-26: Persist UI summary payloads (overall strengths/improvements/tone) server-side and include them in PDF export so server PDF matches client summary view.
- DONE 2025-11-26: Evaluation prompt now embeds explicit JSON schema; invalid payloads log at INFO, retry once, then fallback with heuristic response. See docs/2025-11-26-evaluation-schema-enforcement.md.
- TODO (upcoming): Pre-session settings panel to choose model/effort/verbosity and voice (add `gpt-realtime` option) before generating questions or starting voice; persist via settings/voice PATCH and reset agent so defaults apply on first use.
- TODO (upcoming): Allow generating N additional questions mid-run (UI control + backend append) and allow removing one or more questions (including answered), warning that answers/evaluations/transcripts for removed items are dropped and indices shift.
