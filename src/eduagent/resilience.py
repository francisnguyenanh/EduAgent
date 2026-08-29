"""Shared retry policy for external calls (Firestore, Pub/Sub, Gmail, Sheets).

"Moi call ra ngoai (Gemini, Firestore, Pub/Sub, MCP) deu phai co
timeout + retry + duong thoat khi loi." llm.py has its own retry tuned to
genai's error types (see LLMGenerationError); this module covers everything
else, tuned to the transient gRPC/HTTP error types those clients raise.

Deliberately narrow: only retries errors that are actually transient
(unavailable/timeout/deadline). A permission error or a malformed request
would fail identically on retry #2 -- retrying those just delays the real
failure and burns quota.
"""

from __future__ import annotations

from google.api_core import exceptions as gcp_exceptions
from tenacity import retry, retry_if_exception, retry_if_exception_type, stop_after_attempt, wait_exponential

_TRANSIENT_EXCEPTIONS = (
    gcp_exceptions.ServiceUnavailable,
    gcp_exceptions.DeadlineExceeded,
    gcp_exceptions.GatewayTimeout,
    gcp_exceptions.Aborted,  # Firestore transaction contention -- retry is the correct response
    ConnectionError,
    TimeoutError,
)

with_gcp_retry = retry(
    retry=retry_if_exception_type(_TRANSIENT_EXCEPTIONS),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    reraise=True,
)


def _is_retryable_http_error(exc: BaseException) -> bool:
    """googleapiclient (Gmail/Sheets) raises HttpError, not google.api_core
    exceptions -- a distinct hierarchy needing its own predicate. Only 5xx
    (server-side, transient) is retried; a 4xx (bad request, permission
    denied, invalid scope) means retrying is pointless."""
    from googleapiclient.errors import HttpError

    return isinstance(exc, HttpError) and 500 <= exc.resp.status < 600


with_google_api_retry = retry(
    retry=retry_if_exception(_is_retryable_http_error),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    reraise=True,
)
