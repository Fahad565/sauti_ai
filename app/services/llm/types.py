"""Shared dataclasses and exceptions for the LLM service.

Kept in a dedicated module so both the legacy ``GemmaClient`` (Sprint
2) and the new ``LLMProvider`` implementations (Sprint 4) can
import the same types without circular dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


# --- Exceptions ------------------------------------------------------


class LLMError(RuntimeError):
    """Base class for all errors raised by the LLM service."""


class LLMConfigurationError(LLMError):
    """Raised when required configuration (e.g. API key) is missing."""


class LLMTransportError(LLMError):
    """Raised on transient network-level failures (timeouts,
    connection errors) — eligible for retry."""


class LLMResponseError(LLMError):
    """Raised when the upstream returns a non-success status or
    a payload that does not contain the expected content."""


class LLMRateLimitError(LLMError):
    """Raised when the upstream returns HTTP 429 — eligible for retry."""


# --- Public data types ----------------------------------------------


@dataclass(frozen=True)
class ChatMessage:
    """A single chat-completion message.

    ``role`` is one of ``"system"``, ``"user"``, ``"assistant"``.
    ``content`` is the raw text payload. Keeping this dataclass
    provider-agnostic lets future features swap in a different
    transport without rewriting call sites.
    """

    role: str
    content: str


@dataclass(frozen=True)
class ChatCompletion:
    """A normalised chat-completion reply.

    ``text`` carries the assistant's final text. ``provider`` is the
    name of the LLMProvider that produced the reply (e.g. ``"google"``,
    ``"nvidia"``). ``model`` is the model identifier resolved at
    request time. ``raw`` keeps the provider payload for callers
    that want to inspect token usage or latency fields.

    The ``provider`` and ``model`` fields default to ``"unknown"`` so
    the dataclass stays back-compatible with the Sprint 2 signature
    (which only required ``text`` and ``raw``).
    """

    text: str
    provider: str = "unknown"
    model: str = "unknown"
    raw: dict[str, Any] | None = None


# Set of exception types that the retry layer treats as transient.
# Validation errors (``LLMConfigurationError``) are deliberately
# excluded so the webhook does not busy-loop on a missing key.
RETRYABLE_EXCEPTIONS: tuple[type[BaseException], ...] = (
    LLMTransportError,
    LLMRateLimitError,
)


def is_retryable_status(status_code: int) -> bool:
    """Return ``True`` for HTTP status codes the retry layer should retry."""
    return status_code == 429 or status_code >= 500