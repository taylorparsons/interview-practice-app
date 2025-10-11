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


def test_voice_messages_include_question_index_in_session_payload(session_factory, client):
    session_id = session_factory()

    # Append candidate and coach messages tied to a specific question index
    qidx = 5
    client.post(
        f"/session/{session_id}/voice-messages",
        json={"role": "user", "text": "My answer for q5", "question_index": qidx},
    )
    client.post(
        f"/session/{session_id}/voice-messages",
        json={"role": "agent", "text": "Coach feedback for q5", "question_index": qidx},
    )

    payload = client.get(f"/session/{session_id}").json()
    msgs = [m for m in payload["voice_messages"] if m.get("question_index") == qidx]

    assert len(msgs) == 2
    assert all("question_index" in m for m in msgs)
    assert msgs[0]["question_index"] == qidx and msgs[1]["question_index"] == qidx


def test_role_synonyms_are_normalized(session_factory, client):
    """Posting assistant/agent should normalize to coach; candidate stays candidate."""
    session_id = session_factory()

    # Post as 'assistant' (should become coach)
    r1 = client.post(
        f"/session/{session_id}/voice-messages",
        json={"role": "assistant", "text": "Coach guidance.", "question_index": 1},
    )
    assert r1.status_code == 200

    # Post as 'candidate'
    r2 = client.post(
        f"/session/{session_id}/voice-messages",
        json={"role": "candidate", "text": "My answer.", "question_index": 1},
    )
    assert r2.status_code == 200

    data = client.get(f"/session/{session_id}").json()
    roles = [m["role"] for m in data["voice_messages"] if m.get("question_index") == 1]
    assert set(roles) == {"coach", "candidate"}
    assert data["voice_agent_text"]["1"] == "Coach guidance."
    assert data["voice_transcripts"]["1"] == "My answer."


def test_transcript_and_coach_text_aggregate_across_messages(session_factory, client):
    session_id = session_factory()

    # Two user messages for same index
    client.post(
        f"/session/{session_id}/voice-messages",
        json={"role": "user", "text": "Part A", "question_index": 0},
    )
    client.post(
        f"/session/{session_id}/voice-messages",
        json={"role": "user", "text": "Part B", "question_index": 0},
    )

    # Two coach messages for same index
    client.post(
        f"/session/{session_id}/voice-messages",
        json={"role": "agent", "text": "Coach A", "question_index": 0},
    )
    client.post(
        f"/session/{session_id}/voice-messages",
        json={"role": "agent", "text": "Coach B", "question_index": 0},
    )

    data = client.get(f"/session/{session_id}").json()
    assert data["voice_transcripts"]["0"] == "Part A\nPart B"
    assert data["voice_agent_text"]["0"] == "Coach A\nCoach B"


def test_stream_flag_persists_on_entries(session_factory, client):
    session_id = session_factory()
    client.post(
        f"/session/{session_id}/voice-messages",
        json={"role": "user", "text": "interim", "question_index": 2, "stream": True},
    )
    client.post(
        f"/session/{session_id}/voice-messages",
        json={"role": "user", "text": "final", "question_index": 2, "stream": False},
    )
    data = client.get(f"/session/{session_id}").json()
    entries = [m for m in data["voice_messages"] if m.get("question_index") == 2]
    assert entries[0]["text"] == "interim" and entries[0].get("stream") is True
    assert entries[1]["text"] == "final" and entries[1].get("stream") is False


def test_legacy_session_backfills_missing_voice_fields(client):
    """Older sessions without voice keys are backfilled with defaults on read."""
    import uuid
    sid = str(uuid.uuid4())
    now = "2024-01-01T00:00:00Z"
    legacy_payload = {
        "resume_path": "uploads/resume.txt",
        "job_desc_path": "uploads/job.txt",
        "resume_text": "Sample",
        "job_desc_text": "Sample JD",
        "name": "legacy",
        "questions": ["Tell me about yourself."],
        "answers": [],
        "evaluations": [],
        "agent": None,
        "current_question_index": 0,
        "created_at": now,
        "updated_at": now,
        # Missing or None voice fields
        "voice_transcripts": None,
        "voice_agent_text": None,
        "voice_messages": None,
    }
    # Persist directly via internal helper
    from app.main import _persist_session_state
    _persist_session_state(sid, legacy_payload)

    res = client.get(f"/session/{sid}")
    assert res.status_code == 200
    payload = res.json()
    assert isinstance(payload.get("voice_transcripts"), dict)
    assert isinstance(payload.get("voice_agent_text"), dict)
    assert isinstance(payload.get("voice_messages"), list)
