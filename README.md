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

## Helper Scripts
- `./run_voice.sh`: Boots the FastAPI server with realtime voice defaults. Add `--no-reload` to disable auto-reload or `--python 3.11` to prefer a specific Python version.
- `./test.sh`: Runs the test suite with `pytest -q`. Use `--health` to ping the running server (`http://localhost:8000` by default) after tests, or override the health-check target with `--url <base_url>`.

## Realtime Voice Interviews
- Upload your resume and job description to start a session, then click **Start Voice Session** to open a WebRTC call with the `gpt-realtime-mini-2025-10-06` coach.
- The browser will prompt for microphone access—grant permission so the agent can hear you.
- Conversation summaries stream into the transcript panel while audio plays through the embedded `<audio>` element.
- Use **Stop Voice Session** to release the connection, or restart the interview to reset the voice UI.

### Voice Turn Detection (VAD) settings
You can control server-side turn detection behavior via environment variables in `.env`:

- `OPENAI_TURN_DETECTION` = `server_vad` (default) or `none`
- `OPENAI_TURN_THRESHOLD` = `0.5` (float string)
- `OPENAI_TURN_PREFIX_MS` = `300` (milliseconds)
- `OPENAI_TURN_SILENCE_MS` = `500` (milliseconds)

These map to the Realtime session `turn_detection` payload. Set values, restart the server, and start a new voice session to apply.

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
Taylor Parsons - taylor.parsons@gmaio.com


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
