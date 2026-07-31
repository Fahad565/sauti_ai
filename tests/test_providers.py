"""Sprint 4 tests: provider abstraction, factory, retry, fallback.

These tests cover the new multi-provider backend:

- :class:`GoogleProvider` — happy path + error mapping using a
  stub ``google.genai`` client (no network).
- :class:`NvidiaProvider` — extracted implementation, exercised
  with a mocked ``httpx.MockTransport``.
- :func:`provider_factory.build_provider` — provider selection
  via ``Settings.llm_provider``.
- :func:`retry.retry_with_backoff` — exponential backoff on
  retryable errors, no-retry on validation errors, and respect
  for ``max_retries``.
- :class:`Twilio webhook <app.api.webhook.twilio_webhook>` —
  graceful degradation when every provider fails.

Together with the existing ``tests/test_llm.py`` these tests
prove that business logic stays vendor-agnostic and that the
webhook never crashes because of an LLM failure.
"""

from __future__ import annotations

import json
import time
from typing import Any

import httpx
import pytest

from app.api import webhook as webhook_module
from app.config.settings import Settings
from app.main import create_app
from app.services import llm as llm_module
from app.services.llm import (
    ChatCompletion,
    ChatMessage,
    LLMConfigurationError,
    LLMError,
    LLMRateLimitError,
    LLMResponseError,
    LLMTransportError,
    get_llm,
    reset_default_llm,
)
from app.services.llm.provider_factory import (
    DEFAULT_PROVIDER,
    SUPPORTED_PROVIDERS,
    build_provider,
    get_llm_provider,
    reset_default_provider,
)
from app.services.llm.providers import (
    GoogleProvider,
    LLMProvider,
    NvidiaProvider,
)
from app.services.llm.retry import retry_with_backoff


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _nvidia_settings(**overrides: Any) -> Settings:
    base = {
        "llm_provider": "nvidia",
        "nvidia_api_key": "test-key",
        "nvidia_model": "google/gemma-4-31b-it",
    }
    base.update(overrides)
    return Settings(**base)


def _google_settings(**overrides: Any) -> Settings:
    base = {
        "llm_provider": "google",
        "google_api_key": "google-test-key",
        "google_model": "gemini-2.0-flash",
    }
    base.update(overrides)
    return Settings(**base)


def _ok_nvidia_payload() -> dict[str, Any]:
    return {
        "model": "google/gemma-4-31b-it",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "NVIDIA summary text",
                },
                "finish_reason": "stop",
            }
        ],
    }


# ---------------------------------------------------------------------------
# NvidiaProvider
# ---------------------------------------------------------------------------


def test_nvidia_provider_sends_correct_request() -> None:
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["auth"] = request.headers["Authorization"]
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json=_ok_nvidia_payload())

    provider = NvidiaProvider(
        _nvidia_settings(),
        transport=httpx.MockTransport(handler),
    )
    completion = provider.generate(
        [
            ChatMessage("system", "sys"),
            ChatMessage("user", "hi"),
        ]
    )

    assert captured["auth"] == "Bearer test-key"
    body = captured["body"]
    assert body["model"] == "google/gemma-4-31b-it"
    assert body["messages"][0]["role"] == "system"
    assert isinstance(completion, ChatCompletion)
    assert completion.text == "NVIDIA summary text"
    assert completion.provider == "nvidia"
    assert completion.model == "google/gemma-4-31b-it"


def test_nvidia_provider_missing_key_raises() -> None:
    provider = NvidiaProvider(_nvidia_settings(nvidia_api_key=None))
    with pytest.raises(LLMConfigurationError):
        provider.generate([ChatMessage("user", "hi")])


def test_nvidia_provider_429_raises_rate_limit() -> None:
    provider = NvidiaProvider(
        _nvidia_settings(),
        transport=httpx.MockTransport(
            lambda r: httpx.Response(429, text="slow down")
        ),
    )
    with pytest.raises(LLMRateLimitError):
        provider.generate([ChatMessage("user", "hi")])


