"""Interactive Debate Step Helper -- one Socratic turn per call, without
re-running the whole Tier 1 ADK2 graph from intake onward.

PHASE 1 noted a real limitation: the graph runs as a single batch call per
essay because `Workflow.node_input` only accepts the essay text once, and
true interrupt/resume (`RequestInput`) needs a Web UI/API to pause on. This
module is the pragmatic bridge until that lands: intake -> sanitizer ->
summarizer -> persona_selector still run ONCE (via `start_debate_session`,
normally called right after persona_selector in a caller's own code, or
directly against already-computed essay/summary/persona), then each human
reply calls `step_debate_turn()` -- which reuses debate.py's
`generate_debate_turn()` (the exact same validated-question logic the batch
graph node uses) -- instead of redoing OCR/sanitizing/summarizing/persona
selection for every single turn.

SESSION STORAGE (ADR-015, superseding this module's original design).

Session state is held in a two-tier store: an in-process dict (`_sessions`)
in front of a Firestore `debate_sessions/{session_id}` document, via
memory/firestore_session.py. Reads prefer the local tier and fall back to
Firestore; writes go to both.

The original docstring here said the opposite -- "intentionally NOT a durable
store (no Firestore)" -- and that stayed in the file after ADR-015 added the
Firestore calls that this module now makes on every session operation (see the
`_firestore_*` imports below). ĐỢT 12 NHÓM 3 corrected it: a comment that
contradicts the code twenty lines under it is worse than no comment.

WHY the durable tier was needed: Cloud Run runs multiple instances behind a
load balancer, and a 3-turn debate is 3+ separate HTTP requests. With
in-process-only state, turn 2 landing on a different instance than turn 1
raised UnknownSessionError and lost the student's debate mid-conversation.

This does NOT collapse the Session-vs-Memory distinction (PROJECT_WIKI.md
7.5.6). `debate_sessions` is still *session* data: short-lived, keyed by
session_id, carrying a 24h `expire_at` for TTL deletion, and torn down by
end_debate_session(). Durability here buys request-to-request continuity, not
long-term recall. Long-term memory remains `student_profiles`, written only
through the profile-mutation path.
"""

from __future__ import annotations

import os
import time

import logging
from eduagent.config import VALIDATOR
from eduagent.nodes.debate import generate_debate_turn
from eduagent.nodes.scorer import score_essay
from eduagent.skills.language import detect_language

_logger = logging.getLogger(__name__)
_sessions: dict[str, dict] = {}


# ĐỢT 3 resource hygiene: an abandoned debate (student opens the page, never
# finishes) would otherwise sit in this in-process dict forever -- a slow
# memory leak on a long-lived Cloud Run instance. 24h is generous for a
# real debate session while still bounding worst-case growth.
_SESSION_TTL_SECONDS = 24 * 60 * 60


class UnknownSessionError(KeyError):
    pass


class DebateSessionComplete(ValueError):
    pass


from eduagent.memory.firestore_session import delete_session as _firestore_delete_session
from eduagent.memory.firestore_session import load_session as _firestore_get_session
from eduagent.memory.firestore_session import save_session as _firestore_save_session


def start_debate_session(
    session_id: str,
    *,
    persona_id: str,
    essay_text: str,
    summary: dict,
    prior_weaknesses: list[str] | None = None,
    language: str | None = None,
    student_id: str = "",
    name: str = "",
    class_id: str = "",
) -> None:
    """Registers a new interactive session. Call once, right after
    persona_selector has run (or with equivalent data), before the first
    step_debate_turn() call. Overwrites any existing session with the same id.

    `student_id`/`class_id` are stored only for logging and for
    complete_debate_session() to look up the right class's
    show_score_radar_to_students setting -- they never affect persona/debate
    logic itself."""
    evict_stale_sessions()  # lazy sweep -- cheap, and every new session start is a natural trigger point
    session_data = {
        "persona_id": persona_id,
        "essay_text": essay_text,
        "summary": summary,
        "prior_weaknesses": prior_weaknesses or [],
        "language": language or detect_language(essay_text),
        "student_id": student_id,
        "name": name or student_id,
        "class_id": class_id,
        "turns": [],
        "created_at": time.time(),
    }
    _sessions[session_id] = session_data
    _firestore_save_session(session_id, session_data)


def evict_stale_sessions(ttl_seconds: float = _SESSION_TTL_SECONDS, *, now: float | None = None) -> list[str]:
    """Removes sessions older than `ttl_seconds` from the in-process store.
    Returns the evicted session_ids (mainly for tests/logging). Sessions
    created before this field existed have no `created_at` and are treated
    as immediately stale -- they predate any TTL tracking at all."""
    now = now if now is not None else time.time()
    stale = [sid for sid, session in _sessions.items() if now - session.get("created_at", 0) > ttl_seconds]
    for sid in stale:
        _sessions.pop(sid, None)
        _firestore_delete_session(sid)
    return stale


def get_debate_session(session_id: str) -> dict:
    session = _sessions.get(session_id)
    if session is None:
        fs_session = _firestore_get_session(session_id)
        if fs_session is not None:
            _sessions[session_id] = fs_session
            return fs_session
        raise UnknownSessionError(f"Unknown session_id: {session_id!r}")
    return session


def end_debate_session(session_id: str) -> None:
    _sessions.pop(session_id, None)
    _firestore_delete_session(session_id)


