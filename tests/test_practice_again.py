import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import app.main as main  # noqa: E402
import app.utils.session_store as store  # noqa: E402
from app.config import OPENAI_MODEL  # noqa: E402


def _seed_session(tmp_path):
    sid = "s-practice"
    payload = {
        "resume_path": "uploads/resume.txt",
        "job_desc_path": "uploads/job.txt",
        "resume_text": "Sample resume",
        "job_desc_text": "Sample JD",
        "name": "practice_test",
        "questions": ["Q1", "Q2"],
        "answers": [{"question": "Q1", "answer": "A1"}],
        "evaluations": [{"score": 5}],
        "per_question": [{"score": 5}, None],
        "agent": "placeholder",
        "current_question_index": 1,
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
        "voice_transcripts": {"0": "user spoke"},
        "voice_agent_text": {"0": "coach said"},
        "voice_messages": [{"role": "candidate", "text": "hi"}, {"role": "coach", "text": "hello"}],
        "voice_settings": {"voice_id": "verse", "model_id": "gpt-4o-mini"},
    }
    main.active_sessions.clear()
    store.save_session(sid, payload)
    return sid


def test_practice_again_resets_and_records_history(monkeypatch, tmp_path):
    monkeypatch.setattr(store, "SESSION_DIR", tmp_path)
    sid = _seed_session(tmp_path)
    client = TestClient(main.app)

    res = client.post(f"/session/{sid}/practice-again", json={"add_questions": ["Q3"]})
    assert res.status_code == 200
    data = res.json()

    history = data.get("practice_history") or []
    assert len(history) == 1
    entry = history[0]
    assert entry["voice_id"] == "verse"
    assert entry["model_id"] in {"gpt-4o-mini", OPENAI_MODEL}
    assert entry["question_ids"] == ["Q1", "Q2"]

    session = main._get_session(sid)
    assert session["answers"] == []
    assert session["evaluations"] == []
    assert session["voice_messages"] == []
    assert session["voice_transcripts"] == {}
    assert session["voice_agent_text"] == {}
    assert session["per_question"] == [None, None, None]
    assert session["questions"] == ["Q1", "Q2", "Q3"]
    assert session["current_question_index"] == 0
    assert session.get("agent") is None
