import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import app.main as main  # noqa: E402
import app.utils.session_store as store  # noqa: E402
from app.utils.markdown import render_markdown_safe  # noqa: E402


def _seed_session(tmp_path):
    sid = "s-markdown"
    payload = {
        "resume_path": "uploads/resume.txt",
        "job_desc_path": "uploads/job.txt",
        "resume_text": "Sample resume",
        "job_desc_text": "Sample JD",
        "name": "voice_test",
        "questions": ["Tell me about yourself."],
        "answers": [],
        "evaluations": [],
        "agent": None,
        "current_question_index": 0,
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
    }
    main.active_sessions.clear()
    store.save_session(sid, payload)
    return sid


def test_render_markdown_safe_strips_scripts():
    html = render_markdown_safe("**Bold**\n\n- item\n\n<script>alert(1)</script>")
    assert "<script" not in html
    assert "<strong>Bold" in html
    assert "<ul>" in html and "<li>item" in html


def test_voice_message_stores_sanitized_html(monkeypatch, tmp_path):
    monkeypatch.setattr(store, "SESSION_DIR", tmp_path)
    sid = _seed_session(tmp_path)
    client = TestClient(main.app)

    payload = {
        "role": "assistant",
        "text": "Line 1\n\n- bullet<script>alert(1)</script>",
        "question_index": 0,
        "timestamp": "2024-01-01T00:00:02Z",
    }
    res = client.post(f"/session/{sid}/voice-messages", json=payload)
    assert res.status_code == 200

    session = main._get_session(sid)
    html = session["voice_messages"][0]["html"]
    assert "<script" not in html
    assert "<ul>" in html and "<li>bullet" in html
