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

import copy
from unittest.mock import patch

import pytest

from eduagent import interactive
from eduagent.memory import firestore_session


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


def test_completion_leaves_the_session_in_a_terminal_reflection_only_state():
    """ĐỢT 15 #2 changed this: completion used to delete the session outright.

    It cannot, because the metacognitive reflection happens AFTER completion and
    is the only thing that proves a debate took place -- deleting the record here
    is exactly what forced /api/debate/reflect to trust the client. So the
    session survives, flagged `completed`, and it must be genuinely terminal:
    no further turn may be taken on it.
    """
    sid = _start_session("sess-p7")
    with patch("eduagent.interactive.score_essay", return_value=_GOOD_SCORE):
        interactive.complete_debate_session(
            sid, persist_essay_result=lambda **kw: None, publish_event=lambda **kw: None, run_publish_in_thread=False
        )

    session = interactive.get_debate_session(sid)
    assert session["completed"] is True
    assert session["completed_at"]
    assert not session.get("has_reflected")

    with pytest.raises(interactive.DebateSessionComplete):
        interactive.step_debate_turn(sid, "one more?")


def test_claim_reflection_is_single_use():
    """The score-farming guard: one finished debate, one growth bonus."""
    sid = _start_session("sess-p8")
    with patch("eduagent.interactive.score_essay", return_value=_GOOD_SCORE):
        interactive.complete_debate_session(
            sid, persist_essay_result=lambda **kw: None, publish_event=lambda **kw: None, run_publish_in_thread=False
        )

    claimed = interactive.claim_reflection(sid)
    assert claimed["student_id"] == "c1_stu01"
    assert claimed["has_reflected"] is True

    with pytest.raises(interactive.ReflectionAlreadySubmitted):
        interactive.claim_reflection(sid)


def test_claim_reflection_rejects_an_unfinished_debate():
    sid = _start_session("sess-p9")
    with pytest.raises(interactive.DebateNotComplete):
        interactive.claim_reflection(sid)


def test_default_seams_are_offline_under_pytest():
    """Guards the offline-by-default property: a test that forgets to inject
    must not reach real Firestore/Pub/Sub."""
    # Neither call raises and neither touches GCP, because PYTEST_CURRENT_TEST is set.
    interactive._default_persist_essay_result(student_id="x")
    interactive._default_publish_event(event_id="x")


# ---------------------------------------------------------------------------
# ĐỢT 17 #2 -- multi-instance regression AT THE interactive LAYER.
#
# tests/test_firestore_session.py already has a two-instance test, but it drives
# firestore_session.load_session() directly -- the inner tier, which owns the 3s
# freshness bound and was never the broken one. Every real request goes through
# interactive.get_debate_session(), the OUTER tier, which had no freshness bound
# at all and shadowed the inner one. That gap is why a green suite coexisted with
# ADR-015 being false on the live read path.
# ---------------------------------------------------------------------------


class _FakeDoc:
    def __init__(self, store, doc_id):
        self._store, self._id = store, doc_id

    @property
    def exists(self):
        return self._id in self._store

    def to_dict(self):
        value = self._store.get(self._id)
        return copy.deepcopy(value) if value is not None else None

    def get(self, transaction=None):
        return self

    def set(self, payload):
        self._store[self._id] = copy.deepcopy(payload)

    def update(self, changes):
        merged = copy.deepcopy(self._store[self._id])
        merged.update(copy.deepcopy(changes))
        self._store[self._id] = merged

    def delete(self):
        self._store.pop(self._id, None)


class _FakeCollection:
    def __init__(self, store):
        self._store = store

    def document(self, doc_id):
        return _FakeDoc(self._store, doc_id)


class _SharedFirestore:
    """The one thing genuinely shared between Cloud Run instances."""

    def __init__(self):
        self.store = {}

    def collection(self, name):
        assert name == "debate_sessions"
        return _FakeCollection(self.store)


@pytest.fixture
def shared_db(monkeypatch):
    db = _SharedFirestore()
    monkeypatch.setattr(firestore_session, "_default_client", lambda: db)
    interactive._sessions.clear()
    firestore_session._LOCAL_SESSION_CACHE.clear()
    yield db
    interactive._sessions.clear()
    firestore_session._LOCAL_SESSION_CACHE.clear()


def _start(session_id):
    interactive.start_debate_session(
        session_id,
        persona_id="skeptic",
        essay_text="E",
        summary={"fallacies_draft": ["hasty generalization"]},
        prior_weaknesses=[],
        language="en",
        student_id="c1_stu01",
        name="An",
        class_id="c1",
    )


def test_interactive_layer_does_not_serve_a_stale_session_to_a_warm_instance(shared_db):
    """ĐỢT 17 #2: instance A keeps its dict warm across requests. When the load
    balancer sends a later turn back to A, A must not serve the copy it made
    before instance B wrote to Firestore."""
    _start("s-multi")
    instance_a_memory = copy.deepcopy(interactive._sessions)

    # --- instance B: fresh process, reads from Firestore, appends a turn ---
    interactive._sessions.clear()
    firestore_session._LOCAL_SESSION_CACHE.clear()
    session_b = interactive.get_debate_session("s-multi")
    session_b["turns"].append({"turn": 2, "question": "written by instance B"})
    firestore_session.save_session("s-multi", session_b)

    # --- load balancer routes the next request back to instance A ---
    interactive._sessions.clear()
    interactive._sessions.update(instance_a_memory)
    firestore_session._LOCAL_SESSION_CACHE.clear()

    session_a = interactive.get_debate_session("s-multi")

    assert [t["turn"] for t in session_a["turns"]] == [2], (
        "instance A served its stale in-process copy and lost instance B's turn "
        "-- ADR-015 regressed at the interactive layer"
    )


def test_a_session_deleted_by_another_instance_is_not_resurrected(shared_db):
    """The flip side: preferring Firestore must not mean falling back to a warm
    local dict when Firestore authoritatively says the session is gone. That
    would undo ADR-022's single-use reflection teardown across instances."""
    _start("s-gone")
    instance_a_memory = copy.deepcopy(interactive._sessions)

    # instance B ends the debate (ADR-022 teardown after reflection)
    interactive.end_debate_session("s-gone")
    assert "s-gone" not in shared_db.store

    # instance A still has it warm in memory
    interactive._sessions.clear()
    interactive._sessions.update(instance_a_memory)
    firestore_session._LOCAL_SESSION_CACHE.clear()

    with pytest.raises(interactive.UnknownSessionError):
        interactive.get_debate_session("s-gone")

    # and the stale local copy is dropped rather than left to be found later
    assert "s-gone" not in interactive._sessions


def test_without_a_durable_store_the_in_process_dict_still_serves(monkeypatch):
    """Local runs and pytest have no Firestore client; the dict IS the store
    there, and must keep working -- otherwise this fix would break every
    laptop demo to close a multi-instance bug."""
    monkeypatch.setattr(firestore_session, "_default_client", lambda: None)
    interactive._sessions.clear()
    firestore_session._LOCAL_SESSION_CACHE.clear()

    _start("s-local")
    assert interactive.get_debate_session("s-local")["student_id"] == "c1_stu01"
