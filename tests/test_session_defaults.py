import sys
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import app.main as main  # noqa: E402
import app.utils.session_store as store  # noqa: E402
from app.config import OPENAI_REALTIME_VOICE  # noqa: E402


def test_load_session_backfills_voice_fields(monkeypatch, tmp_path):
    monkeypatch.setattr(store, "SESSION_DIR", tmp_path)
    payload = {
        "questions": [],
        "answers": [],
        "evaluations": [],
    }
    store.save_session("s1", payload)

    loaded = store.load_session("s1")
    assert loaded["voice_messages"] == []
    assert loaded["voice_transcripts"] == {}
    assert loaded["voice_agent_text"] == {}
    assert loaded["voice_settings"]["voice_id"] == OPENAI_REALTIME_VOICE
    assert loaded["question_type_overrides"] == {}


@pytest.mark.parametrize(
    "voice_settings,expected_voice",
    [
        (None, OPENAI_REALTIME_VOICE),
        ({}, OPENAI_REALTIME_VOICE),
        ({"voice_id": "custom"}, "custom"),
    ],
)
def test_ensure_session_defaults_sets_voice_settings(voice_settings, expected_voice):
    session = {
        "questions": None,
        "answers": None,
        "evaluations": None,
        "per_question": None,
        "voice_transcripts": None,
        "voice_agent_text": None,
        "voice_messages": None,
        "voice_settings": voice_settings,
    }

    updated = main._ensure_session_defaults(session)
    assert updated["voice_settings"]["voice_id"] == expected_voice
    assert updated["voice_messages"] == []
    assert updated["voice_transcripts"] == {}
    assert updated["voice_agent_text"] == {}
    assert updated["question_type_overrides"] == {}
