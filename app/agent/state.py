"""Agent state definition.

The :class:`AgentState` TypedDict describes the data that flows
through every node in the Sauti AI reasoning graph. It is intentionally
minimal at the skeleton stage — it captures only an inbound message,
a sequence of executed step names, and a final response. Future
features will extend this with analysis results, memory references,
tool outputs, and routing metadata.
"""

from __future__ import annotations

from typing import TypedDict


class AgentState(TypedDict, total=False):
    """Typed graph state shared across all nodes.

    ``total=False`` keeps the schema permissive while the skeleton
    evolves: nodes can add fields incrementally without forcing every
    step to populate every key.
    """

    # Raw inbound message captured by the ingestion layer.
    input_message: str

    # Ordered list of node names that have already executed.
    # Used for tracing, debugging, and skeleton verification.
    steps: list[str]

    # Final response produced by the graph. Empty string means
    # "not yet generated".
    response: str

    # Raw assistant text returned by the LLM analyze node. Empty
    # string means the LLM was not invoked or failed. Future nodes
    # may consume this field for downstream reasoning.
    analysis: str

    # Free-form metadata bag for future use (request id, source,
    # language, model id, analyze_error, etc.). Empty dict by
    # default.
    metadata: dict[str, str]