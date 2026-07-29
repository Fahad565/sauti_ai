"""Provider factory.

Single entry point that converts a :class:`Settings` instance into
a concrete :class:`LLMProvider`. Business logic should *always*
go through :func:`get_llm_provider` rather than instantiating a
provider class directly.

Supported providers:

- ``google`` (default) — :class:`GoogleProvider`.
- ``nvidia`` — :class:`NvidiaProvider`.

Any other value raises :class:`LLMConfigurationError` so a
misconfigured ``LLM_PROVIDER`` is surfaced at startup rather than
at request time.
"""

from __future__ import annotations

from functools import lru_cache

from app.config import settings as settings_module
from app.config.settings import Settings
from app.services.llm.providers.base import LLMProvider
from app.services.llm.providers.google_provider import GoogleProvider
from app.services.llm.providers.nvidia_provider import NvidiaProvider
from app.services.llm.types import LLMConfigurationError


SUPPORTED_PROVIDERS: tuple[str, ...] = ("google", "nvidia")
DEFAULT_PROVIDER: str = "google"


def build_provider(settings: Settings | None = None) -> LLMProvider:
    """Build a fresh :class:`LLMProvider` based on ``settings``.

    Use this when you want a new instance per call (e.g. in tests).
    In production code prefer :func:`get_llm_provider`.
    """
    resolved = settings or settings_module.get_settings()
    provider_name = (resolved.llm_provider or DEFAULT_PROVIDER).lower()

    if provider_name == "google":
        # Trace build_provider() and show the exact value passed into GoogleProvider (Task 5)
        print(f"build_provider: building GoogleProvider with google_api_key={resolved.google_api_key!r} and google_model={resolved.google_model!r}")
        return GoogleProvider(resolved)
    if provider_name == "nvidia":
        return NvidiaProvider(resolved)

    raise LLMConfigurationError(
        f"Unknown LLM_PROVIDER='{provider_name}'. "
        f"Supported providers: {', '.join(SUPPORTED_PROVIDERS)}."
    )


@lru_cache(maxsize=1)
def get_llm_provider() -> LLMProvider:
    """Return the cached :class:`LLMProvider` for the process.

    Tests can call :func:`reset_default_provider` to discard the
    cache after mutating the environment.
    """
    return build_provider()


def reset_default_provider() -> None:
    """Discard the cached default provider (test helper)."""
    get_llm_provider.cache_clear()


__all__ = [
    "build_provider",
    "get_llm_provider",
    "reset_default_provider",
    "SUPPORTED_PROVIDERS",
    "DEFAULT_PROVIDER",
]