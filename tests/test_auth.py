"""Unit tests for the mock role-based login (auth.py) -- zero network/LLM calls."""

from __future__ import annotations

import pytest

from eduagent.auth import LoginError, LoginRequest, login, split_class_id


def test_split_class_id_splits_on_first_underscore():
    assert split_class_id("c1_stu01") == ("c1", "stu01")


def test_split_class_id_uses_only_first_underscore():
    assert split_class_id("12A1_Nguyen_An") == ("12A1", "Nguyen_An")


def test_split_class_id_rejects_missing_underscore():
    with pytest.raises(LoginError):
        split_class_id("stu01")


def test_split_class_id_rejects_leading_underscore():
    with pytest.raises(LoginError):
        split_class_id("_stu01")


def test_login_succeeds_with_correct_password(monkeypatch):
    monkeypatch.setattr("eduagent.auth._MOCK_PASSWORD", "eduagent2026")
    result = login(LoginRequest(role="student", user_id="c1_stu01", password="eduagent2026"))
    assert result.role == "student"
    assert result.class_id == "c1"
    assert result.user_id == "c1_stu01"
    assert result.display_name == "stu01"


def test_login_rejects_wrong_password(monkeypatch):
    monkeypatch.setattr("eduagent.auth._MOCK_PASSWORD", "eduagent2026")
    with pytest.raises(LoginError):
        login(LoginRequest(role="teacher", user_id="c1_teacher", password="wrong"))


def test_login_rejects_unknown_role(monkeypatch):
    monkeypatch.setattr("eduagent.auth._MOCK_PASSWORD", "eduagent2026")
    with pytest.raises(LoginError):
        login(LoginRequest(role="admin", user_id="c1_teacher", password="eduagent2026"))


def test_login_succeeds_for_teacher(monkeypatch):
    monkeypatch.setattr("eduagent.auth._MOCK_PASSWORD", "eduagent2026")
    result = login(LoginRequest(role="teacher", user_id="c1_teacher", password="eduagent2026"))
    assert result.role == "teacher"
    assert result.class_id == "c1"
    assert result.user_id == "c1_teacher"


def test_login_rejects_student_account_on_teacher_portal(monkeypatch):
    monkeypatch.setattr("eduagent.auth._MOCK_PASSWORD", "eduagent2026")
    with pytest.raises(LoginError, match="student account"):
        login(LoginRequest(role="teacher", user_id="c1_stu02", password="eduagent2026"))


def test_login_rejects_teacher_account_on_student_portal(monkeypatch):
    monkeypatch.setattr("eduagent.auth._MOCK_PASSWORD", "eduagent2026")
    with pytest.raises(LoginError, match="teacher account"):
        login(LoginRequest(role="student", user_id="c1_teacher", password="eduagent2026"))