def test_nvidia_provider_500_raises_transport() -> None:
    provider = NvidiaProvider(
        _nvidia_settings(),
        transport=httpx.MockTransport(
            lambda r: httpx.Response(500, text="boom")
        ),
    )
    with pytest.raises(LLMTransportError):
        provider.generate([ChatMessage("user", "hi")])


def test_nvidia_provider_400_raises_response_error() -> None:
    provider = NvidiaProvider(
        _nvidia_settings(),
        transport=httpx.MockTransport(
            lambda r: httpx.Response(400, text="bad request")
        ),
    )
    with pytest.raises(LLMResponseError):
        provider.generate([ChatMessage("user", "hi")])


# ---------------------------------------------------------------------------
# GoogleProvider
# ---------------------------------------------------------------------------


class _StubGoogleModels:
    """Records calls and returns a configurable response object."""

    def __init__(self, *, text: str | None = "ok", exc: BaseException | None = None) -> None:
        self.text = text
        self.exc = exc
        self.calls: list[dict[str, Any]] = []

    def generate_content(self, *, model: str, contents: Any, config: Any) -> Any:
        self.calls.append({"model": model, "contents": contents, "config": config})
        if self.exc is not None:
            raise self.exc
        return _FakeGoogleResponse(text=self.text or "")


class _FakeGoogleResponse:
    def __init__(self, text: str) -> None:
        self.text = text
        self.model_version = "models/gemini-2.0-flash"


def _build_google_provider(stub: _StubGoogleModels) -> GoogleProvider:
    """Construct a GoogleProvider with a stubbed ``models`` namespace."""
    provider = GoogleProvider(_google_settings())
    provider._client = type("S", (), {"models": stub})()
    return provider


def test_google_provider_sends_request() -> None:
    stub = _StubGoogleModels(text="hello from gemini")
    provider = _build_google_provider(stub)

    completion = provider.generate(
        [ChatMessage("system", "sys"), ChatMessage("user", "hi")]
    )

    assert isinstance(completion, ChatCompletion)
    assert completion.text == "hello from gemini"
    assert completion.provider == "google"
    assert stub.calls, "google-genai generate_content was not invoked"
    call = stub.calls[0]
    assert call["model"] == "gemini-2.0-flash"
    assert "[system]" in call["contents"]
    assert "[user]" in call["contents"]


def test_google_provider_uses_overrides() -> None:
    stub = _StubGoogleModels(text="ok")
    provider = _build_google_provider(stub)
    provider.generate(
        [ChatMessage("user", "hi")],
        model="gemini-1.5-pro",
        max_tokens=64,
        temperature=0.3,
        top_p=0.5,
    )
    config = stub.calls[0]["config"]
    assert config["max_output_tokens"] == 64
    assert config["temperature"] == 0.3
    assert config["top_p"] == 0.5


def test_google_provider_missing_key_raises() -> None:
    with pytest.raises(LLMConfigurationError):
        GoogleProvider(_google_settings(google_api_key=None))


def test_google_provider_empty_messages_raises() -> None:
    provider = _build_google_provider(_StubGoogleModels())
    with pytest.raises(LLMConfigurationError):
        provider.generate([])


def test_google_provider_rate_limit_maps_to_llm_rate_limit_error() -> None:
    class _RateLimitedError(Exception):
        code = 429
        status_code = 429

        def __str__(self) -> str:
            return "rate limited"

    provider = _build_google_provider(
        _StubGoogleModels(exc=_RateLimitedError("rate limited"))
    )
    with pytest.raises(LLMRateLimitError):
        provider.generate([ChatMessage("user", "hi")])


def test_google_provider_500_maps_to_transport_error() -> None:
    class _ServerError(Exception):
        code = 500
        status_code = 500

        def __str__(self) -> str:
            return "internal error"

    provider = _build_google_provider(
        _StubGoogleModels(exc=_ServerError("internal error"))
    )
    with pytest.raises(LLMTransportError):
        provider.generate([ChatMessage("user", "hi")])


