# Interview Practice App

## Overview
An AI-powered interview practice application that helps job seekers prepare for interviews by generating personalized questions, providing real-time feedback, and offering example answers.

## Features
- Resume upload plus job description file or text input
- AI-Generated Interview Questions
- Real-Time Answer Evaluation
- Markdown-Formatted Example Answers
- Tone and Content Feedback Analysis
- Session autosave with one-click resume
- Realtime Voice Interview Coach (OpenAI GPT Realtime + WebRTC)

### Evaluation schema enforcement
- Evaluation prompts embed an explicit JSON schema; server validates responses and falls back if invalid.
- Invalid payloads log `evaluation.schema.invalid` at INFO, retry once, then use heuristic fallback.
- Details and sequence diagrams: `docs/2025-11-26-evaluation-schema-enforcement.md`.

## Session Flow Overview
```
+---------------------------+
| Upload Documents (form)   |
+-------------+-------------+
              |
              v
+-------------+-------------+        Persisted to
| Generate Questions API     |---+--> disk (`app/session_store/`)
+-------------+-------------+   |    + localStorage session id
              |                 |
              v                 |
+-------------+-------------+   |
| Practice Question UI       |<--+
|  - Answer textarea         |
|  - Voice session controls  |
+-------------+-------------+
              |
              v
+-------------+-------------+
| Evaluation Feedback panel  |
+-------------+-------------+
              |
              v
+-------------+-------------+
| Summary + Restart options  |
+-------------+-------------+
              |
     +--------+--------+
     | Resume Saved    |
     | Session banner  |
     +-----------------+
```
State is mirrored between the in-memory cache, JSON files under `app/session_store/`, and the browser’s `localStorage`. The upload screen surfaces a “Resume Saved Session” call-to-action whenever a session id is detected, enabling users to continue exactly where they left off.

### Saving & Resuming Sessions
1. Upload your resume and job description to start a new session. The server writes the session state to `app/session_store/<session_id>.json`, and the session id is cached in the browser.
2. Each time you generate questions, submit answers, or receive feedback, the latest progress is auto-saved—there is no extra “Save” button.
3. Return to the home page later: a banner above the upload form exposes **Resume Saved Session** (to reload) or **Clear Saved Session** (to delete the stored state).
4. Clearing or restarting removes the session id from both local storage and disk, letting you begin a fresh interview run.

## Prerequisites
- Python 3.9+
- pip
- Virtual Environment

## Setup Instructions
1. Clone the repository
```bash
git clone https://github.com/yourusername/interview-practice-app.git
cd interview-practice-app
chmod +x run_voice.sh test.sh kill.sh
```

2. Configure Environment Variables
Copy `.env.example` to `.env`, then add your OpenAI API key:
```bash
cp .env.example .env
```
Update `.env` with your token (and override realtime model/voice if desired).

3. Run the Application
```bash
./run_voice.sh
```
The script creates/activates the virtual environment (if missing), installs dependencies, confirms realtime voice defaults, and starts the development server with auto-reload by default.
When the UI loads, upload your resume and either attach a job description file or paste its text directly into the job description field.

### One‑Step Bootstrap (Codex‑friendly)
For a single script that sets up a virtual environment, installs dependencies, and either starts the dev server or runs tests, use `scripts/codex_up.sh`.

Examples
```bash
# Install deps into venv and start the server at http://localhost:8000
scripts/codex_up.sh --start

# Create venv and install only (no server)
scripts/codex_up.sh --install

# Run the test suite
scripts/codex_up.sh --tests

# Pre‑generate and cache all voice preview MP3s (requires OPENAI_API_KEY)
scripts/codex_up.sh --preseed-previews
```

Options and env vars
- `--python 3.11` selects a specific Python version if available.
- `--no-reload` disables uvicorn file watching.
- `HOST` and `PORT` control bind address (defaults: `0.0.0.0:8000`).
- `PYTHON_BIN` can point to an explicit interpreter path.

Notes
- Voice features (realtime + previews) require `OPENAI_API_KEY` in `.env`. If missing, the server still starts but voice endpoints will return 5xx when invoked.
- Use `scripts/codex_up.sh` in constrained environments or CI. Use `run_voice.sh` for a stricter voice-first workflow that enforces the API key.
- Voice transcription defaults (browser fallback + metadata display) are now controlled via `.env` instead of runtime toggles:
  - `VOICE_BROWSER_FALLBACK_DEFAULT` (bool, default `false`) – when `true`, the browser speech-recognition fallback auto-starts during voice sessions.
  - `VOICE_SHOW_METADATA_DEFAULT` (bool, default `false`) – when `true`, transcript bubbles show timestamp/confidence/source metadata.
  - These values are injected into `window.APP_CONFIG.voice` so the client respects the server configuration without extra UI toggles.

