# Refactor Plan for Multi-Agent General Chat Expansion

This document captures the refactor strategy needed to evolve the current interview-practice application into a compartmentalized platform that can host multiple **agent teams** (e.g., the existing interview coach plus a new general chat team for Veneo Inc.) with configurable parameters.

## 1. Context and goals

* `app/main.py` currently centralizes HTTP routing, session state management, agent orchestration, and voice/realtime plumbing in a single file of more than 1,100 lines.【F:app/main.py†L1-L1131】
* Domain objects (session metadata, transcripts, evaluation summaries) are shaped as loosely typed dictionaries shared across endpoints, making it difficult to safely add new personas or parameter sets.【F:app/main.py†L74-L1023】
* The new requirement—introducing another team of agents that supports a distinct parameter bundle for Veneo's general chat—requires clearer seams for routing, state, configuration, and agent instantiation so that features can coexist without interference.

**Primary objectives**

1. Decouple HTTP concerns from domain logic so additional features (general chat, future agent teams) can ship independently.
2. Provide explicit data contracts and persistence boundaries for session state to prevent cross-feature regressions.
3. Introduce an extensible agent-team orchestration layer that can register multiple personas per session and surface configuration-driven parameters.
4. Preserve existing interview flows while enabling an opt-in Veneo general chat experience behind feature gates.

## 2. Observed pain points (code review summary)

| Area | Issue | Impact on new agent team |
| --- | --- | --- |
| Routing (`app/main.py`) | All endpoints (upload, questions, evaluation, voice, realtime) live in one module, interleaving FastAPI routing with business logic and cross-cutting concerns.【F:app/main.py†L1-L571】【F:app/main.py†L572-L1023】 | Hard to isolate changes for Veneo chat without risking regressions in interview flows. |
| Session state | Global `active_sessions` dict and helper functions mutate nested dicts in place.【F:app/main.py†L74-L388】 | No schema enforcement; adding a general chat session risks type mismatches and race conditions. |
| Agent orchestration | The `InterviewPracticeAgent` is instantiated and invoked inside route handlers with hard-coded model/temperature parameters.【F:app/main.py†L336-L856】 | Cannot register multiple agents or swap parameter bundles per customer. |
| Realtime/voice setup | Realtime connection payloads and voice catalog helpers are baked into the route logic.【F:app/main.py†L856-L1023】 | Reuse for general chat would require duplicating code or branching logic inline. |

## 3. Target compartmentalized architecture

### 3.1 API boundary

* Create `app/api/` package with routers grouped by concern: `sessions.py`, `questions.py`, `evaluations.py`, `voice.py`, and `chat.py` (new for Veneo general chat).
* Slim down `app/main.py` to FastAPI initialization, dependency wiring, and router inclusion. This file should not hold business rules.
* Each router should delegate to service-layer functions and operate solely on typed request/response models.

### 3.2 Service layer

* **SessionService (`app/services/session_service.py`)**: encapsulate CRUD operations on session state; expose methods like `create_session`, `get_session`, `update_transcript`. Internally depend on a `SessionStore` abstraction.
* **QAService (`app/services/qa_service.py`)**: orchestrate question generation, evaluation, and fallback heuristics. Accept injected agents via an `AgentTeam` facade so both interview and general chat flows can share infrastructure while swapping personas/parameters.
* **ChatService (`app/services/chat_service.py`)**: handle Veneo-specific conversation flows, applying their parameter bundle, conversation memory rules, and guardrails.
* **VoiceService & RealtimeClient**: extract voice catalog lookup, preview synthesis, and realtime session bootstrapping into reusable modules to prevent duplication between interview and general chat experiences.

### 3.3 Agent team orchestration

* Model an `AgentTeam` interface exposing lifecycle hooks (`boot`, `delegate`, `summarize`). Each feature registers its team composition (e.g., Veneo general chat might use `PrimaryResponder` + `SafetyReviewer`).
* Implement an `AgentFactory` that accepts persona definitions (model, parameters, prompt templates, safety settings) and returns configured agent instances. Factor out repeated configuration to support future teams without modifying routes.
* Introduce an `AgentTeamResolver` responsible for selecting the appropriate team per session based on feature flags, tenant metadata, or request payloads.
* Ensure the resolver is injected into services/routers via FastAPI dependencies to keep the API layer declarative.

### 3.4 Data contracts and persistence

