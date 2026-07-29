"""Tests for the LLM service and the LLM-backed analyze node.

These tests avoid hitting the real NVIDIA endpoint by injecting a
``httpx.MockTransport`` into :class:`GemmaClient`. They cover:

- successful chat-completion invocation,
- missing / empty API key,
- HTTP error responses,
- invalid JSON responses,
- analyze_node integration with a stub client,
- analyze_node graceful degradation when the LLM raises.
"""

from __future__ import annotations

import json

import httpx
import pytest

from app.agent.nodes import analyze_node
from app.agent.state import AgentState
from app.config.settings import Settings, get_settings
from app.services import llm as llm_module
from app.services.llm import (
    ChatCompletion,
    ChatMessage,
    GemmaClient,
    LLMConfigurationError,
    LLMResponseError,
    LLMTransportError,
    get_llm,
    reset_default_llm,
)
from app.services.llm.provider_factory import reset_default_provider


# --- Helpers ---------------------------------------------------------


def _ok_response() -> dict[str, object]:
    return {
        "id": "test-id",
        "model": "google/gemma-4-31b-it",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "This is Gemma 4 speaking.",
                },
                "finish_reason": "stop",
            }
        ],
    }


def _make_client(
    handler: httpx.MockTransport,
    settings: Settings,
) -> GemmaClient:
    return GemmaClient(settings=settings, transport=handler)


def _settings_with_key(api_key: str = "test-key") -> Settings:
    """Build a Settings instance with the API key pre-populated.

    Bypasses :func:`get_settings` so the test never reads the real
    ``.env`` file. Pins the provider to NVIDIA so the factory
    selects the NVIDIA backend (Sprint 4 multi-provider design).
    """
    return Settings(llm_provider="nvidia", nvidia_api_key=api_key)


# --- GemmaClient unit tests -----------------------------------------


def test_missing_api_key_raises_configuration_error() -> None:
    settings = Settings(llm_provider="nvidia", nvidia_api_key=None)
    client = GemmaClient(settings=settings, transport=httpx.MockTransport(lambda r: httpx.Response(200, json={})))

    with pytest.raises(LLMConfigurationError):
        client.complete([ChatMessage(role="user", content="hi")])


def test_empty_messages_raises_configuration_error() -> None:
    settings = _settings_with_key()
    client = _make_client(
        httpx.MockTransport(lambda r: httpx.Response(200, json={})),
        settings,
    )

    with pytest.raises(LLMConfigurationError):
        client.complete([])


def test_successful_completion() -> None:
    settings = _settings_with_key()

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer test-key"
        body = json.loads(request.content)
        assert body["model"] == "google/gemma-4-31b-it"
        assert body["messages"][0]["role"] == "user"
        assert body["messages"][0]["content"] == "hello"
        return httpx.Response(200, json=_ok_response())

    client = _make_client(httpx.MockTransport(handler), settings)
    completion = client.complete([ChatMessage(role="user", content="hello")])

    assert isinstance(completion, ChatCompletion)
    assert completion.text == "This is Gemma 4 speaking."
    assert completion.raw is not None
    assert completion.raw["model"] == "google/gemma-4-31b-it"


def test_http_error_raises_response_error() -> None:
    settings = _settings_with_key()
    client = _make_client(
        httpx.MockTransport(
            lambda r: httpx.Response(401, text="unauthorised")
        ),
        settings,
    )

    with pytest.raises(LLMResponseError) as excinfo:
        client.complete([ChatMessage(role="user", content="hi")])
    assert "401" in str(excinfo.value)


def test_invalid_json_raises_response_error() -> None:
    settings = _settings_with_key()
    client = _make_client(
        httpx.MockTransport(
            lambda r: httpx.Response(200, text="not-json")
        ),
        settings,
    )

    with pytest.raises(LLMResponseError):
        client.complete([ChatMessage(role="user", content="hi")])


