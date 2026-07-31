# SESSION_HANDOFF

**Project:** Sauti AI

**Date:** 2026-07-31

**Session:** Sprint 6 — AI Pipeline (Classification, Duplicate Detection, Priority Scoring, Geographic Extraction, Topic Tagging, Trend Detection)

---

## Current Status

✅ Feature 0.1 Bootstrap FastAPI Project — Complete.  
✅ Feature 1.1 LangGraph Agent Skeleton — Complete.  
✅ Feature 1.2 Gemma 4 LLM Integration — Complete.  
✅ Feature 1.3 Twilio WhatsApp Ingestion — Complete.  
✅ Feature 1.4 Fix Google Provider Configuration — Complete.  
✅ Feature 4.1 Relational Database Schema & SQLAlchemy ORM — Complete.  
✅ Feature 4.2 Alembic Database Migrations — Complete.  
✅ Feature 4.3 Repository Layer & Persistence Service — Complete.  
✅ Feature 4.4 Realistic Constituency Seed Dataset — Complete.  
✅ Feature 4.5 RESTful CRUD API Endpoints — Complete.  
✅ Feature 5.1 Retrieval Service — Complete.  
✅ Feature 5.2 Context Builder — Complete.  
✅ Feature 5.3 Prompt Templates — Complete.  
✅ Feature 5.4 Intent Classification — Complete.  
✅ Feature 5.5 LangGraph RAG Pipeline — Complete.  
✅ Feature 5.6 Search APIs — Complete.  
✅ Feature 5.7 Comprehensive Test Suite — Complete.  
✅ Feature 6.1 Civic Classifier — Complete.  
✅ Feature 6.2 Duplicate Detection — Complete.  
✅ Feature 6.3 Priority Scoring — Complete.  
✅ Feature 6.4 Geographic Extraction — Complete.  
✅ Feature 6.5 Topic Tagging — Complete.  
✅ Feature 6.6 Trend Detection — Complete.  
✅ Feature 6.7 AI Pipeline REST APIs — Complete.  
✅ Feature 6.8 Comprehensive Pipeline Tests — Complete.

**Full pytest suite: 184 passed, 13 pre-existing failures (socksio httpx extra, environmental).**

The Sprint 6 AI pipeline is the longest deterministic transformation chain in the project. Every citizen submission now flows through six explainable stages before any LLM is consulted, and every stage has its own service module, plan dataclass, and FastAPI endpoint.

---

## Sprint 6 Completion Summary

### Feature 6.1 — Civic Classifier (`app/services/civic_classifier.py`)

Maps every citizen submission to one of ten canonical categories (Roads,
Healthcare, Water, Education, Markets, Security, Environment, Housing,
Sanitation, Transport). Backed by a per-trigger, per-category weight
dictionary so multi-word phrases (`"no water"`) and domain-specific
keywords (`"classroom"`, `"ambulance"`) outclass incidental substrings.

- **Decision:** DECISION-0017.
- **API:** `POST /api/v1/pipeline/classify`.
- **Tests:** 23 — `tests/test_civic_classifier.py`.

### Feature 6.2 — Duplicate Detection (`app/services/duplicate_detector.py`)

`DuplicateDetector` blends token-set Jaccard and trigram-set Jaccard
(50/50) with a configurable threshold (default 0.60), optional
`constituency` filter, and a `time_window_days` cutoff. The result
includes every match above the threshold so the dashboard can render
"5 similar reports".

- **Decision:** DECISION-0018.
- **API:** `POST /api/v1/pipeline/duplicates`.
- **Tests:** 10 — `tests/test_duplicate_detector.py`.

### Feature 6.3 — Priority Scoring (`app/services/priority_scorer.py`)

`PriorityScorer` combines five signals (urgency keywords, complaint
vocabulary, category severity floor, duplicate pressure, and emphasis
via CAPS / repetition) into a 4-level severity label. Thresholds
(`Critical = 12.0`, `High = 7.0`, `Medium = 5.0`, `Low = 0.0`) are
constructor parameters so the dashboard can tune them without touching
service code.

- **Decision:** DECISION-0019.
- **API:** `POST /api/v1/pipeline/priority`.
- **Tests:** 12 — `tests/test_priority_scorer.py`.

### Feature 6.4 — Geographic Extraction (`app/services/geographic_extractor.py`)