def test_google_provider_400_maps_to_response_error() -> None:
    class _BadRequestError(Exception):
        code = 400
        status_code = 400

        def __str__(self) -> str:
            return "bad request"

    provider = _build_google_provider(
        _StubGoogleModels(exc=_BadRequestError("bad request"))
    )
    with pytest.raises(LLMResponseError):
        provider.generate([ChatMessage("user", "hi")])


def test_google_provider_missing_text_raises_response_error() -> None:
    provider = _build_google_provider(_StubGoogleModels(text=""))
    with pytest.raises(LLMResponseError):
        provider.generate([ChatMessage("user", "hi")])


# ---------------------------------------------------------------------------
# Provider factory
# ---------------------------------------------------------------------------


def test_factory_default_provider_is_google(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.config.settings.get_settings",
        lambda: Settings(google_api_key="x"),
    )
    reset_default_provider()
    try:
        provider = get_llm_provider()
        assert isinstance(provider, GoogleProvider)
        assert provider.provider_name() == "google"
    finally:
        reset_default_provider()


def test_factory_selects_nvidia_when_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.config.settings.get_settings",
        lambda: _nvidia_settings(),
    )
    reset_default_provider()
    try:
        provider = get_llm_provider()
        assert isinstance(provider, NvidiaProvider)
        assert provider.provider_name() == "nvidia"
    finally:
        reset_default_provider()


def test_factory_rejects_unknown_provider() -> None:
    with pytest.raises(LLMConfigurationError) as excinfo:
        build_provider(Settings(llm_provider="anthropic"))
    assert "anthropic" in str(excinfo.value)


def test_factory_supported_providers_constant() -> None:
    assert "google" in SUPPORTED_PROVIDERS
    assert "nvidia" in SUPPORTED_PROVIDERS
    assert DEFAULT_PROVIDER == "google"


# ---------------------------------------------------------------------------
# Retry helper
# ---------------------------------------------------------------------------


def test_retry_succeeds_on_first_attempt() -> None:
    calls = {"n": 0}

    def func() -> str:
        calls["n"] += 1
        return "ok"

    wrapped = retry_with_backoff(func, max_retries=3, base_delay=0.0)
    assert wrapped() == "ok"
    assert calls["n"] == 1


def test_retry_recovers_after_transient_failure() -> None:
    calls = {"n": 0}

    def func() -> str:
        calls["n"] += 1
        if calls["n"] < 3:
            raise LLMTransportError("transient")
        return "ok"

    wrapped = retry_with_backoff(func, max_retries=3, base_delay=0.0)
    assert wrapped() == "ok"
    assert calls["n"] == 3


def test_retry_exhausts_and_raises_last_exception() -> None:
    calls = {"n": 0}

    def func() -> str:
        calls["n"] += 1
        raise LLMTransportError(f"failure #{calls['n']}")

    wrapped = retry_with_backoff(func, max_retries=2, base_delay=0.0)
    with pytest.raises(LLMTransportError) as excinfo:
        wrapped()
    assert calls["n"] == 3  # initial + 2 retries
    assert "failure #3" in str(excinfo.value)


def test_retry_does_not_retry_validation_errors() -> None:
    calls = {"n": 0}

    def func() -> str:
        calls["n"] += 1
        raise LLMConfigurationError("no key")

    wrapped = retry_with_backoff(func, max_retries=3, base_delay=0.0)
    with pytest.raises(LLMConfigurationError):
        wrapped()
    assert calls["n"] == 1


def test_retry_exponential_backoff_timing() -> None:
    calls: list[float] = []

    def func() -> str:
        calls.append(time.monotonic())
        if len(calls) < 3:
            raise LLMTransportError("transient")
        return "ok"

    wrapped = retry_with_backoff(func, max_retries=2, base_delay=0.05)
    wrapped()

    assert len(calls) == 3
    # First retry sleeps base_delay * 1; second retry sleeps base_delay * 2.
    gap1 = calls[1] - calls[0]
    gap2 = calls[2] - calls[1]
    assert gap1 >= 0.04
    assert gap2 >= gap1