## Helper Scripts
- `./run_voice.sh`: Boots the FastAPI server with realtime voice defaults. Add `--no-reload` to disable auto-reload or `--python 3.11` to prefer a specific Python version.
- `./test.sh`: Runs the test suite with `pytest -q`. Use `--health` to ping the running server (`http://localhost:8000` by default) after tests, or override the health-check target with `--url <base_url>`.
- `scripts/codex_up.sh`: One‑step venv + install + start/tests (Codex‑friendly).
- `scripts/install_git_conventions.sh`: Installs a commit template and a pre‑commit guard.

### Demo Checklist (stage)
- See `docs/DEMO_STAGE_VOICE_SETTINGS.md` for a short demo with screenshots covering:
  - Voice settings drawer loading/error/retry
  - Voice preview fallback
  - Save + immediate apply to live session
  - Submit Voice Answer flow
  - Question rail/drawer and Sessions modal

## Realtime Voice Interviews
- Upload your resume and job description to start a session, then click **Start Voice Session** to open a WebRTC call with the `gpt-realtime-mini-2025-10-06` coach.
- The browser will prompt for microphone access—grant permission so the agent can hear you.
- Conversation summaries stream into the transcript panel while audio plays through the embedded `<audio>` element.
- Use **Stop Voice Session** to release the connection, or restart the interview to reset the voice UI.

### Voice Selection & Preview
- Use the **Voice** dropdown to choose a coach voice and click **Save** to persist it for the session.
- Click **Preview** to play an MP3 sample of the selected voice. The first request synthesizes the sample with OpenAI TTS and caches it under `app/static/voices/<id>-preview.mp3`; subsequent previews stream from cache.
- Endpoints involved:
  - `GET /voices` — returns the catalog of voices
  - `PATCH /session/{session_id}/voice` — sets the session’s selected voice
  - `GET /voices/preview/{voice_id}` — returns a cached/synthesized MP3 sample
- Tip: Pre‑generate all previews for faster UX during development:
  - `scripts/codex_up.sh --preseed-previews`

### Browser Transcription Fallback
- The UI exposes a “Browser transcription fallback” toggle (off by default). When server‑side transcription is disabled, you can enable this for local testing.
- The browser ASR is automatically suppressed while the coach is speaking to prevent echo or misattribution.
- Finalized duplicate “You” lines are de‑duplicated using simple normalization when both server and browser transcripts are active.

### Input Transcription (speech-to-text)
Server-side input transcription can be enabled so the candidate’s speech is transcribed within the realtime session and streamed to the UI as text events.

- Env var: `OPENAI_INPUT_TRANSCRIPTION_MODEL`
  - Default when unset: `gpt-4o-mini-transcribe`
  - Set to an empty string to disable server-side transcription
  - Example values:
    - `OPENAI_INPUT_TRANSCRIPTION_MODEL=gpt-4o-mini-transcribe`
    - `OPENAI_INPUT_TRANSCRIPTION_MODEL=`

When disabled, you may still use the UI’s “Browser transcription fallback” toggle (if present) for local testing. Changes take effect when starting a new voice session.

### Voice Turn Detection (VAD) settings
You can control server-side turn detection behavior via environment variables in `.env`:

- `OPENAI_TURN_DETECTION` = `server_vad` (default) or `none`
- `OPENAI_TURN_THRESHOLD` = `0.5` (float string)
- `OPENAI_TURN_PREFIX_MS` = `300` (milliseconds)
- `OPENAI_TURN_SILENCE_MS` = `500` (milliseconds)

These map to the Realtime session `turn_detection` payload. Set values, restart the server, and start a new voice session to apply.

### Coaching Level
- The **Coaching Level** control lets you switch between:
  - `level_1` (Help) — more supportive coaching
  - `level_2` (Strict) — tougher guidance
- The selected level is persisted per session and influences both the text agent and realtime voice instructions. Changes emit a telemetry line: `coach.level.change: session=<id> from=<old> to=<new>`.

### Export Transcript
- Click **Export Transcript** to download a readable text file of the session timeline.
- Behavior mirrors the UI:
  - Backfills missing “You” lines using per‑question `voice_transcripts`.
  - Orders entries by timestamp when available; otherwise by question index and role (You → Coach → System), stable by original order.
  - Coalesces consecutive “You” lines and preserves the earliest timestamp.

## Technologies Used
- FastAPI
- OpenAI GPT
- Tailwind CSS
- Showdown.js
- Python libraries (PyPDF2, python-docx, scikit-learn, nltk)

