from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JS_PATH = ROOT / "app" / "static" / "js" / "app.js"
HTML_PATH = ROOT / "app" / "templates" / "index.html"


def _read_text(p: Path) -> str:
    with open(p, "r", encoding="utf-8") as f:
        return f.read()


def test_coach_level_summary_present_in_template():
    html = _read_text(HTML_PATH)
    assert 'id="voice-summary-coach-level"' in html
    assert 'id="voice-summary-voice"' in html
    # Drawer controls remain for editing
    assert 'id="coach-level-select-2"' in html
    assert 'id="voice-select-2"' in html


def test_coach_level_js_handles_save_and_state():
    js = _read_text(JS_PATH)
    assert 'state.coachLevel' in js
    assert 'coachLevelSaveBtn2' in js
    assert '/coach-level' in js
