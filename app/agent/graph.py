"""Graph construction and compilation.

This module wires the nodes together into a :class:`langgraph.graph.StateGraph`
and exposes two factory functions:

- :func:`build_graph` — returns the uncompiled graph
- :func:`compile_graph` — returns the compiled, runnable graph.

Sprint 5 RAG pipeline:
    intake → classify → retrieval → context → analyze → respond → END
"""

from __future__ import annotations

from langgraph.graph import END, StateGraph

from app.agent.nodes import (
    analyze_node,
    classify_node,
    context_node,
    intake_node,
    respond_node,
    retrieval_node,
)
from app.agent.router import route_after_analyze
from app.agent.state import AgentState


def build_graph() -> StateGraph:
    """Construct the uncompiled agent graph."""
    graph = StateGraph(AgentState)

    # Register RAG pipeline nodes.
    graph.add_node("intake", intake_node)
    graph.add_node("classify", classify_node)
    graph.add_node("retrieval", retrieval_node)
    graph.add_node("context", context_node)
    graph.add_node("analyze", analyze_node)
    graph.add_node("respond", respond_node)

    # Entry chain.
    graph.set_entry_point("intake")
    graph.add_edge("intake", "classify")
    graph.add_edge("classify", "retrieval")
    graph.add_edge("retrieval", "context")
    graph.add_edge("context", "analyze")

    # Conditional routing after analysis.
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
    """Build and compile the agent graph."""
    return build_graph().compile()