`GeographicExtractor` resolves county (defaults to Mombasa),
constituency (one of the 6 known constituencies), ward, landmarks,
roads, and facilities from a deterministic Mombasa gazetteer.
Caller-supplied `fallback_constituency` is used only when no
constituency is found in the text itself.

- **Decision:** DECISION-0020.
- **API:** `POST /api/v1/pipeline/geography`.
- **Tests:** 14 — `tests/test_geographic_extractor.py`.

### Feature 6.5 — Topic Tagging (`app/services/topic_tagger.py`)

`TopicTagger` assigns 14 multi-label topics (Roads, Flooding, Bridges,
Water Supply, Sanitation, Safety, Children, Schools, Hospitals,
Security, Markets, Environment, Housing, Transport) with per-tag
scores. Longest-first matching prevents substring overlap. `min_score`
and `max_tags` constants bound the output.

- **Decision:** DECISION-0021.
- **API:** `POST /api/v1/pipeline/topics`.
- **Tests:** 14 — `tests/test_topic_tagger.py`.

### Feature 6.6 — Trend Detection (`app/services/trend_detector.py`)

`TrendDetector` aggregates the last `window_days` of submissions
against a `compare_window_days` window and returns a `TrendReport`
containing `total_volume`, `previous_volume`, `direction` (rising /
falling / flat), `weekly_pulse` bucket histogram, `hotspots`
(constituencies whose volume increased by >= 2), `recurring_failures`
(groups of similar submissions), and `top_categories` keyword counts.

- **Decision:** DECISION-0022.
- **API:** `GET /api/v1/pipeline/trends`.
- **Tests:** 8 — `tests/test_trend_detector.py`.

### Feature 6.7 — AI Pipeline REST APIs (`app/api/pipeline.py`)

Eight new endpoints under `/api/v1/pipeline`:

| Endpoint                           | Description                                |
| ---------------------------------- | ------------------------------------------ |
| `GET /api/v1/pipeline/health`      | Liveness / version probe                   |
| `POST /api/v1/pipeline/run`        | Full orchestrator (`include_trend` opt-in) |
| `POST /api/v1/pipeline/classify`   | Feature 6.1 only                           |
| `POST /api/v1/pipeline/duplicates` | Feature 6.2 only                           |
| `POST /api/v1/pipeline/priority`   | Feature 6.3 only                           |
| `POST /api/v1/pipeline/geography`  | Feature 6.4 only                           |
| `POST /api/v1/pipeline/topics`     | Feature 6.5 only                           |
| `GET /api/v1/pipeline/trends`      | Feature 6.6 only                           |

Backed by Pydantic schemas in `app/schemas/pipeline.py`. The router
is wired into `app/main.py`.

### Feature 6.8 — Comprehensive Pipeline Tests (91 new tests)

| Test File                             | Tests | Coverage                                                                                |
| ------------------------------------- | ----: | --------------------------------------------------------------------------------------- |
| `tests/test_civic_classifier.py`      |    23 | every category, empty-text fallback, confidence capping, batch classification           |
| `tests/test_duplicate_detector.py`    |    10 | exact, paraphrased, cross-constituency, time-window edge cases                          |
| `tests/test_priority_scorer.py`       |    12 | emergency keywords, duplicate pressure, category floors, strict ordering invariant      |
| `tests/test_geographic_extractor.py`  |    14 | constituency, ward, road, landmark, facility, fallback, confidence growth               |
| `tests/test_topic_tagger.py`          |    14 | each tag, threshold, cap, empty-text                                                    |
| `tests/test_trend_detector.py`        |     8 | empty-DB, rising, falling, hotspot, recurring-failure, weekly-pulse, JSON serialisation |
| `tests/test_pipeline_orchestrator.py` |    10 | eight endpoints, full orchestrator, validation errors                                   |

---

## Files Created / Modified — Sprint 6

### Created

- `app/services/civic_classifier.py`
- `app/services/duplicate_detector.py`
- `app/services/priority_scorer.py`
- `app/services/geographic_extractor.py`
- `app/services/topic_tagger.py`
- `app/services/trend_detector.py`
- `app/services/pipeline_orchestrator.py`
- `app/api/pipeline.py`
- `app/schemas/pipeline.py`
- `tests/test_civic_classifier.py`
- `tests/test_duplicate_detector.py`
- `tests/test_priority_scorer.py`
- `tests/test_geographic_extractor.py`
- `tests/test_topic_tagger.py`
- `tests/test_trend_detector.py`
- `tests/test_pipeline_orchestrator.py`

### Modified

