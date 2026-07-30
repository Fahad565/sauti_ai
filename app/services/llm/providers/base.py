"""Abstract base class for all LLM providers.

Defines the contract every Sprint 4 provider must satisfy. Business
logic (the LangGraph agent, the Twilio webhook) depends only on
this interface, so adding a new provider is a matter of writing a
new subclass and registering it in ``provider_factory``.
"""

from __future__ import annotations

import abc
from typing import Iterable

from app.services.llm.types import ChatCompletion, ChatMessage


class LLMProvider(abc.ABC):
    """Abstract base class for chat-completion providers.

    Concrete implementations must translate vendor-specific
    requests/responses into the normalised :class:`ChatCompletion`
    shape defined in ``types.py``.
    """

    #: Human-readable provider name used in logs and metadata.
    name: str = "unknown"

    @abc.abstractmethod
    def generate(
        self,
        messages: Iterable[ChatMessage],
        *,
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        top_p: float | None = None,
    ) -> ChatCompletion:
        """Run a chat-completion request and return a normalised reply.

        Implementations must:

        - raise :class:`LLMConfigurationError` if configuration is
          missing (e.g. an unset API key),
        - raise :class:`LLMTransportError` on network/timeouts,
        - raise :class:`LLMRateLimitError` on HTTP 429,
        - raise :class:`LLMResponseError` on malformed payloads or
          non-retryable HTTP errors,
        - return a :class:`ChatCompletion` on success.
        """

    def health_check(self) -> bool:
        """Return ``True`` when the provider is reachable.

        The default implementation returns ``True`` if the provider
        has not yet raised during construction. Subclasses may
        override with a lightweight probe (e.g. a 1-token request).
        """

        return True

    def provider_name(self) -> str:
        """Return the stable identifier used in logs and metadata."""
        return self.name

    def close(self) -> None:
        """Release any underlying resources (HTTP clients, SDKs).

        Default implementation is a no-op; subclasses with native
        clients should override.
        """

    def __enter__(self) -> "LLMProvider":
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()