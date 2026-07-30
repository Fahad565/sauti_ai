"""Smoke test for the LangGraph agent graph.

Verifies:
1. The graph compiles without error.
2. Every node (intake, classify, retrieval, context, analyze, respond) executes in order.
3. State flows through the graph and accumulates correctly.
"""

from __future__ import annotations

import pytest

from app.agent import compile_graph
from app.agent import graph as graph_module
from app.agent.graph import build_graph
from app.agent.state import AgentState


@pytest.fixture
def stub_analyze_node(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace ``analyze_node`` with a no-op that does not call the LLM."""

    def _stub(state: AgentState) -> dict[str, object]:
        steps = list(state.get("steps", []))
        steps.append("analyze")
        return {"steps": steps}

    monkeypatch.setattr(graph_module, "analyze_node", _stub)


def test_graph_compiles() -> None:
    """``compile_graph`` returns a runnable compiled graph."""
    compiled = compile_graph()
    assert compiled is not None


def test_build_graph_is_state_graph() -> None:
    """``build_graph`` returns the underlying uncompiled graph."""
    graph = build_graph()
    assert "intake" in graph.nodes
    assert "classify" in graph.nodes
    assert "retrieval" in graph.nodes
    assert "context" in graph.nodes
    assert "analyze" in graph.nodes
    assert "respond" in graph.nodes


def test_graph_executes_linear_path(stub_analyze_node: None) -> None:
    """All RAG nodes run in order and update state."""
    compiled = compile_graph()
    initial: AgentState = {
        "input_message": "hello world",
        "steps": [],
        "response": "",
        "metadata": {},
    }

    final = compiled.invoke(initial)

    # Every node ran, in the expected order.
    assert final["steps"] == ["intake", "classify", "retrieval", "context", "analyze", "respond"]

    # Respond node produced the stub echo because the stub analyze node did not write anything into ``analysis``.
    assert final["response"] == "ack: hello world"

    # Intake node populated the metadata bag.
    assert final["metadata"]["intake_length"] == "11"

    # Original input is preserved end-to-end.
    assert final["input_message"] == "hello world"


def test_graph_handles_empty_message(stub_analyze_node: None) -> None:
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

    assert final["steps"] == ["intake", "classify", "retrieval", "context", "analyze", "respond"]
    assert final["response"] == "ack: "
    assert final["metadata"]["intake_length"] == "0"
