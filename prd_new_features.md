# Product Requirements Document (PRD)
# Voice & Session Experience Enhancements

Project: interview_practice_voice_session_enhancements
Owner: Interview Practice App Team
Date Created: 2025-10-09
Status: Draft
Version: 0.1

---

## Executive Summary

Improve the voice-enabled interview experience so candidates can rehearse, review, and share their coaching sessions. We will capture both sides of the realtime dialog, preserve coach formatting, add resume/resume flows for "Practice Again", let candidates pick their preferred model and voice, and generate a PDF study guide for offline review.

Core Value Proposition:
- Make voice coaching as reviewable as text by persisting transcripts and analysis.
- Give candidates control over AI tone (model/voice) to match their prep style.
- Provide actionable artifacts (PDF study guide, repeat practice) that accelerate improvement.

---

## Problem Statement

### Current Pain Points
- Voice transcripts only capture the coach, leaving user responses invisible after the fact.
- Coach guidance collapses into dense blocks, making it hard to read aloud or repeat.
- "Practice Again" appears only for typed flows and doesn’t support voice insights.
- Model/voice choices are fixed in configuration files—no runtime control for users.
- No single export captures the full interview, transcripts, and feedback.

### Why Now
- Voice coaching adoption is increasing; users request better review tools.
- Recent logging/session refactors give us a reliable persistence layer to extend.
- Competitive tools are adding richer recap and export options.
- Internal stakeholders need structured artifacts for user testing and iteration.

---

## Success Criteria

### Must Have (MVP)
Functional Requirements:
1. Persist and display both coach and candidate voice transcripts during and after sessions.
2. Preserve coach formatting (paragraphs, lists) in the UI and exports.
3. Enable "Practice Again" for voice/text sessions with options to reuse or add questions.
4. Allow runtime selection of GPT model (gpt-4o-mini default, gpt-5-mini, gpt-5) with effort/verbosity controls.
5. Offer realtime voice selection with preview clips and persist the choice per session.
6. Generate a PDF study guide containing questions, evaluations, transcripts, and key takeaways.

Non-Functional Requirements:
1. Privacy: keep transcripts local; no extra external storage.
2. Performance: timeline updates <150 ms; PDF export <5 s for ≤15 questions.
3. Reliability: gracefully load older sessions without new fields.
4. Maintainability: additive schema changes; minimal migration overhead.
5. UX baseline: accessible (keyboard/screen reader), responsive layout.

Success Metrics:
- Transcript completeness rate: 95% of voice sessions show both roles.
- Practice Again reuse: 60% of completed sessions trigger a repeat session within 7 days.
- PDF export usage: 40% of sessions produce at least one study guide in beta.

### Should Have (Phase 2)
- Tag transcript segments with timestamps for granular review.
- Allow custom GPT presets per interview template (e.g., behavioral vs. technical).

### Could Have (Phase 3)
- Collaborative share link for mentors/coaches.
- Automated summary email with highlights and next steps.

### Won’t Have (Out of Scope)
- Real-time multi-language translation.
- Full conversational diarization beyond single candidate + coach.

---

## User Personas & Use Cases

### Primary Persona: Job Seeker
Background:
- Role: Mid-career professional preparing for interviews.
- Context: Desktop browser session with microphone.
- Goals: Practice behavioral answers, review feedback, iterate quickly.
- Pain: Hard to remember what was said; voice feedback collapses; no offline materials.

Key Use Cases:
Use Case 1: Review voice session dialog
```
Scenario: "I just finished a voice coaching session and want to read everything we said."
Current State: Only coach text persists; my words are missing.
Desired State:
1. Open the timeline and see both roles with proper formatting.
2. Copy key passages or export as PDF.
3. Resume later with the same history.
Outcome: Faster iteration because I understand the full dialog.
```

Use Case 2: Practice again with refined questions
```
Scenario: "I completed the interview and want to retry with the same or new questions."
Current State: Practice Again button missing for voice; no easy way to add new questions.
Desired State:
1. See Practice Again once all questions are done (voice or text).
2. Choose to reuse existing questions or add new ones.
3. Start a fresh run with cleared answers but retained context.
Outcome: Efficient re-runs without manual setup.
```

Use Case 3: Customize AI model and voice
```
Scenario: "I need a more challenging coach tone and a different voice persona."
Current State: Model/voice hardcoded; no runtime control.
Desired State:
1. Select GPT model and effort/verbosity in settings or during session.
2. Pick a voice (e.g., Echo) and preview audio before starting.
3. Changes apply immediately for future prompts.
Outcome: Tailored coaching experience that matches learning style.
```

