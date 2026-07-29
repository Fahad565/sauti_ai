"""Application entrypoint for the Sauti AI service.

Exposes a single ``FastAPI`` instance wired with the application
configuration. Adding a new top-level package should not require changes
to this file beyond the corresponding router import.
"""

from fastapi import FastAPI

from app.api import twilio_router
from app.config.settings import get_settings


def create_app() -> FastAPI:
    """Application factory.

    Returns a fully configured ``FastAPI`` instance. Using a factory keeps
    the entrypoint import-safe and makes the app easy to instantiate in
    tests without importing global module state.
    """
    import os
    from app.config.settings import get_settings

    settings = get_settings()

    # Print startup diagnostics (Task 4)
    print("=== STARTUP DIAGNOSTICS ===")
    print(f"CWD: {os.getcwd()}")
    print(f"OS ENV GOOGLE_API_KEY: {os.getenv('GOOGLE_API_KEY')}")
    print(f"SETTINGS GOOGLE_API_KEY: {settings.google_api_key}")

    # Startup diagnostic reporting (Task 8)
    provider_name = settings.llm_provider
    if provider_name == "google":
        model = settings.google_model
        key_loaded = "YES" if settings.google_api_key else "NO"
    elif provider_name == "nvidia":
        model = settings.nvidia_model
        key_loaded = "YES" if settings.nvidia_api_key else "NO"
    else:
        model = "unknown"
        key_loaded = "NO"

    print(f"Provider: {provider_name.capitalize()}")
    print(f"Model: {model}")
    print(f"API Key Loaded: {key_loaded}")
    print("===========================")

    app = FastAPI(
        title=settings.service_name,
        version=settings.version,
        description=(
            "AI-powered civic engagement platform for MPs. "
            "Bootstrap entrypoint for the Sauti AI service."
        ),
    )

    @app.get("/", tags=["health"])
    def root() -> dict[str, str]:
        """Liveness endpoint.

        Returns a static payload identifying the service and confirming
        that the process is running. Used by uptime checks, load
        balancers, and human smoke tests.
        """
        return {"service": settings.service_name, "status": "running"}

    # Register feature routers. Feature 1.3 ships the Twilio
    # ingestion webhook; future features can append more routers
    # here without touching the rest of the application factory.
    app.include_router(twilio_router)

    return app


app = create_app()
