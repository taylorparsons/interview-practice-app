import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import app.main as main  # noqa: E402


@pytest.fixture
def client():
    return TestClient(main.app)


def test_get_voices_catalog(client):
    res = client.get('/voices')
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert all('id' in v and 'label' in v for v in data)


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
                        "id": "sess_abc",
                        "model": json.get("model", "gpt-realtime-mini"),
                        "client_secret": {"value": "secret_xyz"},
                        "expires_at": 4102444800,
                    }
            return _Dummy()
    return _FakeAsyncClient


def test_set_voice_persists_and_used_in_realtime(client, monkeypatch, tmp_path):
    # Create a new session using the existing upload flow shortcuts
    # Build a dummy session via direct persist to avoid heavy flows
    sid = 'session_for_voice'
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
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
        "voice_transcripts": {},
        "voice_agent_text": {},
        "voice_messages": [],
    }
    main._persist_session_state(sid, payload)

    # Update voice to a known catalog id
    r = client.patch(f"/session/{sid}/voice", json={"voice_id": "verse"})
    assert r.status_code == 200
    assert r.json()["voice_id"] == "verse"

    # Stub HTTP client and assert voice is passed in realtime payload
    captured = {}
    monkeypatch.setattr(main, "OPENAI_API_KEY", "test_key")
    monkeypatch.setattr(main.httpx, "AsyncClient", _fake_async_client_factory(captured))
    resp = client.post('/voice/session', json={"session_id": sid})
    assert resp.status_code == 200
    payload = captured.get('json')
    assert payload is not None
    assert payload.get('voice') == 'verse'


def test_set_voice_rejects_unknown_id(client):
    # Attempt to set a non-existent voice id
    sid = 'session_unknown_voice'
    main._persist_session_state(sid, {
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
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
        "voice_transcripts": {},
        "voice_agent_text": {},
        "voice_messages": [],
    })
    r = client.patch(f"/session/{sid}/voice", json={"voice_id": "does-not-exist"})
    assert r.status_code == 400