Use Case 4: Export study guide
```
Scenario: "I want a deliverable to review on the go or share with a mentor."
Current State: No export option.
Desired State:
1. Click Export as PDF.
2. Receive a document with questions, answers, feedback, transcripts, and action items.
3. Save or print for offline practice.
Outcome: Structured artifact for deliberate practice.
```

---

## System Overview

### High-Level Architecture
```
┌────────────────────────┐        ┌────────────────────────┐
│   Browser UI (React)   │ ─────▶ │ FastAPI (app.main)     │
│ • Voice timeline       │        │ • Session endpoints    │
│ • Model/voice controls │ ◀───── │ • PDF export service   │
└─────────┬──────────────┘        └─────────┬──────────────┘
          │                                  │
          ▼                                  ▼
┌────────────────────────┐        ┌────────────────────────┐
│ Session Store (JSON)   │        │ Background workers      │
│ • transcripts, evals   │        │ • PDF rendering jobs    │
└────────────────────────┘        └────────────────────────┘
```

### Core Components
1. Voice Timeline UI — renders combined coach/user messages with preserved formatting and voice controls.
2. Session Persistence Layer — extends session JSON schema (messages, settings, practice history).
3. Model/Voice Config Service — exposes endpoints for updating model/voice per session.
4. Practice Again Flow — resets state, optional question augmentation.
5. PDF Exporter — composes session data into study guides (templating + renderer).

---

## Technical Design Updates (MVP)

### MVP 1 — Dual-Sided Voice Transcripts
- **Existing**: The realtime pipeline only persists coach utterances returned from OpenAI, writing them into session JSON via the `InterviewPracticeAgent`. Candidate speech streams directly to OpenAI with no transcription callback.
- **Additions**: Enable server-side input transcription by including `input_audio_transcription: { model: OPENAI_INPUT_TRANSCRIPTION_MODEL }` when creating the realtime session. Emit interim/final text packets for both roles over the existing channel. FastAPI handlers append `{role, text, timestamp, question_index}` objects to `voice_messages`, mirroring coach entries. The timeline UI renders candidate transcripts immediately without waiting for session save to avoid UI lag. Include a browser transcription fallback toggle for environments where server-side transcription is disabled.
- **UI/UX**: Add a microphone activity indicator with states `idle`, `listening`, `speaking`, `muted`, and `unsupported` using Web Audio; add a “Show transcript metadata” toggle for debugging; provide an “Export Transcript” action to download the current session transcript (JSON/plain text) prior to full PDF support.
- **Rationale**: Keeping transcription in the same realtime session avoids new third-party services, minimizes latency (<150 ms target), and lets us reuse the existing session persistence codepath with only additive schema fields.
- **Acceptance**: GIVEN a voice practice session is in progress with a connected microphone WHEN the candidate speaks THEN the timeline shows their transcript alongside the coach within 150 ms and the session JSON stores the utterance with role `candidate`. GIVEN identical text content is produced by both roles WHEN messages are persisted THEN roles remain distinct (candidate vs coach) without cross-assignment. GIVEN the mic is blocked or permission denied WHEN starting a session THEN the UI surfaces a `muted` indicator and helpful guidance.

### MVP 2 — Coach Formatting Preservation
- **Existing**: Coach feedback is flattened to plain paragraphs before storage/rendering, dropping Markdown structure provided by the model.
- **Additions**: Allow the agent to emit Markdown-formatted guidance, store it verbatim in `voice_messages`, and render it with a shared Markdown → sanitized HTML renderer (python-markdown + bleach). Timeline cards and exports will consume the sanitized HTML while keeping the raw Markdown in session JSON for reuse.
- **Rationale**: Markdown balances expressiveness and safety, keeps storage compact, and aligns with how typed feedback is already generated, reducing incremental complexity.
- **Acceptance**: GIVEN the coach sends Markdown-formatted feedback (e.g., bullet lists) WHEN the UI renders the message or an export is generated THEN the visible output preserves list structure while the stored session data retains the original Markdown text.