# ---------------------------------------------------------------------------
# Twilio webhook graceful degradation
# ---------------------------------------------------------------------------


@pytest.fixture
def twilio_client():
    from fastapi.testclient import TestClient

    app = create_app()
    return TestClient(app)


def test_webhook_responds_200_when_every_provider_fails(
    twilio_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If the LLM raises, the webhook must still return TwiML HTTP 200."""

    class _AlwaysFails(LLMProvider):
        name = "always-fails"

        def generate(self, messages, **_kwargs):
            raise LLMTransportError("upstream provider is down")

    fake = _AlwaysFails()
    monkeypatch.setattr(webhook_module, "compile_graph", lambda: _FakeGraphStub())

    # Patch ``get_llm`` so the analyze node uses our always-failing
    # provider.
    monkeypatch.setattr(
        llm_module,
        "get_llm",
        lambda: llm_module.GemmaClient(provider=fake),
    )
    reset_default_llm()

    # Stub out the outbound Twilio REST call so the test never tries
    # to hit api.twilio.com (which is unreachable from the sandbox).
    sent_payloads: list[dict] = []

    def _fake_send_whatsapp_reply(to, body, account_sid, auth_token, from_number):
        sent_payloads.append({"to": to, "body": body})
        return True

    monkeypatch.setattr(webhook_module, "send_whatsapp_reply", _fake_send_whatsapp_reply)

    response = twilio_client.post(
        "/webhooks/twilio",
        data={
            "MessageSid": "SM-deadbeef",
            "From": "whatsapp:+15550000000",
            "Body": "the road is broken",
        },
    )

    assert response.status_code == 200
    assert "application/xml" in response.headers["content-type"]
    body = response.text
    assert "<Response>" in body
    # In async mode the HTTP response body is empty TwiML; the LLM
    # reply is dispatched to WhatsApp via the background task. Verify
    # the stubbed outbound was called with the fallback text.
    assert any(
        "LLM unavailable" in p["body"] or "Sauti AI" in p["body"] or "received" in p["body"]
        for p in sent_payloads
    ), f"expected outbound to receive an LLM-unavailable reply, got {sent_payloads!r}"


class _FakeGraphStub:
    """Stand-in for a compiled LangGraph graph that invokes ``get_llm``."""

    def invoke(self, state):
        # Force the analyze-node path by calling it directly with the
        # patched get_llm. This mirrors the behaviour of the real
        # graph in tests.
        from app.agent.nodes import analyze_node, respond_node

        state2 = analyze_node(state)
        state.update(state2)
        state3 = respond_node(state)
        state.update(state3)
        return state


# ---------------------------------------------------------------------------
# Task 9 Diagnostics & .env Loading Tests
# ---------------------------------------------------------------------------

def test_dotenv_loaded_successfully() -> None:
    """Prove that .env is loaded and GOOGLE_API_KEY is available in os.environ."""
    import os
    assert "GOOGLE_API_KEY" in os.environ
    assert os.getenv("GOOGLE_API_KEY") is not None


def test_google_api_key_reaches_provider() -> None:
    """Prove that GOOGLE_API_KEY reaches GoogleProvider through Settings."""
    settings = _google_settings(google_api_key="my-google-test-key")
    provider = GoogleProvider(settings)
    assert provider._settings.google_api_key == "my-google-test-key"


def test_google_provider_missing_key_raises_configuration_error() -> None:
    """Prove that a missing key raises LLMConfigurationError."""
    settings = Settings(llm_provider="google")
    settings.google_api_key = None
    settings.model_fields_set.add("google_api_key")
    
    with pytest.raises(LLMConfigurationError) as excinfo:
        GoogleProvider(settings)
    assert "GOOGLE_API_KEY is not configured" in str(excinfo.value)


def test_google_provider_valid_key_initializes_successfully() -> None:
    """Prove that a valid key initializes GoogleProvider successfully."""
    settings = _google_settings(google_api_key="valid-key")
    provider = GoogleProvider(settings)
    assert isinstance(provider, GoogleProvider)