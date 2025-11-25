import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import app.main as main  # noqa: E402
import app.utils.session_store as store  # noqa: E402


def _seed_session(tmp_path):
    sid = "s-settings"
    payload = {
        "resume_path": "uploads/resume.txt",
        "job_desc_path": "uploads/job.txt",
        "resume_text": "Sample resume",
        "job_desc_text": "Sample JD",
        "name": "settings_test",
        "questions": ["Q1"],
        "answers": [],
        "evaluations": [],
        "voice_settings": {"voice_id": "verse", "model_id": "gpt-4o-mini", "thinking_effort": "medium", "verbosity": "balanced"},
        "agent": "placeholder",
    }
    main.active_sessions.clear()
    store.save_session(sid, payload)
    return sid


def test_update_session_settings(monkeypatch, tmp_path):
    monkeypatch.setattr(store, "SESSION_DIR", tmp_path)
    sid = _seed_session(tmp_path)
    client = TestClient(main.app)

    res = client.patch(
        f"/session/{sid}/settings",
        json={"model_id": "gpt-5-mini", "thinking_effort": "high", "verbosity": "low"},
    )
    assert res.status_code == 200
    data = res.json()
    vs = data.get("voice_settings") or {}
    assert vs["model_id"] == "gpt-5-mini"
    assert vs["thinking_effort"] == "high"
    assert vs["verbosity"] == "low"

    session = main._get_session(sid)
    assert session["agent"] is None  # forced restart


def test_update_session_settings_rejects_invalid_model(monkeypatch, tmp_path):
    monkeypatch.setattr(store, "SESSION_DIR", tmp_path)
    sid = _seed_session(tmp_path)
    client = TestClient(main.app)

    res = client.patch(f"/session/{sid}/settings", json={"model_id": "not-real"})
    assert res.status_code == 400
