"""Tier-A coverage (Audit Wave 24): the route-level degrade branches.

Every teacher route wraps its call in `try/except -> HTTPException(503|502)`.
Those handlers are the difference between "Firestore is down, try again
shortly" and a raw 500 with a stack trace, but none of them had a test -- so
nothing would have caught one of them being removed, or leaking the exception
text of an internal failure to the client.
"""

from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient

from eduagent.auth import create_access_token
from eduagent.server import app

client = TestClient(app)
_TEACHER = {"Authorization": f"Bearer {create_access_token('c1_teacher', 'teacher', 'c1')}"}


def test_get_settings_returns_503_not_500_when_firestore_is_down():
    with patch("eduagent.server.get_settings", side_effect=RuntimeError("firestore unreachable")):
        r = client.get("/api/classes/c1/settings", headers=_TEACHER)
    assert r.status_code == 503
    assert "try again" in r.json()["detail"].lower()
    # The internal exception text must not reach the client.
    assert "unreachable" not in r.json()["detail"]


def test_update_settings_returns_503_not_500_when_firestore_is_down():
    with patch("eduagent.server.update_settings", side_effect=RuntimeError("firestore unreachable")):
        r = client.put("/api/classes/c1/settings", headers=_TEACHER, json={"stuck_streak_threshold": 4})
    assert r.status_code == 503
    assert "unreachable" not in r.json()["detail"]


def test_test_sheets_maps_a_missing_spreadsheet_id_to_400_not_502():
    """A missing ID is the caller's mistake (400); a Sheets API failure is
    ours/Google's (502). Collapsing both into one code would tell a teacher to
    'check server logs' when they simply left the field blank."""
    with patch("eduagent.server.test_sheets_connection", side_effect=ValueError("No Google Spreadsheet ID or URL provided or configured.")):
        r = client.post("/api/classes/c1/test-sheets", headers=_TEACHER, json={})
    assert r.status_code == 400
    assert "Spreadsheet ID" in r.json()["detail"]


def test_test_sheets_maps_an_api_failure_to_502():
    with patch("eduagent.server.test_sheets_connection", side_effect=RuntimeError("sheets 403")):
        r = client.post("/api/classes/c1/test-sheets", headers=_TEACHER, json={})
    assert r.status_code == 502
    assert "Sheets test failed" in r.json()["detail"]


def test_parent_note_maps_unknown_student_to_404_and_llm_failure_to_502():
    with patch("eduagent.server.parent_note", side_effect=ValueError("Unknown student_id 'ghost'")):
        r = client.post("/api/parent-note", headers=_TEACHER, json={"class_id": "c1", "student_id": "ghost"})
    assert r.status_code == 404

    with patch("eduagent.server.parent_note", side_effect=RuntimeError("vertex down")):
        r = client.post("/api/parent-note", headers=_TEACHER, json={"class_id": "c1", "student_id": "c1_stu01"})
    assert r.status_code == 502
    assert "vertex down" not in r.json()["detail"]


def test_a_malformed_bearer_token_is_401_not_500():
    r = client.get("/api/classes/c1/settings", headers={"Authorization": "Bearer not-a-real-token"})
    assert r.status_code == 401
