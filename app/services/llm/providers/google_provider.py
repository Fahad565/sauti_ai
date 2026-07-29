"""Google AI Studio (Gemini) chat-completion provider.

Thin wrapper around the official ``google-genai`` SDK that adapts
its client surface to the :class:`LLMProvider` contract used by
the rest of the service.

Authentication uses ``GOOGLE_API_KEY``; the model defaults to
``gemini-2.0-flash`` (configurable via ``GOOGLE_MODEL``).
"""

from __future__ import annotations

import logging
from typing import Iterable

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

logger = logging.getLogger(__name__)

try:  # pragma: no cover - exercised when the SDK is missing
    from google import genai as _genai
    from google.genai import errors as _genai_errors
except ImportError:  # pragma: no cover
    _genai = None  # type: ignore[assignment]
    _genai_errors = None  # type: ignore[assignment]


class GoogleProvider(LLMProvider):
    """Synchronous Google AI Studio (Gemini) chat-completion provider."""

    name = "google"

    def __init__(self, settings: Settings) -> None:
        import os
        self._settings = settings
        if _genai is None:
            raise LLMConfigurationError(
                "google-genai SDK is not installed. "
                "Install it with `pip install google-genai`."
            )
        api_key = settings.google_api_key
        # Ensure provider initialization cannot silently lose environment variables (Task 7)
        env_key = os.getenv("GOOGLE_API_KEY")
        if not api_key and env_key and "google_api_key" not in settings.model_fields_set:
            api_key = env_key
            settings.google_api_key = env_key
            logger.warning("GoogleProvider: API key was missing in settings but found in environment. Aligned settings.")

        if not api_key:
            raise LLMConfigurationError(
                "GOOGLE_API_KEY is not configured. Set it in the "
                "environment or a .env file to use the Google "
                "provider."
            )
        # ``Client`` reads the API key from the constructor argument.
        # ``client_args={"trust_env": False}`` prevents the SDK's
        # internal httpx client from auto-detecting a SOCKS proxy
        # from the environment (mirrors the same flag we pass to
        # :class:`NvidiaProvider`).
        try:
            from google.genai import types as _genai_types

            http_options = _genai_types.HttpOptions(
                client_args={"trust_env": False},
            )
            self._client = _genai.Client(
                api_key=api_key,
                http_options=http_options,
            )
        except (ImportError, TypeError):
            # Older SDK versions may not accept ``http_options``;
            # fall back to the simple constructor.
            self._client = _genai.Client(api_key=api_key)

    # ---- public API ----------------------------------------------

    def generate(
        self,
        messages: Iterable[ChatMessage],
        *,
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        top_p: float | None = None,
    ) -> ChatCompletion:
        materialised: list[ChatMessage] = list(messages)
        if not materialised:
            raise LLMConfigurationError(
                "At least one message is required for chat completion."
            )

        resolved_model = model or self._settings.google_model
        # The SDK expects a single ``contents`` payload. We merge the
        # system prompt into a single ``user`` turn when present, so
        # the call site can keep the same ``ChatMessage`` shape.
        contents = _messages_to_contents(materialised)
        config = _build_config(
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
        )

        try:
            response = self._client.models.generate_content(
                model=resolved_model,
                contents=contents,
                config=config,
            )
        except Exception as exc:  # noqa: BLE001 - convert SDK errors
            mapped = _map_sdk_exception(exc)
            logger.warning(
                "google provider: %s: %s", type(mapped).__name__, mapped
            )
            raise mapped from exc

        text = _extract_text(response)
        if text is None:
            raise LLMResponseError(
                "Google provider response did not contain text."
            )

        raw: dict = {
            "model": resolved_model,
        }
        # ``response.model_version`` is the closest stable identifier
        # on the SDK's response object.
        model_version = getattr(response, "model_version", None)
        if model_version:
            raw["model_version"] = str(model_version)

        return ChatCompletion(
            text=text,
            provider=self.name,
            model=str(model_version or resolved_model),
            raw=raw,
        )

    def health_check(self) -> bool:
        return bool(self._settings.google_api_key)


# --- Helpers ---------------------------------------------------------


def _messages_to_contents(messages: list[ChatMessage]) -> str:
    """Convert ``ChatMessage`` list into a single string ``contents``.

    The Google GenAI SDK accepts plain strings as ``contents`` for
    single-turn chat. For multi-turn we concatenate the messages
    with role prefixes so the model sees the full conversation.
    """
    if len(messages) == 1:
        return messages[0].content

    parts: list[str] = []
    for msg in messages:
        if msg.role == "system":
            parts.append(f"[system]\n{msg.content}")
        elif msg.role == "assistant":
            parts.append(f"[assistant]\n{msg.content}")
        else:
            parts.append(f"[user]\n{msg.content}")
    return "\n\n".join(parts)


def _build_config(
    *,
    max_tokens: int | None,
    temperature: float | None,
    top_p: float | None,
) -> dict:
    """Build the ``GenerateContentConfig`` payload as a plain dict.

    We pass a dict rather than importing ``GenerateContentConfig``
    so the module imports cleanly even when the SDK type surface
    shifts between releases.
    """
    config: dict = {}
    if max_tokens is not None:
        config["max_output_tokens"] = max_tokens
    if temperature is not None:
        config["temperature"] = temperature
    if top_p is not None:
        config["top_p"] = top_p
    return config


def _extract_text(response: object) -> str | None:
    """Pull the assistant text from a Google GenAI response object."""
    text = getattr(response, "text", None)
    if isinstance(text, str) and text:
        return text

    candidates = getattr(response, "candidates", None)
    if not candidates:
        return None
    first = candidates[0]
    content = getattr(first, "content", None)
    if content is None:
        return None
    parts = getattr(content, "parts", None) or []
    chunks: list[str] = []
    for part in parts:
        chunk = getattr(part, "text", None)
        if isinstance(chunk, str):
            chunks.append(chunk)
    joined = "".join(chunks).strip()
    return joined or None


def _map_sdk_exception(exc: Exception) -> Exception:
    """Map SDK-specific exceptions to our typed hierarchy.

    The ``google-genai`` SDK raises ``google.genai.errors.APIError``
    and ``google.genai.errors.ClientError`` subclasses. We inspect
    ``status_code`` where available to choose between transport /
    rate-limit / response errors.
    """
    status_code: int | None = getattr(exc, "code", None) or getattr(
        exc, "status_code", None
    )
    message = str(exc)

    if status_code == 429:
        return LLMRateLimitError(message)
    if status_code is not None and is_retryable_status(status_code):
        return LLMTransportError(message)
    if status_code is not None and status_code >= 400:
        return LLMResponseError(message)
    # SDK-reported network errors carry the ``google.genai.errors``
    # class hierarchy; ``ClientError`` is also non-retryable.
    name = type(exc).__name__
    if name.endswith("ConnectionError") or name.endswith("TimeoutError"):
        return LLMTransportError(message)
    return LLMResponseError(message)