def step_debate_turn(session_id: str, student_reply: str | None = None) -> dict:
    """Advances one turn: turn 1 needs no student_reply (there's nothing to
    reply to yet); turn 2+ requires the student's reply to the PREVIOUS turn,
    matching debate_loop's own `student_responses[turn_number - 2]` semantics
    exactly, so a session stepped one turn at a time produces the identical
    transcript a single batch debate_loop() call would have produced.

    Raises UnknownSessionError if session_id wasn't started, DebateSessionComplete
    if VALIDATOR.max_debate_turns has already been reached.
    """
    session = get_debate_session(session_id)
    turns: list[dict] = session["turns"]
    turn_number = len(turns) + 1

    if turn_number > VALIDATOR.max_debate_turns:
        raise DebateSessionComplete(f"Session {session_id!r} already has {len(turns)} turns (max {VALIDATOR.max_debate_turns}).")
    if turn_number > 1 and student_reply is None:
        raise ValueError(f"student_reply is required to generate turn {turn_number} (reply to turn {turn_number - 1}).")
    if student_reply is not None and turns:
        turns[-1]["student_response"] = student_reply


    new_turn = generate_debate_turn(
        persona_id=session["persona_id"],
        essay_text=session["essay_text"],
        summary=session["summary"],
        turn_number=turn_number,
        prior_turns=turns,
        student_response=student_reply if turn_number > 1 else None,
        prior_weaknesses=session["prior_weaknesses"],
        language=session["language"],
    )
    turns.append(new_turn)
    _firestore_save_session(session_id, session)
    return new_turn


def record_student_reply(session_id: str, student_reply: str) -> None:
    """Records the student's reply to the most recent turn in the session."""
    session = get_debate_session(session_id)
    turns = session.get("turns", [])
    if turns:
        turns[-1]["student_response"] = student_reply
        _firestore_save_session(session_id, session)




def _default_persist_essay_result(**kwargs) -> None:
    """Real Firestore write, or a no-op under pytest.

    ĐỢT 12 NHÓM 4: this used to be an inline `and not os.getenv(
    "PYTEST_CURRENT_TEST")` in the condition below, which had a nasty property --
    it did not just keep tests offline, it made the write path *unreachable* from
    any test. So the feature ĐỢT 9 declared "fixed" (wiring the interactive
    debate into Firestore + Pub/Sub) and ĐỢT 10's Task 10.5 had precisely zero
    tests behind them, and "190/190 passed" said nothing about either.

    Hoisting the decision into injectable seams keeps the offline-by-default
    guarantee while letting a test pass a fake and assert that the write happens
    with the right payload. Same pattern as
    memory/firestore_session.py::_default_client().
    """
    if os.getenv("PYTEST_CURRENT_TEST"):
        return
    from eduagent.memory.firestore_memory import apply_essay_result

    apply_essay_result(**kwargs)


def _default_publish_event(**kwargs) -> None:
    """Real Pub/Sub publish, or a no-op under pytest. See above."""
    if os.getenv("PYTEST_CURRENT_TEST"):
        return
    from eduagent.events import publish_essay_evaluated

    publish_essay_evaluated(**kwargs)


def complete_debate_session(
    session_id: str,
    *,
    persist_essay_result=None,
    publish_event=None,
    run_publish_in_thread: bool = True,
) -> dict:
    """ĐỢT 5 -- scores the finished debate (same cognitive_scorer prompt/
    schema the batch graph uses, via scorer.py's shared score_essay()) and
    tears the session down. Also persists to Firestore and publishes a Pub/Sub
    event to trigger class aggregation / Sheets logging for live web sessions.

    `persist_essay_result` / `publish_event` / `run_publish_in_thread` exist for
    tests (see tests/test_interactive_persistence.py): production callers use the
    defaults. `run_publish_in_thread=False` makes the publish synchronous so a
    test can assert it happened without racing a daemon thread.
    """
    session = get_debate_session(session_id)
    scores, rationale, student_feedback, degraded = score_essay(
        essay_text=session["essay_text"],
        summary=session["summary"],
        debate_turns=session["turns"],
        language=session["language"],
        log_context={"session_id": session_id, "student_id": session.get("student_id")},
    )

    student_id = session.get("student_id")
    student_name = session.get("name") or student_id
    class_id = session.get("class_id") or "c1"
    persona_id = session.get("persona_id") or "skeptic"
    fallacies_draft = session["summary"].get("fallacies_draft", [])

    # A degraded score is deliberately NOT persisted: writing a fabricated 0
    # would corrupt score_trend and flag the student as declining because of an
    # outage rather than their work (same discipline as scorer.py / mutator.py).
    if student_id and not degraded:
        from datetime import datetime, timezone
        import threading

        persist = persist_essay_result or _default_persist_essay_result
        publish = publish_event or _default_publish_event

        essay_id = session_id
        timestamp = datetime.now(timezone.utc).isoformat()

        try:
            persist(
                student_id=student_id,
                name=student_name,
                class_id=class_id,
                essay_id=essay_id,
                timestamp=timestamp,
                persona_used=persona_id,
                scores=scores,
                weakness_detected=fallacies_draft,
                student_feedback=student_feedback,
            )

            def _pub():
                try:
                    publish(
                        event_id=essay_id,
                        student_id=student_id,
                        class_id=class_id,
                        essay_id=essay_id,
                    )
                except Exception:
                    _logger.exception("Failed to publish Pub/Sub event after interactive debate completion")

            if run_publish_in_thread:
                threading.Thread(target=_pub, daemon=True).start()
            else:
                _pub()
        except Exception:
            _logger.exception("Failed to persist interactive debate results to Firestore for student %s", student_id)

    end_debate_session(session_id)
    return {
        "scores": scores,
        "rationale": rationale,
        "student_feedback": student_feedback,
        "degraded": degraded,
        "class_id": session.get("class_id", ""),
    }

