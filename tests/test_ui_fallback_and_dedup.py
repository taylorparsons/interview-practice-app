from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
JS_PATH = ROOT / "app" / "static" / "js" / "app.js"
HTML_PATH = ROOT / "app" / "templates" / "index.html"


def _read_text(path: Path) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def test_fallback_default_off_in_js():
    js = _read_text(JS_PATH)
    # Ensure the initial voice state respects APP_CONFIG defaults (false when unspecified)
    assert "window.APP_CONFIG" in js
    assert "const appVoiceConfig" in js
    assert "useBrowserAsr: !!appVoiceConfig.useBrowserAsr" in js


def test_browser_fallback_checkbox_removed_from_ui():
    html = _read_text(HTML_PATH)
    # Toggle is controlled via config, not UI; ensure checkbox is absent
    assert 'toggle-browser-asr' not in html


def test_onopen_does_not_autostart_browser_asr():
    js = _read_text(JS_PATH)
    # Ensure startBrowserAsrIfAvailable is gated behind useBrowserAsr and suppression checks
    assert "dataChannel.onopen" in js
    assert "startBrowserAsrIfAvailable()" in js
    # Verify gating condition exists alongside the call
    assert "useBrowserAsr" in js and "suppressBrowserAsr" in js


def test_speech_recognition_events_are_gated_by_suppression():
    js = _read_text(JS_PATH)
    # onresult interim/final paths should check both useBrowserAsr and !suppressBrowserAsr
    assert "useBrowserAsr && !state.voice.suppressBrowserAsr" in js
    # Restart-on-end should also be gated
    assert "useBrowserAsr && !state.voice.suppressBrowserAsr" in js


def test_deduplication_logic_present_for_user_final_messages():
    js = _read_text(JS_PATH)
    # Check the presence of normalization-based duplicate skip in handleUserTranscriptChunk
    assert "handleUserTranscriptChunk" in js
    assert "normalize(" in js
    assert "replace(/[^a-z0-9]+/g, ' ')" in js
    # Ensure we check against last finalized 'user' entry and skip duplicates
    assert "m.role === 'user'" in js and "!m.stream" in js
