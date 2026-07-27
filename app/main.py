"""Application entrypoint for the Sauti AI service.

Exposes a single ``FastAPI`` instance wired with the application
configuration. Adding a new top-level package should not require changes
to this file beyond the corresponding router import.
"""

from fastapi import FastAPI

from app.config.settings import get_settings


def create_app() -> FastAPI:
    """Application factory.

    Returns a fully configured ``FastAPI`` instance. Using a factory keeps
    the entrypoint import-safe and makes the app easy to instantiate in
    tests without importing global module state.
    """
    settings = get_settings()

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

    return app


app = create_app()
