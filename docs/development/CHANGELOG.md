# CHANGELOG

**Project:** Sauti AI

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added

- Twilio WhatsApp ingestion webhook (Feature 1.3).
- `app/schemas/webhook.py` — Pydantic `TwilioPayload` model with
  snake*case accessors (`from*`, `body`, `num_media`, ...) backed
by Twilio's PascalCase alias fields, plus `has_media()`and`media_summary()` helpers.
- `app/services/twilio.py` — pure helpers `build_initial_state`,
  `render_twiml_response` (via `twilio.twiml.messaging_response`),
  and `parse_twiml_message` (test helper).
- `app/api/webhook.py` — `POST /webhooks/twilio` accepting
  form-encoded Twilio Sandbox payloads, invoking the compiled
  LangGraph graph, and returning TwiML (`application/xml`) with
  the agent reply. Always returns HTTP 200, even when the graph
  raises (graceful fallback TwiML).
- `app/main.py` — `create_app` now includes the Twilio router via
  `app.include_router(twilio_router)`.
- `app/api/__init__.py` and `app/schemas/__init__.py` — re-export
  the new public symbols.
- `tests/test_twilio_webhook.py` — 20 tests covering schema
  validation, pure helpers, and the FastAPI route (happy path,
  empty body, graph exception, media payload, unauthenticated,
  minimum payload, one-invocation-per-request).
- New dependency pinned in `requirements.txt`:
  `twilio==9.10.9` plus the FastAPI sub-dependency
  `python-multipart==0.0.32`.
- Architectural decision recorded in
  `docs/development/DECISIONS.md` as `DECISION-0004`.

### Verified

- Full `pytest` suite passes (41 passed).
- Live `curl` smoke against `uvicorn app.main:app` returns
  HTTP 200 with a valid TwiML body on the `/webhooks/twilio`
  endpoint, both with and without an empty `Body`.
- OpenAPI schema exposes `paths=['/', '/webhooks/twilio']`.
- The real NVIDIA endpoint was reached end-to-end through the
  webhook during the live smoke test (the model returned HTTP 500
  on the test prompt, but the webhook still produced a graceful
  TwiML fallback, exactly as designed).
- No auth, no persistence, no Neon, no Redis, no LangGraph memory
  introduced — Sprint 3 constraints respected.

---

## [0.4.0] — 2026-07-28 — Twilio Webhook Ingestion (pending release)

### Added

- Gemma 4 LLM integration (Feature 1.2).
- `app/services/llm.py` — provider-isolated wrapper around NVIDIA's
  hosted chat-completions endpoint. Exposes `GemmaClient`,
  `ChatMessage`, `ChatCompletion`, typed `LLMError` hierarchy, and
  a cached `get_llm()` / `reset_default_llm()` singleton.
- `app/agent/nodes.py` — `analyze_node` now calls Gemma 4 through
  `get_llm()`, stores the assistant reply in
  `state["analysis"]`, and records `state["metadata"]["analyze_error"]`
  on any `LLMError` so the graph keeps running.
- `app/agent/nodes.py` — `respond_node` prefers the LLM analysis,
  falls back to the legacy echo, or surfaces an "LLM unavailable"
  message when the analyze node errored.
- `app/agent/state.py` — added the `analysis` field to
  `AgentState`.
- `app/config/settings.py` — added the NVIDIA settings block
  (`nvidia_api_key`, `nvidia_base_url`, `nvidia_model`,
  `nvidia_timeout_seconds`, `nvidia_max_tokens`,
  `nvidia_temperature`, `nvidia_top_p`, `nvidia_enable_thinking`).
- `.env.example` — documents every new NVIDIA variable.
- `tests/test_llm.py` — 13 tests covering the client (mocked
  transport), the analyze node, and graceful degradation paths.

### Verified

- Full `pytest` suite passes (19 passed).
- Graph executes end-to-end with a stubbed NVIDIA transport and
  produces the expected `analysis` + `response` values.
- Analyze node raises no uncaught exceptions when the API key is
  missing — the error is recorded in state metadata and the graph
  produces a graceful "LLM unavailable" response.
- Skeleton tests remain green without an API key by stubbing the
  `analyze_node` symbol bound in `app.agent.graph`.
- No tools, no memory, no RAG are connected — Sprint 2 constraints
  respected.

---

## [0.3.0] — 2026-07-28 — LLM Integration (pending release)

### Added

- LangGraph agent skeleton (Feature 1.1).
- `app/agent/` Python package exposing `build_graph` and
  `compile_graph`.
- `app/agent/state.py` — typed `AgentState` TypedDict with
  `input_message`, `steps`, `response`, `metadata`.
- `app/agent/nodes.py` — three placeholder nodes (`intake`,
  `analyze`, `respond`) that mutate state without any LLM call.
- `app/agent/router.py` — `route_after_analyze` placeholder
  returning `"respond"`.
- `app/agent/graph.py` — `build_graph()` and `compile_graph()`
  factories wiring `intake → analyze → (conditional) → respond → END`.
- `tests/test_agent_skeleton.py` — 4 smoke tests covering
  compilation, node wiring, end-to-end execution, and the
  empty-message edge case.
- New dependencies pinned in `requirements.txt`:
  `langgraph==1.2.9`, `langchain-core==1.5.1`.
- Architectural decision recorded in
  `docs/development/DECISIONS.md` as `DECISION-0001`.

### Verified

- `from app.agent import compile_graph; compile_graph().invoke({...})`
  completes successfully.
- All three placeholder nodes execute in order:
  `["intake", "analyze", "respond"]`.
- The compiled graph is an instance of
  `langgraph.graph.state.CompiledStateGraph`.
- Full `pytest` suite passes (7 passed).
- No LLM, tool, or memory layer is connected — Sprint 1 constraints
  respected.

---

## [0.2.0] — 2026-07-27 — Agent Skeleton (pending release)

### Added

- Bootstrap FastAPI project skeleton (Feature 0.1).
- `app/` Python package with sub-packages: `api`, `config`, `services`,
  `models`, `schemas`, `middleware`, `utils`.
- `app/main.py` — application entrypoint with `create_app()` factory
  and module-level `app` instance for `uvicorn app.main:app`.
- `GET /` endpoint returning `{"service": "Sauti AI", "status": "running"}`.
- `app/config/settings.py` — typed `Settings` class using
  `pydantic_settings.BaseSettings` with `.env` file support and
  `get_settings()` cached accessor.
- `requirements.txt` pinning `fastapi`, `uvicorn`, `python-dotenv`,
  `pydantic-settings`.
- `.env.example` documenting available environment variables.
- `.gitignore` covering Python, virtualenv, IDE, test, and OS artifacts.
- `tests/` package with smoke tests for the root endpoint and settings.

### Verified

- `uvicorn app.main:app` starts successfully.
- `GET /` returns HTTP 200 with the expected JSON payload.
- `GET /docs` (Swagger UI) returns HTTP 200.
- `GET /openapi.json` is auto-generated with `title="Sauti AI"`,
  `version="0.1.0"`, and `paths=["/"]`.
- `pytest` suite passes (3 passed).

---

## [0.1.0] — 2026-07-25

### Added

- Initial repository bootstrap.
