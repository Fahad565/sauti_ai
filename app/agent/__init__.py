"""Agent package: LangGraph orchestration skeleton for Sauti AI.

This package hosts the multi-step reasoning graph that future features
will populate with LLM calls, tools, memory, and routing. At the
skeleton stage it contains only placeholder nodes and a minimal graph
that compiles and executes end-to-end.

Module layout:

- ``state`` — :class:`AgentState`, the typed state that flows through
  every node.
- ``nodes`` — placeholder node functions that mutate the state.
- ``router`` — placeholder routing function used by the graph.
- ``graph`` — :func:`build_graph` / :func:`compile_graph` factories
  that wire nodes and edges together.
"""

from app.agent.graph import build_graph, compile_graph

__all__ = ["build_graph", "compile_graph"]