### MVP 3 — Practice Again for Voice/Text Sessions
- **Existing**: Practice Again leverages a text-only flow that clones question lists but lives outside the voice session state machine.
- **Additions**: Introduce `practice_history` entries recording `{completed_at, question_ids, model_id, voice_id}` per run. Add `POST /sessions/{id}/practice-again` that snapshots the current template, optionally merges user-supplied questions, clears answer/transcript fields, and persists a new run ID. Frontend updates the summary screen with a modal fed by this endpoint.
- **Rationale**: Persisting run metadata keeps the implementation additive (no destructive migrations) and enables future analytics on reuse while ensuring voice and text share the same reset semantics.
- **Acceptance**: GIVEN a session where all questions are completed WHEN the user chooses Practice Again with either reuse or add-questions THEN the system creates a new run with cleared answers/transcripts, records the prior run in `practice_history`, and surfaces the first question of the new run.

### MVP 4 — Runtime Model Selection
- **Existing**: The agent reads a global `settings.py` constant for model choice; effort/verbosity are hard-coded heuristics.
- **Additions**: Add `voice_settings.model_id`, `thinking_effort`, and `verbosity` to session state with defaults (`gpt-4o-mini`, `medium`, `balanced`). Expose `PATCH /sessions/{id}/settings` validating against the approved model matrix. The InterviewPracticeAgent watches for changes and applies them to the next outgoing prompt (no retroactive re-processing) by updating the realtime session parameters. UI includes a settings drawer that persists selection and shows a toast noting “applies to upcoming questions.”
- **Rationale**: A session-scoped settings document keeps behavior predictable across reconnects and maintains isolation between concurrent sessions, while deferring application until the next prompt avoids mid-stream transcript mismatches.
- **Acceptance**: GIVEN a session is active and the user selects a new model/effort/verbosity combination WHEN they save the change THEN the selection persists to `voice_settings`, a confirmation appears stating the change affects upcoming questions, and the next prompt uses the new configuration while previous transcripts remain unchanged.

### MVP 5 — Voice Selection with Preview
- **Existing**: Voice ID is fixed in config and shared across users.
- **Additions**: Define a catalog (`voice_catalog.json`) storing voice IDs, labels, and preview URLs. Serve it via `GET /voices`. Session settings persist the chosen `voice_id`; the realtime agent includes it on stream creation. Frontend fetches the catalog, caches short preview clips locally, and plays them via the `<audio>` element before committing changes.
- **Rationale**: Centralizing voice metadata keeps configuration server-driven while limiting client logic to presentation. Short previews avoid hitting the realtime API during selection and create a more responsive UX.
- **Acceptance**: GIVEN the user opens the voice selector WHEN they preview a voice and confirm their choice THEN the preview plays locally without affecting the active session, and subsequent prompts use the newly selected `voice_id` stored in `voice_settings`.

### MVP 6 — PDF Study Guide Export
- **Existing**: No export path; the server only serves HTML/timeline responses.
- **Additions**: Implement `POST /sessions/{id}/exports/pdf` that enqueues a FastAPI `BackgroundTasks` job to render a Jinja2 template into HTML, pipe it through WeasyPrint, and stream the resulting PDF to the user while caching metadata in `pdf_exports`. Temporary files live under `app/uploads/tmp` and are cleaned after download. Timeline data, transcripts, and takeaways are injected via the same serializer used for the web UI to guarantee parity.
- **Rationale**: Using WeasyPrint keeps the stack pure-Python, avoiding external services and satisfying the privacy constraint. BackgroundTasks prevents blocking the main request while staying simpler than introducing a new worker process for the MVP.
- **Acceptance**: GIVEN a completed session with transcripts and evaluations WHEN the user requests an export THEN the API responds within 5 seconds with a downloadable PDF that includes questions, candidate/coach messages, feedback, and takeaways, and `pdf_exports` logs the generated artifact.

#### Configuration
- `OPENAI_INPUT_TRANSCRIPTION_MODEL` (optional): sets the OpenAI model used for server-side speech-to-text during realtime WebRTC sessions. Default: `gpt-4o-mini-transcribe`. Set to empty to disable server-side transcription (the browser fallback toggle may be used for local testing).

---

## Data Requirements

### Session Schema Additions
- `voice_messages`: ordered list of `{ role, text, timestamp, question_index, stream? }`.
- `voice_settings`: `{ voice_id, model_id, thinking_effort, verbosity }`.
- `practice_history`: timestamps of completed runs and question lists.
- `pdf_exports`: metadata on generated exports (optional caching).

### Data Constraints
- Backward compatibility: default empty structures when keys missing.
- File encoding: UTF-8; maintain <5 MB per session file.
- Sensitive fields (transcripts) remain local; no third-party sync.

---

## Technical Constraints

### Platform/OS
- Runs on macOS/Linux dev environments; deployed as FastAPI + static assets.
- Browser must support WebRTC (voice) and File APIs for downloads.

