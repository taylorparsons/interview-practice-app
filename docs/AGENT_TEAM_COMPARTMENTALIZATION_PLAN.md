# Agent Team Compartmentalization Plan

## Purpose
Veneo Inc. is preparing to expand the general chat capability by onboarding an additional agent team that operates with a new parameter set. This plan outlines how to modularize the current interview practice experience so the new team can plug in without destabilizing the existing flows. The guidance focuses on isolating shared infrastructure (sessions, storage, UI scaffolding) from agent-specific logic to allow multiple personas or parameter packs to coexist.

## Current Coupling Snapshot
- **Session lifecycle lives in `app/main.py`**, where endpoints hydrate in-memory sessions, persist them, and eagerly spin up the `InterviewPracticeAgent`. The agent instance and its OpenAI model choice are stored directly on the session dict, which makes introducing alternative agent types awkward.【F:app/main.py†L45-L119】【F:app/main.py†L270-L288】
- **The front-end orchestrator (`app/static/js/app.js`) binds DOM events directly to long functions that mix UI state updates with REST calls.** Global buttons resolve to specific handler implementations, each assuming a single interview persona. Voice, resume, and session management actions all reach into shared state without a scoped namespace for variants.【F:app/static/js/app.js†L1570-L1784】【F:app/static/js/app.js†L1967-L2059】【F:app/static/js/app.js†L3038-L3195】
- **`InterviewPracticeAgent` encapsulates both prompt construction and OpenAI client setup** with a fixed system prompt and evaluation routine. Adding a second agent persona today would require branching inside this class or duplicating it, risking drift in shared behaviors like question storage and evaluation response parsing.【F:app/models/interview_agent.py†L14-L147】【F:app/models/interview_agent.py†L203-L288】

## Compartmentalization Objectives
1. **Register agent teams declaratively.** Define a central registry that maps `team_id` to OpenAI models, default prompts, and runtime adapters so the API can instantiate the correct persona without modifying endpoint logic.
2. **Segment session state per team.** Persist agent selection, parameters, and runtime caches under a dedicated key so multiple teams can share the same base session without overwriting each other.
3. **Isolate UI contracts.** Wrap CTA handlers so they call a lightweight client that resolves agent capabilities based on the selected team, keeping DOM bindings stable while allowing new teams to plug in specialized flows.
4. **Codify parameter packs.** Store tunable values (temperature, voice, evaluation rubric) in structured configs that can be validated and surfaced to the UI for selection.
5. **Guarantee regression safety.** Introduce tests that validate registry loading, session migrations, and CTA routing for both legacy and new teams.

## Recommended Refactors

### 1. Agent Registry Layer
- Create `app/models/agent_registry.py` exposing:
  - `AgentDescriptor` data class (id, label, prompt builder, OpenAI model id, optional voice metadata).
  - `get_agent(team_id, session_context)` returning a fully configured agent object.
  - Registry bootstrap that includes the current interview coach as `team_id="interview"` and the new general chat team (e.g., `team_id="general_chat"`).
- Update `start_agent` in `app/main.py` to request the descriptor based on `session["active_team"]` with a default fallback so endpoints stop hardcoding `InterviewPracticeAgent` only.【F:app/main.py†L213-L268】
- Allow registry entries to provide custom adapter classes. The general chat team can reuse `InterviewPracticeAgent` or supply a new class if its workflow diverges.

### 2. Session Schema Evolution
- Extend `_ensure_session_defaults` to initialize a `teams` map keyed by `team_id`, storing per-team caches like current question index, feedback history, and voice preferences. Keep shared metadata (resume text, docs) at the root for reuse.【F:app/main.py†L52-L88】
- Introduce a migration helper that upgrades persisted sessions the first time they are loaded, copying legacy top-level agent fields into `teams["interview"]`. Persist a version stamp to avoid repeated migrations.
- Track `session["active_team"]` so the UI knows which team’s CTA state to drive. When switching teams, call `_ensure_agent_ready` with `force_restart=True` to refresh the persona without losing other state.【F:app/main.py†L90-L124】【F:app/main.py†L213-L256】

