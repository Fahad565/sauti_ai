"""Placeholder routing function for the agent graph.

A router in LangGraph inspects the current state and returns the name
of the next node to execute (or :data:`langgraph.graph.END`).

At the skeleton stage this is a fixed function: it always returns
``"respond"`` because the graph has a single linear path. Future
features will use this hook for conditional branching (e.g.
"classify → escalate vs. archive").
"""

from __future__ import annotations

from typing import Literal

from app.agent.state import AgentState

# Using a Literal keeps the typed contract explicit. If we add new
# destinations later we extend this union.
RouteTarget = Literal["respond"]


def route_after_analyze(state: AgentState) -> RouteTarget:
    """Decide the next node after :func:`analyze_node`.

    The skeleton always advances to ``respond``. The function accepts
    the full state for symmetry with future implementations that will
    inspect classification results or urgency scores.
    """
    return "respond"