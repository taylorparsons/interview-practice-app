import sys
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.main import app, _persist_session_state, active_sessions


SESSION_DIR = Path("app/session_store")


def _base_session_payload():
    now = "2024-01-01T00:00:00Z"
    return {
        "resume_path": "uploads/resume.txt",
        "job_desc_path": "uploads/job.txt",
        "resume_text": "Sample resume",
        "job_desc_text": "Sample job description",
        "name": "test_session",
        "questions": ["Tell me about yourself."],
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


@pytest.fixture
def session_factory():
    created = []

    def _create():
        session_id = str(uuid.uuid4())
        payload = _base_session_payload()
        _persist_session_state(session_id, payload)
        created.append(session_id)
        return session_id

    yield _create

    for session_id in created:
        active_sessions.pop(session_id, None)
        path = SESSION_DIR / f"{session_id}.json"
        if path.exists():
            path.unlink()


@pytest.fixture
def client():
    return TestClient(app)


def test_candidate_message_persists_transcript_and_metrics(session_factory, client, caplog):
    session_id = session_factory()

    with caplog.at_level("INFO"):
        response = client.post(
            f"/session/{session_id}/voice-messages",
            json={"role": "user", "text": "I enjoy product design", "question_index": 0},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True

    session_response = client.get(f"/session/{session_id}")
    assert session_response.status_code == 200
    session_data = session_response.json()

    assert session_data["voice_messages"][-1]["role"] == "candidate"
    assert session_data["voice_messages"][-1]["text"] == "I enjoy product design"
    assert session_data["voice_transcripts"]["0"] == "I enjoy product design"

    metric_logs = [
        record for record in caplog.records if record.message.startswith("voice.transcript.metric")
    ]
    assert metric_logs, "Expected transcript metric log entry when candidate message persisted."
    metric_message = metric_logs[-1].message
    assert "candidate_count=" in metric_message and "coach_count=" in metric_message


def test_coach_message_appends_and_updates_history(session_factory, client):
    session_id = session_factory()

    client.post(
        f"/session/{session_id}/voice-messages",
        json={"role": "user", "text": "Candidate response", "question_index": 0},
    )
    response = client.post(
        f"/session/{session_id}/voice-messages",
        json={"role": "agent", "text": "Thanks for sharing that detail.", "question_index": 0},
    )
    assert response.status_code == 200
    assert response.json()["ok"] is True

    session_response = client.get(f"/session/{session_id}")
    data = session_response.json()

    roles = [entry["role"] for entry in data["voice_messages"]]
    assert roles == ["candidate", "coach"]
    assert data["voice_agent_text"]["0"] == "Thanks for sharing that detail."


def test_session_payload_read_by_ui_contains_dual_role_messages(session_factory, client):
    """Simulate the UI fetch to make sure both roles are present and ordered."""
    session_id = session_factory()

    first_chunk = client.post(
        f"/session/{session_id}/voice-messages",
        json={"role": "user", "text": "This is my answer.", "question_index": 0},
    )
    assert first_chunk.status_code == 200

    second_chunk = client.post(
        f"/session/{session_id}/voice-messages",
        json={"role": "agent", "text": "Coach feedback here.", "question_index": 0},
    )
    assert second_chunk.status_code == 200

    session_data = client.get(f"/session/{session_id}").json()
    voice_messages = session_data["voice_messages"]

    assert len(voice_messages) == 2
    assert voice_messages[0]["role"] == "candidate"
    assert voice_messages[0]["text"] == "This is my answer."
    assert voice_messages[1]["role"] == "coach"
    assert voice_messages[1]["text"] == "Coach feedback here."


def test_identical_texts_do_not_cross_roles(session_factory, client):
    """Even identical text snippets must maintain the original roles."""
    session_id = session_factory()
    prompt_text = "Hello and welcome. Let's begin the interview."

    first = client.post(
        f"/session/{session_id}/voice-messages",
        json={"role": "user", "text": prompt_text, "question_index": 2},
    )
    assert first.status_code == 200

    second = client.post(
        f"/session/{session_id}/voice-messages",
        json={"role": "agent", "text": prompt_text, "question_index": 2},
    )
    assert second.status_code == 200

    data = client.get(f"/session/{session_id}").json()
    entries = [entry for entry in data["voice_messages"] if entry.get("question_index") == 2]
    assert entries[0]["role"] == "candidate"
    assert entries[0]["text"] == prompt_text
    assert entries[1]["role"] == "coach"
    assert entries[1]["text"] == prompt_text
