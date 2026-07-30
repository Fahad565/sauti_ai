"""Tests for the Twilio WhatsApp ingestion webhook (Feature 1.3).

The test suite covers:

1. Pure helpers in ``app.services.twilio``:
   - :func:`build_initial_state` shape + metadata propagation.
   - :func:`render_twiml_response` body text + XML wrapper.
   - :func:`parse_twiml_message` round-trip.
2. The :class:`TwilioPayload` schema (validation + media helpers).
3. The FastAPI route ``POST /webhooks/twilio``:
   - 200 status on a happy-path POST.
   - Correct TwiML body returned for the agent's reply.
   - Empty / missing Body still produces a valid TwiML reply.
   - The agent graph is invoked exactly once per request.
   - A graph exception is caught and produces a graceful fallback
     (HTTP 200 + user-friendly TwiML).
   - The route is reachable at the documented path
     (``/webhooks/twilio``).
   - The endpoint is **unauthenticated** (no signature required).

The tests stub the LangGraph graph so no network calls happen.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.agent import graph as graph_module
# Import the webhook module directly BEFORE pulling in the
# ``app.api`` package. ``app.api.__init__`` re-exports
# ``webhook_module.router`` and the order matters for monkeypatch.
from app.api import webhook as webhook_module
from app.main import create_app
from app.schemas import TwilioPayload
from app.services import twilio as twilio_service
from app.services.twilio import (
    build_initial_state,
    parse_twiml_message,
    render_twiml_response,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_graph(monkeypatch: pytest.MonkeyPatch):
    """Replace ``compile_graph`` with a configurable fake.

    The fake records every ``invoke`` call so the tests can assert
    on the ``input_message`` and other state without needing a
    real LangGraph runtime.
    """

    class _FakeGraph:
        def __init__(self) -> None:
            self.calls: list[dict[str, Any]] = []
            self.next_response: str = "ack: hello"
            self.raise_on_invoke: BaseException | None = None

        def invoke(self, state: dict[str, Any]) -> dict[str, Any]:
            self.calls.append(dict(state))
            if self.raise_on_invoke is not None:
                raise self.raise_on_invoke
            return {
                **state,
                "steps": ["intake", "analyze", "respond"],
                "response": self.next_response,
            }

    fake = _FakeGraph()
    # Patch where it is *used* (webhook module), not where it is
    # defined (graph module). `from app.agent.graph import
    # compile_graph` creates a local binding inside ``webhook``.
    monkeypatch.setattr(webhook_module, "compile_graph", lambda: fake)
    return fake


@pytest.fixture
def client(fake_graph) -> TestClient:  # noqa: ARG001 - pytest fixture
    """Build a FastAPI test client backed by the fake graph."""
    app = create_app()
    return TestClient(app)


def _form_payload(**overrides: Any) -> dict[str, str]:
    """Build a Twilio-style form-encoded payload."""
    payload = {
        "MessageSid": "SMxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        "From": "whatsapp:+254712345678",
        "To": "whatsapp:+14155238886",
        "Body": "the road in my ward has potholes",
        "NumMedia": "0",
        "MediaUrl0": "",
        "MediaContentType0": "",
        "ProfileName": "Citizen",
        "WaId": "254712345678",
    }
    payload.update({k: str(v) for k, v in overrides.items()})
    return payload


# ---------------------------------------------------------------------------
# TwilioPayload schema tests
# ---------------------------------------------------------------------------


def test_payload_accepts_alias_form_fields() -> None:
    payload = TwilioPayload(**_form_payload())
    assert payload.message_sid.startswith("SM")
    assert payload.from_ == "whatsapp:+254712345678"
    assert payload.body == "the road in my ward has potholes"


def test_payload_ignores_unknown_fields() -> None:
    raw = _form_payload()
    raw["UnknownTwilioField"] = "ignore-me"
    payload = TwilioPayload(**raw)
    assert payload.body  # still parsed


def test_payload_has_media_helper() -> None:
    no_media = TwilioPayload(**_form_payload())
    with_media = TwilioPayload(**_form_payload(NumMedia="1", MediaUrl0="https://example.com/a.jpg", MediaContentType0="image/jpeg"))
    assert not no_media.has_media()
    assert with_media.has_media()
    assert with_media.media_summary().startswith("media=")


def test_payload_media_summary_no_media() -> None:
    payload = TwilioPayload(**_form_payload())
    assert payload.media_summary() == "no-media"


# ---------------------------------------------------------------------------
# Twilio service helper tests
# ---------------------------------------------------------------------------


def test_build_initial_state_basic() -> None:
    payload = TwilioPayload(**_form_payload(Body="Hello MP"))
    state = build_initial_state(payload)

    assert state["input_message"] == "Hello MP"
    assert state["steps"] == []
    assert state["response"] == ""
    assert state["analysis"] == ""
    assert state["metadata"]["from"] == "whatsapp:+254712345678"
    assert state["metadata"]["message_sid"].startswith("SM")
    assert state["metadata"]["num_media"] == "0"
    assert state["metadata"]["wa_id"] == "254712345678"


def test_build_initial_state_with_media() -> None:
    payload = TwilioPayload(
        **_form_payload(
            NumMedia="1",
            MediaUrl0="https://example.com/voice.ogg",
            MediaContentType0="audio/ogg",
        )
    )
    state = build_initial_state(payload)

    assert state["metadata"]["num_media"] == "1"
    assert state["metadata"]["media_url"] == "https://example.com/voice.ogg"
    assert state["metadata"]["media_content_type"] == "audio/ogg"


def test_build_initial_state_empty_body() -> None:
    payload = TwilioPayload(**_form_payload(Body=""))
    state = build_initial_state(payload)
    assert state["input_message"] == ""


def test_render_twiml_response_wraps_message() -> None:
    twiml = render_twiml_response("thanks for the update")
    assert twiml.startswith("<?xml")
    assert "<Response>" in twiml
    assert "thanks for the update" in twiml
    assert parse_twiml_message(twiml) == "thanks for the update"


def test_render_twiml_response_empty_message() -> None:
    twiml = render_twiml_response("")
    assert "<Response>" in twiml
    assert parse_twiml_message(twiml) == ""


def test_parse_twiml_message_returns_none_on_garbage() -> None:
    assert parse_twiml_message("not xml") is None


def test_twilio_service_module_exports() -> None:
    for name in ("build_initial_state", "render_twiml_response", "parse_twiml_message"):
        assert hasattr(twilio_service, name), name


# ---------------------------------------------------------------------------
# FastAPI route tests
# ---------------------------------------------------------------------------


def test_route_is_registered(client: TestClient) -> None:
    """The webhook path appears in the generated OpenAPI."""
    schema = client.app.openapi()
    assert "/webhooks/twilio" in schema["paths"]


def test_webhook_returns_200_with_twiml(client: TestClient, fake_graph) -> None:
    response = client.post("/webhooks/twilio", data=_form_payload(Body="the road is broken"))

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/xml")
    assert "<Response>" in response.text
    assert parse_twiml_message(response.text) == fake_graph.next_response


def test_webhook_passes_body_to_graph(client: TestClient, fake_graph) -> None:
    client.post("/webhooks/twilio", data=_form_payload(Body="potholes on Main Street"))

    assert len(fake_graph.calls) == 1
    assert fake_graph.calls[0]["input_message"] == "potholes on Main Street"


def test_webhook_populates_metadata(client: TestClient, fake_graph) -> None:
    client.post(
        "/webhooks/twilio",
        data=_form_payload(
            From="whatsapp:+254700000000",
            MessageSid="SMabcdef123456",
            NumMedia="0",
            WaId="254700000000",
        ),
    )

    metadata = fake_graph.calls[0]["metadata"]
    assert metadata["from"] == "whatsapp:+254700000000"
    assert metadata["message_sid"] == "SMabcdef123456"
    assert metadata["num_media"] == "0"
    assert metadata["wa_id"] == "254700000000"


def test_webhook_handles_empty_body(client: TestClient, fake_graph) -> None:
    response = client.post("/webhooks/twilio", data=_form_payload(Body=""))
    assert response.status_code == 200
    assert parse_twiml_message(response.text) == fake_graph.next_response
    assert fake_graph.calls[0]["input_message"] == ""


def test_webhook_handles_graph_exception(client: TestClient, fake_graph) -> None:
    fake_graph.raise_on_invoke = RuntimeError("kaboom")

    response = client.post("/webhooks/twilio", data=_form_payload(Body="hi"))

    assert response.status_code == 200
    assert "application/xml" in response.headers["content-type"]
    body = parse_twiml_message(response.text) or ""
    assert "Sauti AI" in body or "temporarily unavailable" in body


def test_webhook_is_unauthenticated(client: TestClient, fake_graph) -> None:
    """No signature header is required or checked."""
    response = client.post("/webhooks/twilio", data=_form_payload(Body="hi"))
    assert response.status_code == 200


def test_webhook_accepts_missing_optional_fields(client: TestClient, fake_graph) -> None:
    """A minimum Twilio payload (only MessageSid + From) still works."""
    response = client.post(
        "/webhooks/twilio",
        data={"MessageSid": "SMmin", "From": "whatsapp:+15550000000"},
    )

    assert response.status_code == 200
    assert "<Response>" in response.text


def test_webhook_with_media_payload(client: TestClient, fake_graph) -> None:
    response = client.post(
        "/webhooks/twilio",
        data=_form_payload(
            NumMedia="1",
            MediaUrl0="https://example.com/photo.jpg",
            MediaContentType0="image/jpeg",
            Body="see this image",
        ),
    )
    assert response.status_code == 200
    metadata = fake_graph.calls[0]["metadata"]
    assert metadata["num_media"] == "1"
    assert metadata["media_url"] == "https://example.com/photo.jpg"
    assert metadata["media_content_type"] == "image/jpeg"


def test_webhook_invokes_graph_exactly_once_per_request(
    client: TestClient, fake_graph
) -> None:
    for _ in range(3):
        client.post("/webhooks/twilio", data=_form_payload(Body="x"))
    assert len(fake_graph.calls) == 3


# ---------------------------------------------------------------------------
# Router wiring test
# ---------------------------------------------------------------------------


def test_twilio_router_re_exported() -> None:
    from app.api import twilio_router as reexported

    assert reexported is webhook_module.router