## Contributing
1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License
Distributed under the MIT License. See `LICENSE` for more information.

## Contact
Taylor Parsons - taylor.parsons@gmail.com


---

## Lean Canvas

| Problem | Solution | Unique Value Proposition | Unfair Advantage | Customer Segments |
|---------|----------|--------------------------|------------------|-------------------|
| - Job seekers struggle with interview preparation<br>- Lack of personalized practice<br>- Difficulty receiving constructive feedback | - Question generation from job descriptions and resumes<br>- Real-time feedback on answers<br>- Resume-based example answers | - Personalized interview questions and feedback<br>- Real-time interaction using AI analysis<br>- Comprehensive practice tool | - Advanced AI models for evaluation<br>- Personalized adaptive feedback | - Job seekers<br>- Career coaches<br>- Educational institutions |

| Channels | Revenue Streams | Cost Structure | Key Metrics |
|----------|----------------|----------------|-------------|
| - Online platforms<br>- Career service partnerships<br>- Digital marketing | - Subscription model<br>- One-time purchases<br>- Institutional partnerships | - Development and maintenance<br>- AI model licensing<br>- Marketing costs | - Active users<br>- Engagement metrics<br>- Conversion rates |

---

## Technical Requirements Document

### 1. File Upload Capability
- **User Given**: As a user, I want to upload a job description and my resume easily.
- **When**: The user uploads these documents, they should be stored securely for processing.
- **Outcome**: Documents are used to tailor the interview questions specifically to the job description and user's experience.

### 2. Question Generation
- **User Given**: As a user, I want relevant interview questions generated from my resume and the job description.
- **When**: The user uploads documents, the system should analyze them instantly.
- **Outcome**: A set of personalized interview questions is generated and presented to the user.

### 3. User Answer Interaction
- **User Given**: As a user, I want to answer interview questions interactively.
- **When**: The system presents a question, the user should be able to respond easily.
- **Outcome**: The system records user answers for evaluation.

### 4. Answer Evaluation
- **User Given**: As a user, I want my answers evaluated for content and tone.
- **When**: The user submits an answer, it should be analyzed immediately.
- **Outcome**: The system provides feedback on the content accuracy and tone of the response.

### 5. Feedback Mechanism
- **User Given**: As a user, I want to receive constructive feedback to improve my responses.
- **When**: Feedback is provided after each answer.
- **Outcome**: Feedback highlights strengths, weaknesses, and suggestions for improvement.

### 6. Resume-Based Answering
- **User Given**: As a user, I want the app to answer questions using my resume as a source.
- **When**: The user asks how the app would respond to a question based on the resume.
- **Outcome**: The app generates a response using relevant information from the resume, demonstrating potential answers.

---

## Test Document

### 1. File Upload Capability
- **Test Scenario**: Verify that users can upload job descriptions and resumes in various formats (e.g., PDF, DOCX).
- **Expected Outcome**: The app accepts the files, stores them securely, and they can be accessed for question generation.

### 2. Question Generation
- **Test Scenario**: Check if relevant interview questions are generated based on the uploaded job description and resume.
- **Expected Outcome**: The app generates a set of questions that align with the job requirements and the user's qualifications.

### 3. User Answer Interaction
- **Test Scenario**: Confirm that users can interactively answer the generated interview questions.
- **Expected Outcome**: Users should be able to submit answers without errors, and the answers are recorded in the system.

### 4. Answer Evaluation
- **Test Scenario**: Validate that the app evaluates the content and tone of user answers.
- **Expected Outcome**: Each answer is analyzed, and feedback is provided regarding content accuracy and tone appropriateness.

### 5. Feedback Mechanism
- **Test Scenario**: Ensure that users receive constructive feedback after each answer.
- **Expected Outcome**: Feedback should highlight areas for improvement and provide specific suggestions.

### 6. Resume-Based Answering
- **Test Scenario**: Test the app's ability to answer questions using the user's resume as a factual source.
- **Expected Outcome**: The app should generate accurate responses based on the resume, demonstrating potential answers to interview questions.
### Git Conventions (Commit Template + Pre‑Commit Guard)
Install once per clone:

```bash
scripts/install_git_conventions.sh
```

What you get:
- Commit template at `.github/commit_template.txt` prompting for Summary, Rationale, Impact, Testing, Notes.
- Pre‑commit hook that blocks commits that add code without adding at least one comment line in the diff (simple heuristic across `.py`, `.js/.ts/.tsx/.jsx`, `.html`, `.css`).

Bypass (emergencies only):

```bash
BYPASS_COMMENT_CHECK=1 git commit -m "hotfix: ..."
```