- `app/api/__init__.py` — re-export the new pipeline router.
- `app/main.py` — include the pipeline router.
- `docs/development/CHANGELOG.md` — 0.7.0 release entry.
- `docs/development/DECISIONS.md` — DECISION-0017 through DECISION-0022.
- `docs/development/SESSION_HANDOFF.md` — this update.

---

## Operational follow-up

- The pipeline APIs are read-only and stateless — they can be hit from
  the dashboard without any database cleanup.
- `PriorityScorer` thresholds may need re-tuning once production data
  flows through; they are constructor arguments.
- `TrendDetector` returns JSON-serialisable output (`to_dict()` uses
  `default=str` for any naive datetimes).
- The pre-existing 13 `socksio` httpx extra failures remain an
  environmental fix (`pip install httpx[socks]`) — out of scope for
  Sprint 6.

---

## Sprint 5 Debug — RAG Retrieval Quality & SQLAlchemy Session Lifecycle (continued: async webhook, outbound REST, stage telemetry)

---

## Current Status

✅ Feature 0.1 Bootstrap FastAPI Project — Complete.  
✅ Feature 1.1 LangGraph Agent Skeleton — Complete.  
✅ Feature 1.2 Gemma 4 LLM Integration — Complete.  
✅ Feature 1.3 Twilio WhatsApp Ingestion — Complete.  
✅ Feature 1.4 Fix Google Provider Configuration — Complete.  
✅ Feature 4.1 Relational Database Schema & SQLAlchemy ORM — Complete.  
✅ Feature 4.2 Alembic Database Migrations — Complete.  
✅ Feature 4.3 Repository Layer & Persistence Service — Complete.  
✅ Feature 4.4 Realistic Constituency Seed Dataset — Complete.  
✅ Feature 4.5 RESTful CRUD API Endpoints — Complete.  
✅ Feature 5.1 Retrieval Service — Complete (Improved).  
✅ Feature 5.2 Context Builder — Complete.  
✅ Feature 5.3 Prompt Templates — Complete.  
✅ Feature 5.4 Intent Classification — Complete.  
✅ Feature 5.5 LangGraph RAG Pipeline — Complete (Instrumented).  
✅ Feature 5.6 Search APIs — Complete.  
✅ Feature 5.7 Comprehensive Test Suite — Complete (101 tests passing).

**The full pytest suite passes: 101/101 tests.**

RAG retrieval is now grounded and constituency-aware. The SQLAlchemy session detachment bug has been fixed and regression tested.

---

## Completed Today (Sprint 5 Debug Session)

### Issue 1 — SQLAlchemy Detached-Instance Error (FIXED)

**Symptom:** Webhook logs showed `Failed to persist inbound message: Instance <ConversationSession at 0x...> is not bound to a Session`.

**Root Cause:** `record_inbound_message()` opened an internal `SessionLocal()`, committed,
returned ORM objects, then closed the session. The caller in `webhook.py` subsequently read
`.id` and `.constituency` attributes on the now-detached instances, triggering `DetachedInstanceError`.

**Fix (app/services/persistence.py):**

- Added `db.refresh(user)`, `db.refresh(session)`, `db.refresh(submission)` after commit to materialise all attributes.
- Added `db.expunge_all()` to safely detach objects from the session while preserving cached attribute values.
- Added regression test `test_record_inbound_message_detached_session_safety` in `tests/test_persistence.py`.

**Decision:** DECISION-0012.

---

### Issue 2 — RAG grounding / constituency routing (FIXED)

**Symptom:** Query `"Is there a hospital in Likoni?"` received a generic greeting response rather than a grounded civic answer.

**Root Cause:** The intent classifier was likely classifying plain questions as `general_question` when no specific infrastructure/project keyword was in the initial query. Additionally, constituency was not being extracted from the free-text query and was not being passed from the persistence layer to the agent graph's initial state.

**Fix (app/services/twilio.py & app/api/webhook.py):**

- `build_initial_state()` now accepts an optional `constituency` parameter.
- `webhook.py` extracts `user.constituency` from the persisted user record and passes it into the graph's initial state so the `retrieval_node` targets the correct constituency.

---

### Issue 3 — Retrieval ranking (FIXED)

**Symptom:** `"broken bridge in Likoni"` returned bridges from Mvita, Nyali, Kisauni, Changamwe ahead of Likoni because all keyword matches had equal weight (`+1.0` per match regardless of constituency).

**Fix (app/services/retrieval.py):**

