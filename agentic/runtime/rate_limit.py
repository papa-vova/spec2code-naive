"""
Provider-agnostic rate limit handling for LLM invocations.

Uses common HTTP conventions: 429 status, Retry-After, x-ratelimit-reset-* headers.
No provider-specific imports.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any, Callable, List, Optional, TypeVar

from tenacity import retry, retry_if_exception, stop_after_attempt

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Common header names for reset duration (order: try first)
DEFAULT_RESET_HEADER_NAMES = [
    "x-ratelimit-reset-requests",
    "x-ratelimit-reset-tokens",
    "retry-after",
]


def is_rate_limit_error(exc: BaseException) -> bool:
    """Check if exception indicates a rate limit (HTTP 429)."""
    status = getattr(exc, "status_code", None)
    if status is not None and status == 429:
        return True
    response = getattr(exc, "response", None)
    if response is not None:
        resp_status = getattr(response, "status_code", None)
        if resp_status == 429:
            return True
    return False


def _get_headers_from_exception(exc: BaseException) -> Optional[Any]:
    """Extract headers from exception (response.headers or similar)."""
    response = getattr(exc, "response", None)
    if response is None:
        return None
    return getattr(response, "headers", None)


def _parse_duration_to_seconds(value: str) -> Optional[float]:
    """
    Parse duration string to seconds.

    Supports:
    - 1s, 6m0s, 1h0m0s (Go-style)
    - 55 (plain seconds)
    - Retry-After HTTP-date (RFC 7231)
    """
    if not value or not isinstance(value, str):
        return None
    value = value.strip().lower()
    if not value:
        return None

    # Plain integer seconds
    if value.isdigit():
        return float(int(value))

    # Go-style: 1s, 6m0s, 1h0m0s
    # Pattern: optional hours, optional minutes, optional seconds
    total = 0.0
    # Hours: 1h, 1h0m0s
    h_match = re.search(r"(\d+)h", value)
    if h_match:
        total += int(h_match.group(1)) * 3600
    # Minutes: 6m, 6m0s
    m_match = re.search(r"(\d+)m", value)
    if m_match:
        total += int(m_match.group(1)) * 60
    # Seconds: 1s, 0s
    s_match = re.search(r"(\d+)s", value)
    if s_match:
        total += int(s_match.group(1))

    if total > 0 or (h_match or m_match or s_match):
        return total

    # Retry-After HTTP-date (e.g. Wed, 21 Oct 2015 07:28:00 GMT)
    try:
        from email.utils import parsedate_to_datetime

        dt = parsedate_to_datetime(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        delta = (dt - now).total_seconds()
        return max(0.0, delta) if delta > 0 else None
    except (ValueError, TypeError):
        pass

    return None


def get_reset_seconds_from_exception(
    exc: BaseException,
    header_names: Optional[List[str]] = None,
) -> Optional[float]:
    """
    Extract reset wait time in seconds from exception response headers.

    Tries each header in order; returns first successfully parsed value.
    """
    headers = _get_headers_from_exception(exc)
    if headers is None:
        return None

    names = header_names or DEFAULT_RESET_HEADER_NAMES
    for name in names:
        raw = None
        if hasattr(headers, "get"):
            raw = headers.get(name)
        elif hasattr(headers, "__getitem__"):
            try:
                raw = headers[name]
            except (KeyError, TypeError):
                pass
        if raw is not None:
            if isinstance(raw, (int, float)):
                return float(raw)
            parsed = _parse_duration_to_seconds(str(raw))
            if parsed is not None:
                return parsed
    return None


def _should_retry(exc: BaseException) -> bool:
    """Tenacity predicate: retry on rate limit errors."""
    return is_rate_limit_error(exc)


def _wait_strategy(
    use_header_reset: bool,
    header_names: List[str],
    initial_delay: float,
    exponential_base: float,
):
    """Build wait strategy: header-based when available, else exponential."""

    def wait(retry_state) -> float:
        exc = retry_state.outcome.exception() if retry_state.outcome else None
        if exc is not None and use_header_reset:
            seconds = get_reset_seconds_from_exception(exc, header_names)
            if seconds is not None and seconds > 0:
                # Cap at 5 minutes to avoid excessive waits from bad headers
                wait_secs = min(seconds, 300.0)
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(
                        "Rate limit: waiting for header-based reset",
                        extra={
                            "attempt": retry_state.attempt_number,
                            "wait_seconds": wait_secs,
                        },
                    )
                return wait_secs
        # Exponential backoff fallback
        return min(
            initial_delay * (exponential_base ** retry_state.attempt_number),
            60.0,
        )

    return wait


def with_rate_limit_retry(
    max_retries: int = 6,
    initial_delay: float = 1.0,
    exponential_base: float = 2.0,
    use_header_reset: bool = True,
    reset_header_names: Optional[List[str]] = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator that retries a call on rate limit errors.

    Uses header-based wait when available, else exponential backoff.
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        wait_fn = _wait_strategy(
            use_header_reset=use_header_reset,
            header_names=reset_header_names or DEFAULT_RESET_HEADER_NAMES,
            initial_delay=initial_delay,
            exponential_base=exponential_base,
        )

        @retry(
            retry=retry_if_exception(_should_retry),
            stop=stop_after_attempt(max_retries),
            wait=wait_fn,
            reraise=True,
        )
        def wrapped(*args: Any, **kwargs: Any) -> T:
            return func(*args, **kwargs)

        return wrapped

    return decorator


def invoke_with_rate_limit_retry(
    func: Callable[[], T],
    max_retries: int = 6,
    initial_delay: float = 1.0,
    exponential_base: float = 2.0,
    use_header_reset: bool = True,
    reset_header_names: Optional[List[str]] = None,
) -> T:
    """
    Execute a callable with rate limit retry, using config values.

    Convenience for runtime config injection.
    """
    wrapped = with_rate_limit_retry(
        max_retries=max_retries,
        initial_delay=initial_delay,
        exponential_base=exponential_base,
        use_header_reset=use_header_reset,
        reset_header_names=reset_header_names,
    )(func)
    return wrapped()
