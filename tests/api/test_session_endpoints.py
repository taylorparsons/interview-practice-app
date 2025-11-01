"""Regression coverage for the FastAPI session endpoints and logging hooks.

These tests mirror the customer-facing scenarios called out in the operations
checklist: document previews, persona updates, transcript persistence, and
voice session telemetry.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import app.main as main_module
from app.main import app
import app.utils.session_store as session_store


@pytest.fixture
def client(monkeypatch, tmp_path) -> TestClient:
    async def fake_start_agent(session_id: str) -> None:
        return None

    monkeypatch.setattr(main_module, "start_agent", fake_start_agent)
    monkeypatch.setattr(main_module, "UPLOAD_FOLDER", tmp_path.as_posix())
    monkeypatch.setattr(session_store, "SESSION_DIR", tmp_path / "session_store")
    main_module.active_sessions.clear()

    client = TestClient(app)
    try:
        yield client
    finally:
        main_module.active_sessions.clear()


def _upload_session(client: TestClient, resume_text: str = "Sample resume text", job_text: str = "Sample job description") -> dict[str, str]:
    files = {
        "resume": ("resume.txt", resume_text, "text/plain"),
    }
    data = {
        "job_description_text": job_text,
    }
    response = client.post("/upload-documents", files=files, data=data)
    assert response.status_code == 200
    return response.json()


def test_session_documents_preview_includes_uploaded_text(client: TestClient) -> None:
    resume_text = "Alice Example Resume"
    job_text = "Role: Senior Engineer\nCompany: Example Co"
    session_meta = _upload_session(client, resume_text=resume_text, job_text=job_text)
    session_id = session_meta["session_id"]

    docs_response = client.get(f"/session/{session_id}/documents")
    assert docs_response.status_code == 200
    payload = docs_response.json()

    resume_payload = payload["resume"]
    job_payload = payload["job_description"]

    assert resume_payload["present"] is True
    assert resume_text in resume_payload["text"]
    assert job_payload["present"] is True
    assert "Senior Engineer" in job_payload["text"]

    # Cleanup to keep the temp workspace tidy
    delete_resp = client.delete(f"/session/{session_id}")
    assert delete_resp.status_code == 200


def test_upload_accepts_doc_resume_with_job_text(client: TestClient) -> None:
    files = {
        "resume": ("resume.doc", b"Binary DOC payload", "application/msword"),
    }
    data = {"job_description_text": "This is the job context."}
    response = client.post("/upload-documents", files=files, data=data)
    assert response.status_code == 200
    session_id = response.json()["session_id"]

    docs_response = client.get(f"/session/{session_id}/documents")
    assert docs_response.status_code == 200
    payload = docs_response.json()

    assert payload["resume"]["present"] is True
    assert payload["resume"]["text"]
    assert payload["job_description"]["present"] is True

    client.delete(f"/session/{session_id}")


def test_voice_transcripts_and_coach_text_roundtrip(client: TestClient) -> None:
    session_meta = _upload_session(client)
    session_id = session_meta["session_id"]

    transcript_payload = {"question_index": 0, "text": "User said hello.", "source": "realtime"}
    coach_payload = {"question_index": 0, "text": "Coach replied with feedback."}

    save_user = client.post(f"/session/{session_id}/voice-transcript", json=transcript_payload)
    save_coach = client.post(f"/session/{session_id}/voice-agent-text", json=coach_payload)

    assert save_user.status_code == 200
    assert save_user.json()["ok"] is True
    assert save_coach.status_code == 200
    assert save_coach.json()["ok"] is True

    session_response = client.get(f"/session/{session_id}")
    assert session_response.status_code == 200
    session_data = session_response.json()

    assert session_data["voice_transcripts"]["0"] == transcript_payload["text"]
    assert session_data["voice_user_text"]["0"] == transcript_payload["text"]
    assert session_data["voice_agent_text"]["0"] == coach_payload["text"]

    client.delete(f"/session/{session_id}")


def test_voice_transcript_export_returns_entries(client: TestClient) -> None:
    session_meta = _upload_session(client)
    session_id = session_meta["session_id"]

    client.post(f"/session/{session_id}/voice-transcript", json={"question_index": 0, "text": "Candidate answer"})
    client.post(f"/session/{session_id}/voice-agent-text", json={"question_index": 0, "text": "Coach guidance"})

    export_response = client.get(f"/session/{session_id}/voice-transcript/export?format=json")
    assert export_response.status_code == 200
    payload = export_response.json()

    assert payload["session_id"] == session_id
    assert isinstance(payload["entries"], list)
    assert payload["entries"], "Expected at least one export entry"
    assert payload["entries"][0]["question_index"] == 0
    assert payload["entries"][0]["candidate_text"] == "Candidate answer"
    assert payload["entries"][0]["coach_text"] == "Coach guidance"

    unsupported = client.get(f"/session/{session_id}/voice-transcript/export?format=csv")
    assert unsupported.status_code == 415

    client.delete(f"/session/{session_id}")


def test_setting_coach_persona_updates_session_state(client: TestClient) -> None:
    session_meta = _upload_session(client)
    session_id = session_meta["session_id"]

    patch_response = client.patch(
        f"/session/{session_id}/coach",
        json={"persona": "helpful"},
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["coach_persona"] == "helpful"

    session_response = client.get(f"/session/{session_id}")
    assert session_response.status_code == 200
    assert session_response.json()["coach_persona"] == "helpful"

    client.delete(f"/session/{session_id}")


def test_sessions_endpoint_returns_saved_metadata(client: TestClient) -> None:
    session_meta = _upload_session(client)
    session_id = session_meta["session_id"]

    list_response = client.get("/sessions")
    assert list_response.status_code == 200
    payload = list_response.json()
    assert isinstance(payload, list)
    assert any(item["id"] == session_id for item in payload)

    client.delete(f"/session/{session_id}")


def test_voice_session_logs_coach_name(monkeypatch, client: TestClient, caplog: pytest.LogCaptureFixture) -> None:
    session_meta = _upload_session(client)
    session_id = session_meta["session_id"]

    class DummyStore:
        def search(self, q: str, k: int = 5):
            return []

    class DummyResponse:
        def __init__(self) -> None:
            self.status_code = 200

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {
                "id": "rt_session",
                "model": "gpt-voice",
                "client_secret": {"value": "fake-secret"},
                "expires_at": 123,
            }

    requested_payloads: list[dict[str, Any]] = []

    class DummyAsyncClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, *args, **kwargs):
            payload = kwargs.get("json")
            if isinstance(payload, dict):
                requested_payloads.append(payload)
            return DummyResponse()

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(main_module, "_get_work_history_store", lambda: DummyStore())
    monkeypatch.setattr(main_module.httpx, "AsyncClient", DummyAsyncClient)

    caplog.clear()
    with caplog.at_level(logging.INFO):
        response = client.post(
            "/voice/session",
            json={
                "session_id": session_id,
                "agent_name": "Ava",
                "persona": "helpful",
            },
        )
    assert response.status_code == 200

    assert requested_payloads, "Expected realtime provisioning payload to be captured"
    payload = requested_payloads[0]
    transcription = payload.get("input_audio_transcription")
    assert isinstance(transcription, dict), "Expected input_audio_transcription config in payload"
    assert transcription.get("model") == main_module.OPENAI_INPUT_TRANSCRIPTION_MODEL

    success_logs = [
        record for record in caplog.records if record.msg == "voice.session.create.success"
    ]
    start_logs = [
        record for record in caplog.records if record.msg == "voice.session.create.start"
    ]
    assert success_logs, "Expected voice.session.create.success log record"
    assert start_logs, "Expected voice.session.create.start log record"
    assert any(getattr(record, "ctx_agent_name", None) == "Ava" for record in success_logs)
    assert any(getattr(record, "ctx_coach", None) == "Helpful Coach" for record in success_logs)
    assert any(getattr(record, "ctx_coach", None) == "Helpful Coach" for record in start_logs)

    client.delete(f"/session/{session_id}")


def test_persona_update_logs_display_name(client: TestClient, caplog: pytest.LogCaptureFixture) -> None:
    session_meta = _upload_session(client)
    session_id = session_meta["session_id"]

    caplog.clear()
    with caplog.at_level(logging.INFO):
        response = client.patch(
            f"/session/{session_id}/coach",
            json={"persona": "helpful"},
        )
    assert response.status_code == 200
    persona_logs = [record for record in caplog.records if record.msg == "persona.update"]
    assert persona_logs, "Expected persona.update log entry"
    assert any(getattr(record, "ctx_coach", None) == "Helpful Coach" for record in persona_logs)

    client.delete(f"/session/{session_id}")


def test_persona_update_noop_retains_coach_display(client: TestClient, caplog: pytest.LogCaptureFixture) -> None:
    session_meta = _upload_session(client)
    session_id = session_meta["session_id"]

    # Set persona once to establish the helpful coach
    first_patch = client.patch(
        f"/session/{session_id}/coach",
        json={"persona": "helpful"},
    )
    assert first_patch.status_code == 200

    caplog.clear()
    with caplog.at_level(logging.INFO):
        second_patch = client.patch(
            f"/session/{session_id}/coach",
            json={"persona": "helpful"},
        )
    assert second_patch.status_code == 200
    noop_logs = [record for record in caplog.records if record.msg == "persona.update.noop"]
    assert noop_logs, "Expected persona.update.noop log entry"
    assert any(getattr(record, "ctx_coach", None) == "Helpful Coach" for record in noop_logs)

    client.delete(f"/session/{session_id}")


def test_persona_update_invalid_uses_current_coach_display(client: TestClient, caplog: pytest.LogCaptureFixture) -> None:
    session_meta = _upload_session(client)
    session_id = session_meta["session_id"]

    set_helpful = client.patch(
        f"/session/{session_id}/coach",
        json={"persona": "helpful"},
    )
    assert set_helpful.status_code == 200

    caplog.clear()
    with caplog.at_level(logging.INFO):
        response = client.patch(
            f"/session/{session_id}/coach",
            json={"persona": "wizard"},
        )
    assert response.status_code == 400
    invalid_logs = [record for record in caplog.records if record.msg == "persona.update.invalid"]
    assert invalid_logs, "Expected persona.update.invalid log entry"
    assert any(getattr(record, "ctx_coach", None) == "Helpful Coach" for record in invalid_logs)

    client.delete(f"/session/{session_id}")


def test_build_voice_instructions_uses_voice_template(monkeypatch) -> None:
    class DummyStore:
        def search(self, q: str, k: int = 5):
            return []

    monkeypatch.setattr(main_module, "_get_work_history_store", lambda: DummyStore())

    session = {
        "questions": ["How do you prioritize competing tasks?"],
        "resume_text": "Sample resume content",
        "job_desc_text": "Sample JD content",
    }
    instructions = main_module._build_voice_instructions(
        "session-voice",
        session,
        agent_name="Coach",
        persona="helpful",
    )
    assert "You are a Helpful Interview Coach." in instructions
    assert "Positive, collaborative, and specific." in instructions


def test_build_voice_instructions_defaults_to_discovery(monkeypatch) -> None:
    class DummyStore:
        def search(self, q: str, k: int = 5):
            return []

    monkeypatch.setattr(main_module, "_get_work_history_store", lambda: DummyStore())

    session = {
        "questions": [],
        "resume_text": "Resume text",
        "job_desc_text": "JD text",
    }
    instructions = main_module._build_voice_instructions(
        "session-default",
        session,
        agent_name="Coach",
        persona=None,
    )
    assert "You are a Discovery Interview Coach" in instructions


def test_get_voice_system_prompt_falls_back(monkeypatch) -> None:
    import app.models.interview_agent as agent_module

    monkeypatch.setattr(agent_module, "load_prompt_template", lambda *args, **kwargs: None)
    prompt = agent_module.get_voice_system_prompt("helpful")
    assert "You are a Helpful Interview Coach." in prompt