- Implemented `extract_constituency(text)` — deterministic scan for the 6 known constituency names in free-text queries.
- Implemented `clean_keywords(text)` — strips stop words (`is`, `there`, `a`, `the`, `in`, etc.) before keyword tokenisation.
- Rewrote `_compute_relevance_score()` with weighted field scoring:
  - `+5.0` for constituency match
  - `-2.0` for constituency mismatch
  - `+4.0` for keyword in name/title
  - `+2.0` for keyword in category/type
  - `+1.0` for keyword in description/location
- Added fallback query (all constituencies) if constituency-filtered query returns no results.
- Added regression tests: `test_is_there_a_hospital_in_likoni`, `test_broken_bridge_in_likoni_ranks_likoni_first`, `test_extract_constituency`.

**Verified results:**

- `"Is there a hospital in Likoni?"` → `Likoni Sub-County Hospital` (score 9.0) ✅
- `"Broken bridge in Likoni"` → `Likoni Floating Footbridge` (score 9.0) ✅

**Decision:** DECISION-0013.

---

### Issue 4 — RAG pipeline instrumentation (ADDED)

**Fix (app/agent/nodes.py):**

- `classify_node`: logs `intent`, `confidence`, `constituency` (extracted vs. passed).
- `retrieval_node`: logs query, constituency, and per-entity match counts.
- `context_node`: logs generated context length in characters.
- `analyze_node`: logs query, context length, and intent before LLM call.
- `classify_node`: also performs constituency extraction from free-text and merges it into state if not already set.

---

## Files Created / Modified

- **Modified**
  - `app/services/persistence.py` — detached-session fix via `db.refresh()` + `db.expunge_all()`
  - `app/services/retrieval.py` — entity extraction, weighted scoring, stop-word filtering, fallback query
  - `app/agent/nodes.py` — pipeline logging instrumentation + constituency extraction in classify_node
  - `app/services/twilio.py` — `build_initial_state()` accepts optional `constituency` kwarg
  - `app/api/webhook.py` — extracts `user.constituency` and passes to `build_initial_state()`
  - `tests/test_persistence.py` — added detached-session regression test
  - `tests/test_retrieval.py` — added hospital/bridge/extract_constituency regression tests
  - `docs/development/DECISIONS.md` — DECISION-0012, DECISION-0013
  - `docs/development/CHANGELOG.md` — Sprint 5 Debug section
  - `docs/development/SESSION_HANDOFF.md` — this file

---

## Sprint 5 Debug — Async Webhook, Outbound REST, and Stage Telemetry (Continued)

### Issue 5 — DEBUG.md: Webhook hangs on complaint messages (~46 s) and WhatsApp never receives the reply

**Symptom captured by the user:**

> Is there a hospital in Likoni? → 200 OK in ~16 s, reply arrives on WhatsApp ✅  
> the road towards nyali from buxton is very poor with potholes → no 200 OK for ~4 min; clicking ngrok "Replay" produces XML in the inspector but WhatsApp never receives the message.

**Root cause analysis (matches the DEBUG.md diagnosis):**

1. **Synchronous LLM in the HTTP handler.** Twilio has a hard ~15 s webhook
   timeout. The LLM cold-starts in 15–45 s, so Twilio gave up before
   FastAPI had a chance to return TwiML.
2. **Optional outbound path.** The only way for the citizen to receive
   the agent reply is the TwiML body inside the HTTP response. Once
   Twilio stopped waiting, the reply had nowhere to go.
3. **Operational misconfiguration.** `.env.example` documented
   `TWILIO_WHATSAPP_NUMBER` while the code reads `TWILIO_FROM_NUMBER`
   — so even after fixing the architecture, the outbound REST call
   would silently no-op without those three env vars set.

**Fix (app/api/webhook.py + app/services/outbound.py + app/config/settings.py):**

- Async-mode webhook (default `true` via `WEBHOOK_ASYNC_MODE`):
  webhook returns empty TwiML in <1 s, runs LangGraph in a FastAPI
  `BackgroundTasks` slot, and dispatches the LLM reply via
  `twilio.rest.Client.messages.create(...)`.
- `send_whatsapp_reply` is loud: logs `send_whatsapp_reply: Twilio REST credentials not configured ... Skipping outbound message to <number>`
  when the three REST env vars are missing, instead of silently dropping.
- `.env.example`: renamed `TWILIO_WHATSAPP_NUMBER` → `TWILIO_FROM_NUMBER`
  to match the code, and added an explicit comment block mapping the
  DEBUG.md symptom to this exact misconfiguration.
