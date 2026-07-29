"""LLM service package.

Sprint 4 reorganised the original ``app/services/llm.py`` module
into a package with a provider-agnostic backend:

- ``types`` — :class:`ChatMessage`, :class:`ChatCompletion`, and
  the typed :class:`LLMError` hierarchy.
- ``retry`` — exponential-backoff helper used by providers.
- ``providers.base`` — abstract :class:`LLMProvider` interface.
- ``providers.google_provider`` — Google AI Studio (Gemini).
- ``providers.nvidia_provider`` — NVIDIA hosted (Gemma 4).
- ``provider_factory`` — :func:`build_provider` /
  :func:`get_llm_provider`.
- ``client`` — :class:`GemmaClient`, preserved as a thin
  back-compat wrapper around any :class:`LLMProvider`.

The package's public surface keeps every Sprint 2 symbol
(:class:`ChatMessage`, :class:`ChatCompletion`, :class:`LLMError`,
:class:`GemmaClient`, :func:`get_llm`, :func:`reset_default_llm`)
available so existing call sites — ``app/agent/nodes.py``,
``tests/test_llm.py``, ``tests/test_twilio_webhook.py`` — keep
working without modification.
"""

from __future__ import annotations

from functools import lru_cache

from app.services.llm.client import GemmaClient
from app.services.llm.provider_factory import (
    build_provider,
    get_llm_provider,
    reset_default_provider,
)
from app.services.llm.types import (
    ChatCompletion,
    ChatMessage,
    LLMConfigurationError,
    LLMError,
    LLMRateLimitError,
    LLMResponseError,
    LLMTransportError,
    RETRYABLE_EXCEPTIONS,
    is_retryable_status,
)

__all__ = [
    # Public dataclasses.
    "ChatMessage",
    "ChatCompletion",
    # Exception hierarchy.
    "LLMError",
    "LLMConfigurationError",
    "LLMTransportError",
    "LLMResponseError",
    "LLMRateLimitError",
    # Back-compat client.
    "GemmaClient",
    # Provider factory helpers.
    "build_provider",
    "get_llm_provider",
    "reset_default_provider",
    # Retry helpers.
    "RETRYABLE_EXCEPTIONS",
    "is_retryable_status",
]


# --- Legacy singleton helpers ---------------------------------------


_default_client: GemmaClient | None = None


def get_llm() -> GemmaClient:
    """Return the cached :class:`GemmaClient` (back-compat).

    The default client is constructed from the active
    :class:`LLMProvider`. Tests can call
    :func:`reset_default_llm` to discard the cached instance.
    """
    global _default_client
    if _default_client is None:
        _default_client = GemmaClient(provider=get_llm_provider())
    return _default_client


def reset_default_llm() -> None:
    """Close and discard the cached default client (test helper)."""
    global _default_client
    if _default_client is not None:
        _default_client.close()
        _default_client = None