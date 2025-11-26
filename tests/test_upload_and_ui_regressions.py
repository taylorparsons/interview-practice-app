import io
import sys
import uuid
from pathlib import Path

from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import app.main as main  # noqa: E402


HTML_PATH = ROOT / "app" / "templates" / "index.html"
JS_PATH = ROOT / "app" / "static" / "js" / "app.js"


def _read_text(p: Path) -> str:
    with open(p, "r", encoding="utf-8") as f:
        return f.read()


def test_upload_with_pasted_job_desc_text_only():
    client = TestClient(main.app)

    # Build a fake resume file and only paste JD text (no JD file provided)
    files = [
        (
            "resume",
            ("resume.txt", b"Candidate resume content", "text/plain"),
        ),
    ]
    data = {
        "job_description_text": "JD pasted text",
    }

    resp = client.post("/upload-documents", files=files, data=data)
    assert resp.status_code == 200
    payload = resp.json()
    assert "session_id" in payload

    # Verify session reflects the pasted JD text (file ignored)
    sid = payload["session_id"]
    s = client.get(f"/session/{sid}/documents")
    assert s.status_code == 200
    docs = s.json()
    assert docs.get("resume_text", "").startswith("Candidate resume content")
    assert docs.get("job_desc_text") == "JD pasted text"


def test_upload_prefers_text_when_both_file_and_text_provided():
    client = TestClient(main.app)

    files = [
        ("resume", ("resume.txt", b"R", "text/plain")),
        ("job_description", ("jd.txt", b"FILE JD", "text/plain")),
    ]
    data = {"job_description_text": "JD pasted text"}

    resp = client.post("/upload-documents", files=files, data=data)
    assert resp.status_code == 200
    sid = resp.json()["session_id"]
    docs = client.get(f"/session/{sid}/documents").json()
    # Text should win over file contents
    assert docs["job_desc_text"] == "JD pasted text"


def test_upload_form_posts_to_backend():
    html = _read_text(HTML_PATH)
    assert 'id="upload-form"' in html
    assert 'method="post"' in html.lower()
    assert 'action="/upload-documents"' in html
    assert 'enctype="multipart/form-data"' in html.lower()


def test_js_bundle_has_no_legacy_globals_and_eval_identifiers():
    js = _read_text(JS_PATH)
    # After rollback, app.js must not depend on non-existent globals
    assert "appVoiceConfig" not in js
    # Avoid using 'eval' identifier in arrow funcs (strict-mode safe)
    assert "forEach(eval =>" not in js
    assert "(sum, eval)" not in js


def test_documents_endpoint_returns_texts():
    client = TestClient(main.app)
    sid = str(uuid.uuid4())
    now = "2024-01-01T00:00:00Z"
    payload = {
        "resume_path": "uploads/resume.txt",
        "job_desc_path": "uploads/job.txt",
        "resume_text": "R text",
        "job_desc_text": "JD text",
        "name": "doc_test",
        "questions": [],
        "answers": [],
        "evaluations": [],
        "agent": None,
        "current_question_index": 0,
        "created_at": now,
        "updated_at": now,
        "voice_transcripts": {},
        "voice_agent_text": {},
        "voice_messages": [],
    }
    main._persist_session_state(sid, payload)

    r = client.get(f"/session/{sid}/documents")
    assert r.status_code == 200
    docs = r.json()
    assert docs.get("resume_text") == "R text"
    assert docs.get("job_desc_text") == "JD text"


def test_settings_drawer_controls_present_and_wired():
    html = _read_text(HTML_PATH)
    assert 'id="global-settings"' in html
    assert 'id="voice-settings-drawer"' in html
    js = _read_text(JS_PATH)
    # Guarded listener prevents ReferenceError when button is present/absent
    assert "if (openSettingsBtn && voiceSettingsDrawer)" in js
    assert "openSettingsBtn.addEventListener('click'" in js


def test_sessions_modal_controls_present_and_wired():
    html = _read_text(HTML_PATH)
    assert 'id="sessions-modal"' in html
    assert 'id="sessions-modal-select"' in html
    assert 'id="sessions-rename"' in html
    assert 'id="sessions-load"' in html
    js = _read_text(JS_PATH)
    assert "if (openSessionsBtn && sessionsModal)" in js
    assert "openSessionsBtn.addEventListener('click'" in js
    assert "sessionsRenameBtn.addEventListener('click'" in js
    assert "sessionsLoadBtn.addEventListener('click'" in js


def test_mark_for_review_button_and_handler_present():
    html = _read_text(HTML_PATH)
    assert 'id="mark-review"' in html
    js = _read_text(JS_PATH)
    assert "if (markReviewBtn)" in js
    assert "markReviewBtn.addEventListener('click'" in js
    assert "toggleMarkForReview" in js


def test_question_management_controls_present():
    html = _read_text(HTML_PATH)
    assert 'id="generate-more-count"' in html
    assert 'id="generate-more-btn"' in html
    assert 'id="remove-question-select"' in html
    assert 'id="remove-questions-btn"' in html
    js = _read_text(JS_PATH)
    assert "handleGenerateMoreQuestions" in js
    assert "handleRemoveQuestions" in js


def test_voice_model_selects_present():
    html = _read_text(HTML_PATH)
    assert 'id="realtime-model-select"' in html
    assert 'id="realtime-model-select-2"' in html
    js = _read_text(JS_PATH)
    assert "realtimeModelSelect" in js
    assert "realtime_model" in js


def test_export_transcript_button_guard_defined():
    js = _read_text(JS_PATH)
    # Prevent regressions where undeclared exportTranscriptBtn breaks DOMContentLoaded handler
    assert "const exportTranscriptBtn" in js
    assert "if (exportTranscriptBtn)" in js