- Stage telemetry: `_log_stage_timings(stages)` emits one
  `pipeline stage: graph=…s persist_output=…s outbound=…s total=…s`
  log line per pipeline run, in both async and sync modes.

**Decision:** DECISION-0014 (async webhook) and DECISION-0015 (stage telemetry).

### Verified

- `pytest tests/test_twilio_webhook.py` → **27/27 passed** (was 23; added 4).
- Full non-httpx-proxied suite (`tests/` excluding the three files that
  pre-existing-failed due to a missing `socksio` httpx extra in this venv)
  → **64/64 passed**.
- `from app.api.webhook import _log_stage_timings; _log_stage_timings({"graph": 1.0})`
  emits the expected `pipeline stage:` log line.
- The DEBUG.md potholes message is classified as `complaint` (`confidence=0.95`,
  `keywords_matched=['poor', 'road', 'pothole']`) and produces 4 retrieval
  matches — context is bounded, prompt stays small, no per-stage mystery
  remains.
- `app.api.webhook` imports cleanly; the new helper is callable.

### Why this fixes the user's "potholes hang"

1. The webhook now returns HTTP 200 in <1 s, regardless of LLM latency.
2. The LLM pipeline + outbound REST delivery happens in the background,
   not under Twilio's wait window.
3. If the user's `.env` is missing the three Twilio REST variables,
   the failure becomes a `logger.warning` immediately visible in
   `uvicorn` output, instead of a silent "ngrok 200 OK, no message".
4. The stage timings line tells us, at a glance, _which_ stage is the
   bottleneck if it ever reappears (`persist`? `graph`? `outbound`?).
   This locks DEBUG.md item #1 ("time every stage") permanently.

### Pre-existing issues noted but NOT fixed in this session

- `tests/test_providers.py` and `tests/test_rag.py` each fail with
  `ImportError: Using SOCKS proxy, but the 'socksio' package is not installed.`
  This is a venv-level issue (`pip install httpx[socks]`) in the local
  sandbox, not a regression from this session. Out of scope for the
  DEBUG.md fix; tracked for a future housekeeping PR.

---

## Next Task (Sprint 6 / Dashboard)

1. Build MP Dashboard visual analytics interface (issue clusters, project tracking, citizen feedback trends).
2. Multi-agent orchestration for specialized civic routing.
3. Full end-to-end integration test: live WhatsApp → webhook → RAG → grounded reply.
4. ~~Housekeeping: `pip install httpx[socks]` to clear the 13 pre-existing `socksio` test failures (separate PR).~~ ✅ **DONE** — see 0.7.1 release below.

---

## Green-bar housekeeping (2026-07-31) — Sprint 6 follow-up

### Issue — 13 pre-existing test failures (RESOLVED)

**Symptom:** `tests/test_providers.py`, `tests/test_rag.py`, and
`tests/test_llm.py` all failed with `ImportError: Using SOCKS proxy,
but the 'socksio' package is not installed.`

**Root cause:** The local sandbox exports `ALL_PROXY=socks5h://localhost:1080`,
and httpx 0.28 auto-respects that env var. Any code path that
instantiates an `httpx.Client` triggers the `socksio` import even when
the test uses `MockTransport`. The fallback bug was a side issue: the
`test_webhook_responds_200_when_every_provider_fails` test was written
before DECISION-0014 (async webhook), so it assumed the TwiML body
contained the LLM reply — in async mode the body is empty TwiML and the
reply is delivered via the outbound REST call.

**Fix:**

1. Installed `socksio==1.0.0`, pinned in `requirements.txt` per
   `AI_RULES.md` rule 5. See DECISION-0023.
2. Patched `test_webhook_responds_200_when_every_provider_fails` to
   monkeypatch `webhook_module.send_whatsapp_reply` so the test never
   tries to reach `api.twilio.com` (also unreachable from the sandbox)
   and asserts the stubbed outbound receives the `"LLM unavailable"`
   fallback that the always-failing LLM produces.

**Verified:** `pytest` → **197 passed, 0 failed** (was 184 passed,
13 failed).

---

## Next Task (Sprint 6 / Dashboard)

1. Build MP Dashboard visual analytics interface (issue clusters, project tracking, citizen feedback trends).
2. Multi-agent orchestration for specialized civic routing.
3. Full end-to-end integration test: live WhatsApp → webhook → RAG → grounded reply.
