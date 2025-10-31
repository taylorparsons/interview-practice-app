from helium import S, Text, wait_until, write, click, Button
from selenium.webdriver.support.ui import Select
from pathlib import Path



def test_default_discovery_coach_selected(browser, flow_capture):
    """Homepage should preselect Discovery Interview coach by default."""
    # Ensure a clean default (no prior persona persisted)
    browser.execute_script("localStorage.removeItem('coachPersona');")

    # Wait for the page header and upload form to render
    wait_until(lambda: Text("Interview Practice App").exists(), timeout_secs=15)
    wait_until(lambda: S('#upload-form').exists(), timeout_secs=15)

    # Prepare a tiny resume file to satisfy the upload requirement
    tmp_resume = Path("tests/ui/__artifacts__/tmp_resume.txt")
    tmp_resume.write_text("Sample resume for UI test", encoding="utf-8")

    # Populate upload controls
    S('#resume').web_element.send_keys(str(tmp_resume.resolve()))
    write("This is a sample job description for UI default persona test.", into=S('#job-description-text'))
    flow_capture.capture("upload-form-filled")

    # Submit and wait for interview view to appear
    click(Button("Start Interview Practice"))
    wait_until(lambda: Text("Question").exists(), timeout_secs=30)
    wait_until(lambda: Text("Voice Interview Coach").exists(), timeout_secs=30)

    # Ensure the persona selector is present
    selector = S("#coach-persona")
    wait_until(lambda: selector.exists(), timeout_secs=10)
    flow_capture.capture("persona-select-visible")

    # Read currently selected option
    el = selector.web_element
    selected_value = Select(el).first_selected_option.get_attribute("value")
    selected_text = Select(el).first_selected_option.text

    # Validate default selection is Discovery
    assert selected_value == "discovery", f"Expected default value 'discovery', got '{selected_value}'"
    assert "Discovery" in selected_text, f"Expected option text to contain 'Discovery', got '{selected_text}'"
