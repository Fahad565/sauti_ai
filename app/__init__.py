"""Sauti AI application package.

This package hosts the FastAPI application entrypoint and all internal
modules organized by responsibility:

- ``api``: HTTP route definitions and dependency injection wiring.
- ``config``: typed application settings loaded from environment variables.
- ``services``: business logic and external integrations.
- ``models``: persistence-layer data structures (database models).
- ``schemas``: request and response payload models exposed to clients.
- ``middleware``: cross-cutting HTTP concerns (logging, CORS, etc.).
- ``utils``: shared helpers used across the application.
"""

__version__ = "0.1.0"
