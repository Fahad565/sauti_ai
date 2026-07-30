"""Agent state definition.

The :class:`AgentState` TypedDict describes the data that flows
through every node in the Sauti AI reasoning graph.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict
from sqlalchemy.orm import Session


class AgentState(TypedDict, total=False):
    """Typed graph state shared across all nodes.

    ``total=False`` keeps the schema permissive: nodes can add fields
    incrementally without forcing every step to populate every key.
    """

    # Raw inbound message captured by the ingestion layer.
    input_message: str

    # Target constituency if known or detected (e.g. "Likoni", "Mvita", etc.)
    constituency: Optional[str]

    # Intent classification results
    intent: str
    intent_confidence: float

    # Raw structured SQL retrieval results
    retrieved_data: Dict[str, Any]

    # Formatted Markdown prompt context built from retrieval results
    retrieved_context: str

    # Database session reference (optional)
    db: Optional[Session]

    # Ordered list of node names that have already executed.
    steps: List[str]

    # Final response produced by the graph.
    response: str

    # Raw assistant text returned by the LLM analyze/RAG node.
    analysis: str

    # Free-form metadata bag
    metadata: Dict[str, Any]