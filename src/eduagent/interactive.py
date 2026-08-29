"""Interactive Debate Step Helper -- one Socratic turn per call, without
re-running the whole Tier 1 ADK2 graph from intake onward.

WHY THIS MODULE EXISTS, AND WHY IT IS NOT A STOPGAP (ADR-021).

The Tier 1 graph runs as a single batch call per essay: `Workflow.node_input`
accepts the essay text once, so there is no way to inject the student's reply
between turns from inside the graph. An earlier design recorded this as a
limitation to be removed later "using ADK2 Workflow's interrupt/resume
(`RequestInput`)".

That plan was based on a factual error, corrected: **`RequestInput`
is not a `Workflow` primitive at all.** In the installed ADK
(`google-adk` 2.3.0) `google.adk.workflow` exports only BaseNode, Edge,
FunctionNode, JoinNode, Node, NodeTimeoutError, RetryConfig, START and
Workflow -- `from google.adk.workflow import RequestInput` raises ImportError.
The real `RequestInput` lives in `google.adk.events.request_input`, wired up by
`google.adk.tools._request_input_tool` as a `LongRunningFunctionTool` for the
LLM **agent tool-calling flow** (`google.adk.flows.llm_flows`). Our graph is
built entirely from `FunctionNode`s, which never enter that flow, so the
mechanism is not reachable from it.

Using it would mean converting the debate node into an `LlmAgent` that calls
tools -- handing the model control over persona anchoring, escalation order and
when to stop, i.e. discarding the deterministic-first property that the rest of
this codebase is organised around. That is a strictly worse trade.

So this module is the intended architecture, not a bridge awaiting a better
one: intake -> sanitizer -> summarizer -> persona_selector run ONCE (via
`start_debate_session`), then each human reply calls `step_debate_turn()`,
which reuses debate.py's `generate_debate_turn()` -- the exact same validated
question logic the batch graph node uses, not a second implementation --
instead of redoing OCR/sanitizing/summarizing/persona selection every turn.

SESSION STORAGE (ADR-015, superseding this module's original design).

Session state is held in a two-tier store: a Firestore
`debate_sessions/{session_id}` document (via memory/firestore_session.py) with
an in-process dict (`_sessions`) behind it. **Reads prefer Firestore**; the
dict is a fallback for when no durable store is configured at all (local runs,
pytest). Writes go to both.

Corrected this paragraph together with the code under it: it used to
say "Reads prefer the local tier and fall back to Firestore", which was both
what the code did and the exact failure ADR-015 exists to prevent -- see
get_debate_session() for why preferring the local tier loses turns across
Cloud Run instances.

The original docstring here said the opposite -- "intentionally NOT a durable
store (no Firestore)" -- and that stayed in the file after ADR-015 added the
Firestore calls that this module now makes on every session operation (see the
`_firestore_*` imports below). It has since been corrected: a comment that
contradicts the code twenty lines under it is worse than no comment.

WHY the durable tier was needed: Cloud Run runs multiple instances behind a
load balancer, and a 3-turn debate is 3+ separate HTTP requests. With
in-process-only state, turn 2 landing on a different instance than turn 1
raised UnknownSessionError and lost the student's debate mid-conversation.

This does NOT collapse the ADK Session-vs-Memory distinction. `debate_sessions` is still *session* data: short-lived, keyed by
session_id, carrying a 24h `expire_at` for TTL deletion, and torn down by
end_debate_session(). Durability here buys request-to-request continuity, not
long-term recall. Long-term memory remains `student_profiles`, written only
through the profile-mutation path.

SESSION LIFETIME AFTER SCORING (ADR-022).

complete_debate_session() used to delete the session as its last act. It no
longer does: it marks the session `completed` and leaves it in place, because the
metacognitive reflection step happens AFTER the debate finishes and the session
is the only server-side record that the debate ever happened. Deleting it there
is exactly what forced /api/debate/reflect to accept the student id, the essay
and the fallacy from the client -- and therefore to accept a reflection with no
debate behind it at all. api.py::submit_reflection() is what tears the session
down now, and a student who never reflects just lets the 24h TTL collect it.

A `completed` session is terminal: step_debate_turn() refuses to advance it
regardless of turn count, so a debate whose score is already written into the
student's profile cannot be re-opened and made to disagree with it.
"""

from __future__ import annotations

