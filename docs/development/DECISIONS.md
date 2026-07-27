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
