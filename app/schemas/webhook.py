"""Pydantic schemas for the Twilio webhook.

The Twilio WhatsApp Sandbox POSTs form-encoded payloads to the
configured webhook URL. The fields below are the minimum subset
that Feature 1.3 needs:

- ``MessageSid`` — unique message identifier (echoed back in logs).
- ``From`` — sender's WhatsApp number in ``whatsapp:+E164`` form.
- ``Body`` — the text body of the message (may be empty for media-only
  messages).
- ``NumMedia`` — number of media attachments (string per Twilio's
  form encoding).
- ``MediaUrl0``, ``MediaContentType0`` — optional first media
  attachment, surfaced so future features can fetch/process it.

The schema uses :class:`pydantic.BaseModel` so FastAPI can validate
the inbound ``Form`` data and so tests can construct payloads
without going through Twilio's request encoder.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class TwilioPayload(BaseModel):
    """Subset of a Twilio WhatsApp Sandbox webhook payload.

    All string fields default to empty strings so the model can
    still be instantiated from a partial payload in tests, but
    every inbound request must populate at least ``MessageSid``
    and ``From``.
    """

    message_sid: str = Field(default="", alias="MessageSid")
    from_: str = Field(default="", alias="From")
    to: str = Field(default="", alias="To")
    body: str = Field(default="", alias="Body")
    num_media: str = Field(default="0", alias="NumMedia")
    media_url0: str = Field(default="", alias="MediaUrl0")
    media_content_type0: str = Field(default="", alias="MediaContentType0")
    profile_name: str = Field(default="", alias="ProfileName")
    wa_id: str = Field(default="", alias="WaId")

    model_config = {"populate_by_name": True, "extra": "ignore"}

    def has_media(self) -> bool:
        """Return ``True`` if the payload carries at least one media item."""
        try:
            return int(self.num_media or "0") > 0
        except ValueError:
            return False

    def media_summary(self) -> str:
        """Return a short, log-friendly description of any media."""
        if not self.has_media():
            return "no-media"
        return f"media={self.media_content_type0 or 'unknown'}"