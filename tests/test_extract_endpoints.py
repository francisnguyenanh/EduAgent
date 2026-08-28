"""Tests for the two-step ingest flow (Audit Wave 25 review).

`/api/debate/extract-image` and `/api/debate/extract-gdoc` let a student pull
the text out of a photo or Doc, SEE it, correct it, and only then start the
debate. They shipped with no tests; this file adds them, and the first one is a
regression guard for a bug that would have reached production: the UI called
both endpoints without an identity, so every click returned 422 and the OCR
demo path was dead.

Sanitization and the 20k cap are deliberately NOT re-tested here -- extraction
returns raw text on purpose and the guards run at `/api/debate/start`, which is
where the text is actually submitted.
"""

from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient

from eduagent.auth import create_access_token
from eduagent.server import app

client = TestClient(app)
_STUDENT = {"Authorization": f"Bearer {create_access_token('c1_stu01', 'student', 'c1')}"}
_OTHER_STUDENT = {"Authorization": f"Bearer {create_access_token('c1_stu02', 'student', 'c1')}"}

_OCR_OK = {
    "transcribed_text": "Video games are great!",
    "confidence": "high",
    "uncertain_segments": [],
    "degraded": False,
    "cross_check_model": "gemma-4-26b-a4b-it-maas",
}


def _body(**over):
    return {"image_base64": "eA==", "image_mime_type": "image/jpeg", "student_id": "c1_stu01", "name": "An", "class_id": "c1", **over}


def test_extract_image_returns_text_and_the_cross_check_model():
    with patch("eduagent.api.transcribe_essay_image", return_value=_OCR_OK):
        r = client.post("/api/debate/extract-image", headers=_STUDENT, json=_body())
    assert r.status_code == 200
    body = r.json()
    assert body["text"] == "Video games are great!"
    # ADR-028: this is the only place the Gemma signal appears in the two-step
    # flow -- the debate then starts via /api/debate/start (typed text), whose
    # response carries no `ocr` block at all.
    assert body["ocr"]["cross_check_model"] == "gemma-4-26b-a4b-it-maas"


def test_extract_image_requires_an_identity_in_the_payload():
    """Regression guard. The UI shipped calling this with only
    {image_base64, image_mime_type}; `student_id` is required, so every real
    click returned 422 and the handwriting demo was broken. A 422 here means
    the endpoint is doing its job -- the bug was in the caller."""
    with patch("eduagent.api.transcribe_essay_image", return_value=_OCR_OK):
        r = client.post("/api/debate/extract-image", headers=_STUDENT, json={"image_base64": "eA==", "image_mime_type": "image/jpeg"})
    assert r.status_code == 422
    assert any(e["loc"][-1] == "student_id" for e in r.json()["detail"])


def test_extract_image_refuses_an_anonymous_caller():
    """Each call fans out into Vertex requests, so an unauthenticated
    extraction endpoint is an unmetered spend channel (the ADR-018 finding)."""
    with patch("eduagent.api.transcribe_essay_image", return_value=_OCR_OK):
        r = client.post("/api/debate/extract-image", json=_body())
    assert r.status_code == 401


def test_extract_image_refuses_acting_as_another_student():
    with patch("eduagent.api.transcribe_essay_image", return_value=_OCR_OK) as ocr:
        r = client.post("/api/debate/extract-image", headers=_OTHER_STUDENT, json=_body())
    assert r.status_code == 403
    ocr.assert_not_called(), "authorization must be decided before any Vertex spend"


def test_extract_image_reports_a_degraded_transcription_honestly():
    """ADR-008: on a Vertex outage the transcription is EMPTY, never fabricated.
    The flags must survive to the client so the UI can explain the empty box
    instead of leaving the student guessing."""
    degraded = {"transcribed_text": "", "confidence": "unavailable", "uncertain_segments": [], "degraded": True, "cross_check_model": None}
    with patch("eduagent.api.transcribe_essay_image", return_value=degraded):
        r = client.post("/api/debate/extract-image", headers=_STUDENT, json=_body())
    assert r.status_code == 200
    assert r.json()["text"] == ""
    assert r.json()["ocr"]["degraded"] is True
    assert r.json()["ocr"]["confidence"] == "unavailable"


def test_extract_image_rejects_an_oversized_payload_before_calling_vertex():
    """The payload must be VALID base64, just too big. An earlier version of
    this test used "A" * 14_000_001, which is not a multiple of 4 -- b64decode
    raised binascii.Error (a ValueError subclass), the route mapped it to 400,
    and the test passed identically with the size cap deleted. It asserted
    base64 validation while claiming to assert the cap."""
    oversized = "QUFB" * 3_500_001  # 14,000,004 chars, decodes cleanly
    assert len(oversized) > 14_000_000
    with patch("eduagent.api.transcribe_essay_image") as ocr:
        r = client.post("/api/debate/extract-image", headers=_STUDENT, json=_body(image_base64=oversized))
    assert r.status_code == 400
    assert "too large" in r.json()["detail"].lower()
    ocr.assert_not_called(), "the cap must reject before any Vertex spend"


# --- /api/debate/extract-gdoc ----------------------------------------------

_GDOC = {"gdoc_url": "https://docs.google.com/document/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/edit",
         "student_id": "c1_stu01", "name": "An", "class_id": "c1"}


def test_extract_gdoc_returns_the_document_text():
    with patch("eduagent.integrations.gdocs.fetch_gdoc_text", return_value="Homework should be abolished."):
        r = client.post("/api/debate/extract-gdoc", headers=_STUDENT, json=_GDOC)
    assert r.status_code == 200
    assert r.json()["text"] == "Homework should be abolished."


def test_extract_gdoc_requires_an_identity_in_the_payload():
    """Same regression guard: the UI shipped sending only {gdoc_url}."""
    r = client.post("/api/debate/extract-gdoc", headers=_STUDENT, json={"gdoc_url": _GDOC["gdoc_url"]})
    assert r.status_code == 422


def test_extract_gdoc_maps_a_private_document_to_403_not_500():
    """A Doc that is not shared 'anyone with the link' is the single most likely
    user error on this path; it must read as 'your doc is private', not as a
    server fault."""
    with patch("eduagent.integrations.gdocs.fetch_gdoc_text", side_effect=PermissionError("Doc is private -- share as 'Anyone with the link'.")):
        r = client.post("/api/debate/extract-gdoc", headers=_STUDENT, json=_GDOC)
    assert r.status_code == 403
    assert "private" in r.json()["detail"].lower()


def test_extract_gdoc_maps_a_bad_url_to_400():
    with patch("eduagent.integrations.gdocs.fetch_gdoc_text", side_effect=ValueError("Not a valid Google Docs URL.")):
        r = client.post("/api/debate/extract-gdoc", headers=_STUDENT, json=_GDOC)
    assert r.status_code == 400


def test_extract_gdoc_refuses_an_anonymous_caller():
    with patch("eduagent.integrations.gdocs.fetch_gdoc_text", return_value="text") as fetch:
        r = client.post("/api/debate/extract-gdoc", json=_GDOC)
    assert r.status_code == 401
    fetch.assert_not_called()
