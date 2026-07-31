# DECISIONS

**Project:** Sauti AI

**Purpose**

This document records significant architectural and engineering
decisions for the project. Each decision captures the _what_, the
_why_, the alternatives that were considered, and the consequences.
Entries are immutable once merged; supersede by writing a new entry
that references the prior one.

Format based on Michael Nygard's
[documenting architecture decisions](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions).

---

## DECISION-0001 — Adopt LangGraph for agent orchestration

**Date:** 2026-07-27

**Status:** Accepted

**Context**

Sauti AI requires a graph-based orchestration layer that can later
host multi-step reasoning, tool calling, memory, and human-in-the-loop
checkpoints without a rewrite of the foundation. Sprint 1 introduces
only the _skeleton_ of this layer — no LLM, no tools, no memory.

**Decision**

Use [`langgraph`](https://langchain-ai.github.io/langgraph/) as the
agent orchestration framework. Pin `langgraph==1.2.9` and
`langchain-core==1.5.1` in `requirements.txt`.

The agent skeleton is laid out as:

- `app/agent/state.py` — typed `AgentState` (a `TypedDict`).
- `app/agent/nodes.py` — placeholder nodes returning state mutations.
- `app/agent/router.py` — placeholder routing function.
- `app/agent/graph.py` — `StateGraph` definition + `compile_graph()`.

**Alternatives considered**

| Option                                    | Reason rejected                                                                 |
| ----------------------------------------- | ------------------------------------------------------------------------------- |
| Roll our own async DAG                    | High maintenance, no built-in checkpointing for future memory work.             |
| LangChain Agents (legacy `AgentExecutor`) | Opaque control flow, weaker graph semantics, no native branching/checkpointing. |
| Haystack / custom pipeline                | Adds a second framework; no team familiarity yet.                               |

**Consequences**

- Positive: native `StateGraph` + `compile()` + future checkpointing.
- Positive: aligns with the long-term roadmap (Sprints 4–5 mention
  memory, multi-agent orchestration, and AI pipelines).
- Neutral: adds two new top-level dependencies; recorded here.
- Risk: LangGraph 1.x is recent — pin minor versions to avoid
  surprise breaking changes; revisit when 1.x stabilises further.

---

## DECISION-0002 — Configuration framework (FastAPI skeleton)

**Date:** 2026-07-25

**Status:** Accepted

**Context**

Feature 0.1 needed typed application settings.

**Decision**

Adopted `pydantic-settings` for `.env` parsing and validation.

**Consequences**

- Single, consistent configuration source.
- Tests can call `get_settings.cache_clear()` to reset the cached
  singleton between cases.

---

## DECISION-0003 — Adopt NVIDIA Hosted Gemma 4

Date: 2026-07-27

Status:
Accepted

### Context

Sprint 2 introduces the first production LLM.

The project requires a hosted model that is free for development,
supports modern reasoning, and integrates easily with LangGraph.

### Decision

Use NVIDIA's hosted endpoint for:

google/gemma-4-31b-it

Authentication will use:

NVIDIA_API_KEY

The integration will live behind a service abstraction so providers can
be swapped later without changing the graph.

## Example:

import requests

invoke_url = "https://integrate.api.nvidia.com/v1/chat/completions"
stream = False

headers = {
"Authorization": "Bearer $NVIDIA_API_KEY",
"Accept": "text/event-stream" if stream else "application/json",
}

payload = {
"messages": [
{
"role": "user",
"content": ""
}
],
"model": "google/gemma-4-31b-it",
"chat_template_kwargs": {
"enable_thinking": True
},
"max_tokens": 16384,
"stream": stream,
"temperature": 1,
"top_p": 0.95
}

response = requests.post(invoke_url, headers=headers, json=payload, stream=stream)
if stream:
for line in response.iter_lines():
if line:
print(line.decode("utf-8"))
else:
print(response.json())

## A clean Architecture would be:

A clean architecture would be:

app/
├── agent/
│ ├── graph.py
│ ├── nodes.py # analyze_node() calls the LLM service
│ ├── router.py
│ └── state.py
│
├── services/
│ └── llm.py # NVIDIA API wrapper
│
├── config/
│ └── settings.py # NVIDIA_API_KEY, MODEL_NAME
│
└── tests/
└── test_llm.py

### Alternatives

OpenAI

Rejected due to API cost.

Anthropic

Rejected due to API cost.

Self-hosted models

Deferred until infrastructure exists.

### Consequences

Positive

- Free development endpoint
- High-quality reasoning
- Provider isolated behind a service layer

Risk

API rate limits during development.

Mitigation

Keep all model access inside `app/services/llm.py`.

## DECISION-0004 — Adopt Twilio WhatsApp Sandbox as the ingestion layer

**Date:** 2026-07-28

**Status:** Accepted

**Context**

Sprint 3 introduces the first real ingestion channel. Citizens
submit complaints, suggestions, and development requests through
WhatsApp (text, images, voice notes, documents). We need a
provider whose webhook interface can deliver all of those formats
into the LangGraph agent that Sprint 1–2 wired up.

**Decision**

Adopt the **Twilio WhatsApp Sandbox** as the development
ingestion layer. Pin `twilio==9.10.9` in `requirements.txt`.

The clean architecture in the draft (below) is implemented in
this sprint:

```text
app/
├── api/
│   └── webhook.py     # FastAPI router exposing POST /webhooks/twilio
├── services/
│   ├── llm.py         # NVIDIA / Gemma 4 (Sprint 2)
│   └── twilio.py      # Twilio payload parser + TwiML builder
├── schemas/
│   └── webhook.py     # Pydantic TwilioPayload model
└── agent/             # LangGraph (Sprint 1)
```

Twilio's `MessagingResponse` (`twilio.twiml.messaging_response`)
is used to build the TwiML body, keeping the wire format
identical to what a production Twilio number would send.

A future migration to Meta's WhatsApp Cloud API will only
require replacing the parser + TwiML builder in
`app/services/twilio.py`; the route, the agent, and the tests
remain untouched.

**Alternatives considered**

| Option                         | Reason rejected                                                                                                                                    |
| ------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| Meta WhatsApp Cloud API direct | Requires business verification and production-ready phone number before any local development; out of scope for the hackathon.                     |
| Roll our own HTTP ingestion    | Reinventing Twilio's webhook contract; no value-add for Sprint 3.                                                                                  |
| ngrok from day one             | ngrok is a _tunnel_, not a provider — it stays out of the dependency tree; the Sprint 3 feature only ingests HTTP, the user runs ngrok themselves. |

**Consequences**

- Positive: free sandbox; supports text, images, voice notes, and
  documents out of the box.
- Positive: Twilio's `MessagingResponse` guarantees the wire
  format Twilio expects.
- Positive: the agent layer is untouched; future migrations only
  rewrite `app/services/twilio.py`.
- Neutral: introduces one new top-level dependency (`twilio`),
  recorded here per `AI_RULES.md`.
- Neutral: also pulls in `python-multipart==0.0.32` as a FastAPI
  sub-dependency required for parsing form-encoded webhook
  payloads. Recorded here to satisfy `AI_RULES.md`.
- Out of scope (deferred to later features): request signature
  validation, outbound replies, media persistence, and conversation
  memory.

---

## DECISION-0005 — Multi-provider LLM backend (Google primary, NVIDIA fallback)

**Date:** 2026-07-28

**Status:** Accepted

**Context**

Sprint 3's live testing showed that the NVIDIA free-tier endpoint
returned HTTP 500 and occasional 60-second read timeouts when used
from the Twilio webhook. The webhook is the only entry point for
citizen feedback, so any provider outage directly blocks the
service. The current `app/services/llm.py` couples business
logic to NVIDIA's HTTP contract, making it impossible to swap
providers without touching the agent layer.

Sprint 4 introduces a provider-agnostic backend so that:

- providers can be added without modifying business logic,
- a Google primary path can absorb the load when NVIDIA is slow,
- retry + backoff is centralized so transient failures no longer
  crash the webhook,
- the default provider can be flipped by env var alone.

**Decision**

Introduce a new `app.services.llm.providers` package with:

- `base.LLMProvider` — abstract interface with
  `generate(messages) -> ChatCompletion`,
  `health_check() -> bool`,
  `provider_name() -> str`.
- `nvidia_provider.NvidiaProvider` — the existing NVIDIA httpx
  implementation, extracted into its own module.
- `google_provider.GoogleProvider` — new implementation using
  the official `google-genai` SDK (`GOOGLE_API_KEY`).

A `provider_factory.get_llm_provider(settings)` selects the
provider at runtime based on `LLM_PROVIDER` (default `google`).
The `GemmaClient` class (kept for back-compat with the Sprint 2
public API) becomes a thin wrapper around an `LLMProvider`,
translating `ChatMessage` / `ChatCompletion`.

`LLM_TIMEOUT`, `LLM_MAX_RETRIES`, and `LLM_RETRY_DELAY` (new env
vars) centralise retry behaviour via `retry.retry_with_backoff`,
which retries on timeouts, 429, 5xx, and connection errors but
**never** on validation errors.

Pin `google-genai==2.14.0` in `requirements.txt`; the SDK is the
official Google-published package that supersedes
`google-generativeai`.

**Alternatives considered**

| Option                                         | Reason rejected                                                                          |
| ---------------------------------------------- | ---------------------------------------------------------------------------------------- |
| Keep a single provider (NVIDIA only)           | Direct contradiction of the observed reliability problem.                                |
| Use `google-generativeai` (legacy SDK)         | Superseded by `google-genai`; the latter is the supported package per Google's API docs. |
| Hard-code the provider in `app/agent/nodes.py` | Re-couples business logic to a vendor; rejected.                                         |

**Consequences**

- Positive: vendor-agnostic business logic.
- Positive: centralised retry + timeout policy.
- Positive: feature-flag providers via env var only.
- Positive: webhook stays responsive during provider outages.
- Neutral: adds `google-genai==2.14.0` as a dependency,
  recorded here per `AI_RULES.md`.
- Risk: `LLM_PROVIDER` misconfiguration could leave the service
  with no working provider — the factory must raise a clear
  `LLMConfigurationError` in that case.

---

## DECISION-0006 — Centralized settings and environment initialization

**Date:** 2026-07-29

**Status:** Accepted

**Context**

During live testing, the Google Provider was unable to read the `GOOGLE_API_KEY` from the environment because the `.env` file was not loaded early enough into `os.environ` before Pydantic Settings instantiated the `Settings` class. Furthermore, the test suite and agent pipeline suffered from static/stale module imports which bypassed dynamic settings monkeypatching.

**Decision**

1. Explicitly import and call `dotenv.load_dotenv()` at the very top of `app/config/settings.py` before `Settings` class definition to ensure environment variables are populated.
2. Remove duplicate configuration calls to `get_settings()` in `GemmaClient` and `__init__.py`.
3. Modify `provider_factory.py` to import `settings` as a module and call `settings_module.get_settings()` dynamically, ensuring mock values correctly override cached settings in tests.
4. Modify `nodes.py` to import `llm` as a module and call `llm_module.get_llm()` dynamically, preventing stale function references during test execution.
5. Implement safety fallback alignments in `GoogleProvider` and `NvidiaProvider` constructors using `model_fields_set` check to align the API keys with `os.environ` if Pydantic Settings missed them but they are defined in the environment.
6. Introduce startup diagnostics in `create_app()` to output current working directory, loaded API key states, and LLM provider reports.

**Consequences**

- Positive: Google Provider successfully reads valid keys and connects to Google AI Studio.
- Positive: Standardised dynamic imports for settings/clients across the application, resolving test suite fragility.
- Positive: Improved visibility via startup diagnostics.
- Neutral: No new dependencies were introduced.

---

## DECISION-0007 — Virtual environment path configuration for IDE language servers

**Date:** 2026-07-29

**Status:** Accepted

**Context**

IDE type checkers and diagnostics tools (such as Pyrefly and Pyright) were reporting `missing-import` errors for dependencies installed within `.venv` (e.g., `httpx`, `pytest`, `fastapi.testclient`) because the language server fell back to global system site-packages instead of the project virtual environment.

**Decision**

Add `pyrightconfig.json`, `pyproject.toml`, and `.vscode/settings.json` at the root of the project configuring:

1. `venvPath = "."` and `venv = ".venv"` in `pyrightconfig.json` and `pyproject.toml`.
2. Explicit `python.defaultInterpreterPath` (`${workspaceFolder}/.venv/bin/python`) and `python.analysis.extraPaths` (`.venv/lib/python3.13/site-packages`) in `.vscode/settings.json`.

**Consequences**

- Positive: Solves LSP / IDE / Pyrefly `missing-import` warnings across `tests/test_llm.py` and `tests/test_providers.py`.
- Positive: Standardises Python language server interpreter resolution across VS Code and Pyrefly/Pyright development environments.
- Neutral: No runtime dependencies added.

---

## DECISION-0008 — Adopt SQLite & SQLAlchemy ORM for Persistent Storage

**Date:** 2026-07-30

**Status:** Accepted

**Context**

Prior to Sprint 4, Sauti AI functioned as a stateless conversational agent that discarded every inbound WhatsApp message and AI analysis immediately after generating a response. This prevented longitudinal civic analytics, complaint tracking, MP dashboard visualisations, and historical reasoning across citizen interactions.

**Decision**

Adopt SQLite with SQLAlchemy ORM (2.0+) and Alembic migrations as the core persistence layer. The database schema captures:

- `users` (Citizens submitting complaints)
- `sessions` (Conversation sessions)
- `submissions` (Citizen complaints & feedback)
- `issues` (Extracted complaints & categories)
- `clusters` (Grouped thematic issues & summaries)
- `infrastructure` (Constituency assets across 6 constituencies)
- `projects` (Constituency development projects)
- `agent_actions` (Audit log of agent execution steps)
- `ai_summaries` (Persisted AI analysis & reasoning)

**Consequences**

- Positive: Full historical persistence of citizen interactions and agent outputs.
- Positive: Standardized repository abstraction (`app.repositories`) decoupling business logic from storage.
- Positive: Automated schema migrations via Alembic.
- Neutral: SQLite provides zero-config file-based storage suited for local development and hackathon evaluation; seamless path to PostgreSQL for production.

---

## DECISION-0009 — Seed Constituency Infrastructure & Projects Dataset

**Date:** 2026-07-30

**Status:** Accepted

**Context**

To evaluate the agent's capability to ground its responses and analysis in real local context, Sauti AI needs baseline knowledge of existing infrastructure assets and active constituency projects across all 6 target constituencies (Likoni, Mvita, Nyali, Kisauni, Changamwe, Jomvu).

**Decision**

Implement an automated database seed script (`app/db/seed.py`) populating 42 realistic infrastructure assets (Roads, Schools, Hospitals, Markets, Water points, Boreholes, Bridges) and 18 constituency projects (Ongoing, Planned, Completed), alongside initial citizen users and complaints.

**Consequences**

- Positive: Gemma LLM and LangGraph agents can query real local assets and projects to ground responses.
- Positive: Provides instant sample data for MP analytics and dashboard visualizations.

---

## DECISION-0010 — Add SQLAlchemy and Alembic dependencies

**Date:** 2026-07-30

**Status:** Accepted

**Context**

Implementing relational database persistence and automated schema migrations required object-relational mapping and database migration tooling.

**Decision**

Pin `sqlalchemy==2.0.51` and `alembic==1.18.5` in `requirements.txt` to fulfill Sprint 4 Data Foundation requirements per `AI_RULES.md` rule 5.

**Consequences**

- Positive: Enables typed ORM models, migration history tracking, and repository layer abstraction.
- Neutral: Adds two dependencies to `requirements.txt`.

## DECISION-0011

Title

Adopt Retrieval-Augmented Generation using SQL Retrieval

Status

Accepted

Context

The civic knowledge base now exists in SQL.

LLM responses should reference factual constituency information instead of relying solely on model knowledge.

Decision

Implement Retrieval-Augmented Generation using SQLAlchemy repositories.

Retrieved data will be assembled into structured prompts before invoking the LLM.

No vector database will be introduced during the hackathon.

Consequences

Advantages

- Deterministic
- Explainable
- Fast
- Simple deployment
- Uses existing persistence layer

Tradeoffs

- Keyword retrieval only
- Semantic similarity deferred

---

## DECISION-0012 — Fix SQLAlchemy detached-instance session lifecycle in persistence service

**Date:** 2026-07-30

**Status:** Accepted

**Context**

Live Twilio webhook testing produced repeated log warnings:

```
Failed to persist inbound message:
Instance <ConversationSession at 0x...> is not bound to a Session;
attribute refresh operation cannot proceed
```

The root cause was that `record_inbound_message` in `app/services/persistence.py` created
ORM objects (`User`, `ConversationSession`, `Submission`) inside an internal `SessionLocal()`
scope, committed the transaction, then closed the session — returning the now-detached ORM
instances to the caller (`webhook.py`). When the caller read `.id` or `.constituency`
attributes after the session was closed, SQLAlchemy raised `DetachedInstanceError`.

**Decision**

After `db.commit()` and before `db.close()`, call:

1. `db.refresh(user)` — materialises all lazy-loaded attributes into the object.
2. `db.refresh(session)` — same for the conversation session.
3. `db.refresh(submission)` — same for the submission record.
4. `db.expunge_all()` — fully detaches all objects from the session in a safe state,
   so that attribute access after `db.close()` reads cached data without re-querying.

The webhook caller extracts primitive values (`user.id`, `submission.id`, `user.constituency`)
immediately after `record_inbound_message` returns, while the objects are still populated.

**Alternatives considered**

| Option                                              | Reason rejected                                                               |
| --------------------------------------------------- | ----------------------------------------------------------------------------- |
| Return only IDs (primitives) from the service       | Breaks existing call sites and test contracts that check `user.phone_number`. |
| Keep session open and pass it to the caller         | Leaks session lifecycle into the HTTP handler; complicates testing.           |
| Use `expire_on_commit=False` on the session factory | Global config change; risky side-effects on other repository paths.           |

**Consequences**

- Positive: Eliminates `DetachedInstanceError` from the webhook logs.
- Positive: Caller can safely read any scalar attribute after the session closes.
- Positive: Added `test_record_inbound_message_detached_session_safety` regression test to guard this behaviour.
- Neutral: One additional round-trip to DB per `refresh()` call (negligible for SQLite).

---

## DECISION-0013 — Constituency-entity extraction and weighted relevance scoring in RetrievalService

**Date:** 2026-07-30

**Status:** Accepted

**Context**

Live testing and DEBUG.md analysis revealed two retrieval quality issues:

1. **Wrong constituency ranking**: A query for `"broken bridge in Likoni"` returned bridges
   from Mvita, Nyali, Kisauni, Changamwe, and other constituencies ahead of Likoni,
   because the old scoring function treated all keyword matches equally (`score += 1.0`
   per match) with no constituency weighting.

2. **No entity extraction**: The constituency name in the query (`"Likoni"`) was not
   stripped from search keywords before SQL filtering — it polluted keyword scoring
   and was searched as a plain token instead of being used as a SQL `WHERE` filter.

**Decision**

Implement two improvements in `app/services/retrieval.py`:

**1. Entity extraction (`extract_constituency`):**
A deterministic function that scans the raw query string against a list of known
constituency names (`Likoni`, `Mvita`, `Nyali`, `Kisauni`, `Changamwe`, `Jomvu`).
If a match is found, the constituency is stripped from keyword scoring and applied
as the primary SQL `WHERE constituency = ?` filter before any keyword matching.

**2. Weighted relevance scoring (`_compute_relevance_score`):**
The scoring function now awards points by field significance:

| Match type                                 | Score  |
| ------------------------------------------ | ------ |
| Constituency exact match                   | `+5.0` |
| Constituency mismatch (other constituency) | `-2.0` |
| Keyword in record name / title             | `+4.0` |
| Keyword in record category / type          | `+2.0` |
| Keyword in description / location          | `+1.0` |

**3. Stop-word filtering (`clean_keywords`):**
Common English stop words (`is`, `there`, `a`, `the`, `in`, `can`, `please`, etc.)
are removed before keyword matching to reduce noise.

**4. Fallback behaviour:**
If a constituency-filtered query returns zero results (e.g., no hospital seeded
in that constituency), the service re-queries across all constituencies to avoid
silent empty responses.

**Alternatives considered**

| Option                                       | Reason rejected                                                                  |
| -------------------------------------------- | -------------------------------------------------------------------------------- |
| Vector similarity search (pgvector / Qdrant) | Out of scope for hackathon; deferred to post-Sprint 6.                           |
| BM25 full-text indexing                      | Requires additional dependencies; SQL ILIKE is sufficient at this scale.         |
| Named-Entity Recognition model               | Heavyweight; a simple keyword scan over 6 known names is deterministic and fast. |

**Consequences**

- Positive: `"Is there a hospital in Likoni?"` now correctly returns `Likoni Sub-County Hospital` as the top result.
- Positive: `"Broken bridge in Likoni"` now correctly ranks `Likoni Floating Footbridge` first (score `9.0`) above all other constituencies.
- Positive: Constituency is automatically extracted from free-text queries, enabling RAG grounding without requiring the caller to pass `constituency` explicitly.
- Positive: Added regression tests `test_is_there_a_hospital_in_likoni` and `test_broken_bridge_in_likoni_ranks_likoni_first` in `tests/test_retrieval.py`.
- Neutral: No new dependencies added.

## DECISION-0014 — Async webhook with Twilio REST outbound delivery

**Date:** 2026-07-30

**Status:** Accepted

**Context**

Live WhatsApp sandbox testing captured the following failure mode:

1. A simple contextual query like `"Is there a hospital in Likoni?"` reached
   WhatsApp in ~16 s (slow but inside Twilio's webhook timeout).
2. A complaint like `"the road towards nyali from buxton is very poor with
potholes"` produced a webhook that _never_ returned 200 OK within Twilio's
   wait window — Twilio displayed "Waiting to receive a response from your
   server 46 seconds so far" and retried.
3. Hitting "Replay" on ngrok inspect caused the request to return quickly
   (DB warm, LLM warm, modules imported), but the response went only to the
   ngrok inspector and never to WhatsApp.

Root cause analysis showed two contributing factors:

- **Synchronous LLM in the request loop.** The webhook invoked the
  LangGraph pipeline (which calls Gemma / Gemini) inside the HTTP handler,
  so Twilio's hard ~15 s webhook timeout was exceeded on cold starts.
- **Optional/no outbound path.** The only path that returned TwiML back to
  Twilio was the synchronous HTTP response. There was no fallback that
  could deliver a reply _after_ the request had returned.

The architectural fix is to acknowledge Twilio immediately (≤ 1 s, empty
TwiML body), execute the pipeline asynchronously, and dispatch the final
reply through the Twilio REST API.

**Decision**

Introduce async-mode webhook delivery:

1. `webhook_async_mode: bool` flag in `Settings` (default `true`,
   env `WEBHOOK_ASYNC_MODE`) toggles between modes without code changes.
   - `true` → webhooks return empty TwiML immediately; the pipeline runs
     in a FastAPI `BackgroundTasks` slot and the reply is sent via
     `app.services.outbound.send_whatsapp_reply`.
   - `false` → legacy synchronous path retained for local demos and tests
     that want the agent reply inside the HTTP response body.
2. `BackgroundTasks.add_task(_run_pipeline_and_reply, …)` schedules a
   deterministic background coroutine that:
   - builds the agent state,
   - invokes the compiled LangGraph `_GRAPH`,
   - persists `AgentAction` + `AISummary`,
   - calls `send_whatsapp_reply(to, body, sid, token, from_number)`.
3. `send_whatsapp_reply` (`app/services/outbound.py`) sends via
   `twilio.rest.Client.messages.create`, prefixing both numbers with
   `whatsapp:` and returning `False` (with a `logger.warning`) when any
   of `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, or `TWILIO_FROM_NUMBER`
   is missing — failures are loud, never silent.
4. The webhook route always returns HTTP 200 in async mode (empty TwiML);
   this satisfies Twilio's contract regardless of pipeline outcome.
5. Sync mode stays untouched and continues to return a TwiML body inside
   the response, so test fixtures and the OpenAPI surface are stable.
6. Documented in `.env.example` that the three Twilio REST variables are
   required for _outbound_ delivery, not for the webhook itself.

**Alternatives considered**

| Option                                      | Reason rejected                                                                                                                                         |
| ------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Always synchronous (wait for the LLM)       | The bug: Twilio's 15 s timeout; cold LLM starts (15–45 s) are common.                                                                                   |
| Always reject slow webhooks / 503           | Twilio retries with the same payload, which causes duplicate `_GRAPH.invoke()` calls and duplicate outbound messages.                                   |
| Twilio status callbacks + server push       | Requires public, authenticated storage of partial replies — overkill for the sandbox + adds a new dependency on Redis or a DB queue.                    |
| Long-polling Twilio (`<Response>` deferral) | Twilio waits at most ~60 s; still brittle on cold LLM starts; requires Twilio-side `<Enqueue>` / TwiML verb gymnastics no cleaner than BackgroundTasks. |
| Polling worker reading the DB               | Adds a new infra component; doesn't help Twilio see a fast 200 OK.                                                                                      |

**Consequences**

- Positive: Twilio sees a 200 OK in <1 s on every request, regardless of
  pipeline latency. Citizen messages that took 40 s before now show up
  in the user's WhatsApp after the model returns, via REST outbound.
- Positive: Replay from ngrok no longer matters for normal delivery —
  it's a debug affordance, not the primary reply path.
- Positive: All test fixtures that assert sync behaviour (`fake_graph.calls`,
  TwiML body matching) are unchanged; the async test `test_webhook_async_mode_returns_empty_twiml_immediately`
  plus the new `test_async_mode_background_task_invokes_graph_and_outbound`
  and `test_async_mode_outbound_skipped_when_credentials_missing` lock in the
  ack + REST outbound guarantees.
- Positive: Outbound failures are explicitly logged (`"send_whatsapp_reply:
Twilio REST credentials not configured ... Skipping outbound message to"`)
  so a missing env var surfaces immediately instead of silently dropping
  the reply.
- Neutral: Adds the `app/services/outbound.py` module and three new
  `.env`-documented Twilio REST variables.

**Operational note**

The DEBUG.md symptom — _webhook returns 200 OK in ngrok but WhatsApp never
receives the message_ — is the operational fingerprint of **async mode
without Twilio REST credentials**. With this decision the fix is twofold:

1. Architectural (above) — the code path is correct.
2. Configuration — set `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, and
   `TWILIO_FROM_NUMBER` in `.env`. If any of them is missing, the outbound
   function logs a warning and returns `False`; the failure is loud,
   not silent.

## DECISION-0015 — Stage telemetry for webhook pipeline

**Date:** 2026-07-30

**Status:** Accepted

**Context**

DEBUG.md item #1 called out that every stage of the pipeline
(persist → classify → retrieve → context → prompt → LLM → TwiML) needed
its own wall-clock measurement so the actual bottleneck could be located
without guessing. At the time of capture only fragmentary timing existed:
the LangGraph nodes logged `⏱ <node>: …s` lines individually, but there
was no consolidated per-request breakdown.

**Decision**

Introduce `_log_stage_timings(stages: dict[str, float])` in
`app/api/webhook.py` that emits a single structured `INFO` line per
pipeline run summarising every stage and the total, in the form:

```
pipeline stage: graph=12.34s persist_output=0.03s outbound=0.05s total=12.42s
```

Both async and sync modes emit this line, with the only difference being
`outbound=0.00s` (render-only) in sync mode because the TwiML body is
returned inline.

**Consequences**

- Positive: Production observability — a single grep on
  `pipeline stage:` recovers every webhook's per-stage cost.
- Positive: New unit test `test_log_stage_timings_emits_total_line` locks
  in the log format so future edits cannot accidentally break log-scrapers.
- Neutral: No new dependencies.
- Neutral: ~6 lines of code in `app/api/webhook.py`.

## DECISION-0016

Title

Adopt Multi-stage AI Pipeline

Decision

Citizen reports shall pass through a sequence of deterministic AI stages:

Classification

Duplicate Detection

Priority Scoring

Geographic Extraction

Topic Tagging

Trend Aggregation

Reason

Separating these concerns improves explainability,
testing,
future model replacement,
and dashboard analytics.

---

## DECISION-0017 — Civic Classifier (Sprint 6 Feature 6.1)

**Date:** 2026-07-31

**Status:** Accepted

**Context**

Sprint 6 requires that every citizen submission be classified into a
canonical civic category (Roads, Healthcare, Water, Education, Markets,
Security, Environment, Housing, Sanitation, Transport) so the MP
dashboard can group, count, and prioritise feedback. The classifier
must be deterministic, fast, and runnable from both the webhook and
the REST pipeline APIs without any LLM calls.

**Decision**

Introduce `app/services/civic_classifier.py` with `CivicClassifier`:

- A 10-element category list (`CIVIC_CATEGORIES`) aligned to the
  FEATURES.md Sprint 6 deliverable.
- A per-trigger, per-category weight dictionary
  (`CATEGORY_KEYWORDS`) so multi-word phrases (`"no water"`) and
  domain-specific keywords (`"classroom"`, `"ambulance"`) score
  higher than incidental substrings.
- A scoring loop that maps each non-empty text to a
  `CivicClassification` dataclass with `category`, `confidence`,
  `matched_keywords`, and a per-category `scores` map.
- A safe default behavior — empty / whitespace-only / no-match texts
  yield `Sanitation` with low confidence, so callers always get a
  category.

**Alternatives considered**

| Option                                | Reason rejected                                                                |
| ------------------------------------- | ------------------------------------------------------------------------------ |
| Reuse the Sprint 5 `IntentClassifier` | It returns _intent_ (infrastructure_lookup, complaint, …), not civic category. |
| LLM-based classification              | Adds latency, cost, and a dependency on external availability.                 |
| Embeddings + nearest-neighbor         | Out of scope for the hackathon; vector DBs are a Sprint 7+ concern.            |

**Consequences**

- Positive: 10-category civic taxonomy is fixed, version-controlled, and deterministic.
- Positive: Pure-Python, no I/O, no LLM — runs in microseconds.
- Positive: `matched_keywords` is exposed for downstream explainability.
- Positive: 23 unit tests in `tests/test_civic_classifier.py` lock the behaviour.
- Neutral: Heuristic accuracy is bounded; future sprints may swap
  for an LLM-based classifier without breaking the public API.

---

## DECISION-0018 — Duplicate Detection (Sprint 6 Feature 6.2)

**Date:** 2026-07-31

**Status:** Accepted

**Context**

Multiple citizens often report the same streetlight / pothole / borehole
problem. The dashboard needs to count _unique_ incidents, not raw
submissions, and the agent should know when a new complaint is just a
re-statement of an existing one. We need a deterministic, DB-backed
duplicate detector that runs cheaply on every inbound webhook.

**Decision**

Introduce `app/services/duplicate_detector.py` with `DuplicateDetector`:

- Two complementary similarity signals: token-set Jaccard (vocabulary
  overlap) and trigram-set Jaccard (capture word-order variants).
- Combined similarity = `0.5 * token_jaccard + 0.5 * trigram_jaccard`.
- Default threshold `0.60`; submissions with score `>=` threshold are
  returned as matches.
- Optional `constituency` filter restricts the candidate pool to a
  citizen's home constituency (avoids matching Mombasa CBD reports
  to Likoni reports).
- `time_window_days` (default 30) bounds the candidate pool to
  recent submissions, so the detector scales to multi-year datasets.

**Alternatives considered**

| Option                           | Reason rejected                                       |
| -------------------------------- | ----------------------------------------------------- |
| Pure embedding similarity        | Requires a vector DB; out of scope for the hackathon. |
| Levenshtein distance on raw text | Punishes rephrasing too heavily; misses parity.       |
| Hash on canonicalised text       | Misses paraphrases.                                   |
| Only trigram Jaccard             | Loses high-signal keywords like "pothole".            |

**Consequences**

- Positive: Reproducible, explainable, runs in microseconds.
- Positive: Returns a `DuplicateDetectionResult` with a list of
  `DuplicateMatch` records so the dashboard can show "5 similar
  reports".
- Positive: 10 unit tests cover exact, paraphrased, cross-constituency,
  and time-window edge cases.
- Neutral: Threshold `0.60` may need tuning once production data is
  available; it's an instance-level parameter.

---

## DECISION-0019 — Priority Scoring (Sprint 6 Feature 6.3)

**Date:** 2026-07-31

**Status:** Accepted

**Context**

The dashboard needs a 4-level severity label (Critical / High / Medium
/ Low) for every submission. We cannot have an LLM in the hot path on
every webhook, so the scorer must be deterministic and fast, while
still capturing the difference between _"There is a fire at the
school and children are trapped"_ and _"Hello there"_.

**Decision**

Introduce `app/services/priority_scorer.py` with `PriorityScorer`,
which combines five signals:

| Signal               | Source                                             |
| -------------------- | -------------------------------------------------- |
| `urgency`            | keywords like fire, flood, ambulance, gun, cholera |
| `complaint`          | broken, leaking, uncollected, dirty, …             |
| `category_floor`     | Healthcare=8, Security=8, Water=6, Roads=5, …      |
| `duplicate_pressure` | `min(8, duplicate_count * 2)`                      |
| `emphasis`           | ALL-CAPS rate + word repetition rate               |

Final score is the sum of the five signals. The level is picked by
thresholds (`Critical >= 12.0`, `High >= 7.0`, `Medium >= 5.0`,
`Low >= 0.0`). The thresholds are constructor arguments so the
dashboard can tune them without touching service code.

**Alternatives considered**

| Option                 | Reason rejected                                             |
| ---------------------- | ----------------------------------------------------------- |
| Single keyword density | Loses cross-signal richness (e.g. healthcare + duplicates). |
| LLM severity score     | Adds latency + cost to every webhook.                       |
| Learnt classifier      | Requires training data; not available for the hackathon.    |

**Consequences**

- Positive: Same priority level for the same text — fully reproducible.
- Positive: `rationale` list explains _why_ a score is High or Critical.
- Positive: 12 unit tests including a strict ordering invariant
  (`Critical >= High >= Medium >= Low`).
- Neutral: Tuned thresholds may need data-driven recalibration.

---

## DECISION-0020 — Geographic Extraction (Sprint 6 Feature 6.4)

**Date:** 2026-07-31

**Status:** Accepted

**Context**

Every citizen submission must be associated with a county,
constituency, ward, and any landmark, road, or facility referenced in
the text. The citizen's profile only knows the constituency; the agent
needs to extract the rest from free text.

**Decision**

Introduce `app/services/geographic_extractor.py` with
`GeographicExtractor`, backed by a curated gazetteer for Mombasa:

- `COUNTIES` = `["Mombasa"]` (the gazetteer is Mombasa-only).
- `CONSTITUENCIES` = the 6 known constituencies.
- `WARDS` = 25 wards from the seed data and common civic references.
- `LANDMARKS` / `ROADS` / `FACILITIES` = highest-visibility citizen
  references, longest-first to defeat substring overlap.

The extractor returns a `GeographicExtraction` with five fields and a
`confidence` value. When the caller passes a `fallback_constituency`
(e.g. `User.constituency`), it is used only when no constituency is
found in the text itself.

**Alternatives considered**

| Option                     | Reason rejected                                           |
| -------------------------- | --------------------------------------------------------- |
| NER model from spaCy / HF  | Heavyweight dependency; overkill for a 25-ward gazetteer. |
| Geocoding API              | Cost, latency, network dependency.                        |
| Reverse geocoding from GPS | Citizens send raw text, not coordinates.                  |

**Consequences**

- Positive: Zero-network, deterministic, runs in microseconds.
- Positive: 14 unit tests covering all five fields plus fallback.
- Positive: Confidence score grows monotonically with the number of
  signals filled in.
- Neutral: Gazetteer is Mombasa-only; a future multi-county
  deployment will need to extend the lists.

---

## DECISION-0021 — Topic Tagging (Sprint 6 Feature 6.5)

**Date:** 2026-07-31

**Status:** Accepted

**Context**

A single submission can belong to multiple topics (e.g. _"school
children are crossing a dangerous road with potholes"_ → `Schools`,
`Children`, `Roads`, `Safety`). The dashboard uses tags to filter
for an MP's weekly brief, and the trend detector uses them to
aggregate "this is the 5th similar complaint this week".

**Decision**

Introduce `app/services/topic_tagger.py` with `TopicTagger`. 14 tags
are defined (`Roads`, `Flooding`, `Bridges`, `Water Supply`,
`Sanitation`, `Safety`, `Children`, `Schools`, `Hospitals`,
`Security`, `Markets`, `Environment`, `Housing`, `Transport`).

Each tag has a per-trigger weight dictionary. Multi-word triggers
are matched longest-first (so `"live wire"` wins over `"live"`).
Tags are returned sorted by score descending, a `min_score` threshold
drops noise, and a `max_tags` cap stops a noisy submission from
flooding the dashboard with every topic.

**Alternatives considered**

| Option                           | Reason rejected                     |
| -------------------------------- | ----------------------------------- |
| Single-label classification      | Loses the multi-topic reality.      |
| Hashtag extraction from WhatsApp | Citizens don't tag their messages.  |
| TF-IDF / LDA                     | Heavyweight; needs training corpus. |

**Consequences**

- Positive: Multi-label output matches how a human would tag incidents.
- Positive: 14 unit tests cover each tag plus threshold / cap behaviour.
- Positive: `TopicTaggingResult.top_tag` exposes the head label for UI.
- Neutral: Trigger weights are hand-tuned; future sprints may move
  to a learned model.

---

## DECISION-0022 — Trend Detection (Sprint 6 Feature 6.6)

**Date:** 2026-07-31

**Status:** Accepted

**Context**

MPs need to know whether new submissions are ramping up, holding
flat, or fading — and which constituencies are emerging as trouble
spots. A simple count is not enough; the dashboard needs
direction, hotspots, recurring failures, and a weekly pulse.

**Decision**

Introduce `app/services/trend_detector.py` with `TrendDetector`. The
report contains:

- `total_volume`, `previous_volume`, `direction` ("rising" /
  "falling" / "flat") — ratio >= 1.20 is rising, <= 0.80 is falling.
- `weekly_pulse` — bucket histogram of submissions across the window.
- `hotspots` — constituencies whose current-window volume increased
  by `>= 2` against the previous window.
- `recurring_failures` — groups of submissions in the window whose
  DuplicateDetector score is high (>= 0.55).
- `top_categories` — substring keyword counts (`road`, `water`,
  `hospital`, `school`, `garbage`, `pothole`, `flood`).

The detector's time-window and compare-window are constructor
parameters (`window_days`=7, `compare_window_days`=7 by default).

**Alternatives considered**

| Option                             | Reason rejected                                       |
| ---------------------------------- | ----------------------------------------------------- |
| Time-series forecasting (ARIMA, …) | Overkill for 7-day windows; needs more data.          |
| Daily-only rollups                 | Misses cross-constituency hotspot emergence.          |
| Pure SQL aggregation               | Cannot detect recurring failures (similarity needed). |

**Consequences**

- Positive: One engine, 8 unit tests, including rising / falling /
  flat / hotspot / recurring-failure cases.
- Positive: `to_dict()` is JSON-serialisable for the dashboard API.
- Positive: Reuses `DuplicateDetector` for the recurring-failure
  cluster grouping — no separate similarity implementation.
- Neutral: Window choice is a dashboard-level decision; 7 days is
  the default but can be overridden per call.

---

## DECISION-0023 — Install socksio to unblock 13 pre-existing test failures

**Date:** 2026-07-31

**Status:** Accepted

**Context**

The Sprint 7 housekeeping checklist (per `SESSION_HANDOFF.md`) called
out that `tests/test_providers.py`, `tests/test_rag.py`, and
`tests/test_llm.py` were failing with `ImportError: Using SOCKS proxy,
but the 'socksio' package is not installed.` The failures had been
flagged as environmental (out of scope for Sprint 5 / Sprint 6) but
they corrupted the green-bar status of the full suite.

Root cause: the local sandbox exports `ALL_PROXY=socks5h://localhost:1080`,
and httpx 0.28 auto-respects that environment variable. Any code path
that instantiates an `httpx.Client` against a SOCKS proxy triggers the
import even when the test uses `MockTransport` for the wire layer.

**Decision**

1. Install `socksio==1.0.0` (the runtime Python SOCKS proxy
   implementation that httpx ships its proxy support on). Recorded
   in `requirements.txt` per `AI_RULES.md` rule 5.
2. Patch `tests/test_providers.py::test_webhook_responds_200_when_every_provider_fails`
   to monkeypatch `webhook_module.send_whatsapp_reply` so the test
   never attempts to reach `api.twilio.com` (also unreachable from
   the sandbox). The test now asserts that the stubbed outbound
   receives the `"LLM unavailable"` reply, which is what the
   async-mode webhook actually delivers in production.

**Alternatives considered**

| Option                                     | Reason rejected                                                                   |
| ------------------------------------------ | --------------------------------------------------------------------------------- |
| Unset `ALL_PROXY` in the test runner       | Fragile; the env var exists in production shells too.                             |
| Pin `httpx<0.28` (no SOCKS support)        | Loses httpx 0.28 features; can't ship since 0.28 is the current required version. |
| `httpx.Client(trust_env=False)` everywhere | Surfaces in every test fixture; bigger diff, lower value.                         |

**Consequences**

- Positive: Full pytest suite now **197 passed, 0 failed** (was 184 passed, 13 failed).
- Positive: `socksio` is a tiny pure-Python runtime dependency (≈12 kB).
- Positive: The webhook test now correctly asserts the production
  behaviour (async mode → outbound REST) instead of the legacy
  sync-mode behaviour the test was written for.
- Neutral: One new top-level dependency, recorded in `requirements.txt`
  and `DECISION-0023` per `AI_RULES.md` rule 5.
