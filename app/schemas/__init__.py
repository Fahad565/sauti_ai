"""Schemas package: request and response payload models.

Re-exports the Pydantic models that describe the inbound
webhook payloads. Keeping the package surface narrow lets call
sites import everything they need from ``app.schemas`` without
hard-coding internal submodule paths.
"""

from app.schemas.webhook import TwilioPayload

__all__ = ["TwilioPayload"]
