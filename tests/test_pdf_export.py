import io
import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import app.main as main  # noqa: E402
import app.utils.session_store as store  # noqa: E402


def _seed_session(tmp_path):
    sid = "s-pdf"
    payload = {
        "resume_path": "uploads/resume.txt",
        "job_desc_path": "uploads/job.txt",
        "resume_text": "Sample resume",
        "job_desc_text": "Sample JD",
        "name": "pdf_test",
        "questions": ["Q1"],
        "answers": [{"question": "Q1", "answer": "A1"}],
        "evaluations": [{"score": 7, "feedback": "Good", "strengths": ["a"], "weaknesses": ["b"]}],
        "voice_messages": [{"role": "candidate", "text": "hi", "question_index": 0}],
        "agent": None,
    }
    main.active_sessions.clear()
    store.save_session(sid, payload)
    return sid


def test_export_pdf(monkeypatch, tmp_path):
    monkeypatch.setattr(store, "SESSION_DIR", tmp_path)
    sid = _seed_session(tmp_path)
    client = TestClient(main.app)

    # Stub renderer to avoid heavy deps during test
    called = {}

    def fake_render(html, base_url=None):
        called["html"] = html
        return b"%PDF-FAKE%"

    monkeypatch.setattr(main, "render_pdf_from_html", fake_render)

    res = client.post(f"/sessions/{sid}/exports/pdf")
    assert res.status_code == 200
    assert res.headers.get("content-type") == "application/pdf"
    assert res.headers.get("content-disposition", "").startswith("attachment; filename=")
    assert res.content.startswith(b"%PDF-FAKE%")

    session = main._get_session(sid)
    exports = session.get("pdf_exports") or []
    assert len(exports) == 1
    assert exports[0]["filename"].endswith(".pdf")
