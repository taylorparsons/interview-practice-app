# Running the Test Suite

1. **Create/activate virtual env (if needed)**
   ```bash
   python3.11 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Execute the tests**
   ```bash
   pytest -vv --maxfail=1 --durations=5
   ```
   - Uses FastAPI TestClient and local session store; no network calls required.
   - Emits per-test names and shows the five slowest tests for easier debugging.
   - Voice messages: verifies candidate/coach transcript entries, aggregation, and metrics logging.
   - Voice session: validates realtime session payload fields (model, voice, input transcription, VAD none), fully stubbed httpx client.
   - Voice preview: exercises cached MP3 serving and synth-on-miss, 404 for unknown ids, 503 without key, and catalog cache invalidation.
   - UI toggles: ensures browser ASR fallback is OFF by default, gating is present, and dedup logic exists for finalized user messages.
   - Upload + UI regressions: verifies the upload form posts multipart to `/upload-documents`, pasted JD text is accepted when no file is provided, text wins when both text and a file are present, and the JS bundle does not rely on removed globals or the `eval` identifier.

Or simply run:
```bash
./run_tests.sh
```
This script prints the command being used and mirrors the detailed pytest output.

3. **Targeted runs**
   - Voice message tests only:
     ```bash
     pytest -q -k voice_messages
     ```
   - Realtime session payload tests only:
     ```bash
     pytest -q -k voice_session
     ```
   - Voice catalog/preview tests:
     ```bash
     pytest -q -k voice_preview
     ```
   - UI fallback + dedup assertions (static analysis of HTML/JS):
     ```bash
     pytest -q -k ui_fallback
     ```
   - Voice selection + persistence:
     ```bash
     pytest -q -k voice_selection
     ```
   - Transcript export ordering + coalescing:
     ```bash
     pytest -q -k export_transcript
     ```
   - Upload + UI regression tests:
     ```bash
     pytest -q -k upload_and_ui_regressions
     ```

4. **Review output**
   - `..` indicates passing tests; any failure will show stack traces for investigation.
   - Warnings about PyPDF2 are expected; follow-up separately if you plan to migrate to `pypdf`.

## What The Tests Cover
- `tests/test_voice_messages.py`: persistence and retrieval of dual-role transcripts, session JSON shape, and role fidelity when texts are identical.
- `tests/test_voice_session.py`: outbound payload to OpenAI Realtime sessions API, including:
  - inclusion/omission of `input_audio_transcription` based on configuration
  - `turn_detection` set to `{"type": "none"}` when `OPENAI_TURN_DETECTION=none`
  - schema compatibility for `expires_at` (epoch integer)
- `tests/test_voice_preview.py`: voice preview endpoint behavior (cache hit/miss, synth, error codes) and catalog invalidation; session payload returns `voice_settings` after update.
- `tests/test_voice_selection.py`: voice catalog endpoint, session voice persistence via `PATCH /session/{sid}/voice`, and usage in the realtime session payload.
- `tests/test_ui_fallback_and_dedup.py`: asserts default OFF browser fallback, gated start on data channel open, suppression of ASR while coach speaks, and duplicate “You” de‑duplication logic presence.
- `tests/test_ui_voice_layout.py`: template/JS wiring for live layout toggles (hiding manual inputs, expanding transcript viewport).
- `tests/test_export_transcript.py`: export logic that backfills “You” from per‑question transcripts, orders lines predictably, and coalesces adjacent “You” lines.
- `tests/test_upload_and_ui_regressions.py`: end‑to‑end upload behaviors + safety checks.
  - Accepts pasted job description text when the file input is empty.
  - Prefers pasted JD text when both file and text are provided.
  - Ensures the upload form uses `POST /upload-documents` with `multipart/form-data` (prevents long GET URLs with querystrings).
  - Guards against accidental reliance on removed JS globals and avoids `eval` as a variable name in strict mode.

## Observability Follow-Up
- Subscribe your log pipeline to `voice.transcript.metric` to monitor completeness ratios.
- Trend the `candidate_count` and `coach_count` fields to ensure both sides stay populated across sessions.
- Monitor latency during real sessions to keep transcript rendering under the 150 ms target.

## Troubleshooting
- If tests fail with schema errors on `expires_at`, ensure your stubs return an integer epoch, not a timestamp string.
- No OpenAI key is required for tests; network calls are stubbed in `tests/test_voice_session.py`.
- Voice preview tests do not make real network calls; TTS synthesis is stubbed and the generated MP3 is written under `app/static/voices/`. Ensure this directory is writable in your environment.
- If a preview test fails due to an unexpected cache hit, remove `app/static/voices/*-preview.mp3` files and re-run.
- If an upload test fails with 422, ensure the form posts `multipart/form-data` and that the JD file field is truly empty when testing the pasted‑text path.
