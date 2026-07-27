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

    # --- NVIDIA hosted Gemma 4 integration (Feature 1.2) -----------
    nvidia_api_key: str | None = None
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"
    nvidia_model: str = "google/gemma-4-31b-it"
    nvidia_timeout_seconds: float = 60.0
    nvidia_max_tokens: int = 16384
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
