# Refactor Plan for `app/main.py`

## Current pain points
- `app/main.py` mixes HTTP routing, session persistence, AI agent orchestration, realtime voice plumbing, and fallback heuristics inside a single 1,100+ line module, making it hard to reason about or extend.【F:app/main.py†L1-L336】【F:app/main.py†L337-L676】【F:app/main.py†L677-L1023】【F:app/main.py†L1024-L1131】
- Domain concepts (session metadata, voice messaging, evaluation summaries) are implicit dictionaries that are mutated from multiple endpoints, which invites inconsistent shapes and brittle tests.【F:app/main.py†L74-L164】【F:app/main.py†L336-L571】【F:app/main.py†L572-L856】
- OpenAI realtime/voice configuration is hard-coded inside the route, preventing reuse for the upcoming general chat experience and any “team of agents” orchestration with new parameters.【F:app/main.py†L856-L1023】

## Target architecture
1. **API routers**
   - Introduce `app/api/__init__.py` and split FastAPI routes into dedicated routers: `sessions.py`, `questions.py`, `evaluations.py`, and `voice.py`. Each router imports thin service functions instead of touching globals directly.
   - Mount routers from a slim `app/main.py` (now mostly FastAPI initialization and middleware wiring).

2. **Service layer**
   - Create `app/services/session_service.py` encapsulating `_get_session`, `_persist_session_state`, and CRUD helpers. Use dataclasses or Pydantic models for strongly typed session structures to make mutation explicit.
   - Move question generation, evaluation, and example-answer fallbacks into `app/services/qa_service.py`, parameterized to accept an injected `InterviewPracticeAgent` (or a more general `AgentTeam` factory for future multi-agent support).
   - Extract voice-specific helpers (`_build_voice_instructions`, catalog helpers, preview synthesis) into `app/services/voice_service.py` with a `VoiceConfig` settings object so different features can reuse the same plumbing.
   - Encapsulate OpenAI realtime session bootstrapping into `app/services/realtime_client.py`, allowing dependency injection of API clients and customizable parameters for new agent teams or general chat.

3. **Agent orchestration**
   - Replace the `active_sessions` global dict with a dedicated `SessionStore` abstraction that composes the existing persistent store and in-memory cache. Expose a strategy interface so the forthcoming “team of agents” feature can register multiple agents per session (e.g., `PrimaryCoach`, `FeedbackCoach`, `GeneralChatCoach`).
   - Model a reusable `AgentTeam` concept that aggregates multiple agent instances behind a single facade. Each team exposes lifecycle hooks (`boot`, `delegate`, `summarize`) so the API layer never talks to raw agents.
   - Add a lightweight `AgentFactory` that accepts configuration (model, persona, parameters) and returns initialized agents. `start_agent` becomes a service function that registers whichever agents the feature flag requires.
   - Define configuration-driven personas (e.g., YAML or Pydantic settings) so product teams can roll out additional agents by adding parameter bundles instead of code changes.

4. **Schemas & DTOs**
   - Move all request/response models into `app/schemas/*.py`. Group by concern (e.g., `session.py`, `voice.py`). This keeps the routers concise and centralizes validation logic.
   - Provide explicit models for session state slices (e.g., `SessionSummary`, `VoiceTranscript`) so downstream tests can assert structure without brittle dict-key checks.

5. **Configuration**
   - Introduce `app/settings.py` or extend `app/config.py` with structured Pydantic settings classes (e.g., `RealtimeSettings`, `AgentSettings`). Dependency injection via FastAPI’s `Depends` can supply the configuration to routers/services, simplifying overrides for new environments.
   - Capture the general chat defaults in a `GeneralChatSettings` object (model id, tone, allowed tools) so the new agent team can opt-in without mutating interview-specific values.
   - Externalize runtime-tunable parameters (temperature, max tokens, concurrency) for each agent persona to support experimentation.

6. **Observability**
   - Instrument the new service layer with structured logs/metrics (agent decision traces, queue times) to validate multi-agent coordination.
   - Emit tracing spans around agent-team delegation to pinpoint latency regressions when general chat launches.

7. **Extensibility for additional teams**
   - Ensure routers/services accept an injected `AgentTeamResolver` that selects the right team based on feature flags, session metadata, or tenant configuration.
   - Provide clear extension points for future teams (e.g., skill-assessment, onboarding) so new personas can ship without touching existing flows.

## Testing strategy
1. **Unit tests**
   - Add tests for the new service modules (`tests/services/test_session_service.py`, `test_voice_service.py`) that validate business rules such as transcript aggregation, session naming, and fallback scoring.
   - Use dependency injection to pass fake agents into `qa_service` tests to cover both agent and fallback paths without live API calls.
   - Mock the HTTP client in `realtime_client` tests to validate payload composition, ensuring the new agent parameters are forwarded correctly.

2. **Integration tests**
   - With routers split, write FastAPI `TestClient` tests per router module (e.g., `tests/api/test_voice_routes.py`) asserting HTTP status codes, validation errors, and session state mutations.
   - Introduce fixtures for `SessionStore` that start with seeded session data to test rename/delete flows and verify persistence hooks.
   - Add general-chat scenarios that assert the correct agent team is selected and that team-specific parameters (model, style guides) propagate to downstream services.

3. **End-to-end contract**
   - Keep a small set of smoke tests hitting the high-level flows (`upload -> generate -> evaluate`). These should mock outbound HTTP calls but run against the assembled FastAPI app to ensure routers and middleware wiring remain intact.
   - Add a general-chat smoke test covering `start chat -> exchange messages -> summarize` to detect regressions in the agent-team orchestration.

## Incremental adoption plan
1. Extract session helper functions into `app/services/session_service.py` and refactor a single router (e.g., `/sessions` endpoints) to use it. Add unit tests for the new service.
2. Move the question/evaluation endpoints into `app/api/questions.py` + `qa_service`. Introduce agent factory abstraction and tests for fallback scoring logic.
3. Carve out voice-specific routes and helpers into `voice.py` + `voice_service` and `realtime_client`. Backfill catalog/preview tests using local fixtures.
4. Once services are covered, slim down `app/main.py` to FastAPI initialization, router registration, and the `if __name__ == "__main__"` block.
5. Introduce new general-chat feature module that composes the shared services and registers additional agent teams by supplying different agent factory parameters.
6. Ship the general-chat configuration behind a feature flag, validate telemetry, and then document how partner teams can add new agent personas via configuration plus targeted service tests.

This staged approach keeps the app deployable while enabling the upcoming agent-team functionality and richer configuration without rewriting everything at once.
