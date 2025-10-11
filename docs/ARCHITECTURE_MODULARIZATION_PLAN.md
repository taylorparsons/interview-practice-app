Architecture Modularization Plan (Follow-up to PR: voice-preview + fallback dedup)

Context
- Current stack: FastAPI backend (Python), vanilla JS frontend served from app/static.
- Goal: make feature work (voice previews, fallback suppression/dedup) sustainable as we add agent capabilities.

Plan

1) Frontend Modules (no framework required)
- Create app/static/js/modules/ with:
  - api.js: thin wrappers for GET/POST/PATCH endpoints (sessions, voices, previews).
  - voice.js: WebRTC + realtime event handling, ASR suppression, transcript pipeline.
  - ui.js: DOM helpers for timeline rendering and control state.
  - state.js: central state (current session, voice settings, flags), exported factory + single instance.
- Split app.js by moving functions into these modules, keeping app.js as the bootstrap/wire-up.
- Add a simple build step (esbuild/rollup optional) or keep native modules with type="module" for now.

2) Backend Service Boundaries
- Create app/services/: 
  - openai_client.py: wraps httpx calls to OpenAI (realtime sessions, TTS, chat) with retries and logging.
  - voice_service.py: voice catalog, preview synthesis/cache, realtime session payload assembly.
  - session_service.py: session CRUD, voice settings updates, transcript persistence helpers.
- Keep app/main.py focused on FastAPI route wiring and input validation.

3) Agent-team Abstraction
- Add app/agents/registry.py: registry from agent_id -> {model_id, voice_id, defaults}.
- Expose GET /agents and allow session to select an agent_id, resolving to concrete model/voice settings.
- Defer to InterviewPracticeAgent for prompt specifics; inject model/voice via session voice_settings.

4) Cross-cutting Concerns
- app/logging_config.py already present; extend to log voice selection + fallback usage (telemetry TODO).
- Add structured error types and consistent JSON errors for service boundaries.

5) Tests
- Keep API-level tests as primary.
- Add unit tests for services/ (voice_service preview, openai_client error mapping).
- Optionally, add Playwright for UI toggles (fallback off/on, preview loading state).

Incremental Steps
- Phase A: extract voice_service + openai_client; keep routes intact.
- Phase B: move voice handlers in main.py to thin routes calling services.
- Phase C: split app.js into modules; no bundler required initially.
