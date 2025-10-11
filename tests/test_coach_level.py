import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import app.main as main  # noqa: E402


@pytest.fixture
def client():
    return TestClient(main.app)


def _fake_async_client_factory(captured: dict):
    class _FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, headers=None, json=None):
            captured["url"] = url
            captured["headers"] = headers
            captured["json"] = json

            class _Dummy:
                def __init__(self):
                    self.status_code = 200

                def raise_for_status(self):
                    return None

                def json(self):
                    return {
                        "id": "sess_xyz",
                        "model": json.get("model", "gpt-realtime-mini"),
                        "client_secret": {"value": "secret_123"},
                        "expires_at": 4102444800,
                    }

            return _Dummy()

    return _FakeAsyncClient


def test_set_coach_level_affects_voice_instructions(client, monkeypatch):
    # Create a dummy session payload directly
    sid = 'session_coach_level'
    now = "2024-01-01T00:00:00Z"
    payload = {
        "resume_path": "uploads/resume.txt",
        "job_desc_path": "uploads/job.txt",
        "resume_text": "Sample",
        "job_desc_text": "Sample JD",
        "name": "voice_test",
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
        "coach_level": "level_2",
    }
    main._persist_session_state(sid, payload)

    # Set coach level to level_1
    r = client.patch(f"/session/{sid}/coach-level", json={"level": "level_1"})
    assert r.status_code == 200
    assert r.json()["level"] == "level_1"

    captured = {}
    monkeypatch.setattr(main, "OPENAI_API_KEY", "test_key")
    monkeypatch.setattr(main.httpx, "AsyncClient", _fake_async_client_factory(captured))

    resp = client.post('/voice/session', json={"session_id": sid})
    assert resp.status_code == 200
    payload = captured.get('json')
    assert payload is not None
    assert "instructions" in payload
    assert "Selected Level: level_1" in payload["instructions"]

