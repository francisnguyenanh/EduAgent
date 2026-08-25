"""ĐỢT 12 NHÓM 4 -- tests for the interactive debate's write-back path.

The audit's finding: `interactive.complete_debate_session()` wrapped its
Firestore write and Pub/Sub publish in `... and not os.getenv(
"PYTEST_CURRENT_TEST")`. That does not merely keep tests offline -- it makes the
code unreachable from any test. So the feature ĐỢT 9 declared "fixed" (wiring
the live web debate into Firestore + Pub/Sub) had no test behind it at all, and
the headline "190/190 passed" carried no information about it.

The env-var switch has been replaced by injectable seams, so these tests assert
the write really happens, with the right payload, and that it is correctly
SKIPPED when the score is degraded.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from eduagent import interactive


@pytest.fixture(autouse=True)
def _clean_sessions():
    interactive._sessions.clear()
    yield
    interactive._sessions.clear()


def _start_session(session_id="sess-p1", student_id="c1_stu01"):
    interactive.start_debate_session(
        session_id,
        persona_id="skeptic",
        essay_text="Video games cause bad grades.",
        summary={"fallacies_draft": ["hasty generalization"], "main_claim": "x"},
        prior_weaknesses=[],
        language="en",
        student_id=student_id,
        class_id="c1",
    )
    interactive.get_debate_session(session_id)["turns"] = [
        {"turn": 1, "persona": "skeptic", "question": "Evidence?", "student_response": "None really."}
    ]
    return session_id


_GOOD_SCORE = (
    {"logical_coherence": 4, "evidence_quality": 2, "counterargument_handling": 3, "scope_awareness": 5},
    {"logical_coherence": "r", "evidence_quality": "r", "counterargument_handling": "r", "scope_awareness": "r"},
    "Nice effort.",
    False,  # degraded
)
_DEGRADED_SCORE = ({}, {}, "", True)


def test_completion_persists_the_essay_result_with_the_expected_payload():
    sid = _start_session()
    persisted: list[dict] = []
    published: list[dict] = []

    with patch("eduagent.interactive.score_essay", return_value=_GOOD_SCORE):
        interactive.complete_debate_session(
            sid,
            persist_essay_result=lambda **kw: persisted.append(kw),
            publish_event=lambda **kw: published.append(kw),
            run_publish_in_thread=False,
        )

    assert len(persisted) == 1, "the interactive debate did not write back to the profile store"
    call = persisted[0]
    assert call["student_id"] == "c1_stu01"
    assert call["class_id"] == "c1"
    assert call["essay_id"] == sid
    assert call["persona_used"] == "skeptic"
    assert call["scores"]["evidence_quality"] == 2
    assert call["weakness_detected"] == ["hasty generalization"]
    assert call["student_feedback"] == "Nice effort."
    assert call["timestamp"]


def test_completion_publishes_the_pubsub_event_that_triggers_tier_2():
    sid = _start_session("sess-p2")
    published: list[dict] = []

    with patch("eduagent.interactive.score_essay", return_value=_GOOD_SCORE):
        interactive.complete_debate_session(
            sid,
            persist_essay_result=lambda **kw: None,
            publish_event=lambda **kw: published.append(kw),
            run_publish_in_thread=False,
        )

    assert len(published) == 1, "no essay.evaluated event was published, so Tier 2 would never run"
    event = published[0]
    # event_id doubles as the idempotency key the aggregator dedupes on.
    assert event["event_id"] == sid
    assert event["essay_id"] == sid
    assert event["student_id"] == "c1_stu01"
    assert event["class_id"] == "c1"


def test_degraded_score_is_never_persisted():
    """A fabricated 0 would corrupt score_trend and mark the student as
    declining because Gemini was down, not because their work got worse."""
    sid = _start_session("sess-p3")
    persisted: list[dict] = []
    published: list[dict] = []

    with patch("eduagent.interactive.score_essay", return_value=_DEGRADED_SCORE):
        result = interactive.complete_debate_session(
            sid,
            persist_essay_result=lambda **kw: persisted.append(kw),
            publish_event=lambda **kw: published.append(kw),
            run_publish_in_thread=False,
        )

    assert persisted == []
    assert published == []
    assert result["degraded"] is True


def test_anonymous_session_is_not_persisted():
    sid = _start_session("sess-p4", student_id="")
    persisted: list[dict] = []

    with patch("eduagent.interactive.score_essay", return_value=_GOOD_SCORE):
        interactive.complete_debate_session(
            sid,
            persist_essay_result=lambda **kw: persisted.append(kw),
            publish_event=lambda **kw: None,
            run_publish_in_thread=False,
        )

    assert persisted == []


def test_publish_failure_does_not_lose_the_persisted_result():
    """Firestore is the durable record; a Pub/Sub hiccup must not roll it back or
    surface as an error to the student."""
    sid = _start_session("sess-p5")
    persisted: list[dict] = []

    def _boom(**_kw):
        raise RuntimeError("pubsub down")

    with patch("eduagent.interactive.score_essay", return_value=_GOOD_SCORE):
        result = interactive.complete_debate_session(
            sid,
            persist_essay_result=lambda **kw: persisted.append(kw),
            publish_event=_boom,
            run_publish_in_thread=False,
        )

    assert len(persisted) == 1
    assert result["student_feedback"] == "Nice effort."


def test_persist_failure_still_returns_feedback_to_the_student():
    sid = _start_session("sess-p6")

    def _boom(**_kw):
        raise RuntimeError("firestore down")

    with patch("eduagent.interactive.score_essay", return_value=_GOOD_SCORE):
        result = interactive.complete_debate_session(
            sid, persist_essay_result=_boom, publish_event=lambda **kw: None, run_publish_in_thread=False
        )

    assert result["student_feedback"] == "Nice effort."
    assert result["degraded"] is False


def test_completion_tears_the_session_down():
    sid = _start_session("sess-p7")
    with patch("eduagent.interactive.score_essay", return_value=_GOOD_SCORE):
        interactive.complete_debate_session(
            sid, persist_essay_result=lambda **kw: None, publish_event=lambda **kw: None, run_publish_in_thread=False
        )
    with pytest.raises(interactive.UnknownSessionError):
        interactive.get_debate_session(sid)


def test_default_seams_are_offline_under_pytest():
    """Guards the offline-by-default property: a test that forgets to inject
    must not reach real Firestore/Pub/Sub."""
    # Neither call raises and neither touches GCP, because PYTEST_CURRENT_TEST is set.
    interactive._default_persist_essay_result(student_id="x")
    interactive._default_publish_event(event_id="x")
