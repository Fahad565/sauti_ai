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

| Option | Reason rejected |
| --- | --- |
| Keep a single provider (NVIDIA only) | Direct contradiction of the observed reliability problem. |
| Use `google-generativeai` (legacy SDK) | Superseded by `google-genai`; the latter is the supported package per Google's API docs. |
| Hard-code the provider in `app/agent/nodes.py` | Re-couples business logic to a vendor; rejected. |

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

