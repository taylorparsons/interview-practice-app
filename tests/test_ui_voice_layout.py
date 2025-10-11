from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
JS_PATH = ROOT / "app" / "static" / "js" / "app.js"
HTML_PATH = ROOT / "app" / "templates" / "index.html"


def _read_text(path: Path) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def test_template_has_expected_targets():
    html = _read_text(HTML_PATH)
    # Transcript container should start with max-h-64 and be scrollable
    assert 'id="voice-transcript"' in html
    assert 'max-h-64' in html
    assert 'overflow-y-auto' in html
    # Manual input controls exist so they can be toggled hidden during live voice
    assert 'label for="answer"' in html
    assert 'id="answer"' in html
    assert 'id="submit-answer"' in html
    assert 'id="get-example"' in html


def test_set_voice_layout_is_wired_on_start_and_stop():
    js = _read_text(JS_PATH)
    # Function is present and toggles key elements
    assert 'function setVoiceLayout(isLive)' in js
    assert 'answerInput.classList.toggle(' in js
    assert 'answerBtn' in js and 'getExampleBtn' in js
    assert 'voiceTranscript.classList.toggle(\'max-h-64\'' in js
    assert 'voiceTranscript.classList.toggle(\'max-h-96\'' in js
    # Called when starting/stopping a voice session
    assert 'setVoiceLayout(true);' in js
    assert 'setVoiceLayout(false);' in js

