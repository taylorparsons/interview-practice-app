import sys
import uuid
from pathlib import Path

from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import app.main as main  # noqa: E402


def _session_payload():
    now = "2024-01-01T00:00:00Z"
    return {
        "resume_path": "uploads/resume.txt",
        "job_desc_path": "uploads/job.txt",
        "resume_text": "Sample resume text",
        "job_desc_text": "Sample job description",
        "name": "custom_question_session",
        "questions": [],
        "answers": [],
        "evaluations": [],
        "per_question": [],
        "agent": None,
        "current_question_index": 0,
        "created_at": now,
        "updated_at": now,
        "voice_transcripts": {},
        "voice_agent_text": {},
        "voice_messages": [],
    }


def test_add_custom_question_appends_and_activates():
    client = TestClient(main.app)
    sid = str(uuid.uuid4())
    payload = _session_payload()
    payload["questions"] = ["Tell me about yourself."]
    payload["per_question"] = [None]
    main._persist_session_state(sid, payload)

    new_q = "What is your proudest project, and why?"
    resp = client.post(f"/session/{sid}/questions", json={"question": new_q})
    assert resp.status_code == 200
    body = resp.json()
    assert body["question"] == new_q
    assert body["index"] == 1
    assert body["current_question_index"] == 1
    assert body["questions"][-1] == new_q

    session = client.get(f"/session/{sid}").json()
    assert session["questions"][-1] == new_q
    assert session["current_question_index"] == 1
    assert len(session.get("per_question")) == len(session["questions"])


def test_add_custom_question_trims_and_deduplicates():
    client = TestClient(main.app)
    sid = str(uuid.uuid4())
    payload = _session_payload()
    payload["questions"] = ["Why do you want this role?"]
    payload["per_question"] = [None]
    main._persist_session_state(sid, payload)

    resp = client.post(
        f"/session/{sid}/questions",
        json={"question": "   Why do you want this role?   ", "make_active": False},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["index"] == 0
    assert body["questions"] == ["Why do you want this role?"]
    assert body["current_question_index"] == 0

    session = client.get(f"/session/{sid}").json()
    assert session["current_question_index"] == 0
    assert session["questions"] == ["Why do you want this role?"]


def test_custom_question_controls_render_in_template():
    html_path = ROOT / "app" / "templates" / "index.html"
    html = html_path.read_text(encoding="utf-8")
    assert 'id="custom-question-input"' in html
    assert 'id="add-custom-question"' in html
    assert 'id="clear-custom-question"' in html
