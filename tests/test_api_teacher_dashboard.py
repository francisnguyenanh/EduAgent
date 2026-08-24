"""Unit tests for ĐỢT 4 #2/#3 teacher-dashboard API functions: class_priority,
get_settings/update_settings, parent_note. Mocks Firestore-backed calls and
the LLM call underneath draft_parent_note -- must never touch real GCP."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from eduagent.api import ClassSettingsRequest, ParentNoteRequest, class_priority, get_settings, parent_note, update_settings


def test_class_priority_ranks_students():
    profiles = {
        "s1": {"name": "Mai", "persona_streak": {"times_repeated_without_improvement": 0}, "score_trend": "improving", "essay_history": [], "weakness_taxonomy": {}},
        "s2": {"name": "Binh", "persona_streak": {"times_repeated_without_improvement": 4}, "score_trend": "stagnant", "essay_history": [], "weakness_taxonomy": {}},
    }
    with patch("eduagent.aggregator.class_aggregator.load_class_profiles", return_value=profiles):
        result = class_priority("c1")
    assert result["class_id"] == "c1"
    assert result["ranking"][0]["student_id"] == "s2"  # higher stuck streak -> ranked first


def test_get_settings_returns_defaults_when_none_saved():
    with patch("eduagent.api.get_class_settings", return_value={"show_score_radar_to_students": True, "stuck_streak_threshold": 3, "digest_notify_email": ""}):
        result = get_settings("c1")
    assert result["settings"]["stuck_streak_threshold"] == 3


def test_update_settings_only_sends_non_none_fields():
    with patch("eduagent.api.set_class_settings", return_value={"stuck_streak_threshold": 5}) as mock_set:
        update_settings("c1", ClassSettingsRequest(stuck_streak_threshold=5))
    mock_set.assert_called_once_with(class_id="c1", settings={"stuck_streak_threshold": 5})


def test_parent_note_raises_value_error_for_unknown_student():
    with patch("eduagent.api.get_profile", return_value=None):
        with pytest.raises(ValueError):
            parent_note(ParentNoteRequest(class_id="c1", student_id="ghost"))


def test_parent_note_returns_note_and_priority():
    profile = {"name": "Mai", "persona_streak": {"times_repeated_without_improvement": 3}, "score_trend": "stagnant", "essay_history": [], "weakness_taxonomy": {}}
    with (
        patch("eduagent.api.get_profile", return_value=profile),
        patch("eduagent.aggregator.class_aggregator.load_class_profiles", return_value={"s1": profile}),
        patch("eduagent.api.draft_parent_note", return_value=("Note text", False)),
    ):
        result = parent_note(ParentNoteRequest(class_id="c1", student_id="s1"))
    assert result["note"] == "Note text"
    assert result["degraded"] is False
    assert "priority" in result
