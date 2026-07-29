"""Twilio service module.

Provides pure-function helpers that adapt Twilio's webhook contract
to the rest of the Sauti AI service:

- :func:`build_initial_state` — converts a :class:`TwilioPayload`
  into the initial :class:`AgentState` consumed by the LangGraph
  graph.
- :func:`render_twiml_response` — wraps the graph's final reply in
  a Twilio-compatible TwiML ``<Response>`` document.

Keeping these functions separate from the FastAPI router means
they are easy to unit-test without spinning up a web server and
easy to swap if we migrate from Twilio to Meta's WhatsApp Cloud API
in a future feature.
"""

from __future__ import annotations

from xml.etree import ElementTree as ET

from twilio.twiml.messaging_response import MessagingResponse

from app.agent.state import AgentState
from app.schemas.webhook import TwilioPayload


def build_initial_state(payload: TwilioPayload) -> AgentState:
    """Build the initial :class:`AgentState` from a webhook payload.

    The text ``Body`` becomes ``input_message``. Sender and media
    metadata are stored in ``metadata`` so downstream nodes can
    read them later (without changing the ``AgentState`` schema).
    """
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
        "metadata": metadata,
    }


def render_twiml_response(message: str) -> str:
    """Render a Twilio TwiML ``<Response>`` carrying ``message``.

    Uses :class:`twilio.twiml.messaging_response.MessagingResponse`
    so the wire format matches what Twilio expects on the wire.
    The returned string is what the FastAPI handler returns with
    ``media_type="application/xml"``.
    """
    response = MessagingResponse()
    response.message(message or "")
    # ``str(response)`` produces a UTF-8 XML document that includes
    # the XML declaration. Tests assert both the structure and the
    # body text.
    return str(response)


def parse_twiml_message(twiml: str) -> str | None:
    """Extract the first ``<Message>`` body from a TwiML document.

    Used by the test suite to assert that the right reply was
    rendered. Returns ``None`` if the document does not carry a
    message body.
    """
    try:
        root = ET.fromstring(twiml)
    except ET.ParseError:
        return None
    for child in root:
        # Strip the namespace if Twilio included it.
        tag = child.tag.split("}", 1)[-1]
        if tag.lower() == "message":
            return child.text or ""
    return None