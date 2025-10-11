from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JS_PATH = ROOT / "app" / "static" / "js" / "app.js"
HTML_PATH = ROOT / "app" / "templates" / "index.html"


def _read_text(p: Path) -> str:
    with open(p, "r", encoding="utf-8") as f:
        return f.read()


def test_coach_level_selector_present_in_template():
    html = _read_text(HTML_PATH)
    assert 'id="coach-level-select"' in html
    assert 'id="coach-level-save"' in html


def test_coach_level_js_wires_save_and_fetch():
    js = _read_text(JS_PATH)
    # Init function present and attached on DOMContentLoaded
    assert 'function initCoachLevelSelector()' in js
    assert 'fetch(`/session/${state.sessionId}/coach-level`' in js or '"/session/${state.sessionId}/coach-level"' in js or '/coach-level' in js
    # Ensures select is filled from GET /session/{id}
    assert 'fetch(`/session/${state.sessionId}`' in js or 'fetch(`/session/`' in js
