"""Unit tests for src/eduagent/api.py's interactive-debate orchestration
(ĐỢT 3 #2). Mocks summarize_essay/get_profile (start_debate's own concerns)
and eduagent.nodes.debate.generate_text (the only network call underneath
step_debate_turn, same pattern as test_interactive.py) -- must never touch
real Vertex AI/Firestore."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from eduagent import interactive
from eduagent.api import (
    DebateStartFromGDocRequest,
    DebateStartFromImageRequest,
    DebateStartRequest,
    DebateTurnRequest,
    start_debate,
    start_debate_from_gdoc,
    start_debate_from_image,
    submit_debate_turn,
)


@pytest.fixture(autouse=True)
def _clean_sessions():
    interactive._sessions.clear()
    yield
    interactive._sessions.clear()


def test_start_debate_returns_session_with_first_turn():
    payload = DebateStartRequest(essay_text="Cats are great pets.", student_id="s1", name="An", class_id="c1")
    with (
        patch("eduagent.api.summarize_essay", return_value=({"fallacies_draft": ["hasty generalization"]}, False)),
        patch("eduagent.api.get_profile", return_value=None),
        patch("eduagent.nodes.debate.generate_text", return_value="Why do you believe that?"),
    ):
        result = start_debate(payload)

    assert result["turn_number"] == 1
    assert result["turn"]["question"] == "Why do you believe that?"
    assert result["language"] == "en"
    assert "session_id" in result


def test_start_debate_degrades_gracefully_when_profile_lookup_fails():
    payload = DebateStartRequest(essay_text="Cats are great.", student_id="s1")
    with (
        patch("eduagent.api.summarize_essay", return_value=({"fallacies_draft": []}, False)),
        patch("eduagent.api.get_profile", side_effect=RuntimeError("firestore down")),
        patch("eduagent.nodes.debate.generate_text", return_value="Why?"),
    ):
        result = start_debate(payload)

    assert "session_id" in result  # did not crash despite the profile lookup failing


def test_submit_debate_turn_marks_complete_at_max_turns():
    payload_start = DebateStartRequest(essay_text="x", student_id="s1")
    with (
        patch("eduagent.api.summarize_essay", return_value=({"fallacies_draft": []}, False)),
        patch("eduagent.api.get_profile", return_value=None),
        patch("eduagent.nodes.debate.generate_text", return_value="Q1"),
    ):
        started = start_debate(payload_start)
    session_id = started["session_id"]

    with patch("eduagent.nodes.debate.generate_text", return_value="Q2"):
        turn2 = submit_debate_turn(DebateTurnRequest(session_id=session_id, student_reply="r1"))
    assert turn2["turn_number"] == 2
    assert turn2["completed"] is False

    with patch("eduagent.nodes.debate.generate_text", return_value="Q3"):
        turn3 = submit_debate_turn(DebateTurnRequest(session_id=session_id, student_reply="r2"))
    assert turn3["turn_number"] == 3
    assert turn3["completed"] is False

    scored = {
        "scores": {"logical_coherence": 5, "evidence_quality": 5, "counterargument_handling": 5, "scope_awareness": 5},
        "rationale": {"logical_coherence": "", "evidence_quality": "", "counterargument_handling": "", "scope_awareness": ""},
        "student_feedback": "Good effort overall.",
    }
    with (
        patch("eduagent.nodes.scorer.generate_json", return_value=scored),
        patch("eduagent.api.get_class_settings", return_value={"show_score_radar_to_students": True}),
    ):
        turn_finish = submit_debate_turn(DebateTurnRequest(session_id=session_id, student_reply="r3"))
    assert turn_finish["turn_number"] == 3
    assert turn_finish["completed"] is True
    assert turn_finish["result"]["student_feedback"] == "Good effort overall."
    assert turn_finish["result"]["show_score_radar"] is True
    assert turn_finish["result"]["scores"]["logical_coherence"] == 5

    # complete_debate_session already ran inside submit_debate_turn on completion --
    # the session should no longer be reachable.
    with pytest.raises(interactive.UnknownSessionError):
        interactive.get_debate_session(session_id)


def test_submit_debate_turn_hides_scores_when_radar_disabled():
    payload_start = DebateStartRequest(essay_text="x", student_id="s1", class_id="c1")
    with (
        patch("eduagent.api.summarize_essay", return_value=({"fallacies_draft": []}, False)),
        patch("eduagent.api.get_profile", return_value=None),
        patch("eduagent.nodes.debate.generate_text", return_value="Q1"),
    ):
        started = start_debate(payload_start)
    session_id = started["session_id"]

    scored = {
        "scores": {"logical_coherence": 5, "evidence_quality": 5, "counterargument_handling": 5, "scope_awareness": 5},
        "rationale": {"logical_coherence": "", "evidence_quality": "", "counterargument_handling": "", "scope_awareness": ""},
        "student_feedback": "Keep it up.",
    }
    with (
        patch("eduagent.nodes.debate.generate_text", return_value="Q2"),
        patch("eduagent.nodes.scorer.generate_json", return_value=scored),
        patch("eduagent.api.get_class_settings", return_value={"show_score_radar_to_students": False}),
    ):
        submit_debate_turn(DebateTurnRequest(session_id=session_id, student_reply="r1"))
        with patch("eduagent.nodes.debate.generate_text", return_value="Q3"):
            submit_debate_turn(DebateTurnRequest(session_id=session_id, student_reply="r2"))
        turn_finish = submit_debate_turn(DebateTurnRequest(session_id=session_id, student_reply="r3"))

    assert turn_finish["result"]["show_score_radar"] is False
    assert "scores" not in turn_finish["result"]
    assert turn_finish["result"]["student_feedback"] == "Keep it up."



def test_start_debate_from_image_transcribes_then_starts_debate():
    import base64

    payload = DebateStartFromImageRequest(image_base64=base64.b64encode(b"fake-jpeg-bytes").decode(), student_id="s1")
    with (
        patch(
            "eduagent.api.transcribe_essay_image",
            return_value={"transcribed_text": "Cats are great pets.", "confidence": "high", "uncertain_segments": [], "degraded": False},
        ) as mock_transcribe,
        patch("eduagent.api.summarize_essay", return_value=({"fallacies_draft": []}, False)),
        patch("eduagent.api.get_profile", return_value=None),
        patch("eduagent.nodes.debate.generate_text", return_value="Why do you believe that?"),
    ):
        result = start_debate_from_image(payload)

    mock_transcribe.assert_called_once()
    assert result["ocr"]["confidence"] == "high"
    assert result["turn"]["question"] == "Why do you believe that?"
    assert "session_id" in result


def test_start_debate_from_image_still_starts_on_low_confidence():
    import base64

    payload = DebateStartFromImageRequest(image_base64=base64.b64encode(b"blurry").decode(), student_id="s1")
    with (
        patch(
            "eduagent.api.transcribe_essay_image",
            return_value={"transcribed_text": "", "confidence": "unavailable", "uncertain_segments": [], "degraded": True},
        ),
        patch("eduagent.api.summarize_essay", return_value=({"fallacies_draft": []}, False)),
        patch("eduagent.api.get_profile", return_value=None),
        patch("eduagent.nodes.debate.generate_text", return_value="What evidence do you have?"),
    ):
        result = start_debate_from_image(payload)

    assert result["ocr"]["degraded"] is True
    assert "session_id" in result  # still usable, just flagged for the caller to warn about


def test_start_debate_from_gdoc_fetches_text_and_starts_debate():
    payload = DebateStartFromGDocRequest(
        gdoc_url="https://docs.google.com/document/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/edit",
        student_id="s1",
    )
    with (
        patch("eduagent.integrations.gdocs.fetch_gdoc_text", return_value="AI is transforming education.") as mock_fetch,
        patch("eduagent.api.summarize_essay", return_value=({"fallacies_draft": []}, False)),
        patch("eduagent.api.get_profile", return_value=None),
        patch("eduagent.nodes.debate.generate_text", return_value="What role should teachers play?"),
    ):
        result = start_debate_from_gdoc(payload)

    mock_fetch.assert_called_once()
    assert result["gdoc"]["doc_id"] == "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"
    assert result["gdoc"]["char_count"] == len("AI is transforming education.")
    assert result["turn"]["question"] == "What role should teachers play?"
    assert "session_id" in result
