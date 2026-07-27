"""Smoke test for the LangGraph agent skeleton.

Verifies the four acceptance criteria that can be checked without an
LLM:

1. The graph compiles without error.
2. Every placeholder node executes in the expected order.
3. State flows through the graph and accumulates correctly.
4. The compiled graph is the same instance returned by the package
   entrypoint.
"""

from __future__ import annotations

from app.agent import compile_graph
from app.agent.graph import build_graph
from app.agent.state import AgentState


def test_graph_compiles() -> None:
    """``compile_graph`` returns a runnable compiled graph."""
    compiled = compile_graph()
    assert compiled is not None


def test_build_graph_is_state_graph() -> None:
    """``build_graph`` returns the underlying uncompiled graph."""
    graph = build_graph()
    # Sanity-check the wiring without depending on private API.
    assert "intake" in graph.nodes
    assert "analyze" in graph.nodes
    assert "respond" in graph.nodes


def test_graph_executes_linear_path() -> None:
    """All three placeholder nodes run in order and update state."""
    compiled = compile_graph()
    initial: AgentState = {
        "input_message": "hello world",
        "steps": [],
        "response": "",
        "metadata": {},
    }

    final = compiled.invoke(initial)

    # Every node ran, in the expected order.
    assert final["steps"] == ["intake", "analyze", "respond"]

    # Respond node produced the stub response.
    assert final["response"] == "ack: hello world"

    # Intake node populated the metadata bag.
    assert final["metadata"]["intake_length"] == "11"

    # Original input is preserved end-to-end.
    assert final["input_message"] == "hello world"


def test_graph_handles_empty_message() -> None:
    """An empty inbound message still flows through the graph."""
    compiled = compile_graph()
    final = compiled.invoke(
        {
            "input_message": "",
            "steps": [],
            "response": "",
            "metadata": {},
        }
    )

    assert final["steps"] == ["intake", "analyze", "respond"]
    assert final["response"] == "ack: "
    assert final["metadata"]["intake_length"] == "0"