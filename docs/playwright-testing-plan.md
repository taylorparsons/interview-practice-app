# Playwright UI Testing Expansion Plan

## Objectives
- Increase confidence in the user experience by covering critical end-to-end flows with browser automation.
- Ensure interview and upcoming general chat surfaces remain stable while new agent teams and parameters are introduced.
- Provide a framework for integrating limited-use API keys when live agent responses are required for validation.

## Phase 1: Foundational Setup
1. **Tooling**
   - Add Playwright with the Python test runner (`pip install playwright pytest-playwright`).
   - Run `playwright install` during CI setup to provision Chromium (headless by default).
   - Store configuration under `tests/ui/playwright.config.ts` (or `.py` if using the Python flavor) with sensible defaults: 30s timeout, trace collection on failure, screenshots for diffing.
2. **Project Structure**
   - Create `tests/ui/` for browser specs. Organize subfolders by feature: `interview/`, `chat/`, `shared/`.
   - Share fixtures in `tests/ui/conftest.py`, exposing helpers for session seeding and API mocking.
3. **Environment Management**
   - Introduce `.env.test` for deterministic defaults (mock API endpoints, disable analytics).
   - For runs that require calling OpenAI, inject a *limited-scope* API key via CI secrets; default to mocked responses when the key is absent.

## Phase 2: Critical Interview Flows
1. **Session Creation & Uploads**
   - Automate selecting resume files and text input to confirm the correct precedence logic.
   - Validate UI reactions: submit button enable/disable, progress indicators, transcript container visibility.
2. **Question Navigation**
   - Step through generated questions, ensuring manual answer controls (start/stop recording, submit answer) remain operable.
   - Assert that voice layout toggles trigger the expected DOM changes (e.g., compact vs. split view).
3. **Coaching Controls**
   - Verify the coaching-level selector renders and persists user choices across refreshes (exercise local storage or API-backed persistence).

## Phase 3: General Chat (Veneo Inc.) Coverage
1. **Agent Team Selector**
   - Test switching between interview practice and general chat workspaces; ensure the UI loads the correct templates and hides irrelevant controls.
   - Confirm the backend payload contains the new agent team parameters when the chat workspace is active.
2. **Chat Interaction Loop**
   - Simulate message sending, streaming updates, and follow-up prompts.
   - Validate compartmentalized components: chat transcript, prompt composer, agent metadata panel.
3. **Regression Guards**
   - Capture baseline screenshots for both workspaces to detect layout shifts when modifying shared components.

## Phase 4: Accessibility & Visual Checks
1. **Accessibility**
   - Integrate `@axe-core/playwright` to scan critical views for WCAG violations.
   - Fail tests on high-severity issues (missing labels, contrast failures) to safeguard the UX.
2. **Visual Regression**
   - Employ Playwright's `toHaveScreenshot` assertions on stable components (upload panel, chat composer) with per-feature baselines stored under `tests/ui/__screenshots__/`.
   - Run screenshot comparisons only in nightly/PR builds to balance runtime.

## Phase 5: Continuous Integration & Reporting
1. **CI Pipeline**
   - Extend the existing workflow to run `pytest tests/ui --headless`. Cache Playwright browsers between runs.
   - Allow an opt-in job (`RUN_E2E_WITH_API_KEY=true`) that unlocks live-agent scenarios using the limited API key.
2. **Artifacts & Observability**
   - Upload Playwright traces, videos, and failure screenshots on test failures for quick debugging.
   - Publish summarized reports (e.g., HTML, GitHub summary) with pass/fail counts per workspace.

## Phase 6: Maintenance
1. **Mocking & Fixtures**
   - Provide helper utilities to seed session data through backend APIs or direct fixture injection, enabling fast deterministic tests.
   - Version shared fixtures with semantic names (e.g., `interview_baseline`, `chat_default_agent_team`).
2. **Review Checklist**
   - Update the code review template to require Playwright coverage for user-facing features.
   - Encourage pairing DOM changes with updated Playwright selectors to keep tests resilient.

By rolling out this plan iteratively, we can expand UI coverage with Playwright while keeping the application compartmentalized for both interview practice and the new Veneo Inc. general chat experience.
