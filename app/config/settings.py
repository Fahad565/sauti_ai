"""Typed application settings.

Settings are loaded from environment variables (and optionally a
``.env`` file) using :mod:`pydantic_settings`. The :class:`Settings`
class is a process-wide singleton obtained through
:func:`get_settings` so all modules read consistent values.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration values.

    Each field is populated from an environment variable. Defaults are
    chosen so the service can boot in a development environment with no
    additional configuration. Production deployments are expected to
    override every value.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    service_name: str = "Sauti AI"
    version: str = "0.1.0"
    environment: str = "development"
    debug: bool = True

    # --- Multi-provider LLM backend (Sprint 4 / DECISION-0005) -----
    # ``LLM_PROVIDER`` selects the active backend. Supported values:
    # ``"google"`` (default) and ``"nvidia"``. The factory raises a
    # clear ``LLMConfigurationError`` if the value is unknown or the
    # selected provider's API key is missing.
    llm_provider: str = "google"
    llm_timeout: float = 30.0
    llm_max_retries: int = 2
    llm_retry_delay: float = 1.0

    # --- Google AI Studio (Gemini) ----------------------------------
    google_api_key: str | None = None
    google_model: str = "gemini-2.0-flash"

    # --- NVIDIA hosted Gemma 4 (kept as a fallback option) ----------
    nvidia_api_key: str | None = None
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"
    nvidia_model: str = "google/gemma-4-31b-it"
    # HTTP timeout for the chat-completion request. 120 s leaves
    # enough head-room for the free-tier NVIDIA endpoint on cold
    # starts while still bounded so a stuck request cannot block
    # the webhook indefinitely. (Sprint 3 timeout debug.)
    nvidia_timeout_seconds: float = 120.0
    # Cap the response at a value that comfortably fits a citizen-
    # feedback summary/classification (~300 tokens) plus a small
    # reasoning budget when ``nvidia_enable_thinking`` is True.
    # The previous default (16 384) caused the free-tier endpoint to
    # exceed the read timeout when thinking was enabled.
    nvidia_max_tokens: int = 512
    nvidia_temperature: float = 1.0
    nvidia_top_p: float = 0.95
    nvidia_enable_thinking: bool = True


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached :class:`Settings` instance.

    ``lru_cache`` ensures the environment file is parsed only once per
    process. Tests that need to override values can call
    :func:`get_settings.cache_clear` after mutating the environment.
    """
    return Settings()
