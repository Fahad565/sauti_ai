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

Note: Tests run with ``WEBHOOK_ASYNC_MODE=false`` (synchronous mode)
so the graph is invoked within the HTTP request lifecycle, making
assertions on ``fake_graph.calls`` deterministic without needing to
wait for background tasks.
"""

from __future__ import annotations

import os
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


@pytest.fixture(autouse=True)
def force_sync_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force synchronous webhook mode so graph assertions are deterministic."""
    monkeypatch.setenv("WEBHOOK_ASYNC_MODE", "false")
    # Clear settings cache so the new env var is picked up.
    from app.config.settings import get_settings
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def fake_graph(monkeypatch: pytest.MonkeyPatch):
    """Replace the pre-compiled ``_GRAPH`` in webhook with a configurable fake."""

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
    # Patch the pre-compiled module-level ``_GRAPH`` used by the handler.
    monkeypatch.setattr(webhook_module, "_GRAPH", fake)
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
# FastAPI route tests (sync mode)
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
# Async mode test
# ---------------------------------------------------------------------------


def test_webhook_async_mode_returns_empty_twiml_immediately(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """In async mode the webhook returns immediately with empty TwiML."""
    monkeypatch.setenv("WEBHOOK_ASYNC_MODE", "true")
    from app.config.settings import get_settings
    get_settings.cache_clear()

    class _FakeGraph:
        def __init__(self) -> None:
            self.calls: list[dict] = []

        def invoke(self, state: dict) -> dict:
            self.calls.append(state)
            return {**state, "response": "grounded reply"}

    fake = _FakeGraph()
    monkeypatch.setattr(webhook_module, "_GRAPH", fake)
    # Prevent real outbound delivery.
    monkeypatch.setattr(webhook_module, "send_whatsapp_reply", lambda **_kw: False)

    app = create_app()
    with TestClient(app, raise_server_exceptions=False) as c:
        response = c.post("/webhooks/twilio", data=_form_payload(Body="test async"))

    assert response.status_code == 200
    assert "<Response>" in response.text
    # Async mode returns empty TwiML body (graph reply arrives via REST).
    msg = parse_twiml_message(response.text)
    assert msg == "" or msg is None or len(msg or "") == 0

    get_settings.cache_clear()


# ---------------------------------------------------------------------------
# Router wiring test
# ---------------------------------------------------------------------------


def test_twilio_router_re_exported() -> None:
    from app.api import twilio_router as reexported

    assert reexported is webhook_module.router


# ---------------------------------------------------------------------------
# Async-mode background-task regression (DECISION-0014 / DEBUG.md)
# ---------------------------------------------------------------------------


def test_async_mode_background_task_invokes_graph_and_outbound(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """In async mode the BackgroundTask must actually run the graph
    AND call the outbound delivery function with the LLM reply.

    Without this guarantee, async mode silently degenerates into a
    no-op: the webhook returns empty TwiML and the citizen never
    receives a WhatsApp message — the exact symptom described in
    DEBUG.md.
    """
    monkeypatch.setenv("WEBHOOK_ASYNC_MODE", "true")
    monkeypatch.setenv("TWILIO_ACCOUNT_SID", "AC_fake")
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "tok_fake")
    monkeypatch.setenv("TWILIO_FROM_NUMBER", "whatsapp:+14155238886")
    from app.config.settings import get_settings

    get_settings.cache_clear()

    graph_calls: list[dict] = []
    outbound_calls: list[dict] = []

    class _FakeGraph:
        def invoke(self, state: dict) -> dict:
            graph_calls.append(dict(state))
            return {**state, "response": "grounded reply"}

    def _fake_outbound(*, to: str, body: str, **_: Any) -> bool:
        outbound_calls.append({"to": to, "body": body})
        return True

    monkeypatch.setattr(webhook_module, "_GRAPH", _FakeGraph())
    monkeypatch.setattr(webhook_module, "send_whatsapp_reply", _fake_outbound)

    app = create_app()
    with TestClient(app, raise_server_exceptions=False) as c:
        response = c.post("/webhooks/twilio", data=_form_payload(Body="hi"))

    # Webhook itself returns empty TwiML immediately.
    assert response.status_code == 200
    assert "<Response>" in response.text

    # FastAPI TestClient drains BackgroundTasks before returning, so we
    # can assert the side-effects deterministically here.
    assert len(graph_calls) == 1, "graph must be invoked exactly once"
    assert graph_calls[0]["input_message"] == "hi"

    assert len(outbound_calls) == 1, (
        "async mode must dispatch the LLM reply via Twilio REST — "
        "otherwise DEBUG.md reproduction (no WhatsApp message) recurs."
    )
    assert outbound_calls[0]["to"] == "whatsapp:+254712345678"
    assert outbound_calls[0]["body"] == "grounded reply"

    get_settings.cache_clear()


def test_async_mode_outbound_skipped_when_credentials_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If Twilio REST credentials are absent the outbound function is
    called (and reports False) so the failure is visible in logs
    rather than silently swallowed.
    """
    monkeypatch.setenv("WEBHOOK_ASYNC_MODE", "true")
    # Wipe REST credentials.
    monkeypatch.delenv("TWILIO_ACCOUNT_SID", raising=False)
    monkeypatch.delenv("TWILIO_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("TWILIO_FROM_NUMBER", raising=False)
    from app.config.settings import get_settings

    get_settings.cache_clear()

    outbound_calls: list[dict] = []

    def _fake_outbound(*, to: str, body: str, **_: Any) -> bool:
        outbound_calls.append({"to": to, "body": body})
        return False

    monkeypatch.setattr(webhook_module, "_GRAPH", type("_G", (), {"invoke": lambda self, s: {**s, "response": "ok"}})())
    monkeypatch.setattr(webhook_module, "send_whatsapp_reply", _fake_outbound)

    app = create_app()
    with TestClient(app, raise_server_exceptions=False) as c:
        response = c.post("/webhooks/twilio", data=_form_payload())

    assert response.status_code == 200
    # Outbound was still attempted — the no-credentials path is loud.
    assert outbound_calls == [
        {"to": "whatsapp:+254712345678", "body": "ok"}
    ], "send_whatsapp_reply must still be invoked when credentials are missing"

    get_settings.cache_clear()


def test_log_stage_timings_emits_total_line(caplog) -> None:
    """The DEBUG.md call-out #1 ('time every stage') is satisfied by
    a single structured log line per background run.
    """
    import logging

    caplog.set_level(logging.INFO, logger="app.api.webhook")
    webhook_module._log_stage_timings({"graph": 12.34, "persist_output": 0.01, "outbound": 0.05})

    matching = [
        r.message
        for r in caplog.records
        if "pipeline stage:" in r.message
    ]
    assert matching, "expected a 'pipeline stage:' log line"
    line = matching[-1]
    assert "graph=12.34s" in line
    assert "persist_output=0.01s" in line
    assert "outbound=0.05s" in line
    assert "total=12.40s" in line


# ---------------------------------------------------------------------------
# DEBUG.md regression test — the user-reported failing message
# ---------------------------------------------------------------------------


def test_potholes_complaint_is_routed_as_complaint() -> None:
    """The DEBUG.md failing prompt must be classified as a complaint,
    not as a generic infrastructure lookup, so retrieval stays scoped
    and the LLM prompt stays small.
    """
    from app.services.classifier import IntentClassifier

    classifier = IntentClassifier()
    result = classifier.classify(
        "the road towards nyali from buxton is very poor with potholes"
    )

    assert result["intent"] == "complaint", (
        f"expected complaint, got {result['intent']!r} "
        f"(matches={result['keywords_matched']})"
    )
    assert "pothole" in result["keywords_matched"]
    assert result["confidence"] >= 0.5