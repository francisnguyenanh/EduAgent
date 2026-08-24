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

Session state lives in an in-process dict, keyed by caller-supplied
session_id. This is intentionally NOT a durable store (no Firestore) --
Session vs Memory stays the same distinction as everywhere else in this
project (PROJECT_WIKI.md 7.5.6): a live debate's turn-by-turn state is
per-session, not the kind of thing that needs to survive a process restart,
whereas the finished transcript still gets persisted the normal way through
profile_mutator once the graph resumes/completes.
"""

from __future__ import annotations

import time

from eduagent.config import VALIDATOR
from eduagent.nodes.debate import generate_debate_turn
from eduagent.nodes.scorer import score_essay
from eduagent.skills.language import detect_language

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


def start_debate_session(
    session_id: str,
    *,
    persona_id: str,
    essay_text: str,
    summary: dict,
    prior_weaknesses: list[str] | None = None,
    language: str | None = None,
    student_id: str = "",
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
    _sessions[session_id] = {
        "persona_id": persona_id,
        "essay_text": essay_text,
        "summary": summary,
        "prior_weaknesses": prior_weaknesses or [],
        "language": language or detect_language(essay_text),
        "student_id": student_id,
        "class_id": class_id,
        "turns": [],
        "created_at": time.time(),
    }


def evict_stale_sessions(ttl_seconds: float = _SESSION_TTL_SECONDS, *, now: float | None = None) -> list[str]:
    """Removes sessions older than `ttl_seconds` from the in-process store.
    Returns the evicted session_ids (mainly for tests/logging). Sessions
    created before this field existed have no `created_at` and are treated
    as immediately stale -- they predate any TTL tracking at all."""
    now = now if now is not None else time.time()
    stale = [sid for sid, session in _sessions.items() if now - session.get("created_at", 0) > ttl_seconds]
    for sid in stale:
        _sessions.pop(sid, None)
    return stale


def get_debate_session(session_id: str) -> dict:
    session = _sessions.get(session_id)
    if session is None:
        raise UnknownSessionError(f"Unknown session_id: {session_id!r}")
    return session


def end_debate_session(session_id: str) -> None:
    _sessions.pop(session_id, None)


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
    return new_turn


def complete_debate_session(session_id: str) -> dict:
    """ĐỢT 5 -- scores the finished debate (same cognitive_scorer prompt/
    schema the batch graph uses, via scorer.py's shared score_essay()) and
    tears the session down. Meant to be called once VALIDATOR.max_debate_turns
    has been reached; does NOT persist to Firestore or mutate the student's
    profile -- see interactive.py's module docstring and api.py's for why
    that write-back stays the batch graph's job. This purely produces the
    student-facing "how did I do" summary for the live Web UI."""
    session = get_debate_session(session_id)
    scores, rationale, student_feedback, degraded = score_essay(
        essay_text=session["essay_text"],
        summary=session["summary"],
        debate_turns=session["turns"],
        language=session["language"],
        log_context={"session_id": session_id, "student_id": session.get("student_id")},
    )
    end_debate_session(session_id)
    return {
        "scores": scores,
        "rationale": rationale,
        "student_feedback": student_feedback,
        "degraded": degraded,
        "class_id": session.get("class_id", ""),
    }
