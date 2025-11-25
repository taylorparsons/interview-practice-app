import sys
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import app.main as main  # noqa: E402


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
        main._persist_session_state(session_id, payload)
        created.append(session_id)
        return session_id

    yield _create

    for session_id in created:
        main.active_sessions.pop(session_id, None)
        path = SESSION_DIR / f"{session_id}.json"
        if path.exists():
            path.unlink()


@pytest.fixture
def client():
    return TestClient(main.app)


class _DummyResponse:
    def __init__(self, payload: dict, status_code: int = 200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code and self.status_code >= 400:
            # Mimic httpx exception shape when needed
            raise Exception(f"HTTP {self.status_code}")

    def json(self):
        return self._payload

    @property
    def text(self):
        return str(self._payload)


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
            # Return a minimal successful realtime session response
            return _DummyResponse(
                {
                    "id": "sess_123",
                    "model": json.get("model", "gpt-realtime-mini"),
                    "client_secret": {"value": "secret_abc"},
                    # Any epoch-like int works for model validation
                    "expires_at": 4102444800,
                }
            )

    return _FakeAsyncClient


def test_voice_session_includes_input_transcription_when_configured(
    session_factory, client, monkeypatch
):
    session_id = session_factory()

    # Ensure API key and config are set for the endpoint
    monkeypatch.setattr(main, "OPENAI_API_KEY", "test_key")
    monkeypatch.setattr(main, "OPENAI_INPUT_TRANSCRIPTION_MODEL", "gpt-4o-mini-transcribe")

    captured = {}
    monkeypatch.setattr(main.httpx, "AsyncClient", _fake_async_client_factory(captured))

    resp = client.post("/voice/session", json={"session_id": session_id})
    assert resp.status_code == 200

    # Validate outbound payload to realtime sessions API
    payload = captured.get("json")
    assert payload is not None
    assert payload["model"] == main.OPENAI_REALTIME_MODEL
    assert payload["voice"] == main.OPENAI_REALTIME_VOICE
    assert payload.get("input_audio_transcription") == {
        "model": "gpt-4o-mini-transcribe"
    }


def test_voice_session_omits_input_transcription_when_disabled(
    session_factory, client, monkeypatch
):
    session_id = session_factory()

    # Disable server-side transcription via empty model string
    monkeypatch.setattr(main, "OPENAI_API_KEY", "test_key")
    monkeypatch.setattr(main, "OPENAI_INPUT_TRANSCRIPTION_MODEL", "")

    captured = {}
    monkeypatch.setattr(main.httpx, "AsyncClient", _fake_async_client_factory(captured))

    resp = client.post("/voice/session", json={"session_id": session_id})
    assert resp.status_code == 200

    payload = captured.get("json")
    assert payload is not None
    assert "input_audio_transcription" not in payload


def test_voice_session_turn_detection_none_sets_type_none(
    session_factory, client, monkeypatch
):
    session_id = session_factory()

    monkeypatch.setattr(main, "OPENAI_API_KEY", "test_key")
    monkeypatch.setattr(main, "OPENAI_INPUT_TRANSCRIPTION_MODEL", "gpt-4o-mini-transcribe")
    monkeypatch.setattr(main, "OPENAI_TURN_DETECTION", "none")

    captured = {}
    monkeypatch.setattr(main.httpx, "AsyncClient", _fake_async_client_factory(captured))

    resp = client.post("/voice/session", json={"session_id": session_id})
    assert resp.status_code == 200

    payload = captured.get("json")
    assert payload is not None
    assert payload.get("turn_detection") == {"type": "none"}


def test_voice_session_server_vad_parses_thresholds(
    session_factory, client, monkeypatch
):
    session_id = session_factory()

    monkeypatch.setattr(main, "OPENAI_API_KEY", "test_key")
    monkeypatch.setattr(main, "OPENAI_TURN_DETECTION", "server_vad")
    # Provide string inputs to validate parsing into float/int types
    monkeypatch.setattr(main, "OPENAI_TURN_THRESHOLD", "0.7")
    monkeypatch.setattr(main, "OPENAI_TURN_PREFIX_MS", "250")
    monkeypatch.setattr(main, "OPENAI_TURN_SILENCE_MS", "600")

    captured = {}
    monkeypatch.setattr(main.httpx, "AsyncClient", _fake_async_client_factory(captured))

    resp = client.post("/voice/session", json={"session_id": session_id})
    assert resp.status_code == 200

    payload = captured.get("json")
    assert payload is not None
    assert payload.get("turn_detection") == {
        "type": "server_vad",
        "threshold": 0.7,
        "prefix_padding_ms": 250,
        "silence_duration_ms": 600,
    }


def test_voice_session_starts_from_current_question(session_factory, client, monkeypatch):
    session_id = session_factory()
    session = main._get_session(session_id)
    session["questions"] = ["Q1", "Q2", "Q3", "Q4"]
    session["current_question_index"] = 2
    main._persist_session_state(session_id, session)

    monkeypatch.setattr(main, "OPENAI_API_KEY", "test_key")
    captured = {}
    monkeypatch.setattr(main.httpx, "AsyncClient", _fake_async_client_factory(captured))

    resp = client.post("/voice/session", json={"session_id": session_id})
    assert resp.status_code == 200
    payload = captured.get("json")
    assert payload is not None
    instructions = payload.get("instructions") or ""
    assert 'exactly as "Q3"' in instructions
    # Ensure question plan prioritizes the current question first
    assert instructions.find("- Q3") < instructions.find("- Q1")