### Libraries & Tools
- Frontend: vanilla JS + Tailwind updates for new components.
- Backend: FastAPI, Jinja2, httpx, playwright/weasyprint (candidate) for PDF.
- Storage: JSON files under `app/session_store/`.

### External APIs
- OpenAI Realtime API for voice; pass selected voice/model parameters.
- (Optional) PDF rendering library; avoid SaaS providers to keep data local.

---

## Security & Privacy

Privacy Requirements:
1. Do not send transcripts to new external services; stay within OpenAI interactions already approved.
2. Obfuscate sensitive tokens in logs; re-use existing logging filters.
3. PDF exports generated locally; ensure temporary files are cleaned up.
4. Provide user-facing note that transcripts stay local unless they export/share.

Data Access:
- Read/Write: FastAPI service for session JSON.
- No third-party modification or cloud sync.

Permissions Required:
- Microphone access (existing requirement).
- File write permission for PDF output in local environment.

Threats & Controls:
- Transcript leakage → ensure exports stored in user-chosen location only.
- Large file sizes → enforce size limits and compression options.

---

## User Experience Requirements

Design Principles:
1. Make transcripts scannable and voice controls obvious.
2. Keep critical actions (Practice Again, Export) above the fold.
3. Maintain accessibility (labels, keyboard navigation, ARIA roles).

UI Requirements:
1. Voice timeline component with role badges, timestamps, preserved spacing, and a mic activity indicator.
2. Model/voice selector panel with dropdowns and audio preview buttons.
3. Practice Again modal/wizard offering reuse or add-questions path.
4. PDF export CTA in summary section with progress feedback.
5. Transcript export control within the voice section to download JSON/plain-text transcripts.

Sample UX Flows:
- Voice Review Flow: finish session → timeline updates → export PDF.
- Practice Again Flow: summary screen → click Practice Again → choose reuse/add → restart interview.
- Model Switch Flow: open settings → change model/effort/verbosity → resume questioning with confirmation toast.

---

## Risks & Mitigation

Technical Risks
- Risk: PDF rendering increases dependencies or runtime errors.
  - Mitigation: prototype with pure Python library (WeasyPrint/ReportLab); add integration tests.
- Risk: Session files grow too large with transcripts.
  - Mitigation: paginate transcripts in UI; consider trimming streaming metadata.

User Experience Risks
- Risk: Additional controls overwhelm onboarding users.
  - Mitigation: sensible defaults, progressive disclosure, tooltips.
- Risk: Practice Again confusion about what resets.
  - Mitigation: confirmation dialog summarizing what carries over and what resets.

---

## Timeline & Milestones

Option A — Aggressive 2-Week Plan
- Week 1: Schema updates, voice timeline UI, model/voice selectors.
- Week 2: Practice Again flow, PDF export, QA + polish.
Milestone: All MVP features behind feature flag, ready for beta.

Option B — Phased Plan
- Phase 1 (MVP): Transcript persistence, timeline UI, Practice Again reuse — 2025-10-23.
- Phase 2 (Enhancements): Model/voice selector, PDF export — 2025-11-06.
- Phase 3 (Advanced): Timestamping, custom presets — TBD.

---

## Open Questions
- Should PDF exports include raw resume/JD snippets? — Status: Unresolved.
- How do we handle voice message deletions/edits if requested? — Status: Unresolved.
- Do we need analytics on model/voice selection usage? — Status: Unresolved.

---

## Success Measurement

Quantitative Metrics
- Voice transcript completeness: baseline 0% → target 95% by beta launch.
- Practice Again adoption: baseline <10% → target 60% by end of beta.
- PDF export completion: baseline 0 → target 40% of sessions by Phase 2 end.

Qualitative Metrics
- User interviews report transcript clarity and actionable feedback.
- Confidence ratings improve in post-session surveys.

Business Impact
- Higher retention for premium users; improved NPS among voice adopters.

---

Status: Draft
Next Steps:
1. Review requirements with engineering and design.
2. Create technical design doc for schema/UI changes.
3. Estimate effort and slot into upcoming sprint planning.

Document Control:
- Author: Interview Practice App Team (Taylor Parsons)
- Reviewers: Engineering, Design, Product
- Approval Required: Yes (Product Lead)
 - Version History: v0.1 (2025-10-09) — Initial draft covering voice, practice, export, and customization enhancements.
 - Version History: v0.2 (2025-10-10) — Add server-side input transcription configuration, mic activity indicator, browser ASR fallback toggle, transcript export action, and role-fidelity acceptance.
