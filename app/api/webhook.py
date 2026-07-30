"""Twilio WhatsApp webhook router.

Exposes :func:`POST /webhooks/twilio` which:

1. Accepts the form-encoded Twilio Sandbox payload.
2. Persists the inbound message to the database.
3. **Returns empty TwiML immediately** (≤ 1 s) to keep Twilio happy.
4. Runs the full LangGraph RAG pipeline in a FastAPI BackgroundTask.
5. Delivers the LLM reply via the Twilio REST API (outbound message).

Why async mode?
- Twilio has a hard ~15 s webhook timeout. Gemma can take 15–45 s.
- The synchronous design caused Twilio to time out and retry, resulting
  in duplicate deliveries and "waiting 46 seconds" warnings.
- The fix: acknowledge immediately, process in the background, reply
  via REST. See DECISION-0014.

Async mode is controlled by ``WEBHOOK_ASYNC_MODE=true`` (default).
Synchronous mode (``WEBHOOK_ASYNC_MODE=false``) is preserved for
testing and local demo scenarios where background delivery is not needed.

Stage telemetry
---------------
The background pipeline emits one ``INFO`` log per stage
(persist, graph, persist_output, outbound) so the bottleneck
called out in ``DEBUG.md`` ("time every stage") is visible from
the first request. Format::

    pipeline stage: graph=12.34s persist=0.03s outbound=0.18s total=12.55s
"""

from __future__ import annotations

import logging
import time
from typing import Dict

from fastapi import APIRouter, BackgroundTasks, Form, status
from fastapi.responses import Response

from app.agent.graph import compile_graph
from app.agent.state import AgentState
from app.config.settings import get_settings
from app.schemas.webhook import TwilioPayload
from app.services.outbound import send_whatsapp_reply
from app.services.persistence import record_agent_execution, record_inbound_message
from app.services.twilio import build_initial_state, render_twiml_response


def _log_stage_timings(stage_durations: Dict[str, float]) -> None:
    """Emit a single structured line with every stage's elapsed seconds.

    Keeps the format stable so log scrapers / dashboards can extract
    timings with a regular expression like::

        pipeline stage: graph=12.34s persist=0.03s outbound=0.18s total=...
    """
    total = sum(stage_durations.values())
    parts = " ".join(f"{name}={secs:.2f}s" for name, secs in stage_durations.items())
    logger.info("pipeline stage: %s total=%.2fs", parts, total)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["twilio"])

# Pre-compile the graph once at import time to avoid repeated compilation overhead.
_GRAPH = compile_graph()

# Acknowledgement sent immediately in async mode.
_ACK_MESSAGE = (
    "✅ Your message has been received by Sauti AI. "
    "We are looking into your query and will reply shortly…"
)


def _run_pipeline_and_reply(
    payload: TwilioPayload,
    session_id: int | None,
    submission_id: int | None,
    user_constituency: str | None,
) -> None:
    """Background task: run LangGraph pipeline and deliver reply via Twilio REST."""
    t_start = time.perf_counter()
    settings = get_settings()
    stages: Dict[str, float] = {}

    try:
        initial_state: AgentState = build_initial_state(payload, constituency=user_constituency)

        t_graph_start = time.perf_counter()
        final_state = _GRAPH.invoke(initial_state)
        stages["graph"] = time.perf_counter() - t_graph_start
        logger.info(
            "pipeline: graph completed in %.2fs (total so far: %.2fs)",
            stages["graph"],
            time.perf_counter() - t_start,
        )

        if session_id is not None and submission_id is not None:
            t_persist = time.perf_counter()
            record_agent_execution(session_id, submission_id, final_state)
            stages["persist_output"] = time.perf_counter() - t_persist
            logger.info(
                "pipeline: agent_execution persisted in %.2fs",
                stages["persist_output"],
            )

    except Exception:
        logger.exception("pipeline: graph raised during background processing")
        final_state = {}

    reply = str(final_state.get("response") or "").strip() or (
        "Thank you, your message has been received by the MP's office."
    )
    logger.info("pipeline: reply ready (chars=%d)", len(reply))

    # Deliver the reply via Twilio REST API.
    t_send = time.perf_counter()
    send_whatsapp_reply(
        to=payload.from_,
        body=reply,
        account_sid=settings.twilio_account_sid,
        auth_token=settings.twilio_auth_token,
        from_number=settings.twilio_from_number,
    )
    stages["outbound"] = time.perf_counter() - t_send
    logger.info(
        "pipeline: outbound delivery attempted in %.2fs | total pipeline: %.2fs",
        stages["outbound"],
        time.perf_counter() - t_start,
    )

    # One consolidated DEBUG.md-style breakdown line (issue from DEBUG.md
    # investigation #1: "time every stage").
    _log_stage_timings(stages)


@router.post(
    "/webhooks/twilio",
    status_code=status.HTTP_200_OK,
    summary="Twilio WhatsApp Sandbox webhook",
    response_class=Response,
)
async def twilio_webhook(
    background_tasks: BackgroundTasks,
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

    In async mode (default): acknowledges immediately with empty TwiML,
    then processes the LLM pipeline in the background.

    In sync mode: waits for the full pipeline before returning TwiML.
    """
    t_webhook_start = time.perf_counter()
    settings = get_settings()

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
        "twilio webhook: sid=%s from=%s body_len=%d %s async_mode=%s",
        payload.message_sid or "<missing>",
        payload.from_ or "<missing>",
        len(payload.body),
        payload.media_summary(),
        settings.webhook_async_mode,
    )

    # --- Persist inbound message (fast, always synchronous) ---
    session_id: int | None = None
    submission_id: int | None = None
    user_constituency: str | None = None

    t_persist = time.perf_counter()
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
        user_constituency = user.constituency
    except Exception as exc:
        logger.warning("Failed to persist inbound message: %s", exc)

    logger.info("webhook: persist=%.3fs", time.perf_counter() - t_persist)

    # --- Async mode: return immediately, process in background ---
    if settings.webhook_async_mode:
        background_tasks.add_task(
            _run_pipeline_and_reply,
            payload,
            session_id,
            submission_id,
            user_constituency,
        )
        logger.info(
            "webhook: async ack returned in %.3fs",
            time.perf_counter() - t_webhook_start,
        )
        # Return empty TwiML — Twilio is satisfied, WhatsApp gets nothing yet.
        # The reply arrives via outbound REST in the background task.
        return Response(
            content=render_twiml_response(""),
            media_type="application/xml",
        )

    # --- Sync mode (fallback for demos / testing) ---
    initial_state: AgentState = build_initial_state(payload, constituency=user_constituency)
    sync_stages: Dict[str, float] = {}

    try:
        t_graph = time.perf_counter()
        final_state = _GRAPH.invoke(initial_state)
        sync_stages["graph"] = time.perf_counter() - t_graph
        logger.info("webhook: sync graph=%.2fs", sync_stages["graph"])
        if session_id is not None and submission_id is not None:
            t_persist = time.perf_counter()
            record_agent_execution(session_id, submission_id, final_state)
            sync_stages["persist_output"] = time.perf_counter() - t_persist
    except Exception:
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
    sync_stages["twiml_render"] = 0.0  # trivial; present for parity with async path
    total_sync = time.perf_counter() - t_webhook_start
    logger.info("webhook: sync total=%.2fs", total_sync)
    _log_stage_timings(sync_stages)
    return Response(
        content=render_twiml_response(reply),
        media_type="application/xml",
    )