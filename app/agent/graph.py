"""Graph construction and compilation.

This module wires the placeholder nodes together into a minimal
:class:`langgraph.graph.StateGraph` and exposes two factory functions:

- :func:`build_graph` — returns the uncompiled graph (useful for
  inspection, dry-runs, and visual export).
- :func:`compile_graph` — returns the compiled, runnable graph.

At the skeleton stage the graph is linear:

    intake → analyze → respond → END

with a conditional edge after ``analyze`` routed by
:func:`app.agent.router.route_after_analyze` (currently a no-op that
always selects ``respond``).
"""

from __future__ import annotations

from langgraph.graph import END, StateGraph

from app.agent.nodes import analyze_node, intake_node, respond_node
from app.agent.router import route_after_analyze
from app.agent.state import AgentState


def build_graph() -> StateGraph:
    """Construct the uncompiled agent graph.

    Returns the :class:`StateGraph` instance so callers can inspect
    nodes and edges. To run the graph, prefer
    :func:`compile_graph`.
    """
    graph = StateGraph(AgentState)

    # Register every placeholder node under a stable string name.
    graph.add_node("intake", intake_node)
    graph.add_node("analyze", analyze_node)
    graph.add_node("respond", respond_node)

    # Linear entry chain.
    graph.set_entry_point("intake")
    graph.add_edge("intake", "analyze")

    # Conditional routing after analysis. The router currently always
    # returns "respond"; the conditional edge is in place so future
    # features can branch without restructuring the graph.
    graph.add_conditional_edges(
        "analyze",
        route_after_analyze,
        {
            "respond": "respond",
        },
    )

    graph.add_edge("respond", END)

    return graph


def compile_graph():
    """Build and compile the agent graph.

    The returned object is a runnable LangGraph ``CompiledStateGraph``
    supporting ``invoke``, ``ainvoke``, ``stream``, and ``astream``.
    """
    return build_graph().compile()