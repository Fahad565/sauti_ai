"""Placeholder node functions for the agent graph.

Each node accepts an :class:`AgentState` and returns a partial state
update. At the skeleton stage the nodes perform only the smallest
possible useful work:

- appending their own name to ``steps`` so we can verify execution
  order in tests,
- deriving a stub ``response`` from ``input_message``.

No LLM call, no tool call, no memory access happens here. Future
features will replace these bodies with real reasoning logic.
"""

from __future__ import annotations

from app.agent.state import AgentState


def intake_node(state: AgentState) -> dict[str, object]:
    """First node — accepts the inbound message.

    In future features this node will validate input, normalise text,
    detect language, and stage the message for analysis.
    """
    message = state.get("input_message", "")
    steps = list(state.get("steps", []))
    steps.append("intake")
    return {
        "steps": steps,
        "metadata": {"intake_length": str(len(message))},
    }


def analyze_node(state: AgentState) -> dict[str, object]:
    """Second node — placeholder analysis step.

    Future features will dispatch to LLM-based classification,
    clustering, and priority ranking here.
    """
    steps = list(state.get("steps", []))
    steps.append("analyze")
    return {"steps": steps}


def respond_node(state: AgentState) -> dict[str, object]:
    """Final node — produces a stub response.

    The skeleton response simply echoes the original message and
    records that ``respond`` ran. Future features will replace this
    with the MP-facing recommendation output.
    """
    message = state.get("input_message", "")
    steps = list(state.get("steps", []))
    steps.append("respond")
    return {
        "steps": steps,
        "response": f"ack: {message}",
    }