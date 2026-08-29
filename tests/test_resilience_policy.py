"""Tier-A coverage: the shared retry POLICY itself.

`tests/test_resilience.py` exercises nodes that degrade; this file tests the
predicate that decides what is even worth retrying. That predicate is the
whole safety argument of resilience.py's docstring -- "deliberately narrow:
only retries errors that are actually transient" -- and `_is_retryable_http_error`
had no test, so nothing would have caught it widening to retry a 403 forever.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from google.api_core import exceptions as gcp_exceptions
from googleapiclient.errors import HttpError

from eduagent.resilience import _is_retryable_http_error, with_gcp_retry, with_google_api_retry


def _http_error(status: int) -> HttpError:
    resp = MagicMock()
    resp.status = status
    return HttpError(resp=resp, content=b"{}")


def test_only_5xx_http_errors_are_retryable():
    """googleapiclient (Gmail/Sheets) raises HttpError, a hierarchy entirely
    separate from google.api_core -- which is why it needs its own predicate."""
    assert _is_retryable_http_error(_http_error(500)) is True
    assert _is_retryable_http_error(_http_error(503)) is True
    assert _is_retryable_http_error(_http_error(599)) is True
    # A 4xx means the request itself is wrong: bad scope, no permission,
    # malformed body. Retrying delays the real failure and burns quota.
    assert _is_retryable_http_error(_http_error(400)) is False
    assert _is_retryable_http_error(_http_error(403)) is False
    assert _is_retryable_http_error(_http_error(404)) is False
    # Not an HttpError at all.
    assert _is_retryable_http_error(ValueError("unrelated")) is False


def test_google_api_retry_gives_up_after_three_attempts_and_reraises():
    calls = {"n": 0}

    @with_google_api_retry
    def flaky():
        calls["n"] += 1
        raise _http_error(503)

    with patch("time.sleep", return_value=None), pytest.raises(HttpError):
        flaky()
    assert calls["n"] == 3


def test_google_api_retry_does_not_retry_a_403():
    calls = {"n": 0}

    @with_google_api_retry
    def forbidden():
        calls["n"] += 1
        raise _http_error(403)

    with patch("time.sleep", return_value=None), pytest.raises(HttpError):
        forbidden()
    assert calls["n"] == 1, "a 403 retried is a 403 three times"


def test_gcp_retry_recovers_from_a_transient_unavailable():
    calls = {"n": 0}

    @with_gcp_retry
    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise gcp_exceptions.ServiceUnavailable("transient")
        return "recovered"

    with patch("time.sleep", return_value=None):
        assert flaky() == "recovered"
    assert calls["n"] == 3


def test_gcp_retry_retries_aborted_because_that_is_transaction_contention():
    """Firestore raises Aborted when two transactions collide. Retrying is the
    documented correct response -- it is the one 4xx-shaped error here that is
    genuinely transient."""
    calls = {"n": 0}

    @with_gcp_retry
    def contended():
        calls["n"] += 1
        if calls["n"] < 2:
            raise gcp_exceptions.Aborted("contention")
        return "committed"

    with patch("time.sleep", return_value=None):
        assert contended() == "committed"


def test_gcp_retry_does_not_retry_invalid_argument():
    calls = {"n": 0}

    @with_gcp_retry
    def bad_request():
        calls["n"] += 1
        raise gcp_exceptions.InvalidArgument("malformed")

    with pytest.raises(gcp_exceptions.InvalidArgument):
        bad_request()
    assert calls["n"] == 1
