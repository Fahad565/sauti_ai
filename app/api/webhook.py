"""Twilio WhatsApp webhook router.

Exposes :func:`POST /webhooks/twilio` which:

1. Accepts the form-encoded Twilio Sandbox payload.
2. Builds a :class:`TwilioPayload` from the form fields.
3. Converts it into an initial :class:`AgentState`.
4. Invokes the compiled LangGraph graph.
5. Returns a TwiML response containing the graph's reply.

The endpoint is **unauthenticated** per the Feature 1.3
acceptance criteria. Signature validation will be added in a
future feature (see :class:`DECISION-0004`).
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Form, status
from fastapi.responses import Response

from app.agent.graph import compile_graph
from app.agent.state import AgentState
from app.schemas.webhook import TwilioPayload
from app.services.persistence import record_agent_execution, record_inbound_message
from app.services.twilio import build_initial_state, render_twiml_response

logger = logging.getLogger(__name__)

router = APIRouter(tags=["twilio"])


@router.post(
    "/webhooks/twilio",
    status_code=status.HTTP_200_OK,
    summary="Twilio WhatsApp Sandbox webhook",
    response_class=Response,
)
async def twilio_webhook(
    MessageSid: str = Form(default=""),
    From: str = Form(default=""),
    To: str = Form(default=""),
    Body: str = Form(default=""),
    NumMedia: str = Form(default="0"),
    MediaUrl0: str = Form(default=""),
    MediaContentType0: str = Form(default=""),
    ProfileName: str = Form(default=""),
    WaId: str = Form(default=""),
) -> Response:
    """Handle an inbound Twilio WhatsApp message.

    The handler always returns HTTP 200 with a TwiML body so that
    Twilio considers the request successful even if the agent
    graph raised an unexpected error. The error is logged and the
    caller receives a friendly fallback message.
    """
    payload = TwilioPayload(
        MessageSid=MessageSid,
        From=From,
        To=To,
        Body=Body,
        NumMedia=NumMedia,
        MediaUrl0=MediaUrl0,
        MediaContentType0=MediaContentType0,
        ProfileName=ProfileName,
        WaId=WaId,
    )

    logger.info(
        "twilio webhook: sid=%s from=%s body_len=%d %s",
        payload.message_sid or "<missing>",
        payload.from_ or "<missing>",
        len(payload.body),
        payload.media_summary(),
    )

    # Persist citizen message and session details (Sprint 4)
    session_id: int | None = None
    submission_id: int | None = None
    try:
        user, session, submission = record_inbound_message(
            phone_number=payload.from_ or "unknown",
            raw_content=payload.body,
            user_name=payload.profile_name,
            media_url=payload.media_url0,
            media_type=payload.media_content_type0,
        )
        session_id = int(session.id)  # type: ignore[arg-type]
        submission_id = int(submission.id)  # type: ignore[arg-type]
    except Exception as exc:
        logger.warning("Failed to persist inbound message: %s", exc)

    initial_state: AgentState = build_initial_state(payload)
    graph = compile_graph()

    try:
        final_state = graph.invoke(initial_state)
        if session_id is not None and submission_id is not None:
            record_agent_execution(session_id, submission_id, final_state)
    except Exception:  # noqa: BLE001 - last-resort safety net

        logger.exception("agent graph raised during webhook handling")
        fallback = (
            "Sauti AI is temporarily unavailable. "
            "Please try again in a moment."
        )
        return Response(
            content=render_twiml_response(fallback),
            media_type="application/xml",
        )

    reply = str(final_state.get("response") or "").strip() or (
        "Thank you, your message has been received."
    )


    return Response(
        content=render_twiml_response(reply),
        media_type="application/xml",
    )