import os
import time
from datetime import datetime as _dt
from datetime import timezone as _tz

import logging
from eduagent.config import VALIDATOR
from eduagent.nodes.debate import generate_debate_turn
from eduagent.nodes.scorer import score_essay
from eduagent.skills.language import detect_language

_logger = logging.getLogger(__name__)
_sessions: dict[str, dict] = {}


# Resource hygiene: an abandoned debate (student opens the page, never
# finishes) would otherwise sit in this in-process dict forever -- a slow
# memory leak on a long-lived Cloud Run instance. 24h is generous for a
# real debate session while still bounding worst-case growth.
_SESSION_TTL_SECONDS = 24 * 60 * 60


class UnknownSessionError(KeyError):
    pass


class DebateSessionComplete(ValueError):
    pass


class DebateNotComplete(ValueError):
    """Raised when a post-debate action (currently only the metacognitive
    reflection) is attempted on a session that has not finished its turns."""


class ReflectionAlreadySubmitted(ValueError):
    """Raised on a second reflection for the same session. One debate earns at
    most one growth bonus, and this is the flag that enforces it."""


from eduagent.memory.firestore_session import delete_session as _firestore_delete_session
from eduagent.memory.firestore_session import load_session as _firestore_get_session
from eduagent.memory.firestore_session import store_is_authoritative as _firestore_is_authoritative
from eduagent.memory.firestore_session import claim_reflection_atomically as _firestore_claim_reflection
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
    """Reads prefer Firestore; the in-process dict is a failure fallback only.

    This used to be `_sessions.get()` first, consulting Firestore
    only when the dict held nothing. That is precisely the bug ADR-015 says it
    fixed, reintroduced one layer up: there are TWO caches here, and the outer
    one had no freshness bound at all (only `evict_stale_sessions`, a 24h
    sweep), so it shadowed the 3-second bound that `firestore_session` applies.
    README described "a 3-second bounded in-memory read cache"; that bound was
    unreachable on the path every request actually takes. Verified by
    simulating two instances at THIS layer: instance A served a stale copy and
    lost the turn instance B had written.

    The existing multi-instance regression test did not catch it because it
    exercises `firestore_session.load_session()` directly -- the inner tier,
    which was never the broken one.

    `load_session()` already owns the 3s freshness bound, its own cache, and
    the degrade-to-stale-copy behaviour when Firestore is unreachable, so
    preferring it here is what makes ADR-015 true rather than aspirational.
    """
    fs_session = _firestore_get_session(session_id)
    if fs_session is not None:
        # Do NOT populate the local dict on a Firestore hit. Once
        # reads prefer Firestore, caching here buys nothing -- the next read
        # goes to Firestore anyway (that is the whole point of ADR-027) -- while
        # every read of every session would grow a dict that is only swept on a
        # 24h TTL, on a 512Mi instance. `firestore_session` already keeps its
        # own 3s-bounded cache for the repeat reads inside a single request.
        # The dict now exists solely for the no-durable-store case below.
        return fs_session

    if _firestore_is_authoritative():
        # A durable store exists and reports no such document -- e.g.
        # end_debate_session() ran on another instance. Trusting this
        # instance's dict here would resurrect a session that ADR-022
        # deliberately tore down, so drop the local copy instead.
        _sessions.pop(session_id, None)
        raise UnknownSessionError(f"Unknown session_id: {session_id!r}")

    # No durable store configured (local run / pytest): the dict IS the store.
    session = _sessions.get(session_id)
    if session is None:
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

    # a scored session is terminal, and the flag says so
    # independently of the turn count. Completion normally coincides with
    # max_debate_turns, but the session now outlives completion (so the
    # reflection can be tied to it), and re-opening a debate whose score has
    # already been written to the student's profile would let the transcript and
    # the score disagree.
    if session.get("completed"):
        raise DebateSessionComplete(f"Session {session_id!r} is already scored and closed.")
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


