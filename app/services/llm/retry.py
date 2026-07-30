"""Retry helpers for the LLM service.

Centralises exponential-backoff retry logic so the agent layer
and the provider implementations don't need to know about retry
policies.

The policy is intentionally narrow:

- Retries on :class:`LLMTransportError` and
  :class:`LLMRateLimitError`.
- Retries on HTTP 429 and HTTP 5xx (via
  :func:`is_retryable_status`).
- Does **not** retry on :class:`LLMConfigurationError` or
  :class:`LLMResponseError` (validation/payload errors).
- Uses exponential backoff with the base delay provided by
  :attr:`Settings.llm_retry_delay`.

The helper is intentionally synchronous — the existing providers
are synchronous so this stays simple. An async variant can be
added later when providers go async.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import TypeVar

from app.services.llm.types import (
    RETRYABLE_EXCEPTIONS,
    LLMError,
    LLMRateLimitError,
    LLMResponseError,
    LLMTransportError,
    is_retryable_status,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")


def _sleep(attempt: int, base_delay: float) -> float:
    """Sleep ``base_delay * 2 ** (attempt - 1)`` seconds.

    Returns the actual delay so tests can assert on it. ``attempt``
    is 1-based.
    """
    delay = base_delay * (2 ** max(0, attempt - 1))
    if delay > 0:
        time.sleep(delay)
    return delay


def retry_with_backoff(
    func: Callable[..., T],
    *,
    max_retries: int,
    base_delay: float,
    is_rate_limited_response: Callable[[object], bool] | None = None,
) -> Callable[..., T]:
    """Wrap ``func`` with exponential-backoff retry behaviour.

    ``func`` may either raise a :class:`LLMTransportError` /
    :class:`LLMRateLimitError`, or — when used with a provider that
    surfaces errors via return values — return an object for which
    ``is_rate_limited_response`` returns ``True``.
    """

    def wrapper(*args: object, **kwargs: object) -> T:
        last_exc: BaseException | None = None
        attempts = max_retries + 1  # initial attempt + retries
        for attempt in range(1, attempts + 1):
            try:
                result = func(*args, **kwargs)
            except RETRYABLE_EXCEPTIONS as exc:
                last_exc = exc
                logger.warning(
                    "llm: transient error on attempt %d/%d: %s",
                    attempt,
                    attempts,
                    exc,
                )
            except LLMResponseError as exc:
                # 5xx response errors are retriable; 4xx are not.
                if is_retryable_status(getattr(exc, "status_code", 0)):
                    last_exc = exc
                    logger.warning(
                        "llm: retryable response on attempt %d/%d: %s",
                        attempt,
                        attempts,
                        exc,
                    )
                else:
                    raise
            else:
                if is_rate_limited_response is not None and is_rate_limited_response(result):
                    logger.warning(
                        "llm: rate-limited result on attempt %d/%d",
                        attempt,
                        attempts,
                    )
                    continue
                return result

            if attempt < attempts:
                _sleep(attempt, base_delay)

        # All attempts exhausted.
        if last_exc is not None:
            raise last_exc
        raise LLMError("llm: all retry attempts exhausted")

    return wrapper


__all__ = [
    "retry_with_backoff",
    "is_retryable_status",
    "RETRYABLE_EXCEPTIONS",
    "LLMTransportError",
    "LLMRateLimitError",
    "LLMResponseError",
    "LLMError",
]