* Define Pydantic models under `app/schemas/` for session state slices (e.g., `SessionSummary`, `TranscriptEntry`, `AgentRunConfig`).
* Replace dictionary mutation with typed updates to guarantee compatibility when multiple features read/write the same session record.
* Consider persisting session data via an interface (in-memory + optional durable backend) to support parallel development of new agent teams without reworking storage.

### 3.5 Configuration management

* Create `app/settings.py` (Pydantic `BaseSettings`) containing structured configuration classes: `AgentSettings`, `RealtimeSettings`, `VoiceSettings`, and feature-specific `GeneralChatSettings` for Veneo.
* Store persona/parameter bundles in configuration (YAML or JSON) to enable non-engineering teams to adjust prompts, temperatures, and tool permissions.
* Use FastAPI dependency injection to fetch settings per request, enabling environment overrides and A/B experiments.

### 3.6 Observability and compliance

* Instrument the new services with structured logging around agent delegation, latency, and error handling so that introducing additional teams remains debuggable.
* Emit metrics/traces for team selection decisions to verify that Veneo tenants route to the general chat persona while others stay on the interview coach.
* Centralize audit logging (message content, agent responses, safety filters) to satisfy enterprise compliance requirements when multiple agent teams coexist.

## 4. Implementation roadmap

1. **Lay the foundation**
   * Add `app/api/`, `app/services/`, `app/schemas/`, and `app/settings.py` modules.
   * Introduce `SessionStore` abstraction with unit tests to cover basic CRUD plus concurrency edge cases.

2. **Extract session and QA flows**
   * Move existing session and question/evaluation logic into `SessionService` and `QAService` respectively.
   * Update existing routes to use the services while keeping their public API unchanged; add targeted tests.

3. **Introduce agent-team infrastructure**
   * Implement `AgentFactory`, `AgentTeam`, and `AgentTeamResolver`.
   * Wrap current `InterviewPracticeAgent` usage into an interview-specific team for backwards compatibility.

4. **Enable Veneo general chat**
   * Create `ChatService` and `app/api/chat.py` router exposing the general chat endpoints.
   * Define Veneo configuration bundle and register it with the resolver behind a feature flag.
   * Verify routing/tests ensure only opted-in sessions receive the new team.

5. **Refine realtime & voice modules**
   * Extract voice/realtime helpers into dedicated services.
   * Update both interview and general chat flows to consume the shared implementations.

6. **Hardening & rollout**
   * Expand test coverage (unit + integration + smoke tests) for both agent teams.
   * Instrument telemetry dashboards; conduct load testing to ensure the resolver/agent factory scale.
   * Document extension points for additional teams and finalize migration guide.

## 5. Testing strategy

* **Unit tests**: cover service classes, resolver logic, and agent factory configuration parsing. Use fakes/mocks for agents to avoid live API calls.
* **Integration tests**: FastAPI `TestClient` suites per router validating HTTP contracts, feature flag behaviour, and session persistence.
* **Contract/smoke tests**: orchestrate end-to-end flows (upload → generate → evaluate, start general chat → exchange messages → summarize) with mocked outbound calls to ensure the assembled app behaves correctly.

## 6. Risks and mitigations

| Risk | Mitigation |
| --- | --- |
| Refactor touches many files simultaneously | Ship in the staged roadmap above with feature-flagged Veneo chat; keep tests green at each step. |
| Configuration drift between agent teams | Centralize persona definitions in configuration files validated by CI (schema linting). |
| Session schema incompatibilities | Use versioned Pydantic models and migration helpers when storing sessions. |
| Performance regressions with multi-agent orchestration | Add tracing and load tests to monitor latency; allow teams to toggle agents per feature until tuning is complete. |

## 7. Definition of done

* `app/main.py` reduced to bootstrapper with <200 lines and no embedded business logic.
* All routes reside under `app/api/` and rely on typed schemas and service abstractions.
* `SessionStore`, `AgentFactory`, and `AgentTeamResolver` support both interview and Veneo general chat flows, with tests demonstrating persona selection and parameter propagation.
* Configuration-driven persona bundles documented and validated in CI.
* Observability dashboards updated to reflect multi-agent metrics.

Executing this plan will compartmentalize the application, enabling Veneo's general chat team—and future agent teams—to plug into a consistent architecture without destabilizing existing interview functionality.
