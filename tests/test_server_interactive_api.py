"""Unit tests for the REST API additions to server.py (debate
start/turn, class analytics, demo page). Mocks the underlying business logic
-- same discipline as test_server.py -- these must not touch real Vertex
AI/Firestore."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from eduagent.api import DebateSessionComplete, UnknownSessionError
from eduagent.auth import create_access_token
from eduagent.server import app

client = TestClient(app)
_C1_HEADERS = {"Authorization": f"Bearer {create_access_token('c1_teacher', 'teacher', 'c1')}"}

# The debate endpoints now require a student (or same-class
# teacher) Bearer token, so every debate request below carries one.
_STUDENT_ID = "c1_stu01"
_STUDENT_HEADERS = {"Authorization": f"Bearer {create_access_token(_STUDENT_ID, 'student', 'c1')}"}
_SESSION = {"student_id": _STUDENT_ID, "class_id": "c1"}


def test_demo_page_served_at_root_and_slash_demo():
    for path in ("/", "/demo"):
        response = client.get(path)
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "eduagent" in response.text


def test_pubsub_push_still_works_on_post_root_despite_new_get_route():
    with patch("eduagent.server._verify_pubsub_push_auth", return_value=None), patch(
        "eduagent.server.process_event", new_callable=AsyncMock
    ) as mock_process:
        response = client.post("/", json={"message": {"data": "aGVsbG8="}})
    # Undecodable-as-JSON payload -- still handled by the existing push logic,
    # proving the new GET / route didn't shadow the POST / one.
    assert response.status_code == 200
    mock_process.assert_not_awaited()


def test_api_debate_start_returns_session_and_first_turn():
    fake_result = {
        "session_id": "sess-1",
        "persona_id": "skeptic",
        "persona_name": "The Skeptic",
        "language": "en",
        "summary": {"fallacies_draft": []},
        "summary_degraded": False,
        "turn": {"turn": 1, "persona": "skeptic", "question": "Where's your evidence?", "student_response": None},
        "turn_number": 1,
    }
    with patch("eduagent.server.start_debate", return_value=fake_result) as mock_start:
        response = client.post(
            "/api/debate/start",
            json={"essay_text": "Cats are great.", "student_id": _STUDENT_ID},
            headers=_STUDENT_HEADERS,
        )

    assert response.status_code == 200
    assert response.json() == fake_result
    mock_start.assert_called_once()


def test_api_debate_start_with_image_returns_session_with_ocr_meta():
    import base64

    fake_result = {
        "session_id": "sess-img-1",
        "persona_id": "nitpicker",
        "persona_name": "The Nitpicker",
        "language": "en",
        "summary": {"fallacies_draft": []},
        "summary_degraded": False,
        "turn": {"turn": 1, "persona": "nitpicker", "question": "Walk me through it.", "student_response": None},
        "turn_number": 1,
        "ocr": {"confidence": "high", "uncertain_segments": [], "degraded": False},
    }
    with patch("eduagent.server.start_debate_from_image", return_value=fake_result) as mock_start:
        response = client.post(
            "/api/debate/start-with-image",
            json={"image_base64": base64.b64encode(b"fake").decode(), "student_id": _STUDENT_ID},
            headers=_STUDENT_HEADERS,
        )

    assert response.status_code == 200
    assert response.json()["ocr"]["confidence"] == "high"
    mock_start.assert_called_once()


def test_api_debate_start_with_image_failure_returns_502():
    import base64

    with patch("eduagent.server.start_debate_from_image", side_effect=RuntimeError("boom")):
        response = client.post(
            "/api/debate/start-with-image",
            json={"image_base64": base64.b64encode(b"fake").decode(), "student_id": _STUDENT_ID},
            headers=_STUDENT_HEADERS,
        )
    assert response.status_code == 502


def test_api_debate_start_failure_returns_502():
    with patch("eduagent.server.start_debate", side_effect=RuntimeError("boom")):
        response = client.post(
            "/api/debate/start",
            json={"essay_text": "x", "student_id": _STUDENT_ID},
            headers=_STUDENT_HEADERS,
        )
    assert response.status_code == 502


def test_api_debate_turn_returns_next_turn():
    fake_result = {"turn": {"turn": 2, "persona": "skeptic", "question": "Why?", "student_response": "reply"}, "turn_number": 2, "completed": False}
    with patch("eduagent.server.get_debate_session", return_value=_SESSION), patch(
        "eduagent.server.submit_debate_turn", return_value=fake_result
    ):
        response = client.post(
            "/api/debate/turn",
            json={"session_id": "sess-1", "student_reply": "reply"},
            headers=_STUDENT_HEADERS,
        )
    assert response.status_code == 200
    assert response.json() == fake_result


def test_api_debate_turn_unknown_session_returns_404():
    with patch("eduagent.server.get_debate_session", side_effect=UnknownSessionError("sess-x")):
        response = client.post(
            "/api/debate/turn",
            json={"session_id": "sess-x", "student_reply": "reply"},
            headers=_STUDENT_HEADERS,
        )
    assert response.status_code == 404


def test_api_debate_turn_already_complete_returns_409():
    with patch("eduagent.server.get_debate_session", return_value=_SESSION), patch(
        "eduagent.server.submit_debate_turn", side_effect=DebateSessionComplete("done")
    ):
        response = client.post(
            "/api/debate/turn",
            json={"session_id": "sess-1", "student_reply": "reply"},
            headers=_STUDENT_HEADERS,
        )
    assert response.status_code == 409


def test_api_class_analytics_returns_digests():
    fake_digests = [{"digest_id": "e1", "ranked_students": [], "common_fallacies": [], "timestamp": "t1"}]
    with patch("eduagent.server.list_recent_digests", return_value=fake_digests) as mock_list:
        response = client.get("/api/classes/c1/analytics", headers=_C1_HEADERS)

    assert response.status_code == 200
    body = response.json()
    assert body["class_id"] == "c1"
    # Compares field-by-field rather than to `fake_digests`: the route enriches
    # the dicts the mock handed it IN PLACE, so an `== fake_digests` assertion
    # would stay green even if the enrichment were deleted -- the mock's own
    # object would have mutated alongside it. Asserted against literals instead.
    assert [d["digest_id"] for d in body["digests"]] == ["e1"]
    assert body["digests"][0]["timestamp"] == "t1"
    mock_list.assert_called_once_with(class_id="c1", limit=10)


def test_api_class_analytics_attaches_the_draft_body_as_digest_html():
    """A reader with no access to the system mailbox must still be
    able to read what the Gmail draft says. The preview is the draft body."""
    fake_digests = [
        {
            "digest_id": "e1",
            "digest_text": {
                "headline": "Binh needs attention.",
                "priority_students": [{"student_id": "stu_stuck", "why": "three flat essays"}],
                "class_wide_pattern": "hasty generalization",
                "mini_lesson_suggestion": "15-minute exercise",
            },
            "ranked_students": [{"student_id": "stu_stuck", "name": "Binh", "priority": 9.0, "reason": {}}],
            "common_fallacies": [],
            "gmail_draft_id": "r-123",
            "timestamp": "t1",
        }
    ]
    with patch("eduagent.server.list_recent_digests", return_value=fake_digests):
        response = client.get("/api/classes/c1/analytics", headers=_C1_HEADERS)

    html = response.json()["digests"][0]["digest_html"]
    assert "Binh needs attention." in html
    assert "three flat essays" in html
    assert "Binh (stu_stuck)" in html          # resolved from ranked_students, not re-guessed
    assert "15-minute exercise" in html


def test_api_class_analytics_survives_a_digest_it_cannot_render():
    """A doc written before a schema field existed must degrade to no preview,
    never take the whole Analytics tab down with a 500."""
    fake_digests = [{"digest_id": "old", "digest_text": {"headline": "h"}, "timestamp": "t1"}]
    with patch("eduagent.server.list_recent_digests", return_value=fake_digests):
        response = client.get("/api/classes/c1/analytics", headers=_C1_HEADERS)

    assert response.status_code == 200
    assert response.json()["digests"][0]["digest_html"] is None


def test_api_class_analytics_firestore_failure_returns_503():
    with patch("eduagent.server.list_recent_digests", side_effect=RuntimeError("boom")):
        response = client.get("/api/classes/c1/analytics", headers=_C1_HEADERS)
    assert response.status_code == 503


def test_api_class_students_returns_roster():
    fake_students = [{"student_id": "stu_1", "name": "An", "flags": {"last_updated": "t1"}}]
    with patch("eduagent.server.list_students_by_class", return_value=fake_students) as mock_list:
        response = client.get("/api/classes/c1/students", headers=_C1_HEADERS)

    assert response.status_code == 200
    assert response.json() == {"class_id": "c1", "students": fake_students}
    mock_list.assert_called_once_with("c1", limit=50)


def test_api_class_students_firestore_failure_returns_503():
    with patch("eduagent.server.list_students_by_class", side_effect=RuntimeError("boom")):
        response = client.get("/api/classes/c1/students", headers=_C1_HEADERS)
    assert response.status_code == 503


def test_api_get_sample_ocr_image_returns_base64():
    response = client.get("/api/demo/sample-ocr-image")
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "messy_essay_videogames.jpg"
    assert data["mime_type"] == "image/jpeg"
    assert len(data["image_base64"]) > 1000


