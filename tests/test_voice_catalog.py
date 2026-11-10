import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import app.main as main  # noqa: E402
import app.utils.session_store as store  # noqa: E402


def _seed_session(tmp_path):
    sid = "s-voice-catalog"
    payload = {
        "resume_path": "uploads/resume.txt",
        "job_desc_path": "uploads/job.txt",
        "resume_text": "Sample resume",
        "job_desc_text": "Sample JD",
        "name": "voice_catalog_test",
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


def test_list_voices_returns_catalog():
    client = TestClient(main.app)
    res = client.get("/voices")
    assert res.status_code == 200

    voices = res.json()
    assert isinstance(voices, list)
    ids = {voice.get("id") for voice in voices}
    assert "verse" in ids

    verse = next(v for v in voices if v.get("id") == "verse")
    assert verse.get("preview_url", "").endswith("/voices/preview/verse")


def test_update_session_voice_persists(monkeypatch, tmp_path):
    monkeypatch.setattr(store, "SESSION_DIR", tmp_path)
    client = TestClient(main.app)
    sid = _seed_session(tmp_path)

    res = client.patch(f"/session/{sid}/voice", json={"voice_id": "verse"})
    assert res.status_code == 200
    assert res.json().get("voice_id") == "verse"

    session = main._get_session(sid)
    assert session["voice_settings"]["voice_id"] == "verse"


def test_update_session_voice_rejects_unknown(monkeypatch, tmp_path):
    monkeypatch.setattr(store, "SESSION_DIR", tmp_path)
    client = TestClient(main.app)
    sid = _seed_session(tmp_path)

    res = client.patch(f"/session/{sid}/voice", json={"voice_id": "not-a-voice"})
    assert res.status_code == 400
    assert res.json().get("detail") == "Unknown voice_id"


def test_voice_preview_serves_static_file():
    client = TestClient(main.app)
    res = client.get("/voices/preview/alloy")
    assert res.status_code == 200
    assert res.headers.get("content-type", "").startswith("audio/")
    assert res.content


def test_voice_preview_requires_api_key_when_missing(monkeypatch):
    client = TestClient(main.app)
    monkeypatch.setattr(main, "OPENAI_API_KEY", "")

    original_exists = main.os.path.exists

    def fake_exists(path):
        if path.endswith("gpt-realtime-preview.mp3"):
            return False
        return original_exists(path)

    monkeypatch.setattr(main.os.path, "exists", fake_exists)

    res = client.get("/voices/preview/gpt-realtime")
    assert res.status_code == 503
    assert res.json().get("detail") == "Preview unavailable"


def test_voice_preview_unknown_voice_returns_404():
    client = TestClient(main.app)
    res = client.get("/voices/preview/not-a-voice")
    assert res.status_code == 404
    assert res.json().get("detail") == "Unknown voice"
