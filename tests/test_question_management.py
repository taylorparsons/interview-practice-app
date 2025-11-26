import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import app.main as main  # noqa: E402
import app.utils.session_store as store  # noqa: E402


class _StubAgent:
    def __init__(self, generated):
        self.generated = generated
        self.calls = 0

    async def generate_interview_questions(self, num_questions: int = 5, prompt_hint=None):
        self.calls += 1
        return self.generated[:num_questions]


def test_generate_additional_questions_appends(monkeypatch, tmp_path):
    monkeypatch.setattr(store, "SESSION_DIR", tmp_path)
    sid = "s-gen-more"
    agent = _StubAgent(["New Q2", "New Q3", "New Q4"])
    payload = {
        "resume_path": "uploads/resume.txt",
        "job_desc_path": "uploads/job.txt",
        "resume_text": "R",
        "job_desc_text": "JD",
        "name": "gen_more",
        "questions": ["Q1"],
        "per_question": [None],
        "answers": [],
        "evaluations": [],
        "agent": agent,
        "current_question_index": 0,
        "voice_transcripts": {},
        "voice_agent_text": {},
        "voice_messages": [],
    }
    store.save_session(sid, payload)
    main.active_sessions[sid] = payload

    client = TestClient(main.app)
    res = client.post(f"/session/{sid}/questions/generate-more", json={"num_questions": 2})
    assert res.status_code == 200
    data = res.json()
    assert data["questions"] == ["Q1", "New Q2", "New Q3"]
    assert agent.calls == 1

    session = main._get_session(sid)
    assert session["questions"] == ["Q1", "New Q2", "New Q3"]
    assert len(session.get("per_question")) == 3


def test_delete_questions_reindexes_and_cleans_state(monkeypatch, tmp_path):
    monkeypatch.setattr(store, "SESSION_DIR", tmp_path)
    sid = "s-del-q"
    payload = {
        "resume_path": "uploads/resume.txt",
        "job_desc_path": "uploads/job.txt",
        "resume_text": "R",
        "job_desc_text": "JD",
        "name": "del_test",
        "questions": ["Q1", "Q2", "Q3"],
        "answers": [
            {"question": "Q1", "answer": "A1"},
            {"question": "Q2", "answer": "A2"},
        ],
        "evaluations": [
            {"score": 1, "feedback": "f1"},
            {"score": 2, "feedback": "f2"},
        ],
        "per_question": [
            {"score": 1},
            {"score": 2},
            {"score": 3},
        ],
        "agent": None,
        "current_question_index": 2,
        "voice_transcripts": {"0": "t1", "1": "t2", "2": "t3"},
        "voice_agent_text": {"0": "c1", "1": "c2", "2": "c3"},
        "voice_messages": [
            {"role": "candidate", "text": "hi", "question_index": 1},
            {"role": "coach", "text": "hey", "question_index": 2},
        ],
    }
    store.save_session(sid, payload)
    main.active_sessions[sid] = payload

    client = TestClient(main.app)
    res = client.request("DELETE", f"/session/{sid}/questions", json={"indices": [1]})
    assert res.status_code == 200
    body = res.json()
    assert body["questions"] == ["Q1", "Q3"]
    assert body["current_question_index"] == 1

    sess = main._get_session(sid)
    assert sess["questions"] == ["Q1", "Q3"]
    assert len(sess["per_question"]) == 2
    assert sess["per_question"][1]["score"] == 3  # reindexed from old index 2
    assert len(sess["answers"]) == 1
    assert sess["answers"][0]["question"] == "Q1"
    assert len(sess["evaluations"]) == 1
    assert sess["voice_transcripts"] == {"0": "t1", "1": "t3"}
    assert sess["voice_agent_text"] == {"0": "c1", "1": "c3"}
    # voice message for removed idx dropped, later idx reindexed
    msgs = sess["voice_messages"]
    assert len(msgs) == 1
    assert msgs[0]["question_index"] == 1
