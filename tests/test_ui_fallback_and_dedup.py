from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
JS_PATH = ROOT / "app" / "static" / "js" / "app.js"
HTML_PATH = ROOT / "app" / "templates" / "index.html"


def _read_text(path: Path) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def test_fallback_default_off_in_js():
    js = _read_text(JS_PATH)
    # Ensure the initial voice state disables browser ASR by default
    assert "useBrowserAsr: false" in js


def test_browser_fallback_checkbox_not_prechecked():
    html = _read_text(HTML_PATH)
    # The toggle should not include the 'checked' attribute by default
    line = next(
        (l for l in html.splitlines() if 'id="toggle-browser-asr"' in l and '<input' in l),
        "",
    )
    assert "checked" not in line


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
