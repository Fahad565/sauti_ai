"""Smoke test for application settings."""

from app.config.settings import Settings, get_settings


def test_settings_singleton() -> None:
    assert get_settings() is get_settings()


def test_settings_defaults() -> None:
    settings = Settings()
    assert settings.service_name == "Sauti AI"
    assert settings.version == "0.1.0"
    assert settings.environment == "development"
