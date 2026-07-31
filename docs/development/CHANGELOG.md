# CHANGELOG

**Project:** Sauti AI

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

## [0.7.2] — 2026-07-31 — Issues Sync, Analytics Removal & appendChild Error Elimination

### Fixed

- **"Failed to appendChild" JavaScript error (`app/static/dashboard/assets/ui.js`)**: Rewrote the `el()` and `svg()` DOM helper functions to use a safe recursive `appendChildren()` function that handles `null`, `boolean`, `string`, `number`, and `Node` (including `SVGElement`) children without throwing. Previously, SVG nodes returned by `donutChart()`/`lineChart()` were treated as text via `createTextNode()`, causing a `HierarchyRequestError: Failed to execute 'appendChild'` on every chart render.
- **Issues page citizen name & created time sync (`app/api/dashboard.py`)**: Issues API now returns `submitted_at` (from `Submission` model) as the primary `created_at` timestamp, falling back to `Issue.created_at`. This ensures the citizen name and timestamp shown in the Issues table are real, synchronized values from the seeded dataset rather than missing or stale values.
- **Analytics page removed from SPA (`app/static/dashboard/assets/app.js`, `index.html`)**: Removed the Analytics route and its import from `app.js`, and removed the nav link from `index.html`. Navigating to `#/analytics` now safely falls back to the Overview page instead of throwing a render error.
- **Hardened page error handler (`app/static/dashboard/assets/app.js`)**: Wrapped the `renderRoute()` catch block in a secondary try/catch so any DOM errors during error reporting itself don't cascade into an uncaught exception that freezes the shell.

### Verified

- Full pytest suite: **17/17 passed** (`test_dashboard_api.py`).

---

## [0.7.1] — 2026-07-31 — Dashboard Visual Refinement & MP Constituency Sync

### Fixed

- **Blurred Glass Overlay Bug (`app/static/dashboard/assets/styles.css`)**: Fixed a CSS specificity issue where `.modal { display: grid; backdrop-filter: blur(4px); position: fixed; inset: 0; }` was overriding the browser's default `[hidden]` attribute stylesheet (`display: none`), causing the hidden modal container to overlay the entire dashboard viewport with a blur filter and translucent dark layer. Added explicit `[hidden] { display: none !important; }` and `.modal[hidden] { display: none !important; }` rules so the dashboard displays sharply and clearly with no unwanted glassmorphic blur.

### Changed

