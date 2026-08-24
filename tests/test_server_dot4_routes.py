from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient

from eduagent.auth import create_access_token
from eduagent.server import app

client = TestClient(app)
_C1_HEADERS = {"Authorization": f"Bearer {create_access_token('c1_teacher', 'teacher', 'c1')}"}


def test_login_route_returns_200_and_identity(monkeypatch):
    monkeypatch.setattr("eduagent.auth._MOCK_PASSWORD", "eduagent2026")
    response = client.post("/api/auth/login", json={"role": "student", "user_id": "c1_stu01", "password": "eduagent2026"})
    assert response.status_code == 200
    body = response.json()
    assert body["class_id"] == "c1"
    assert body["role"] == "student"
    assert "token" in body
    assert len(body["token"]) > 10


def test_login_route_returns_401_for_wrong_password(monkeypatch):
    monkeypatch.setattr("eduagent.auth._MOCK_PASSWORD", "eduagent2026")
    response = client.post("/api/auth/login", json={"role": "teacher", "user_id": "c1_teacher", "password": "wrong"})
    assert response.status_code == 401


def test_priority_route_returns_ranking():
    with patch("eduagent.server.class_priority", return_value={"class_id": "c1", "ranking": []}):
        response = client.get("/api/classes/c1/priority", headers=_C1_HEADERS)
    assert response.status_code == 200
    assert response.json() == {"class_id": "c1", "ranking": []}


def test_priority_route_returns_503_on_firestore_error():
    with patch("eduagent.server.class_priority", side_effect=RuntimeError("boom")):
        response = client.get("/api/classes/c1/priority", headers=_C1_HEADERS)
    assert response.status_code == 503


def test_settings_get_and_put_routes():
    with patch("eduagent.server.get_settings", return_value={"class_id": "c1", "settings": {}}):
        get_resp = client.get("/api/classes/c1/settings", headers=_C1_HEADERS)
    assert get_resp.status_code == 200

    with patch("eduagent.server.update_settings", return_value={"class_id": "c1", "settings": {"stuck_streak_threshold": 5}}) as mock_update:
        put_resp = client.put("/api/classes/c1/settings", json={"stuck_streak_threshold": 5}, headers=_C1_HEADERS)
    assert put_resp.status_code == 200
    mock_update.assert_called_once()


def test_parent_note_route_returns_404_for_unknown_student():
    with patch("eduagent.server.parent_note", side_effect=ValueError("No profile found")):
        response = client.post("/api/parent-note", json={"class_id": "c1", "student_id": "ghost"}, headers=_C1_HEADERS)
    assert response.status_code == 404


def test_parent_note_route_returns_note():
    with patch("eduagent.server.parent_note", return_value={"student_id": "s1", "note": "Hi", "degraded": False, "priority": {}}):
        response = client.post("/api/parent-note", json={"class_id": "c1", "student_id": "s1"}, headers=_C1_HEADERS)
    assert response.status_code == 200
    assert response.json()["note"] == "Hi"

