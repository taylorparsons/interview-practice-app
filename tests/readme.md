# Interview Practice App Test Suite

This directory hosts the automated checks that guard against regressions across the API and UI layers of the Interview Practice App. Tests are grouped by their surface area so contributors can quickly target or expand the suite as new features land.

## API Tests (`tests/api/`)

- `test_session_endpoints.py` exercises the FastAPI routes that underpin session management and logging. These tests verify the customer-visible behaviours called out in the support checklist:
  - Upload flows persist resume and job description previews so the “View Docs” panel renders real content.
  - Persona updates return the chosen coach persona and emit structured logs that now include the human-readable coach name. Reproducing the recent logging story keeps log quality from regressing.
  - Voice transcript endpoints capture both user and coach turns, ensuring transcripts remain in sync when support teams review sessions.
  - Voice session creation logs embed the coach display name and agent label, which lets support staff correlate realtime sessions with the correct persona configuration.

Running this module with `pytest tests/api/test_session_endpoints.py` is a fast, hermetic way to confirm server-side contracts before shipping.

## UI Tests (`tests/ui/`)

- `test_homepage_smoke.py` is a Helium/Selenium smoke test that loads the landing page and asserts the upload workflow renders. It captures screenshots at each step via the `FlowCapture` helper, which stores artifacts under `tests/ui/__artifacts__/` for post-failure triage.
- `conftest.py` provisions the shared browser fixtures, toggles headless/headful mode via `HEADFUL_UI_TESTS`, and automatically snapshots the DOM when a run fails. Keeping this harness in version control ensures UI regression checks are repeatable in CI and on local machines.

To run the UI suite locally, point the `UI_BASE_URL` environment variable at a live dev server and execute `pytest tests/ui -q`. The artifacts folder can be safely cleaned between runs.

## How to Extend the Suite

- Mirror the `app/` package layout when adding new pytest modules so future contributors know where to look.
- Each bug fix should land with a focused regression test that fails prior to the fix and passes afterwards. This keeps the behaviours described in the repository guidelines continuously enforced.
- For client-facing features, pair API coverage with UI flows where feasible; Helium smoke tests offer quick confidence without requiring full end-to-end scripting.

Consistent coverage here ensures the support scenarios described in the user story—voice transcripts, document previews, persona fidelity, and voice session diagnostics—remain stable as the app evolves.
