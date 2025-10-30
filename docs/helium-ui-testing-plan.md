# Helium UI Testing Plan

## Objectives
- Exercise core interview and general chat journeys with browser automation that mirrors real user actions.
- Keep the toolchain lightweight, Python-focused, and free/open-source for local and CI execution.
- Support both mocked and limited live-agent runs without exposing full OpenAI credentials.

## Phase 1: Environment & Tooling
1. **Dependencies**
   - Add `helium`, `pytest`, `pytest-dotenv`, and `webdriver-manager` to `requirements-dev.txt` (or `requirements.txt` if shared).
   - Helium rides on Selenium; `webdriver-manager` downloads the correct Chrome/Firefox drivers automatically during the test setup fixture.
2. **Project Layout**
   - Create `tests/ui/` with subfolders by surface (`interview/`, `chat/`, `shared/`).
   - Place shared fixtures and Helium helpers in `tests/ui/conftest.py`.
3. **Helium Session Fixture**
   - Implement a pytest fixture that calls `from helium import start_chrome, kill_browser`.
   - Default to headless mode via `start_chrome(base_url, headless=True)`; allow `HEADFUL_UI_TESTS=true` to aid debugging.
   - Register finalizers to capture screenshots on failure (`take_screenshot("...")`) before closing the browser.
4. **Configuration**
   - Store deterministic defaults in `.env.test` (mock API base URL, feature toggles).
   - Load `.env.test` automatically via `pytest-dotenv`; allow CI to inject `OPENAI_API_KEY_LIMITED` when live calls are required.

## Phase 2: Critical Interview Flow Coverage
1. **Session Bootstrapping**
   - Script resume uploads using `attach_file("Resume upload", path)` and confirm precedence when both resume text and file are present.
   - Assert UI feedback: submit enabled state, loading indicators, transcript container visibility.
2. **Question Loop**
   - Navigate generated questions with `click("Next question")`, verify timers, microphone controls (`click("Start recording")` / `click("Stop recording")`).
   - Confirm layout toggles (compact/split) by checking for expected DOM markers via `S(...)` selectors.
3. **Coaching Configuration**
   - Exercise coaching level dropdown, persist selection, refresh page, and verify Helium reads back the stored value.

## Phase 3: General Chat Scenarios
1. **Workspace Switching**
   - Automate switching between interview practice and the general chat workspace; validate that irrelevant controls disappear and correct headers render.
   - Inspect network payloads (via backend stubs or server-side assertions) to ensure agent-team parameters are sent.
2. **Chat Loop**
   - Send messages, wait for streaming responses by polling the transcript container, and validate follow-up prompts appear.
   - Confirm the metadata panel updates with agent persona details when toggling workspaces.
3. **Regression Guards**
   - Capture smoke screenshots using Helium’s `take_screenshot` for critical panels (upload form, chat composer) and store under `tests/ui/__artifacts__/`.

## Phase 4: Supporting Utilities
1. **API Stubs & Data Seeds**
   - Provide helper functions to seed sessions through internal FastAPI endpoints, or monkeypatch agent calls to deterministic fixtures when the limited API key is absent.
   - Maintain fixtures under `tests/ui/shared/data/` with semantic names (`interview_basic_session.json`, `chat_default_thread.json`).
2. **Accessibility Checks**
   - Integrate `axe-selenium-python` with Helium’s underlying driver to run WCAG scans on key pages; fail on serious violations.
3. **Visual Diffs (Optional)**
   - If regression detection is needed, pair Helium with `pytest-needle` or `pil` for baseline comparisons. Run these in nightly workflows to reduce PR noise.

## Phase 5: Continuous Integration
1. **Workflow Updates**
   - Add a CI job executing `pytest tests/ui -k "not live_agent"`. Cache WebDriver binaries in the CI workspace.
   - Provide an opt-in matrix entry (`RUN_LIVE_UI=1`) that loads the limited API key secret and enables scenarios tagged with `@pytest.mark.live_agent`.
2. **Artifacts & Diagnostics**
   - On failure, upload Helium screenshots and any collected HTML dumps for fast debugging.
   - Emit a concise pytest summary (use `--maxfail=1 --disable-warnings -q` for PR gatekeeping).

## Phase 6: Maintenance & Review
1. **Selector Hygiene**
   - Favor data attributes (`data-testid`) over brittle CSS/text selectors. Coordinate with frontend when introducing new UI components.
2. **Review Checklist**
   - Update the engineering PR template to ask whether Helium UI coverage was added or adjusted for user-facing changes.
3. **Test Health Monitoring**
   - Track flakiness in CI dashboards; schedule monthly audits to prune obsolete fixtures and update driver versions.

By rolling out these phases incrementally, the team gains reliable user-level regression coverage with minimal setup overhead, while keeping the stack entirely Python-based and open source.
