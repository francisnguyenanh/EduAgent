"""Google Docs integration for public 'Anyone with the link' documents.

Extracts the plain text content of a Google Doc by exporting it as plain text
(GET https://docs.google.com/document/d/<DOC_ID>/export?format=txt).
Zero extra heavy GCP dependencies needed for public docs; deterministic and fast.
"""

from __future__ import annotations

import re
import urllib.error
import urllib.request

_GDOC_PATTERN = re.compile(r"docs\.google\.com/document/(?:u/\d+/)?d/([a-zA-Z0-9_-]+)")
_EXPORT_URL_TEMPLATE = "https://docs.google.com/document/d/{doc_id}/export?format=txt"
_USER_AGENT = "eduagent/1.0 (Educational Socratic Mentor; Google Cloud ADK2)"


def extract_gdoc_id(url_or_id: str) -> str | None:
    """Extracts the Google Doc ID from a URL, or returns the string if it's already an ID."""
    match = _GDOC_PATTERN.search(url_or_id)
    if match:
        return match.group(1)
    # Check if the string itself looks like a raw doc ID (30-60 alphanumeric characters)
    trimmed = url_or_id.strip()
    if re.fullmatch(r"[a-zA-Z0-9_-]{25,70}", trimmed):
        return trimmed
    return None


def fetch_gdoc_text(url_or_id: str, timeout: float = 10.0) -> str:
    """Fetches the plain text of a publicly shared Google Doc.

    Args:
        url_or_id: Full Google Doc share URL or raw document ID.
        timeout: HTTP request timeout in seconds.

    Returns:
        The stripped plain text content of the document.

    Raises:
        ValueError: If URL format is invalid, document is not found (404), or content is empty.
        PermissionError: If document is private and not shared as 'Anyone with the link'.
        RuntimeError: For other network transport failures.
    """
    doc_id = extract_gdoc_id(url_or_id)
    if not doc_id:
        raise ValueError(
            f"Invalid Google Doc URL: {url_or_id!r}. Expected format: https://docs.google.com/document/d/<DOC_ID>/..."
        )

    export_url = _EXPORT_URL_TEMPLATE.format(doc_id=doc_id)
    req = urllib.request.Request(
        export_url,
        headers={"User-Agent": _USER_AGENT, "Accept": "text/plain, text/html, */*"},
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            final_url = response.geturl()
            # If Google redirects to ServiceLogin / accounts.google.com, it means the doc is private
            if "accounts.google.com" in final_url or "ServiceLogin" in final_url:
                raise PermissionError(
                    "Google Doc is private. Please set sharing to 'Anyone with the link can view'."
                )

            MAX_READ_BYTES = 100_000
            MAX_TEXT_CHARS = 20_000

            data = response.read(MAX_READ_BYTES)
            text = data.decode("utf-8-sig", errors="replace").strip()

            if not text:
                raise ValueError("Google Doc appears to be empty.")

            if len(text) > MAX_TEXT_CHARS:
                text = text[:MAX_TEXT_CHARS]

            return text

    except urllib.error.HTTPError as exc:
        if exc.code in (401, 403):
            raise PermissionError(
                "Google Doc is not accessible. Please set sharing to 'Anyone with the link can view'."
            ) from exc
        if exc.code == 404:
            raise ValueError(f"Google Doc not found (ID: {doc_id}). Please check the URL.") from exc
        raise RuntimeError(f"Failed to fetch Google Doc (HTTP {exc.code}): {exc.reason}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Network error connecting to Google Docs: {exc.reason}") from exc
