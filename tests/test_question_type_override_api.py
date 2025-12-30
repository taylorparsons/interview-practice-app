import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import app.main as main  # noqa: E402
import app.utils.session_store as store  # noqa: E402
from app.utils.question_type import normalize_question_text  # noqa: E402


def _seed_session(tmp_path):
    sid = "s-question-type"
    payload = {
        "resume_path": "uploads/resume.txt",
        "job_desc_path": "uploads/job.txt",
        "resume_text": "R",
        "job_desc_text": "JD",
        "name": "type_test",
        "questions": ["Tell me about yourself."],
        "answers": [],
        "evaluations": [],
        "agent": None,
        "current_question_index": 0,
        "voice_transcripts": {},
        "voice_agent_text": {},
        "voice_messages": [],
    }
    main.active_sessions.clear()
    store.save_session(sid, payload)
    return sid


def test_question_type_override_roundtrip(monkeypatch, tmp_path):
    monkeypatch.setattr(store, "SESSION_DIR", tmp_path)
    sid = _seed_session(tmp_path)
    client = TestClient(main.app)

    resp = client.patch(
        f"/session/{sid}/question-type",
        json={"question": "Tell me about yourself.", "question_type": "narrative"},
    )
    assert resp.status_code == 200
    data = resp.json()
    key = normalize_question_text("Tell me about yourself.")
    assert data["question_type_overrides"][key] == "narrative"

    session = client.get(f"/session/{sid}").json()
    assert session["question_type_overrides"][key] == "narrative"


def test_question_type_override_auto_clears(monkeypatch, tmp_path):
    monkeypatch.setattr(store, "SESSION_DIR", tmp_path)
    sid = _seed_session(tmp_path)
    client = TestClient(main.app)
    key = normalize_question_text("Tell me about yourself.")

    resp = client.patch(
        f"/session/{sid}/question-type",
        json={"question": "Tell me about yourself.", "question_type": "behavioral"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["question_type_overrides"][key] == "behavioral"

    resp = client.patch(
        f"/session/{sid}/question-type",
        json={"question": "Tell me about yourself.", "question_type": "auto"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert key not in data["question_type_overrides"]
