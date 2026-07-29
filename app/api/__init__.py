"""API package: HTTP routes and routers for the Sauti AI service.

The :data:`twilio_router` is re-exported here so
``app.main.create_app`` can include it without reaching into
``app.api.webhook`` directly. Adding new routers should follow
the same pattern: declare them in their own module and re-export
the ``router`` instance from this package.
"""

from app.api.webhook import router as twilio_router

__all__ = ["twilio_router"]
