"""Unit tests for ĐỢT 3 #2's REST API additions to server.py (debate
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


def test_demo_page_served_at_root_and_slash_demo():
    for path in ("/", "/demo"):
        response = client.get(path)
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "eduagent" in response.text


def test_pubsub_push_still_works_on_post_root_despite_new_get_route():
    with patch("eduagent.server.process_event", new_callable=AsyncMock) as mock_process:
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
        response = client.post("/api/debate/start", json={"essay_text": "Cats are great.", "student_id": "s1"})

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
            json={"image_base64": base64.b64encode(b"fake").decode(), "student_id": "s1"},
        )

    assert response.status_code == 200
    assert response.json()["ocr"]["confidence"] == "high"
    mock_start.assert_called_once()


def test_api_debate_start_with_image_failure_returns_502():
    import base64

    with patch("eduagent.server.start_debate_from_image", side_effect=RuntimeError("boom")):
        response = client.post(
            "/api/debate/start-with-image",
            json={"image_base64": base64.b64encode(b"fake").decode(), "student_id": "s1"},
        )
    assert response.status_code == 502


def test_api_debate_start_failure_returns_502():
    with patch("eduagent.server.start_debate", side_effect=RuntimeError("boom")):
        response = client.post("/api/debate/start", json={"essay_text": "x", "student_id": "s1"})
    assert response.status_code == 502


def test_api_debate_turn_returns_next_turn():
    fake_result = {"turn": {"turn": 2, "persona": "skeptic", "question": "Why?", "student_response": "reply"}, "turn_number": 2, "completed": False}
    with patch("eduagent.server.submit_debate_turn", return_value=fake_result):
        response = client.post("/api/debate/turn", json={"session_id": "sess-1", "student_reply": "reply"})
    assert response.status_code == 200
    assert response.json() == fake_result


def test_api_debate_turn_unknown_session_returns_404():
    with patch("eduagent.server.submit_debate_turn", side_effect=UnknownSessionError("sess-x")):
        response = client.post("/api/debate/turn", json={"session_id": "sess-x", "student_reply": "reply"})
    assert response.status_code == 404


def test_api_debate_turn_already_complete_returns_409():
    with patch("eduagent.server.submit_debate_turn", side_effect=DebateSessionComplete("done")):
        response = client.post("/api/debate/turn", json={"session_id": "sess-1", "student_reply": "reply"})
    assert response.status_code == 409


def test_api_class_analytics_returns_digests():
    fake_digests = [{"digest_id": "e1", "ranked_students": [], "common_fallacies": [], "timestamp": "t1"}]
    with patch("eduagent.server.list_recent_digests", return_value=fake_digests) as mock_list:
        response = client.get("/api/classes/c1/analytics", headers=_C1_HEADERS)

    assert response.status_code == 200
    assert response.json() == {"class_id": "c1", "digests": fake_digests}
    mock_list.assert_called_once_with(class_id="c1", limit=10)


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

