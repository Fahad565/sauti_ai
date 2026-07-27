"""LLM service module.

Provides a thin, provider-isolated wrapper around NVIDIA's hosted
Gemma 4 chat-completions endpoint. The wrapper exposes a single
class, :class:`GemmaClient`, and a small set of typed exceptions so
the rest of the application can interact with the model without
knowing the underlying HTTP details.

Design goals (per ``DECISION-0003``):

- Keep all model access behind one service module.
- Accept configuration via :class:`app.config.settings.Settings` so
  tests can swap keys, endpoints, and parameters.
- Surface clear, typed errors rather than leaking ``httpx`` /
  provider-specific exceptions into the agent layer.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from app.config.settings import Settings, get_settings


# --- Exceptions ------------------------------------------------------


class LLMError(RuntimeError):
    """Base class for all errors raised by the LLM service."""


class LLMConfigurationError(LLMError):
    """Raised when required configuration (e.g. API key) is missing."""


class LLMTransportError(LLMError):
    """Raised on network-level failures (timeouts, connection errors)."""


class LLMResponseError(LLMError):
    """Raised when the upstream returns a non-success status or
    a payload that does not contain the expected content."""


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
    """The minimal projection of a chat-completion response that the
    rest of the application needs: the assistant's text reply and
    the raw provider payload for advanced consumers.
    """

    text: str
    raw: dict[str, Any]


# --- Client ---------------------------------------------------------


class GemmaClient:
    """Synchronous client for NVIDIA's hosted Gemma 4 endpoint.

    The client owns an :class:`httpx.Client` and reads its
    configuration from a :class:`Settings` instance on construction
    so it can be safely instantiated in tests with overridden
    environment variables.
    """

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._client = httpx.Client(
            base_url=self._settings.nvidia_base_url,
            timeout=self._settings.nvidia_timeout_seconds,
            transport=transport,
            trust_env=False,
        )

    # ---- public API ----------------------------------------------

    def complete(
        self,
        messages: list[ChatMessage],
        *,
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        top_p: float | None = None,
        enable_thinking: bool | None = None,
    ) -> ChatCompletion:
        """Send a chat-completion request and return the response.

        All keyword arguments fall back to the values declared in
        :class:`Settings`. ``messages`` must contain at least one
        element. The method validates configuration up front so
        failures are reported as :class:`LLMConfigurationError`.
        """
        if not messages:
            raise LLMConfigurationError(
                "At least one message is required for chat completion."
            )

        api_key = self._settings.nvidia_api_key
        if not api_key:
            raise LLMConfigurationError(
                "NVIDIA_API_KEY is not configured. "
                "Set it in the environment or a .env file to use the "
                "real LLM. The agent skeleton will not function "
                "without it."
            )

        payload: dict[str, Any] = {
            "model": model or self._settings.nvidia_model,
            "messages": [
                {"role": msg.role, "content": msg.content}
                for msg in messages
            ],
            "max_tokens": max_tokens
            if max_tokens is not None
            else self._settings.nvidia_max_tokens,
            "temperature": temperature
            if temperature is not None
            else self._settings.nvidia_temperature,
            "top_p": top_p if top_p is not None else self._settings.nvidia_top_p,
            "stream": False,
            "chat_template_kwargs": {
                "enable_thinking": (
                    enable_thinking
                    if enable_thinking is not None
                    else self._settings.nvidia_enable_thinking
                ),
            },
        }

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        try:
            response = self._client.post(
                "/chat/completions",
                headers=headers,
                json=payload,
            )
        except httpx.HTTPError as exc:
            raise LLMTransportError(
                f"HTTP transport error while contacting the LLM: {exc}"
            ) from exc

        if response.status_code >= 400:
            raise LLMResponseError(
                f"LLM responded with HTTP {response.status_code}: "
                f"{response.text[:500]}"
            )

        try:
            data = response.json()
        except ValueError as exc:
            raise LLMResponseError(
                "LLM response was not valid JSON."
            ) from exc

        text = _extract_assistant_text(data)
        if text is None:
            raise LLMResponseError(
                "LLM response did not contain an assistant message."
            )

        return ChatCompletion(text=text, raw=data)

    def close(self) -> None:
        """Release the underlying HTTP client."""
        self._client.close()

    def __enter__(self) -> "GemmaClient":
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()


# --- Helpers ---------------------------------------------------------


def _extract_assistant_text(payload: dict[str, Any]) -> str | None:
    """Pull the assistant message text from an OpenAI-style response.

    The NVIDIA hosted endpoint follows the OpenAI chat-completion
    schema, so the assistant reply lives at
    ``payload["choices"][0]["message"]["content"]``. This helper is
    intentionally narrow: it accepts dicts only and returns
    ``None`` for any unexpected shape so the caller can raise a
    typed :class:`LLMResponseError`.
    """
    try:
        choices = payload["choices"]
    except (KeyError, TypeError):
        return None
    if not choices:
        return None
    first = choices[0]
    if not isinstance(first, dict):
        return None
    message = first.get("message")
    if not isinstance(message, dict):
        return None
    content = message.get("content")
    return content if isinstance(content, str) else None


# --- Module-level singleton -----------------------------------------


_default_client: GemmaClient | None = None


def get_llm() -> GemmaClient:
    """Return a process-wide :class:`GemmaClient` instance.

    The singleton avoids recreating the underlying HTTP connection
    pool on every node invocation. Tests should call
    :func:`reset_default_llm` to discard the cached instance after
    mutating the environment.
    """
    global _default_client
    if _default_client is None:
        _default_client = GemmaClient()
    return _default_client


def reset_default_llm() -> None:
    """Close and discard the cached default client."""
    global _default_client
    if _default_client is not None:
        _default_client.close()
        _default_client = None