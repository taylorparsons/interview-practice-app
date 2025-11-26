import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import app.main as main  # noqa: E402
import app.utils.session_store as store  # noqa: E402


def test_generate_questions_includes_followups(monkeypatch, tmp_path):
    monkeypatch.setattr(store, "SESSION_DIR", tmp_path)
    # seed a session
    sid = "s-followups"
    payload = {
        "resume_path": "uploads/resume.txt",
        "job_desc_path": "uploads/job.txt",
        "resume_text": "R",
        "job_desc_text": "JD",
        "name": "followup_test",
        "questions": [],
        "question_followups": [],
        "answers": [],
        "evaluations": [],
        "agent": None,
        "current_question_index": 0,
        "voice_transcripts": {},
        "voice_agent_text": {},
        "voice_messages": [],
    }
    main._persist_session_state(sid, payload)
    client = TestClient(main.app)

    res = client.post("/generate-questions", json={"session_id": sid, "num_questions": 2})
    assert res.status_code == 200
    body = res.json()
    assert "follow_ups" in body
    followups = body["follow_ups"]
    assert isinstance(followups, list)
    assert len(followups) == 2
    session = main._get_session(sid)
    assert len(session.get("question_followups") or []) == len(session.get("questions") or [])
