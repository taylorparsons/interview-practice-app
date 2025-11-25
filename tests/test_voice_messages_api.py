import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import app.main as main  # noqa: E402
import app.utils.session_store as store  # noqa: E402
from app.config import OPENAI_REALTIME_VOICE  # noqa: E402


def _seed_session(tmp_path):
    sid = "s-voice"
    payload = {
        "resume_path": "uploads/resume.txt",
        "job_desc_path": "uploads/job.txt",
        "resume_text": "Sample resume",
        "job_desc_text": "Sample JD",
        "name": "voice_test",
        "questions": ["Tell me about yourself."],
        "answers": [],
        "evaluations": [],
        "agent": None,
        "current_question_index": 0,
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
    }
    main.active_sessions.clear()
    store.save_session(sid, payload)
    return sid


def test_voice_messages_persist_both_roles(monkeypatch, tmp_path):
    monkeypatch.setattr(store, "SESSION_DIR", tmp_path)
    client = TestClient(main.app)
    sid = _seed_session(tmp_path)

    r1 = client.post(
        f"/session/{sid}/voice-messages",
        json={"role": "user", "text": "candidate says hi", "question_index": 0, "timestamp": "2024-01-01T00:00:01Z"},
    )
    assert r1.status_code == 200 and r1.json().get("ok") is True

    r2 = client.post(
        f"/session/{sid}/voice-messages",
        json={"role": "assistant", "text": "coach reply", "question_index": 0, "timestamp": "2024-01-01T00:00:02Z"},
    )
    assert r2.status_code == 200 and r2.json().get("ok") is True

    session = main._get_session(sid)
    assert session["voice_messages"][0]["role"] == "candidate"
    assert session["voice_messages"][0]["question_index"] == 0
    assert session["voice_messages"][1]["role"] == "coach"
    assert session["voice_messages"][1]["question_index"] == 0
    assert session["voice_transcripts"]["0"].startswith("candidate says hi")
    assert session["voice_agent_text"]["0"].startswith("coach reply")


def _fake_realtime_client(record):
    class _FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, headers=None, json=None):
            record["url"] = url
            record["headers"] = headers
            record["json"] = json

            class _Resp:
                status_code = 200

                def raise_for_status(self_inner):
                    return None

                def json(self_inner):
                    return {
                        "id": "rt_123",
                        "model": json.get("model"),
                        "client_secret": {"value": "secret"},
                        "expires_at": 123,
                    }

            return _Resp()

    return _FakeAsyncClient


def test_realtime_session_payload_includes_transcription(monkeypatch, tmp_path):
    monkeypatch.setattr(store, "SESSION_DIR", tmp_path)
    main.active_sessions.clear()
    sid = _seed_session(tmp_path)

    monkeypatch.setattr(main, "OPENAI_API_KEY", "test_key")
    captured = {}
    monkeypatch.setattr(main.httpx, "AsyncClient", _fake_realtime_client(captured))

    client = TestClient(main.app)
    res = client.post("/voice/session", json={"session_id": sid})
    assert res.status_code == 200
    payload = captured["json"]
    assert payload["voice"] == OPENAI_REALTIME_VOICE
    assert payload["input_audio_transcription"]["model"] == main.OPENAI_INPUT_TRANSCRIPTION_MODEL
