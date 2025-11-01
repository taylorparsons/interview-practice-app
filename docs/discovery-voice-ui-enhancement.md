# Discovery Voice UI Enhancement (Minimal Scope)

- **Status:** Implemented (awaiting extended manual QA)
- **Owner:** Interview Practice Agent Team
- **Last Updated:** 2025-11-01

## Context

Discovery persona voice sessions already stream coach feedback and candidate speech through the OpenAI Realtime API. The UI renders a single-column transcript feed, but candidate turns were not reliably persisted or re-hydrated, making it difficult to review “You” transcripts after navigation or session reloads. This iteration keeps the layout and realtime plumbing intact while guaranteeing that both candidate and coach turns appear in the timeline and post-session views.

## Goals

- Display each final candidate transcript in the existing timeline with a “You” label.
- Maintain chronological ordering between candidate and coach entries without redesigning the layout.
- Persist candidate transcript text so the conversation survives reloads and is visible in summary views.
- Reuse the current WebRTC data channel to deliver live updates; no new realtime transports.
- Capture lightweight analytics for transcript review behaviour.

## Current State Overview (pre-change)

- **Realtime flow:** Structured events arrive over the `oai-events` data channel. `appendAgentDelta` creates coach bubbles. `appendUserTranscriptSegment` received user deltas but often failed to persist the final text.
- **Persistence:** `/session/{id}/voice-transcript` stored candidate speech in `voice_transcripts`; coach turns lived in `voice_agent_text`. No dedicated map existed for final user text.
- **UI:** The transcript panel is a single-column list. Speaker labels existed, yet “You” entries vanished after page refresh because the frontend never rehydrated from storage.
- **Analytics:** Only coarse session lifecycle logs (`voice.session.*`) were emitted; no insight into transcript reviews.

## Implementation Summary

- **Backend**
  - Added `voice_user_text` to session storage and extended `save_voice_transcript` to trim/persist text, capture an optional `source`, and emit `voice.transcript.user.save`.
  - Updated evaluation and memorize flows to prefer `voice_user_text` while keeping the legacy `voice_transcripts` map in sync for compatibility.
  - Provisioned realtime sessions with `input_audio_transcription.model` (default `gpt-4o-mini-transcribe`) so the API returns user speech transcripts in-line.
  - Introduced `GET /session/{session_id}/voice-transcript/export?format=json`, producing ordered conversation entries and logging `voice.transcript.export`.
  - Expanded API regression tests to cover the new persistence map and export endpoint.
- **Frontend**
  - Added a `persistUserTranscript` helper, immediate persistence from `appendUserTranscriptSegment`, and deduped navigation/summary saves using `persistedByIndex`.
  - Hydrated the timeline on session resume by replaying `voice_user_text`/`voice_agent_text`, preserving the single-column UI while restoring “You” bubbles.
  - Updated summary cards, feedback panes, and evaluation fetches to prioritise `voice_user_text` with graceful fallback.
  - Logged `voice.timeline.user.append` after successful persistence and `voice.timeline.user.view` once the transcript pane is meaningfully scrolled.
- **Export UX**
  - JSON export endpoint implemented; no UI button yet (can be wired later).
- **Testing**
  - `pytest tests/api/test_session_endpoints.py` (pass).
  - Full `pytest` run timed out in `tests/ui/test_homepage_smoke.py` (Helium UI smoke); rerun with extended timeout/headless driver remains TODO.
- **Out of Scope**
  - No SSE broadcaster or audio capture was added; realtime requirements are met via the existing data channel.

## Updated Behaviour

### Data Model & Persistence

1. `voice_user_text[str(question_index)]` now mirrors `voice_agent_text`, storing trimmed candidate transcripts.
2. `voice_transcripts` remains populated for backwards compatibility.
3. `GET /session/{id}` returns `voice_user_text` so clients can hydrate timelines and summary cards.
4. Export endpoint emits JSON containing ordered question/candidate/coach entries.

### Realtime Handling

- `appendUserTranscriptSegment` immediately persists completed utterances via `persistUserTranscript`, logging `voice.timeline.user.append` only after a successful response.
- Navigation (`displayQuestion`) and summary transitions flush buffered text through the same helper, keyed by question index to avoid duplicate POSTs.
- No SSE broadcast layer was reintroduced; secondary tabs continue to rely on manual refresh, but hydration restores transcripts on load.

### Frontend Rendering

- Session resume uses `hydrateVoiceTranscriptFromSession` to rebuild the timeline from persisted maps while retaining the existing styling.
- Summary/per-question cards and feedback drawers rely on `readTranscriptValue` to prioritise `voice_user_text` and fall back to `voice_transcripts`.
- `clearVoiceTranscript` resets local caches and analytics state; hydration repopulates messages as needed.

### Analytics & Logging

- Frontend logs:
  - `voice.timeline.user.append` after persistence (question index, character count, source).
  - `voice.timeline.user.view` the first time the transcript pane is scrolled past 50%.
- Backend logs:
  - `voice.transcript.user.save` with `question_index`, `characters`, and `source`.
  - `voice.transcript.export` when the JSON export endpoint is invoked.

## Risks & Mitigations

- **Duplicate bubbles:** Deduped using `persistedByIndex` before POSTing; hydration writes once per question.
- **Realtime lag:** Browser ASR updates can overwrite realtime text only when confidence improves; dedupe prevents repeated persistence.
- **Backwards compatibility:** Sessions lacking `voice_user_text` default to `{}`. UI gracefully falls back to `voice_transcripts`.
- **UI regression risk:** Manual QA still needed to confirm timeline hydration across resume/summary flows.

## Remaining Work

1. **Manual QA:** Exercise live Discovery sessions (record, navigate, resume) and confirm analytics/log output alongside export payloads.
2. **Export Control (optional):** If stakeholders want an in-app download button, wire it to the JSON endpoint.
3. **Documentation:** Update `README.md` voice section and user-facing release notes once QA is complete.

## Conversation Export

- Endpoint: `GET /session/{id}/voice-transcript/export?format=json`.
- Response example:

  ```json
  {
    "session_id": "SESSION123",
    "name": "Mock Interview",
    "generated_at": "2025-11-01T12:00:00Z",
    "entries": [
      {
        "question_index": 0,
        "question": "Tell me about yourself.",
        "candidate_text": "I focus on STAR stories...",
        "coach_text": "Nice opening; add metrics."
      }
    ]
  }
  ```

- Unsupported formats (e.g., `?format=csv`) return HTTP 415.
- No UI trigger yet; endpoint covered by API tests.

## Open Questions

- Do we need a visible “transcription in progress” indicator while the candidate speaks?
- Should we expose a UI control for the export endpoint in this release or defer to analytics?
- Are additional export formats (CSV/PDF) required for follow-up work?

## Validation Plan

- **Automated:** `pytest tests/api/test_session_endpoints.py` (pass); full `pytest` currently times out during `tests/ui/test_homepage_smoke.py` and should be re-run with an increased timeout/headless configuration.
- **Manual:** Pending—validate Discovery persona sessions end-to-end (live conversation, resume, summary) and confirm analytics/logs (`voice.transcript.user.save`, `voice.timeline.user.view`, export response).
- **Documentation:** Update `README.md` and release notes after manual QA; this document now reflects the implemented behaviour.
