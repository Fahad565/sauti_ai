"""NVIDIA hosted chat-completion provider.

Extracted from the Sprint 2 ``GemmaClient`` implementation in
``app/services/llm.py``. Implements the :class:`LLMProvider`
contract using ``httpx.Client`` against NVIDIA's
``integrate.api.nvidia.com`` endpoint.

Retry/timeout/backoff are the responsibility of the caller (the
provider factory wires :func:`retry_with_backoff` around each
provider).
"""

from __future__ import annotations

from typing import Iterable

import httpx

from app.config.settings import Settings
from app.services.llm.providers.base import LLMProvider
from app.services.llm.types import (
    ChatCompletion,
    ChatMessage,
    LLMConfigurationError,
    LLMResponseError,
    LLMRateLimitError,
    LLMTransportError,
    is_retryable_status,
)


class NvidiaProvider(LLMProvider):
    """Synchronous NVIDIA-hosted chat-completion provider."""

    name = "nvidia"

    def __init__(
        self,
        settings: Settings,
        *,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._settings = settings
        self._client = httpx.Client(
            base_url=settings.nvidia_base_url,
            timeout=settings.nvidia_timeout_seconds,
            transport=transport,
            trust_env=False,
        )

    # ---- public API ----------------------------------------------

    def generate(
        self,
        messages: Iterable[ChatMessage],
        *,
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        top_p: float | None = None,
        enable_thinking: bool | None = None,
    ) -> ChatCompletion:
        api_key = self._settings.nvidia_api_key
        # Ensure provider initialization cannot silently lose environment variables (Task 7)
        import os
        env_key = os.getenv("NVIDIA_API_KEY")
        if not api_key and env_key and "nvidia_api_key" not in self._settings.model_fields_set:
            api_key = env_key
            self._settings.nvidia_api_key = env_key

        if not api_key:
            raise LLMConfigurationError(
                "NVIDIA_API_KEY is not configured. Set it in the "
                "environment or a .env file to use the NVIDIA "
                "provider."
            )

        materialised: list[ChatMessage] = list(messages)
        if not materialised:
            raise LLMConfigurationError(
                "At least one message is required for chat completion."
            )

        payload: dict = {
            "model": model or self._settings.nvidia_model,
            "messages": [
                {"role": msg.role, "content": msg.content}
                for msg in materialised
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

        if response.status_code == 429:
            raise LLMRateLimitError(
                f"LLM responded with HTTP 429: {response.text[:500]}"
            )

        if response.status_code >= 400:
            status_code = response.status_code
            message = (
                f"LLM responded with HTTP {status_code}: "
                f"{response.text[:500]}"
            )
            if is_retryable_status(status_code):
                raise LLMTransportError(message)
            err = LLMResponseError(message)
            # Attach the status code so ``retry_with_backoff`` can
            # distinguish retryable from non-retryable response
            # errors.
            setattr(err, "status_code", status_code)
            raise err

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

        resolved_model = (
            data.get("model")
            if isinstance(data, dict)
            else (model or self._settings.nvidia_model)
        )

        return ChatCompletion(
            text=text,
            provider=self.name,
            model=str(resolved_model or ""),
            raw=data if isinstance(data, dict) else {},
        )

    def health_check(self) -> bool:
        return bool(self._settings.nvidia_api_key)

    def close(self) -> None:
        self._client.close()


def _extract_assistant_text(payload: dict) -> str | None:
    """Pull the assistant message text from an OpenAI-style response."""
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