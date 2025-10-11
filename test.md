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

4. **Review output**
   - `..` indicates passing tests; any failure will show stack traces for investigation.
   - Warnings about PyPDF2 are expected; follow-up separately if you plan to migrate to `pypdf`.

## What The Tests Cover
- `tests/test_voice_messages.py`: persistence and retrieval of dual-role transcripts, session JSON shape, and role fidelity when texts are identical.
- `tests/test_voice_session.py`: outbound payload to OpenAI Realtime sessions API, including:
  - inclusion/omission of `input_audio_transcription` based on configuration
  - `turn_detection` set to `{"type": "none"}` when `OPENAI_TURN_DETECTION=none`
  - schema compatibility for `expires_at` (epoch integer)

## Observability Follow-Up
- Subscribe your log pipeline to `voice.transcript.metric` to monitor completeness ratios.
- Trend the `candidate_count` and `coach_count` fields to ensure both sides stay populated across sessions.
- Monitor latency during real sessions to keep transcript rendering under the 150 ms target.

## Troubleshooting
- If tests fail with schema errors on `expires_at`, ensure your stubs return an integer epoch, not a timestamp string.
- No OpenAI key is required for tests; network calls are stubbed in `tests/test_voice_session.py`.