- **White-Background Dashboard Theme** (`app/static/dashboard/assets/styles.css`, `ui.js`): Updated the dashboard SPA theme from dark mode (`#0b1220`) to a modern, high-contrast, professional light-mode scheme with a pure white background (`#ffffff`), soft slate elevation (`#f8fafc`), crisp slate text, and emerald/sky accents. All SVG charts (donut, line graph, bar indicators) and table controls were updated to render sharply on white.
- **Constituency-Aware Telemetry & API Sync** (`app/api/dashboard.py`, `app/static/dashboard/assets/`): Updated `/overview`, `/infrastructure/summary`, `/projects/summary`, and `/activity` FastAPI endpoints to accept an optional `constituency` parameter and execute SQL-filtered aggregations.
- **MP Office Dashboard View** (`app/static/dashboard/index.html`, `app.js`): Added an MP badge (`🏛 Hon. MP Office`) and a constituency selector dropdown in the sticky topbar. Defaults to Likoni Constituency (or MP's active selection) across all tabs (Overview, Issues, Projects, Infrastructure, Analytics, Live Feed).
- **Enriched Database Seed Dataset** (`app/db/seed.py`): Populated 18 realistic citizen submissions, matching open/in-progress issues, AI summaries, and agent actions distributed across all 6 target constituencies (Likoni, Mvita, Nyali, Kisauni, Changamwe, Jomvu) to ensure full data sync with backend database models.

### Verified

- Full pytest suite: **60/60 passed** (`test_dashboard_api.py`, `test_crud_api.py`, `test_database.py`, `test_persistence.py`, `test_retrieval.py`, `test_twilio_webhook.py`). Added `test_overview_filters_by_constituency` regression test.
- Live seed execution: `python -m app.db.seed` successfully reseeded database.

---

## [0.7.0] — 2026-07-31 — MP Dashboard & Civic Intelligence Platform (Sprint 7)

### Added

- **Read-only dashboard analytics router** (`app/api/dashboard.py`): six new FastAPI endpoints under `/api/v1/dashboard` that power the entire SPA — `overview`, `issues` (with filters + facet counts), `infrastructure/summary`, `projects/summary`, `activity` (merged feed), and `pipeline/preview` (run the deterministic stages of the LangGraph pipeline against any hypothetical citizen message, including SQL retrieval, without invoking the LLM). See DECISION-0016.
- **Static dashboard SPA** (`app/static/dashboard/`): self-contained, hand-rolled, ES-module single-page app — no build step, no `node_modules`, no framework. Pages: Overview, Issues Explorer, Projects, Infrastructure, AI Pipeline Visualizer, Analytics, Live Activity Feed. Hand-rolled SVG bar / donut / line charts in `assets/ui.js`. Hash router for deep-linkable URLs. Responsive sidebar (collapses on `<800px`). See DECISION-0017.
- **Static SPA mount** (`app/main.py`): FastAPI now serves the dashboard from `/dashboard/index.html` and `/dashboard/assets/*` via `StaticFiles(html=True)`. No build step required — `uvicorn app.main:app` immediately exposes the dashboard.
- **Pipeline explainer endpoint** (`/api/v1/dashboard/pipeline/preview`): demonstrates to judges and users _exactly_ how a citizen message becomes a grounded response — returns the same intermediate state the agent sees (intent, confidence, top retrieval matches with relevance scores, assembled context).
- **Regression tests** (`tests/test_dashboard_api.py`, 16 tests): cover the SPA mount, the static file presence, every analytics endpoint, the issue filter behaviour, the pipeline preview's stage ordering, and the "hospital in Likoni" / "potholes in Nyali" demo prompts.

### Verified

- Full pytest suite: **80/80 passed** (was 64; +16 new dashboard tests). The 13 pre-existing `socksio` failures in `test_providers.py`, `test_rag.py`, and `test_llm.py` are still pre-existing and out of scope for this release.
- Live `uvicorn app.main:app` smoke test:
  - `GET /dashboard/index.html` → HTTP 200, 2971 bytes
  - `GET /dashboard/assets/styles.css` → HTTP 200, 13 462 bytes
  - `GET /dashboard/assets/app.js` → HTTP 200, 3296 bytes
  - `GET /api/v1/dashboard/overview` → JSON with 370 citizen reports, 18 projects, 42 infrastructure assets.
  - `GET /api/v1/dashboard/pipeline/preview?message=Is%20there%20a%20hospital%20in%20Likoni%3F` → `intake → classify (intent=infrastructure_lookup, confidence=0.72) → retrieval (top match: Likoni Sub-County Hospital, score 9.0) → context → analyze`. The exact demo flow Sprint 7 promised.
  - `GET /api/v1/dashboard/pipeline/preview?message=…potholes…` → `intent=complaint, confidence>0.5, keywords_matched=['pothole']`, 4 retrieval matches.
- `from app.api.dashboard import router; router.routes` → 6 routes registered.
- All dashboard pages render from the same JSON endpoints the SPA consumes; no parallel implementation, no data drift.

### Operational notes

- The dashboard is served from the same FastAPI process that ingests Twilio webhooks and exposes CRUD. No additional port or process to manage.
- No new Python dependencies (the SPA is plain ES modules + inline SVG).
- Authentication remains intentionally absent per the Sprint 7 spec; the dashboard is meant to be opened immediately at the demo URL.

---

## [0.6.2] — 2026-07-30 — Async Webhook, Outbound REST, and Stage Telemetry

### Fixed

- **Twilio webhook timeout on slow LLM turns** (`app/api/webhook.py`, `app/services/outbound.py`, `app/config/settings.py`): The webhook now returns HTTP 200 with empty TwiML in <1 s and runs the LangGraph pipeline + outbound delivery inside a FastAPI `BackgroundTask`. The citizen reply is dispatched to WhatsApp via `twilio.rest.Client.messages.create(...)`. This eliminates the `"Waiting to receive a response from your server 46 seconds so far"` failure captured in `DEBUG.md` and stops the slow-complaint hangs that previously left WhatsApp with no reply. See DECISION-0014.
- **Silent outbound drops** (`app/services/outbound.py`, `.env.example`): When `TWILIO_ACCOUNT_SID` / `TWILIO_AUTH_TOKEN` / `TWILIO_FROM_NUMBER` are unset the outbound function now logs `send_whatsapp_reply: Twilio REST credentials not configured ... Skipping outbound message to <number>` and returns `False` — failures are loud, never silent. `.env.example` was corrected: the legacy `TWILIO_WHATSAPP_NUMBER` (which the code never read) is now `TWILIO_FROM_NUMBER`, with a comment block explaining the DEBUG.md symptom (`ngrok 200 OK but no WhatsApp message`) maps to this exact misconfiguration.

### Added

- **`app/services/outbound.py`** — pure helper `send_whatsapp_reply(to, body, account_sid, auth_token, from_number) -> bool` that wraps `twilio.rest.Client.messages.create`, normalises the `whatsapp:` prefix on both numbers, and never raises (background tasks must not crash the server process).
- **`webhook_async_mode` setting** (`app/config/settings.py`, `.env.example`): boolean flag (default `true`, env `WEBHOOK_ASYNC_MODE`) toggles async vs sync webhook delivery without code changes. Sync mode is retained for local demos and tests that want the agent reply inside the HTTP response body.
- **Stage telemetry** (`app/api/webhook.py`, DECISION-0015): New `_log_stage_timings(stages: dict[str, float])` emits a single structured log line per pipeline run — `pipeline stage: graph=12.34s persist_output=0.03s outbound=0.05s total=12.42s` — exactly the breakdown DEBUG.md item #1 asked for. Both async and sync modes emit the line.
- **Regression tests** (`tests/test_twilio_webhook.py`):
  - `test_async_mode_background_task_invokes_graph_and_outbound` — asserts that in async mode the BackgroundTask actually runs the graph AND calls `send_whatsapp_reply` with the LLM reply (the guarantee DEBUG.md cares about).
  - `test_async_mode_outbound_skipped_when_credentials_missing` — asserts the no-credentials path is loud (outbound is still attempted, returns False, logs a warning).
  - `test_log_stage_timings_emits_total_line` — locks in the new structured log format.
  - `test_potholes_complaint_is_routed_as_complaint` — pins the DEBUG.md failing prompt (`"the road towards nyali from buxton is very poor with potholes"`) to the `complaint` intent, so retrieval stays scoped and the LLM prompt stays small.

### Verified

- Full webhook test suite: **27/27 passed** (`tests/test_twilio_webhook.py`).
- Full non-httpx-proxied suite: **64/64 passed** (`tests/` excluding `test_providers.py`, `test_rag.py`, `test_llm.py`; the 13 pre-existing failures in those three files are caused by a missing `socksio` module in this venv and are unrelated to this release — they were broken before any edits in this session).
- `from app.api.webhook import _log_stage_timings; _log_stage_timings({"graph": 1.0})` emits the expected `pipeline stage:` log line.
- The DEBUG.md potholes message is classified as `complaint` with confidence `0.95` and produces 4 retrieval matches (bounded context).
- The DECISION-0014 async path documented in the source docstring matches the actual behaviour.

### Operational follow-up (user-facing)

If you ever observe `"ngrok returned 200 OK but WhatsApp never received a message"` again, check `.env` first — you need all three of `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER` set. Without them the webhook behaves as designed but the reply is logged and dropped, which is exactly the symptom you saw before this release.

---

## [0.6.1] — 2026-07-30 — RAG Retrieval Quality & Session Lifecycle Fixes

### Fixed

- **SQLAlchemy Detached-Instance Error** (`app/services/persistence.py`): Calling `db.refresh()` on all three returned ORM objects (`user`, `session`, `submission`) and `db.expunge_all()` before closing the internal session eliminates the `DetachedInstanceError` that was logged on every inbound Twilio webhook request. See DECISION-0012.
- **Constituency routing to agent graph** (`app/services/twilio.py`, `app/api/webhook.py`): `build_initial_state()` now accepts an optional `constituency` parameter; the webhook handler extracts `user.constituency` from the persisted user record and passes it into the graph's initial state so that `retrieval_node` correctly targets the citizen's registered constituency.

### Improved

- **Entity extraction** (`app/services/retrieval.py`): New `extract_constituency(text)` function deterministically identifies one of the 6 known constituency names (`Likoni`, `Mvita`, `Nyali`, `Kisauni`, `Changamwe`, `Jomvu`) from free-text queries and applies it as a primary SQL `WHERE constituency = ?` filter.
- **Stop-word filtering** (`app/services/retrieval.py`): New `clean_keywords(text)` strips common English stop words before SQL keyword matching to reduce noise.
- **Weighted relevance scoring** (`app/services/retrieval.py`): Rewrote `_compute_relevance_score()` with tiered field weighting — constituency match `+5.0`, mismatch `-2.0`, name/title keyword `+4.0`, category `+2.0`, description `+1.0` — replacing the flat `+1.0 per keyword` approach.
- **Fallback retrieval**: If constituency-filtered query returns zero results, the service re-queries across all constituencies to prevent silent empty responses.
- **RAG pipeline logging** (`app/agent/nodes.py`): Added structured `logger.info()` calls in `classify_node`, `retrieval_node`, `context_node`, and `analyze_node` — logging intent, constituency, retrieval counts, context length, and pre-LLM prompt metadata for production observability.
- **Constituency auto-detection in classify_node**: `classify_node` now calls `extract_constituency()` on the inbound message and merges the result into agent state if not already set.

### Verified

- `"Is there a hospital in Likoni?"` → `Likoni Sub-County Hospital` (relevance score `9.0`) ✅
- `"Broken bridge in Likoni"` → `Likoni Floating Footbridge` (relevance score `9.0`) ✅
- No `DetachedInstanceError` on attribute access after `record_inbound_message()` closes its session.
- Full `pytest` suite passes (101/101 passed).

### Added

- SQL Retrieval Service (`app/services/retrieval.py`): Implemented multi-entity search across infrastructure, projects, previous submissions, and categorized issues with keyword relevance scoring and SQL constituency filtering.
- Context Builder (`app/services/context_builder.py`): Built structured Markdown prompt context generator with token/character limits and truncation controls.
- Prompt Templates & Prompt Builder (`app/prompts/`, `app/services/prompt_builder.py`): Added external template files (`system_prompt.md`, `rag_prompt.md`, `summarizer_prompt.md`) and dynamic prompt rendering without hardcoded prompts.
- Intent Classifier (`app/services/classifier.py`): Added rule-based and heuristic classification for citizen inquiries into standard intents (`infrastructure_lookup`, `project_lookup`, `complaint`, `status_update`, `general_question`) with confidence scoring.
- LangGraph RAG Pipeline (`app/agent/`): Extended `AgentState` schema with RAG metadata, implemented `classify_node`, `retrieval_node`, `context_node`, and updated graph execution path to `intake` → `classify` → `retrieval` → `context` → `analyze` → `respond` → `END`.
- RAG Pipeline Service (`app/services/rag.py`): Synchronous and agent-based RAG execution helper for easy invocation across API and CLI layers.
- Search REST API Router (`app/api/search.py`): Exposed `/api/v1/search`, `/api/v1/projects/search`, and `/api/v1/infrastructure/search`.
- Unit & Integration Test Suite (`tests/test_retrieval.py`, `tests/test_context_builder.py`, `tests/test_classifier.py`, `tests/test_rag.py`, `tests/test_search_api.py`): Expanded test coverage from 78 to 97 passing tests.
- Architectural Decision recorded in `docs/development/DECISIONS.md` under `DECISION-0011`.
- Comprehensive RAG architecture documentation in `docs/architecture/RAG.md`.

### Verified

- Full `pytest` suite passes (97 passed).
- RAG end-to-end responses correctly ground answers in SQL database seed context.
- Search REST APIs return ranked JSON search results.

### Added

- Relational Database Schema & SQLAlchemy 2.0 ORM integration (`app/db/session.py`, `app/models/domain.py`).
- Alembic database migration environment and initial schema migration (`alembic/`, `alembic/versions/68efad667dff_initial_schema_for_sprint_4_data_.py`).
- Domain models: `User`, `ConversationSession`, `Submission`, `Issue`, `Cluster`, `Infrastructure`, `Project`, `AgentAction`, and `AISummary`.
- Repository layer (`app/repositories/base.py`) providing clean data access for users, sessions, submissions, issues, infrastructure, projects, agent actions, and AI summaries.
- Persistence service (`app/services/persistence.py`) hooking inbound Twilio WhatsApp webhook messages and agent outputs into the SQLite database.
- Realistic seed dataset script (`app/db/seed.py`) populating 42 infrastructure items across 7 types (Roads, Schools, Hospitals, Markets, Water points, Boreholes, Bridges) and 18 projects (Ongoing, Planned, Completed) for 6 target constituencies (Likoni, Mvita, Nyali, Kisauni, Changamwe, Jomvu).
- RESTful CRUD API router (`app/api/crud.py`) exposing endpoints under `/api/v1/users`, `/api/v1/submissions`, `/api/v1/infrastructure`, `/api/v1/projects`, `/api/v1/issues`, `/api/v1/sessions`, and `/api/v1/clusters`.
- Pydantic domain schemas (`app/schemas/domain.py`) for API request validation and response serialization.
- Comprehensive unit and integration test suite (`tests/test_database.py`, `tests/test_repositories.py`, `tests/test_crud_api.py`, `tests/test_persistence.py`), expanding test coverage to 78 passing tests.
- Dependencies pinned in `requirements.txt`: `sqlalchemy==2.0.51`, `alembic==1.18.5`.
- Architectural decisions recorded in `docs/development/DECISIONS.md`: `DECISION-0008` (SQLite + SQLAlchemy Persistence), `DECISION-0009` (Seed Constituency Data), `DECISION-0010` (Dependency additions).
- Updated architecture documentation (`docs/architecture/DATABASE.md` with Mermaid ER diagram and table specs; `docs/architecture/ARCHITECTURE.md` with flowchart and system breakdown).

### Verified

- Full `pytest` suite passes (78 passed).
- Database migrations and seed execution verified end-to-end.
- RESTful CRUD endpoints return valid JSON responses for all entities.

### Fixed

- Google Provider configuration initialization: Call `dotenv.load_dotenv()` explicitly at settings startup to ensure `.env` parameters populate `os.environ` beforehand.
- Dynamic settings resolution and client imports: Resolved test suite monkeypatching fragility by calling `get_settings()` and `get_llm()` dynamically as module attributes.
- Duplicate settings loading: Removed duplicate calls to `get_settings()` in `GemmaClient` constructor and `app/services/llm/__init__.py`.
- Missing environment variable safety fallbacks: Added alignment fallback in `GoogleProvider` and `NvidiaProvider` constructors using `model_fields_set` checks.
- Twilio webhook LLM-failure fallback assertion in tests.
- IDE / LSP missing-import diagnostics: Added `pyrightconfig.json`, `pyproject.toml`, and `.vscode/settings.json` configuring `venvPath`, `extraPaths`, and `python.defaultInterpreterPath` pointing to `.venv`.
- Secret scanning push protection: Sanitized `.env.example` to replace accidental committed API key with empty placeholder and amended commit to unblock GitHub push protection (`docs/deployment/ISSUES.md`).

### Added

- `docs/deployment/ISSUES.md` — deployment and push protection issues log.
- `pyrightconfig.json`, `pyproject.toml`, `.vscode/settings.json` — workspace configuration for Pyrefly / Pyright / VS Code virtual environment path and interpreter resolution.
- Startup diagnostics in `create_app` displaying CWD, loaded API keys, and active provider/model configurations.
- Task 9 verification unit tests in `tests/test_providers.py` covering `.env` loading, key routing to provider, configuration error raises, and successful provider initialization.
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
