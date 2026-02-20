"""Tests for provider-agnostic rate limit handling."""

import unittest
from unittest.mock import MagicMock

from agentic.runtime.rate_limit import (
    _parse_duration_to_seconds,
    get_reset_seconds_from_exception,
    is_rate_limit_error,
    invoke_with_rate_limit_retry,
)


class TestParseDuration(unittest.TestCase):
    """Tests for duration string parsing."""

    def test_plain_seconds(self):
        self.assertEqual(_parse_duration_to_seconds("55"), 55.0)
        self.assertEqual(_parse_duration_to_seconds("1"), 1.0)

    def test_go_style_seconds(self):
        self.assertEqual(_parse_duration_to_seconds("1s"), 1.0)
        self.assertEqual(_parse_duration_to_seconds("0s"), 0.0)

    def test_go_style_minutes(self):
        self.assertEqual(_parse_duration_to_seconds("6m0s"), 360.0)
        self.assertEqual(_parse_duration_to_seconds("1m"), 60.0)

    def test_go_style_hours(self):
        self.assertEqual(_parse_duration_to_seconds("1h0m0s"), 3600.0)
        self.assertEqual(_parse_duration_to_seconds("1h"), 3600.0)

    def test_invalid_returns_none(self):
        self.assertIsNone(_parse_duration_to_seconds(""))
        self.assertIsNone(_parse_duration_to_seconds("xyz"))
        self.assertIsNone(_parse_duration_to_seconds(None))


class TestIsRateLimitError(unittest.TestCase):
    """Tests for generic 429 detection."""

    def test_status_code_on_exception(self):
        exc = MagicMock()
        exc.status_code = 429
        self.assertTrue(is_rate_limit_error(exc))

    def test_status_code_on_response(self):
        exc = MagicMock()
        exc.status_code = 500
        exc.response = MagicMock()
        exc.response.status_code = 429
        self.assertTrue(is_rate_limit_error(exc))

    def test_not_rate_limit(self):
        exc = MagicMock()
        exc.status_code = 500
        self.assertFalse(is_rate_limit_error(exc))

    def test_no_response(self):
        exc = MagicMock(spec=[])
        self.assertFalse(is_rate_limit_error(exc))


class TestGetResetSeconds(unittest.TestCase):
    """Tests for header extraction from exception."""

    def test_extracts_from_headers(self):
        exc = MagicMock()
        exc.response = MagicMock()
        exc.response.headers = {"x-ratelimit-reset-requests": "5s"}
        result = get_reset_seconds_from_exception(exc)
        self.assertEqual(result, 5.0)

    def test_returns_none_when_no_headers(self):
        exc = MagicMock()
        exc.response = None
        self.assertIsNone(get_reset_seconds_from_exception(exc))

    def test_returns_none_when_header_missing(self):
        exc = MagicMock()
        exc.response = MagicMock()
        exc.response.headers = {}
        self.assertIsNone(get_reset_seconds_from_exception(exc))


class TestInvokeWithRetry(unittest.TestCase):
    """Tests for retry wrapper."""

    def test_success_no_retry(self):
        call_count = 0

        def succeed():
            nonlocal call_count
            call_count += 1
            return "ok"

        result = invoke_with_rate_limit_retry(succeed, max_retries=3)
        self.assertEqual(result, "ok")
        self.assertEqual(call_count, 1)

    def test_non_429_not_retried(self):
        call_count = 0

        def fail_with_500():
            nonlocal call_count
            call_count += 1
            exc = MagicMock()
            exc.status_code = 500
            raise ValueError("server error")

        with self.assertRaises(ValueError):
            invoke_with_rate_limit_retry(fail_with_500, max_retries=3)
        self.assertEqual(call_count, 1)
