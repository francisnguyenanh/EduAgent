"""Unit tests for src/eduagent/integrations/gdocs.py.

Deterministic, zero network calls -- mocks urllib.request.urlopen.
"""

from __future__ import annotations

import io
import urllib.error
from unittest.mock import MagicMock, patch

import pytest

from eduagent.integrations.gdocs import extract_gdoc_id, fetch_gdoc_text


def test_extract_gdoc_id_from_various_url_formats():
    assert (
        extract_gdoc_id("https://docs.google.com/document/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/edit")
        == "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"
    )
    assert (
        extract_gdoc_id("https://docs.google.com/document/u/0/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/preview")
        == "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"
    )
    assert (
        extract_gdoc_id("1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms")
        == "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"
    )
    assert extract_gdoc_id("not-a-valid-url-or-id") is None


def test_fetch_gdoc_text_success():
    fake_response = MagicMock()
    fake_response.geturl.return_value = "https://docs.google.com/document/d/123/export?format=txt"
    fake_response.read.return_value = b"\xef\xbb\xbfThis is an essay written in Google Docs."
    fake_response.__enter__.return_value = fake_response
    fake_response.__exit__.return_value = None

    with patch("urllib.request.urlopen", return_value=fake_response):
        text = fetch_gdoc_text("https://docs.google.com/document/d/1234567890abcdef1234567890/edit")

    assert text == "This is an essay written in Google Docs."


def test_fetch_gdoc_text_private_doc_raises_permission_error():
    fake_response = MagicMock()
    fake_response.geturl.return_value = "https://accounts.google.com/ServiceLogin?continue=https://docs.google.com..."
    fake_response.read.return_value = b"<html>Sign in to continue</html>"
    fake_response.__enter__.return_value = fake_response
    fake_response.__exit__.return_value = None

    with patch("urllib.request.urlopen", return_value=fake_response):
        with pytest.raises(PermissionError, match="Google Doc is private"):
            fetch_gdoc_text("https://docs.google.com/document/d/1234567890abcdef1234567890/edit")


def test_fetch_gdoc_text_404_raises_value_error():
    http_error = urllib.error.HTTPError(
        url="https://docs.google.com/...", code=404, msg="Not Found", hdrs={}, fp=io.BytesIO(b"")
    )
    with patch("urllib.request.urlopen", side_effect=http_error):
        with pytest.raises(ValueError, match="Google Doc not found"):
            fetch_gdoc_text("https://docs.google.com/document/d/1234567890abcdef1234567890/edit")


def test_fetch_gdoc_text_empty_doc_raises_value_error():
    fake_response = MagicMock()
    fake_response.geturl.return_value = "https://docs.google.com/document/d/123/export?format=txt"
    fake_response.read.return_value = b"   \n\n  "
    fake_response.__enter__.return_value = fake_response
    fake_response.__exit__.return_value = None

    with patch("urllib.request.urlopen", return_value=fake_response):
        with pytest.raises(ValueError, match="Google Doc appears to be empty"):
            fetch_gdoc_text("https://docs.google.com/document/d/1234567890abcdef1234567890/edit")
