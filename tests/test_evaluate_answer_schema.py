import logging
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import app.main as main  # noqa: E402
import app.utils.session_store as store  # noqa: E402


class _InvalidAgent:
    def __init__(self, counter):
        self.counter = counter

    async def evaluate_answer(self, question, answer, transcript_text, level=None):
        self.counter["count"] += 1
        # Return a malformed payload (missing required fields)
        return {"foo": "bar"}


def _seed_session(tmp_path):
    sid = "s-eval-schema"
    payload = {
        "resume_path": "uploads/resume.txt",
        "job_desc_path": "uploads/job.txt",
        "resume_text": "R",
        "job_desc_text": "JD",
        "name": "schema_test",
        "questions": ["Q1"],
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


def test_invalid_evaluation_payload_uses_fallback_and_logs_at_info(monkeypatch, tmp_path, caplog):
    monkeypatch.setattr(store, "SESSION_DIR", tmp_path)
    sid = _seed_session(tmp_path)

    # Shared counter to track all agent calls across retries
    call_counter = {"count": 0}
    # Seed initial stub agent
    session = main._get_session(sid)
    session["agent"] = _InvalidAgent(call_counter)
    main.active_sessions[sid] = session

    async def _fake_start_agent(session_id: str):
        sess = main._get_session(session_id)
        sess["agent"] = _InvalidAgent(call_counter)
        main.active_sessions[session_id] = sess
        store.save_session(session_id, sess)

    monkeypatch.setattr(main, "start_agent", _fake_start_agent)
    client = TestClient(main.app)

    caplog.set_level(logging.INFO)
    resp = client.post(
        "/evaluate-answer",
        json={"session_id": sid, "question": "Q1", "answer": "A1"},
    )
    assert resp.status_code == 200
    body = resp.json()
    eval_payload = body.get("evaluation") or {}
    # Should fall back to heuristic response with expected keys
    assert isinstance(eval_payload.get("score"), int)
    assert "feedback" in eval_payload
    # Agent should have been attempted twice (minimal retries) before fallback
    assert call_counter["count"] == 2
    # Ensure we didn't emit warnings/errors for the invalid schema path
    assert not [r for r in caplog.records if r.levelno > logging.INFO]
    assert any("evaluation.schema.invalid" in r.getMessage() for r in caplog.records)
