# LangGraph integration sketch

## Goals
- Wrap `app/models/interview_agent.py` in a minimal LangGraph to add explicit control flow, retries, and streaming for the clarify → respond → fallback loop.
- Add checkpointed memory so sessions persist across turns (start with in‑memory, allow swap to Redis/Postgres later).

## State graph (clarify → respond → fallback)
- **State shape (TypedDict example)**: `{"session_id": str, "mode": Literal["star", "capability"], "user_msg": str, "resume": str, "jd": str, "clarifications": list[str], "answer": str | None, "evaluation": dict | None, "error": str | None}`
- **Nodes**
  - `ingest`: Normalize inbound message, decide mode (STAR+I vs capability coaching), attach resume/JD from session store, and flag if clarifications are needed.
  - `clarify`: If required info is missing (e.g., metric, impact, scope), `interrupt()` and ask 1–2 targeted questions; resume when the user replies.
  - `respond`: Call `InterviewPracticeAgent` to draft or evaluate. On success, update `answer/evaluation`. On exceptions or bad JSON, set `error="model_failed"`.
  - `fallback`: If `error` is set, produce heuristic feedback (existing fallback heuristics) and a concise answer scaffold.
  - `finish`: Return a stable payload for the FastAPI layer (`answer`, `evaluation`, `clarifications_needed`, `mode`, `used_fallback`).
- **Edges (example)**
  - ingest → (needs_clarification?) clarify : respond
  - clarify → respond
  - respond → (error?) fallback : finish
  - fallback → finish
- **Retries**: Use node-level retry for `respond` with small backoff; log attempt counts (`attempt=1/2`) to match existing retry semantics in logs.
- **Streaming**: Use `graph.stream(..., stream_mode="messages")` to surface model tokens and `stream_mode="updates"` for state changes; map to SSE/websocket in FastAPI for live UI updates.

## Persistence plan
- **Start (no infra change)**: `MemorySaver` checkpointer; set `thread_id=session_id` from your existing session id. This preserves history across requests within the same session.
  ```python
  from langgraph.checkpoint.memory import MemorySaver
  checkpointer = MemorySaver()
  graph = builder.compile(checkpointer=checkpointer)
  result = graph.invoke(
      {"session_id": sid, "user_msg": msg},
      config={"configurable": {"thread_id": sid}},
  )
  ```
- **Upgrade path**
  - Redis: swap to `RedisSaver` for higher concurrency and eviction control.
  - Postgres: use `PostgresSaver`/`AsyncPostgresSaver` when you need durable, queryable history (session replay, audit, analytics).
  - Store resume/JD in state (or a store keyed by `session_id`) so clarifications and answers remain contextual across turns.
- **Schema hygiene**: Keep input/output schemas distinct so the API only returns user-safe fields (omit internal flags, retries).

## Integration steps (high level)
1. Add `langgraph` deps; create `app/graphs/interview_graph.py` with the StateGraph definition above, wiring `InterviewPracticeAgent` calls inside `respond`.
2. Wrap existing FastAPI endpoints to call the graph (`graph.invoke` for sync, `graph.astream_events` for streaming).
3. Wire session ids into `thread_id`; ensure logging includes `session_id` and `request_id`.
4. Add tests: API-level (FastAPI TestClient) for clarify → respond → fallback paths; unit tests for graph node routing with fake agent/tool stubs.

## MCP doc helper setup (`~/.codex/config.toml`)
- Purpose: enable atlas-docs MCP so you can query LangGraph docs (and others) from the Codex CLI while coding.
- Add (or merge) this block to `~/.codex/config.toml`:
  ```toml
  [mcp_servers.atlas-docs]
  command = "npx"
  args = ["-y", "@cartographai/atlas-docs-mcp"]
  ```
- If you already have other `mcp_servers.*` entries, keep them and only add the `atlas-docs` table.
- Restart the Codex CLI session (or reload config) if changes don’t take effect immediately.
