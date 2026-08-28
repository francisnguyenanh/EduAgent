"""Unit tests for Wave 4 #3 Parent Communication Co-Pilot (parent_note.py).
Mocks generate_text -- must never touch real Vertex AI."""

from __future__ import annotations

from unittest.mock import patch

from eduagent.llm import LLMGenerationError
from eduagent.skills.parent_note import draft_parent_note


def test_draft_parent_note_returns_llm_text_when_available():
    reason = {"stuck_streak_count": 3, "score_trend": "stagnant", "inactivity_days": 0, "shared_fallacies": []}
    with patch("eduagent.skills.parent_note.generate_text", return_value="A warm note about Mai.") as mock_gen:
        note, degraded = draft_parent_note(student_name="Mai", reason=reason)
    assert note == "A warm note about Mai."
    assert degraded is False
    mock_gen.assert_called_once()


def test_draft_parent_note_falls_back_when_llm_fails():
    reason = {"stuck_streak_count": 0, "score_trend": "declining", "inactivity_days": 0, "shared_fallacies": []}
    with patch("eduagent.skills.parent_note.generate_text", side_effect=LLMGenerationError("boom")):
        note, degraded = draft_parent_note(student_name="Binh", reason=reason)
    assert "Binh" in note
    assert degraded is True


def test_draft_parent_note_never_mentions_priority_in_fallback():
    reason = {"stuck_streak_count": 0, "score_trend": "insufficient_data", "inactivity_days": 0, "shared_fallacies": []}
    with patch("eduagent.skills.parent_note.generate_text", side_effect=LLMGenerationError("boom")):
        note, _ = draft_parent_note(student_name="Chi", reason=reason)
    assert "priority" not in note.lower()
