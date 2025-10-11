import json
import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import app.main as main  # noqa: E402


CATALOG_PATH = Path(main.__file__).parent / "voice_catalog.json"
VOICES_DIR = ROOT_DIR / "app" / "static" / "voices"


def _read_catalog():
    with open(CATALOG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _write_catalog(data):
    with open(CATALOG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


@pytest.fixture
def client():
    return TestClient(main.app)


def test_preview_serves_cached_file(client, tmp_path):
    voices = _read_catalog()
    test_id = "testcached"
    try:
        # Ensure catalog entry exists and mtime changes
        if not any(v.get("id") == test_id for v in voices):
            voices.append({"id": test_id, "label": "Test Cached", "preview_url": f"/voices/preview/{test_id}"})
            _write_catalog(voices)

        # Create a dummy cached mp3
        VOICES_DIR.mkdir(parents=True, exist_ok=True)
        p = VOICES_DIR / f"{test_id}-preview.mp3"
        payload = b"ID3FAKE-CACHED"
        with open(p, "wb") as f:
            f.write(payload)

        r = client.get(f"/voices/preview/{test_id}")
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("audio/mpeg")
        assert r.content == payload
    finally:
        # Cleanup
        try:
            (VOICES_DIR / f"{test_id}-preview.mp3").unlink()
        except FileNotFoundError:
            pass
        # Restore catalog
        base = [v for v in _read_catalog() if v.get("id") != test_id]
        _write_catalog(base)


def _fake_tts_client_factory(audio_bytes: bytes, record: dict):
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
                content = audio_bytes

                def raise_for_status(self):
                    return None

            return _Resp()

    return _FakeAsyncClient


def test_preview_synthesizes_and_caches_when_missing(client, monkeypatch):
    voices = _read_catalog()
    test_id = "newsynth"
    mp3_path = VOICES_DIR / f"{test_id}-preview.mp3"
    try:
        if not any(v.get("id") == test_id for v in voices):
            voices.append({"id": test_id, "label": "New Synth", "preview_url": f"/voices/preview/{test_id}"})
            _write_catalog(voices)

        # Ensure no cached file
        if mp3_path.exists():
            mp3_path.unlink()

        # Mock API key and TTS HTTP client
        monkeypatch.setattr(main, "OPENAI_API_KEY", "test_key")
        fake_audio = b"ID3FAKE-SYNTH"
        captured = {}
        monkeypatch.setattr(main.httpx, "AsyncClient", _fake_tts_client_factory(fake_audio, captured))

        r = client.get(f"/voices/preview/{test_id}")
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("audio/mpeg")
        assert r.content == fake_audio
        # Cached file written
        assert mp3_path.exists() and mp3_path.stat().st_size == len(fake_audio)

        # On second call, ensure it serves cached file (no TTS). Replace client to raise if called.
        class _FailClient:
            async def __aenter__(self):
                raise AssertionError("TTS should not be called when cache exists")
            async def __aexit__(self, *args, **kwargs):
                return False

        monkeypatch.setattr(main.httpx, "AsyncClient", _FailClient)
        r2 = client.get(f"/voices/preview/{test_id}")
        assert r2.status_code == 200
        assert r2.content == fake_audio
    finally:
        try:
            mp3_path.unlink()
        except FileNotFoundError:
            pass
        base = [v for v in _read_catalog() if v.get("id") != test_id]
        _write_catalog(base)


def test_preview_unknown_voice_returns_404(client):
    # Use an id unlikely to exist in catalog
    r = client.get("/voices/preview/does-not-exist--12345")
    assert r.status_code == 404


def test_preview_returns_503_without_key_and_no_cache(client):
    voices = _read_catalog()
    test_id = "nokey"
    try:
        if not any(v.get("id") == test_id for v in voices):
            voices.append({"id": test_id, "label": "No Key", "preview_url": f"/voices/preview/{test_id}"})
            _write_catalog(voices)
        mp3 = VOICES_DIR / f"{test_id}-preview.mp3"
        if mp3.exists():
            mp3.unlink()
        # Ensure API key is blank
        main.OPENAI_API_KEY = ""
        r = client.get(f"/voices/preview/{test_id}")
        assert r.status_code == 503
    finally:
        try:
            (VOICES_DIR / f"{test_id}-preview.mp3").unlink()
        except FileNotFoundError:
            pass
        base = [v for v in _read_catalog() if v.get("id") != test_id]
        _write_catalog(base)


def test_catalog_cache_invalidation(client):
    original = _read_catalog()
    new_id = "tmpinvalidate"
    try:
        if not any(v.get("id") == new_id for v in original):
            updated = list(original) + [{"id": new_id, "label": "Tmp", "preview_url": f"/voices/preview/{new_id}"}]
            _write_catalog(updated)
        res = client.get("/voices")
        assert res.status_code == 200
        ids = {v.get("id") for v in res.json()}
        assert new_id in ids
    finally:
        _write_catalog(original)


def test_session_payload_includes_voice_settings(client):
    # Create a minimal session
    sid = "session_voice_settings"
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
    }
    main._persist_session_state(sid, payload)
    r = client.patch(f"/session/{sid}/voice", json={"voice_id": "verse"})
    assert r.status_code == 200
    res = client.get(f"/session/{sid}")
    assert res.status_code == 200
    data = res.json()
    assert data.get("voice_settings", {}).get("voice_id") == "verse"


def test_voices_list_includes_all_expected_ids(client):
    res = client.get("/voices")
    assert res.status_code == 200
    ids = {v.get("id") for v in res.json()}
    expected = {
        "alloy", "ash", "ballad", "cedar", "coral",
        "echo", "marin", "sage", "shimmer", "verse",
    }
    assert expected.issubset(ids)

