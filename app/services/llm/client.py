"""``GemmaClient`` adapter preserved for Sprint 2 back-compat.

The Sprint 2 release exposed :class:`GemmaClient` directly. Sprint 4
introduces a provider abstraction; this module keeps the public
name working by wrapping any :class:`LLMProvider` in a thin
adapter that translates :class:`ChatMessage` to provider kwargs
and converts the returned :class:`ChatCompletion` into the same
call shape.

New code should depend on :class:`LLMProvider` directly via
:func:`app.services.llm.provider_factory.get_llm_provider`.
"""

from __future__ import annotations

from typing import Iterable

from app.config.settings import Settings
from app.services.llm.providers.base import LLMProvider
from app.services.llm.types import (
    ChatCompletion,
    ChatMessage,
    LLMError,
)

# Re-export so ``from app.services.llm import LLMError`` keeps working.
__all__ = [
    "GemmaClient",
    "ChatMessage",
    "ChatCompletion",
    "LLMError",
]


class GemmaClient:
    """Thin back-compat adapter around an :class:`LLMProvider`.

    Accepts the same constructor signature as the Sprint 2
    implementation (``settings=`` optional, ``transport=`` keyword)
    so existing tests keep passing. The ``transport`` argument is
    accepted for NVIDIA providers and ignored for non-NVIDIA
    providers — this preserves the
    ``GemmaClient(settings=..., transport=httpx.MockTransport(...))``
    pattern used by the test suite.
    """

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        provider: LLMProvider | None = None,
        transport=None,  # httpx transport; optional, ignored for non-NVIDIA
    ) -> None:
        if provider is None:
            from app.services.llm.provider_factory import build_provider

            provider = build_provider(settings)

            # If the active provider is NVIDIA, allow tests to inject
            # an httpx MockTransport by rebuilding the underlying
            # client.
            if transport is not None:
                from app.services.llm.providers.nvidia_provider import (
                    NvidiaProvider,
                )

                if isinstance(provider, NvidiaProvider):
                    provider._client.close()
                    import httpx as _httpx

                    provider._client = _httpx.Client(
                        base_url=provider._settings.nvidia_base_url,
                        timeout=provider._settings.nvidia_timeout_seconds,
                        transport=transport,
                        trust_env=False,
                    )

        self._provider = provider
        self._settings = settings

    # ---- public API ----------------------------------------------

    @property
    def provider(self) -> LLMProvider:
        return self._provider

    @property
    def provider_name(self) -> str:
        return self._provider.provider_name()

    def complete(
        self,
        messages: list[ChatMessage] | Iterable[ChatMessage],
        *,
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        top_p: float | None = None,
        enable_thinking: bool | None = None,
    ) -> ChatCompletion:
        """Back-compat wrapper around :meth:`LLMProvider.generate`.

        The ``enable_thinking`` kwarg is preserved for callers that
        still pass it; for non-NVIDIA providers it's silently
        accepted and ignored.
        """
        if enable_thinking is not None:
            try:
                return self._provider.generate(
                    messages,
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    top_p=top_p,
                    enable_thinking=enable_thinking,  # type: ignore[arg-type]
                )
            except TypeError:
                # Provider doesn't accept enable_thinking (e.g. Google).
                pass

        return self._provider.generate(
            messages,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
        )

    def close(self) -> None:
        self._provider.close()

    def __enter__(self) -> "GemmaClient":
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()