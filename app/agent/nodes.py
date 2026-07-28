"""Agent node functions.

Each node accepts an :class:`AgentState` and returns a partial state
update that LangGraph will merge into the running state.

Feature 1.2 (Sprint 2) swaps the previously-empty ``analyze_node``
for one that calls the real Gemma 4 LLM through
:class:`app.services.llm.GemmaClient`. Failure modes are caught and
recorded in state metadata so the rest of the graph keeps executing.
"""

from __future__ import annotations

import logging

from app.agent.state import AgentState
from app.services.llm import (
    ChatMessage,
    GemmaClient,
    LLMError,
    get_llm,
)

logger = logging.getLogger(__name__)


# System prompt for the analyze node.
#
# Gemma 4 (per the model card) enables "thinking" when the system
# prompt begins with the literal token ``<|think|>``. With thinking
# enabled the model emits an internal reasoning block before the
# final answer; we therefore pair this prompt with a small
# ``max_tokens`` budget (see ``Settings.nvidia_max_tokens``) so the
# reasoning fits inside the HTTP read timeout.
ANALYZE_SYSTEM_PROMPT = (
    "<|think|>"
    "You are Sauti AI, an assistant that analyzes citizen feedback "
    "submitted to a Member of Parliament. Summarise the message in "
    "two short sentences, identify any locations mentioned, and "
    "suggest a priority level (low / medium / high)."
)


def intake_node(state: AgentState) -> dict[str, object]:
    """First node - accepts the inbound message.

    Validates that the message is present, captures a few metadata
    fields, and records the step name in ``steps``.
    """
    message = state.get("input_message", "")
    steps = list(state.get("steps", []))
    steps.append("intake")

    metadata = dict(state.get("metadata", {}))
    metadata["intake_length"] = str(len(message))

    return {
        "steps": steps,
        "metadata": metadata,
    }


def analyze_node(
    state: AgentState,
    *,
    client: GemmaClient | None = None,
) -> dict[str, object]:
    """LLM-backed analysis node.

    Sends the inbound message to the configured LLM provider and
    stores the assistant reply in ``analysis``. Errors are caught
    and surfaced via ``state["metadata"]["analyze_error"]`` so the
    graph remains runnable in development environments without a
    configured provider API key while still reporting what went
    wrong.

    Tests can pass a ``client=`` to inject any object with a
    ``.complete(messages)`` method (duck-typed) without going
    through :func:`get_llm`.
    """
    message = state.get("input_message", "")
    steps = list(state.get("steps", []))
    steps.append("analyze")

    metadata = dict(state.get("metadata", {}))

    llm = client or get_llm()
    try:
        completion = llm.complete(
            [
                ChatMessage(role="system", content=ANALYZE_SYSTEM_PROMPT),
                ChatMessage(role="user", content=message or "(empty)"),
            ]
        )
    except LLMError as exc:
        # Graceful degradation: record the error and continue so the
        # rest of the graph can still run. Future features can branch
        # on this metadata to retry, escalate, or surface the issue.
        logger.warning("LLM call failed in analyze_node: %s", exc)
        metadata["analyze_error"] = str(exc)
        return {"steps": steps, "metadata": metadata}

    raw = completion.raw if isinstance(completion.raw, dict) else {}
    metadata["analyze_model"] = str(
        raw.get("model", completion.model or "unknown")
    )
    metadata["analyze_provider"] = completion.provider
    return {
        "steps": steps,
        "analysis": completion.text,
        "metadata": metadata,
    }


def respond_node(state: AgentState) -> dict[str, object]:
    """Final node - produces a response for the caller.

    Prefers the LLM analysis when available; otherwise falls back to
    the legacy ``ack:`` echo so the agent stays useful even before
    the LLM is configured.
    """
    analysis = state.get("analysis", "")
    analyze_error = state.get("metadata", {}).get("analyze_error")
    steps = list(state.get("steps", []))
    steps.append("respond")

    if analyze_error:
        response = (
            "LLM unavailable. The analyze node reported: "
            f"{analyze_error}"
        )
    elif analysis:
        response = analysis
    else:
        message = state.get("input_message", "")
        response = f"ack: {message}"

    return {
        "steps": steps,
        "response": response,
    }
