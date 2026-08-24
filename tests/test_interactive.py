"""Unit tests for the Interactive Debate Step Helper (interactive.py).

Mocks eduagent.nodes.debate.generate_text (the only network call inside
generate_debate_turn) so this suite runs fast and offline -- same pattern as
test_class_aggregator.py mocking synthesize_digest/Gmail/Sheets.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from eduagent import interactive
from eduagent.config import VALIDATOR


@pytest.fixture(autouse=True)
def _clean_sessions():
    interactive._sessions.clear()
    yield
    interactive._sessions.clear()


def test_start_and_step_first_turn_needs_no_reply():
    interactive.start_debate_session(
        "s1", persona_id="skeptic", essay_text="Homework is bad.", summary={"main_claim": "Homework is bad."}
    )
    with patch("eduagent.nodes.debate.generate_text", return_value="What evidence supports that claim?"):
        turn = interactive.step_debate_turn("s1")

    assert turn["turn"] == 1
    assert turn["persona"] == "skeptic"
    assert turn["student_response"] is None


def test_step_turn_two_requires_student_reply():
    interactive.start_debate_session("s2", persona_id="skeptic", essay_text="Homework is bad.", summary={})
    with patch("eduagent.nodes.debate.generate_text", return_value="What evidence supports that claim?"):
        interactive.step_debate_turn("s2")
        with pytest.raises(ValueError):
            interactive.step_debate_turn("s2", student_reply=None)


def test_step_turn_two_uses_prior_reply():
    interactive.start_debate_session("s3", persona_id="skeptic", essay_text="Homework is bad.", summary={})
    with patch("eduagent.nodes.debate.generate_text", return_value="What evidence supports that claim?"):
        interactive.step_debate_turn("s3")
        turn2 = interactive.step_debate_turn("s3", student_reply="Because my cousin said so.")

    assert turn2["turn"] == 2
    assert turn2["student_response"] == "Because my cousin said so."


def test_unknown_session_raises():
    with pytest.raises(interactive.UnknownSessionError):
        interactive.step_debate_turn("nonexistent")


def test_session_stops_at_max_turns():
    interactive.start_debate_session("s4", persona_id="skeptic", essay_text="Homework is bad.", summary={})
    with patch("eduagent.nodes.debate.generate_text", return_value="What evidence supports that claim?"):
        for turn_number in range(1, VALIDATOR.max_debate_turns + 1):
            reply = "some reply" if turn_number > 1 else None
            interactive.step_debate_turn("s4", student_reply=reply)
        with pytest.raises(interactive.DebateSessionComplete):
            interactive.step_debate_turn("s4", student_reply="one more reply")


def test_session_language_defaults_to_detected_language():
    interactive.start_debate_session(
        "s5", persona_id="skeptic", essay_text="Học sinh không nên có bài tập về nhà.", summary={}
    )
    assert interactive.get_debate_session("s5")["language"] == "vi"


def test_end_debate_session_removes_it():
    interactive.start_debate_session("s6", persona_id="skeptic", essay_text="Homework is bad.", summary={})
    interactive.end_debate_session("s6")
    with pytest.raises(interactive.UnknownSessionError):
        interactive.get_debate_session("s6")
