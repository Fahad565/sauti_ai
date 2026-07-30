"""Twilio service module.

Provides pure-function helpers that adapt Twilio's webhook contract
to the rest of the Sauti AI service:

- :func:`build_initial_state` — converts a :class:`TwilioPayload`
  into the initial :class:`AgentState` consumed by the LangGraph
  graph.
- :func:`render_twiml_response` — wraps the graph's final reply in
  a Twilio-compatible TwiML ``<Response>`` document.
"""

from __future__ import annotations

from typing import Optional
from xml.etree import ElementTree as ET

from twilio.twiml.messaging_response import MessagingResponse

from app.agent.state import AgentState
from app.schemas.webhook import TwilioPayload


def build_initial_state(
    payload: TwilioPayload,
    constituency: Optional[str] = None,
) -> AgentState:
    """Build the initial :class:`AgentState` from a webhook payload."""
    metadata: dict[str, str] = {
        "from": payload.from_,
        "message_sid": payload.message_sid,
        "num_media": payload.num_media or "0",
        "media_summary": payload.media_summary(),
        "wa_id": payload.wa_id,
    }

    if payload.has_media():
        metadata["media_url"] = payload.media_url0
        metadata["media_content_type"] = payload.media_content_type0

    return {
        "input_message": payload.body or "",
        "steps": [],
        "response": "",
        "analysis": "",
        "constituency": constituency,
        "metadata": metadata,
    }


def render_twiml_response(message: str) -> str:
    """Render a Twilio TwiML ``<Response>`` carrying ``message``."""
    response = MessagingResponse()
    response.message(message or "")
    return str(response)


def parse_twiml_message(twiml: str) -> str | None:
    """Extract the first ``<Message>`` body from a TwiML document."""
    try:
        root = ET.fromstring(twiml)
    except ET.ParseError:
        return None
    for child in root:
        tag = child.tag.split("}", 1)[-1]
        if tag.lower() == "message":
            return child.text or ""
    return None