def test_transport_error_wrapped() -> None:
    settings = _settings_with_key()

    def boom(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    client = _make_client(httpx.MockTransport(boom), settings)

    with pytest.raises(LLMTransportError):
        client.complete([ChatMessage(role="user", content="hi")])


def test_missing_assistant_message_raises() -> None:
    settings = _settings_with_key()
    bad_payload = {"choices": [{"message": {}}]}
    client = _make_client(
        httpx.MockTransport(lambda r: httpx.Response(200, json=bad_payload)),
        settings,
    )

    with pytest.raises(LLMResponseError):
        client.complete([ChatMessage(role="user", content="hi")])


# --- Singleton lifecycle ---------------------------------------------


def test_get_llm_singleton(monkeypatch: pytest.MonkeyPatch) -> None:
    """The cached default client must be a process-wide singleton.

    Pins the provider to NVIDIA (Sprint 4 multi-provider design)
    so the factory does not fall back to Google — which would
    fail with a missing ``GOOGLE_API_KEY`` even when the singleton
    itself is just being constructed.
    """
    import app.config.settings as settings_module
    import app.services.llm.provider_factory as factory_module

    get_settings.cache_clear()
    reset_default_provider()

    nvidia_settings = Settings(
        llm_provider="nvidia", nvidia_api_key="singleton-test-key"
    )

    monkeypatch.setattr(settings_module, "get_settings", lambda: nvidia_settings)
    reset_default_llm()

    try:
        # Without an API key the singleton must still be created —
        # the lazy check happens inside ``complete()``.
        assert get_llm() is get_llm()
    finally:
        reset_default_llm()
        reset_default_provider()
        get_settings.cache_clear()


# --- analyze_node integration ---------------------------------------


class _StubClient:
    """Minimal stand-in for :class:`GemmaClient` for node tests."""

    def __init__(self, text: str | None = None, exc: Exception | None = None) -> None:
        self.text = text
        self.exc = exc
        self.calls: list[list[ChatMessage]] = []

    def complete(self, messages, **_kwargs):  # noqa: ANN001 - signature parity
        from app.services.llm import ChatCompletion

        self.calls.append(list(messages))
        if self.exc is not None:
            raise self.exc
        assert self.text is not None
        return ChatCompletion(text=self.text, raw={"model": "stub"})


def _initial_state(message: str = "the road is broken") -> AgentState:
    return {
        "input_message": message,
        "steps": [],
        "response": "",
        "metadata": {},
    }


def test_analyze_node_uses_stub_client() -> None:
    stub = _StubClient(text="summary from stub")
    state = _initial_state()

    update = analyze_node(state, client=stub)  # type: ignore[arg-type]
    # ``analyze_node`` returns ``dict[str, object]`` so Pylance sees
    # ``object`` here. We narrow the metadata value at the test
    # boundary to keep the type checker happy.
    assert update["steps"] == ["analyze"]
    assert update["analysis"] == "summary from stub"
    metadata: dict[str, str] = update["metadata"]  # type: ignore[assignment]
    assert metadata["analyze_model"] == "stub"
    # The stub received both a system prompt and the user message.
    assert len(stub.calls) == 1
    assert [m.role for m in stub.calls[0]] == ["system", "user"]


def test_analyze_node_handles_llm_error() -> None:
    stub = _StubClient(exc=LLMResponseError("upstream 500"))
    state = _initial_state()

    update = analyze_node(state, client=stub)  # type: ignore[arg-type]

    assert update["steps"] == ["analyze"]
    assert "analysis" not in update
    metadata: dict[str, str] = update["metadata"]  # type: ignore[assignment]
    assert "upstream 500" in metadata["analyze_error"]


def test_analyze_node_handles_missing_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """With no API key, the global ``get_llm`` raises and the node
    degrades gracefully without raising."""
    import app.config.settings as settings_module
    import app.services.llm as module
    import app.services.llm.provider_factory as factory_module

    nvidia_settings = Settings(llm_provider="nvidia", nvidia_api_key=None)
    monkeypatch.setattr(settings_module, "get_settings", lambda: nvidia_settings)
    monkeypatch.setattr(
        module,
        "get_llm",
        lambda: module.GemmaClient(settings=nvidia_settings),
    )

    update = analyze_node(_initial_state(""))

    metadata: dict[str, str] = update["metadata"]  # type: ignore[assignment]
    assert "analyze_error" in metadata


# --- Module exports --------------------------------------------------


def test_llm_module_exports_expected_symbols() -> None:
    for name in (
        "ChatMessage",
        "ChatCompletion",
        "GemmaClient",
        "get_llm",
        "reset_default_llm",
        "LLMError",
        "LLMConfigurationError",
        "LLMTransportError",
        "LLMResponseError",
    ):
        assert hasattr(llm_module, name), name