def claim_reflection(session_id: str) -> dict:
    """Atomically-enough claims the one reflection a finished debate is entitled
    to, and returns the session it belongs to.

    This is the single place that decides a reflection is
    legitimate, so the caller never has to trust the request body for *any* of
    it. It rejects a session that has not finished (`DebateNotComplete`) and a
    session whose reflection was already spent (`ReflectionAlreadySubmitted`),
    and it writes `has_reflected` BEFORE the caller runs its LLM evaluation --
    a double-clicked "Submit Revised Claim" must not be able to bank two growth
    bonuses while the first request is still waiting on Gemini.
    """
    # Prefer a real Firestore transaction so the check and the write
    # cannot be split by a concurrent request on another instance. Falls back to
    # the read-modify-write below only when there is no Firestore client at all
    # (local dev, pytest), where there is exactly one process and therefore no
    # race to lose.
    status, data = _firestore_claim_reflection(session_id)
    if status == "claimed":
        # claim_reflection_atomically() already refreshed the local read cache
        # with the post-claim document, so there is nothing to write here.
        return data
    if status == "not_complete":
        raise DebateNotComplete(
            f"Session {session_id!r} has {len((data or {}).get('turns', []))} turn(s) and is not finished -- "
            "a reflection is only meaningful after the debate it reflects on."
        )
    if status == "already":
        raise ReflectionAlreadySubmitted(f"Session {session_id!r} has already recorded its reflection.")
    if status == "missing":
        raise UnknownSessionError(f"Unknown debate session {session_id!r}.")

    session = get_debate_session(session_id)
    if not session.get("completed"):
        raise DebateNotComplete(
            f"Session {session_id!r} has {len(session.get('turns', []))} turn(s) and is not finished -- "
            "a reflection is only meaningful after the debate it reflects on."
        )
    if session.get("has_reflected"):
        raise ReflectionAlreadySubmitted(f"Session {session_id!r} has already recorded its reflection.")
    session["has_reflected"] = True
    _firestore_save_session(session_id, session)
    return session


def release_reflection_claim(session_id: str) -> None:
    """Gives back the one reflection a session is entitled to.

    `claim_reflection()` deliberately spends the claim BEFORE the
    LLM call, so a double-click cannot bank two growth bonuses. The cost of
    that ordering is that a Vertex AI outage would otherwise burn the
    student's only attempt on a request that never got evaluated. Releasing
    the claim on a degraded evaluation keeps both properties: the double-click
    window stays closed (the claim was held for the whole in-flight call), and
    an outage becomes retryable instead of permanent.

    Deliberately a no-op on an already-torn-down session -- releasing a claim
    is a best-effort cleanup and must never turn a degraded evaluation into a
    500 on top of it.
    """
    try:
        session = get_debate_session(session_id)
    except UnknownSessionError:
        return
    session["has_reflected"] = False
    _firestore_save_session(session_id, session)


def record_student_reply(session_id: str, student_reply: str) -> None:
    """Records the student's reply to the most recent turn in the session."""
    session = get_debate_session(session_id)
    turns = session.get("turns", [])
    if turns:
        turns[-1]["student_response"] = student_reply
        _firestore_save_session(session_id, session)




def _default_persist_essay_result(**kwargs) -> None:
    """Real Firestore write, or a no-op under pytest.

    This used to be an inline `and not os.getenv(
    "PYTEST_CURRENT_TEST")` in the condition below, with an important side effect:
    it did not just keep tests offline, it made the write path *unreachable* from
    any test. The feature it was supposed to cover -- wiring the interactive
    debate into Firestore and Pub/Sub -- therefore had precisely zero tests
    behind it, and a green suite said nothing about whether it worked.

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
    """Scores the finished debate (same cognitive_scorer prompt/
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

    # This used to call end_debate_session() here, which deleted the
    # only server-side record that the debate had ever happened -- and the
    # metacognitive reflection step comes AFTER completion. That is precisely why
    # /api/debate/reflect had to accept student_id/original_claim from the client,
    # and therefore why it could be called with no debate behind it at all.
    #
    # So the session now survives completion in a terminal, reflection-only state.
    # It cannot be advanced (step_debate_turn already refuses once turns ==
    # max_debate_turns) and it is not long-term memory: it keeps the same 24h
    # `expire_at` TTL, and submit_reflection() tears it down for real once the
    # reflection lands. A student who never reflects just lets the TTL collect it.
    session["completed"] = True
    session["completed_at"] = _dt.now(_tz.utc).isoformat()
    _firestore_save_session(session_id, session)

    return {
        "scores": scores,
        "rationale": rationale,
        "student_feedback": student_feedback,
        "degraded": degraded,
        "class_id": session.get("class_id", ""),
    }

