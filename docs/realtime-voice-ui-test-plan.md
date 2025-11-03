# Realtime Voice UI Helium Test Plan

## Objective
Add Helium-driven browser automation that exercises the realtime voice coaching controls in `app/static/js/app.js`. The scenarios below close the current high-severity gap where start/stop voice flows, transcript handling, and persona persistence have zero automated coverage.

## Targeted UI Responsibilities
- `rememberBtn` / persona change persistence (`app/static/js/app.js:935-1034`)
- Voice session bootstrap and status handling (`app/static/js/app.js:1036-1198`)
- Voice teardown, controls reset, and speech-recognition hooks (`app/static/js/app.js:1199-1440`)

## Prerequisites
1. Extend `tests/ui/conftest.py` with helpers that:
   - Stub `window.fetch` for `/voice/session` and `/session/*` endpoints.
   - Replace `window.RTCPeerConnection` with a deterministic fake that surfaces the callbacks the UI expects (`createDataChannel`, `onmessage`, `onopen`, etc.).
   - Optionally stub `navigator.mediaDevices.getUserMedia` to avoid microphone prompts.
2. Ensure test runs can mount fixture payloads (JSON templates for `/voice/session` success/error responses, transcript data, etc.).
3. Add lightweight DOM helpers to inject canned transcript events into the data channel.

## Scenario Coverage
1. **Happy Path Start + Transcript Render**
   - Launch page, upload minimal fixtures (reuse existing resume helper).
   - Stub `/voice/session` to return a fake `client_secret` and model metadata.
   - Click “Start Voice Session”.
   - Simulate `dataChannel.onopen`; confirm:
     - `voiceStatus` transitions to “Live”.
     - Intro system message appears in transcript pane.
     - Voice controls toggle visibility (`startVoiceBtn` hidden, `stopVoiceBtn` visible).
   - Inject a mock user transcript event through the fake data channel and assert it renders.
2. **Remember Button + Persona Persistence**
   - Pre-load `state.voice.transcriptsByIndex[currentIndex]` via helper or simulated transcript event.
   - Click the “Remember” button.
   - Assert fetch call to `/session/{id}/voice-transcript/memorize` was triggered (capture via stub).
   - Change persona selector; verify:
     - Local storage updated (`coachPersona` key).
     - UI logs/voice transcript receive persona-change system message.
3. **Voice Session Error Handling**
   - Stub `/voice/session` to return a non-200 response.
   - Click “Start Voice Session” and ensure:
     - Error toast (system message) appears with failure text.
     - `voiceStatus` shows “Connection failed”.
     - Start button is re-enabled (controls not stuck).
4. **Manual Stop / Teardown**
   - Reuse happy path setup.
   - Click “Stop Voice Session”.
   - Confirm:
     - `voiceStatus` resets to “Voice session ended”.
     - `startVoiceBtn` becomes visible again.
     - Transcript pane is marked empty (`voiceTranscript.dataset.empty === "true"`).
     - Fake peer/data channel close handlers invoked (assert via injected spies).
5. **Speech Recognition Hook Regression Guard (optional stretch)**
   - Stub `window.SpeechRecognition` to a fake that calls `onresult`.
   - Simulate partial and final transcripts to ensure the answer textarea receives appended text and that transcript streaming publishes to the voice pane only when a voice session is active.

## Implementation Steps
1. **Test Utilities**
   - Add `FakeRTCPeerConnection` and `FakeDataChannel` classes under `tests/ui/helpers/voice.py` (or similar) with instrumentation hooks.
   - Register global stubs in a new fixture (e.g., `voice_stubs`) that wraps `browser` and restores originals after each test.
2. **Network Stubbing**
   - Provide a generic `stub_fetch` helper via `browser.execute_script` that records requests for later assertions.
   - Seed default responses for `/voice/session`, `/session/{id}/voice-transcript`, and persona PATCH calls.
3. **Helium Tests**
   - Create `tests/ui/test_voice_session_flow.py` with the scenarios above.
   - Use existing `flow_capture` to snapshot key states (start, live, transcript appended, stop).
   - Capture request logs from the stubbed fetch layer to assert expected payloads (session id, persona, etc.).
4. **Artifacts & Reporting**
   - Store generated transcript HTML/JSON under `tests/ui/__artifacts__/voice/` for triage when regressions occur.
   - Extend `run_usertests.sh` summary to mention the new voice scenarios.

## Risks & Mitigations
- **WebRTC APIs missing in headless Chrome**: The fake peer/data channel approach avoids relying on real WebRTC stacks.
- **Async race conditions**: Wrap assertions in `wait_until` to allow the UI’s promises/event handlers to flush.
- **CI stability**: Keep transcripts short, disable animations, and ensure all stubs reset per test to avoid leakage.

## Done Criteria
- New Helium suite fails without the targeted UI logic present (validated by commenting out voice status updates locally).
- `run_usertests.sh` reports the voice coverage block and artifacts.
- Documentation (`README.md` or `docs/helium-ui-testing-plan.md`) references this plan and test entry point.
- TODO: add a dedicated Helium scenario that stubs `SpeechRecognition` and verifies interim/final transcripts append to the answer textarea and voice timeline when the browser mic workflow is active. The stub harness can inject events once implemented.
