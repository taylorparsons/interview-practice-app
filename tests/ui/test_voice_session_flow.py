"""Helium-driven coverage for realtime voice session UI flows."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from helium import Button, S, Text, click, wait_until, write
from selenium.webdriver.support.ui import Select

from tests.ui.helpers.voice import VoiceTestController


def _default_resume_path(stem: str) -> Path:
    path = Path("tests/ui/__artifacts__") / f"{stem}_resume.txt"
    path.write_text("Sample resume content for realtime voice UI tests.", encoding="utf-8")
    return path.resolve()


def _bootstrap_practice_session(browser, flow_capture, name: str = "voice") -> None:
    """Upload fixtures and advance to the interview view."""
    browser.execute_script("localStorage.clear();")

    wait_until(lambda: Text("Interview Practice App").exists(), timeout_secs=20)
    wait_until(lambda: S("#upload-form").exists(), timeout_secs=20)

    resume_path = _default_resume_path(name)
    S("#resume").web_element.send_keys(str(resume_path))
    write(
        "Voice UI automation job description for Helium coverage.",
        into=S("#job-description-text"),
    )
    flow_capture.capture(f"{name}-upload-ready")

    click(Button("Start Interview Practice"))
    wait_until(lambda: Text("Question").exists(), timeout_secs=30)
    wait_until(lambda: Text("Voice Interview Coach").exists(), timeout_secs=30)
    flow_capture.capture(f"{name}-interview-loaded")


def _wait_for_text(selector: Callable[[], str], expected: str | tuple[str, ...] | list[str], timeout_secs: int = 10) -> None:
    if isinstance(expected, (list, tuple, set)):
        wait_until(lambda: any(token in selector() for token in expected), timeout_secs=timeout_secs)
    else:
        wait_until(lambda: expected in selector(), timeout_secs=timeout_secs)


def _wait_for_start_voice_enabled(timeout_secs: int = 30) -> None:
    wait_until(lambda: S("#start-voice").web_element.is_enabled(), timeout_secs=timeout_secs)


def test_voice_session_happy_path(browser, flow_capture, voice_test_controller: VoiceTestController):
    """Voice session should reach 'Live' state and render agent transcript snippets."""
    _bootstrap_practice_session(browser, flow_capture, name="voice-happy")

    _wait_for_start_voice_enabled()
    click(Button("Start Voice Session"))
    _wait_for_text(lambda: S("#voice-status").web_element.text, ("Connecting", "Live"), 10)
    assert voice_test_controller.wait_for_data_channel_open(timeout_secs=10), "Expected data channel to open"

    _wait_for_text(lambda: S("#voice-status").web_element.text, "Live", 10)

    # Simulate agent streaming text followed by completion.
    voice_test_controller.emit_data_channel_message(
        {"type": "response.output_text.delta", "delta": "Welcome to the interview."}
    )
    voice_test_controller.emit_data_channel_message({"type": "response.output_text.done"})

    _wait_for_text(lambda: S("#voice-transcript").web_element.text, "Welcome to the interview.", 10)
    flow_capture.capture("voice-happy-transcript")

    start_classes = browser.execute_script(
        "var el = document.getElementById('start-voice'); return el ? el.className : '';"
    ) or ""
    stop_hidden = browser.execute_script(
        "var el = document.getElementById('stop-voice'); return el ? el.className : '';"
    ) or ""
    assert "hidden" in start_classes, "Start Voice button should be hidden when live"
    assert "hidden" not in stop_hidden, "Stop Voice button should be visible when live"


def test_voice_session_remember_and_persona(browser, flow_capture, voice_test_controller: VoiceTestController):
    """Remember button should persist transcripts and persona changes should reflect in storage."""
    _bootstrap_practice_session(browser, flow_capture, name="voice-remember")

    _wait_for_start_voice_enabled()
    click(Button("Start Voice Session"))
    assert voice_test_controller.wait_for_data_channel_open(timeout_secs=10), "Expected data channel to open"
    _wait_for_text(lambda: S("#voice-status").web_element.text, "Live", 10)

    voice_test_controller.clear_requests()

    # Inject a user transcript so remember has content to save.
    voice_test_controller.emit_data_channel_message(
        {
            "type": "conversation.item.input_audio_transcription.completed",
            "text": "I led a cross-functional launch that improved activation by 15 percent.",
        }
    )
    _wait_for_text(lambda: S("#voice-transcript").web_element.text, "15 percent", 10)

    click(Button("Remember"))
    _wait_for_text(lambda: S("#voice-transcript").web_element.text, "Saved to your knowledge pool.", 10)

    requests = voice_test_controller.get_requests()
    memorize_calls = [req for req in requests if "voice-transcript/memorize" in (req.get("url") or "")]
    assert memorize_calls, "Expected remember flow to POST to voice-transcript/memorize"

    # Verify persona selector persists to localStorage and surfaces feedback.
    persona_select = Select(S("#coach-persona").web_element)
    persona_select.select_by_value("helpful")
    _wait_for_text(lambda: S("#voice-transcript").web_element.text, "Coach persona set to helpful.", 10)

    stored_persona = browser.execute_script("return localStorage.getItem('coachPersona');")
    assert stored_persona == "helpful"

    persona_calls = [req for req in voice_test_controller.get_requests() if "/coach" in (req.get("url") or "")]
    assert persona_calls, "Expected persona change to invoke /coach endpoint"


def test_voice_session_error_recovery(browser, flow_capture, voice_test_controller: VoiceTestController):
    """Failed realtime session creation should surface errors and keep controls accessible."""
    voice_test_controller.configure(
        sessionResponse={
            "ok": False,
            "status": 502,
            "body": {"error": "upstream unavailable"},
        }
    )

    _bootstrap_practice_session(browser, flow_capture, name="voice-error")

    _wait_for_start_voice_enabled()
    click(Button("Start Voice Session"))
    _wait_for_text(lambda: S("#voice-status").web_element.text, "Connection failed", 10)
    _wait_for_text(lambda: S("#voice-transcript").web_element.text, "Voice session error", 10)

    start_displayed = S("#start-voice").web_element.is_displayed()
    assert start_displayed, "Start Voice button should remain available after failure"


def test_voice_session_manual_stop(browser, flow_capture, voice_test_controller: VoiceTestController):
    """Stopping the voice session should reset controls and tear down the peer/data channel."""
    _bootstrap_practice_session(browser, flow_capture, name="voice-stop")

    _wait_for_start_voice_enabled()
    click(Button("Start Voice Session"))
    assert voice_test_controller.wait_for_data_channel_open(timeout_secs=10), "Expected data channel to open"
    _wait_for_text(lambda: S("#voice-status").web_element.text, "Live", 10)

    click(Button("Stop Voice Session"))
    _wait_for_text(lambda: S("#voice-status").web_element.text, "Voice session ended", 10)

    flags = voice_test_controller.flags()
    assert flags.get("channelClosed"), "Expected data channel to close on manual stop"
    assert flags.get("peerClosed"), "Expected peer connection to close on manual stop"

    start_classes = browser.execute_script(
        "var el = document.getElementById('start-voice'); return el ? el.className : '';"
    ) or ""
    stop_classes = browser.execute_script(
        "var el = document.getElementById('stop-voice'); return el ? el.className : '';"
    ) or ""
    assert "hidden" not in start_classes, "Start Voice button should be visible after stop"
    assert "hidden" in stop_classes, "Stop Voice button should be hidden after stop"
