import os
import re
from datetime import datetime
from pathlib import Path

import pytest
from helium import go_to, set_driver
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

ARTIFACTS_DIR = Path(__file__).parent / "__artifacts__"


def _headful_requested() -> bool:
    return os.getenv("HEADFUL_UI_TESTS", "false").lower() in {"1", "true", "yes"}


def _slugify(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-")


class FlowCapture:
    """Utility to snapshot each step of a test's customer journey."""

    def __init__(self, driver, test_name: str):
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        safe_name = _slugify(test_name or "ui_flow")
        self.driver = driver
        self.step_count = 0
        self.directory = ARTIFACTS_DIR / f"{safe_name}_{timestamp}"
        self.directory.mkdir(parents=True, exist_ok=True)

    def capture(self, label: str) -> Path:
        safe_label = _slugify(label or f"step_{self.step_count}")
        path = self.directory / f"{self.step_count:02d}_{safe_label}.png"
        self.driver.save_screenshot(str(path))
        self.step_count += 1
        return path


@pytest.fixture(scope="session")
def base_url() -> str:
    """Base URL of the running app under test."""
    return os.getenv("UI_BASE_URL", "http://localhost:8000")


@pytest.fixture
def browser(request: pytest.FixtureRequest, base_url: str):
    """Provision a Helium/Selenium browser session for UI tests."""
    options = Options()
    options.add_argument("--window-size=1280,800")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")
    if not _headful_requested():
        options.add_argument("--headless=new")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    set_driver(driver)
    flow_capture = FlowCapture(driver, request.node.name)
    request.node._flow_capture = flow_capture  # type: ignore[attr-defined]

    go_to(base_url)
    flow_capture.capture("launch")

    yield driver

    test_failed = getattr(request.node, "rep_call", None)
    if test_failed and test_failed.failed:
        failure_capture = flow_capture.capture("failure")
        failure_html = ARTIFACTS_DIR / f"{_slugify(request.node.name)}_failure.html"
        failure_html.write_text(
            driver.page_source, encoding="utf-8"
        )
        print(f"[ui-tests] Failure screenshot saved to {failure_capture}")
        print(f"[ui-tests] Failure DOM dump saved to {failure_html}")

    driver.quit()


@pytest.fixture
def flow_capture(request: pytest.FixtureRequest) -> FlowCapture:
    capture = getattr(request.node, "_flow_capture", None)
    if capture is None:
        raise RuntimeError(
            "flow_capture fixture requires the browser fixture; add 'browser' to the test signature."
        )
    return capture


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo):
    """Expose test outcome on the item so fixtures can capture artifacts on failure."""
    outcome = yield
    rep = outcome.get_result()
    setattr(item, f"rep_{rep.when}", rep)