### 3. API Surface Updates
- Add endpoints to list available teams (`GET /agent-teams`) and update the active team (`PATCH /session/{id}/team`). These endpoints should read from the registry so new teams ship without further FastAPI code changes.【F:app/main.py†L290-L471】
- Parameterize existing evaluate/generate routes to accept an optional `team_id`, defaulting to the session’s active team. Use the registry to inject prompt builders and parameter packs when calling OpenAI.
- Split long-running background tasks (e.g., resume processing, voice session bootstrapping) into reusable functions that accept agent descriptors so voice-only teams can reuse infrastructure without inheriting irrelevant prompts.【F:app/main.py†L471-L744】

### 4. Front-End Compartmentalization
- Build a lightweight client in `app/static/js/app.js` (e.g., `AgentOrchestrator`) that:
  - Fetches the team registry, caches capabilities (supports_voice, supports_examples, etc.), and exposes helper methods like `submitAnswer(teamId, payload)`.
  - Updates UI state when `activeTeam` changes (toggle voice CTAs off if the new team lacks voice support, swap labels, etc.).【F:app/static/js/app.js†L1420-L1779】【F:app/static/js/app.js†L2475-L2854】
- Wrap existing CTA handlers so they delegate to the orchestrator and inject `teamId`. For example, `handleAnswerSubmission` should read `activeTeam` and call `/evaluate-answer?team=...` while leaving DOM interactions untouched.
- Move team-specific copy, icons, and voice settings into configuration maps to avoid branching across the file.
- For modal workflows (sessions, voice settings), ensure event listeners query capability flags before rendering options so new teams can enable/disable features cleanly.【F:app/static/js/app.js†L3082-L3195】

### 5. Parameter Pack Management
- Represent parameter sets (model, temperature, evaluation rubric, voice defaults) in JSON or Pydantic models that live alongside the registry. Offer per-team overrides with inheritance from a shared base.
- Surface editable parameters via the UI settings drawer so product can tune the new team without redeploying. Persist overrides under `session["teams"][teamId]["parameters"]` for auditability.

### 6. Testing & Migration Checklist
1. **Unit tests** covering registry resolution, session migration logic, and fallback behavior when a team id is unknown (`pytest -k registry`).
2. **API integration tests** using FastAPI’s TestClient to simulate switching teams mid-session and verifying that the appropriate model/prompt is used.
3. **Front-end contract tests** (Jest or Playwright) to ensure CTA availability toggles correctly when switching between interview and general chat personas.
4. **Migration dry run** script that iterates persisted session files, upgrades them, and reports any anomalies before deploying.
5. **Rollback plan**: keep legacy fields populated during the first release so reverting is non-breaking.

## Implementation Milestones
1. **Schema & Registry Foundation (Sprint 1)**
   - Implement registry, session versioning, and new endpoints.
   - Add backend tests ensuring both teams can generate/evaluate with shared documents.
2. **Front-End Orchestrator (Sprint 2)**
   - Introduce orchestrator client, refactor CTA handlers, and gate features by capability flags.
   - Provide UI affordances for selecting the active team and previewing parameter packs.
3. **General Chat Team Enablement (Sprint 3)**
   - Define the new agent descriptor with its parameter pack.
   - Hook up documentation updates (CTA map + team selection guides) and run migration scripts in staging.
4. **Post-Launch Hardening (Sprint 4)**
   - Monitor logging/telemetry by team id, fine-tune prompts, and collect feedback.
   - Incrementally enable advanced CTAs (e.g., voice, transcripts) for the new team once validated.

## Rollout Considerations
- **Logging**: include `team_id` in structured logs and analytics for traceability.【F:app/main.py†L36-L44】
- **Feature flags**: wrap the new team behind a flag so support can toggle access if the parameter set causes quality regressions.
- **Documentation**: update CTA diagrams once the orchestrator refactor is complete so each CTA lists capability coverage per team.
- **Support playbook**: ensure session export/import tools understand per-team data to avoid cross-contamination during troubleshooting.

Following this plan will allow Veneo Inc. to add additional agent teams and parameter sets without duplicating business logic or risking regressions in the existing interview preparation workflows.
