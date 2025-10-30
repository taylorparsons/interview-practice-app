from helium import Button, S, Text, wait_until


def test_homepage_upload_section_visible(browser, flow_capture):
    """Baseline smoke test to ensure the landing page renders key upload controls."""
    wait_until(lambda: Text("Interview Practice App").exists(), timeout_secs=15)
    flow_capture.capture("header-visible")

    assert Text("Upload Documents").exists()
    assert S("#upload-form").exists()
    assert S("#resume").exists()
    assert S("#job-description").exists()
    assert S("#job-description-text").exists()
    assert Button("Start Interview Practice").exists()
    flow_capture.capture("upload-form-ready")
