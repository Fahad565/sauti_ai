"""Outbound WhatsApp messaging via Twilio REST API.

Used by the async webhook background task to deliver LLM replies after
the webhook has already returned empty TwiML to Twilio.
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def send_whatsapp_reply(
    to: str,
    body: str,
    account_sid: Optional[str],
    auth_token: Optional[str],
    from_number: Optional[str],
) -> bool:
    """Send a WhatsApp message via the Twilio REST API.

    Returns True if the message was dispatched successfully, False otherwise.
    All failures are logged but never raised — the background task must not
    crash the server process.
    """
    if not account_sid or not auth_token or not from_number:
        logger.warning(
            "send_whatsapp_reply: Twilio REST credentials not configured "
            "(TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN / TWILIO_FROM_NUMBER missing). "
            "Skipping outbound message to %s.",
            to,
        )
        return False

    try:
        from twilio.rest import Client  # type: ignore[import-untyped]

        client = Client(account_sid, auth_token)

        # Ensure both numbers are prefixed with "whatsapp:"
        from_wa = from_number if from_number.startswith("whatsapp:") else f"whatsapp:{from_number}"
        to_wa = to if to.startswith("whatsapp:") else f"whatsapp:{to}"

        message = client.messages.create(
            body=body,
            from_=from_wa,
            to=to_wa,
        )
        logger.info(
            "send_whatsapp_reply: delivered sid=%s to=%s status=%s",
            message.sid,
            to_wa,
            message.status,
        )
        return True
    except Exception as exc:
        logger.exception("send_whatsapp_reply: failed to send to %s: %s", to, exc)
        return False
