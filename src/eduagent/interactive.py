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

from eduagent.config import VALIDATOR
from eduagent.nodes.debate import generate_debate_turn
from eduagent.skills.language import detect_language

_sessions: dict[str, dict] = {}


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
) -> None:
    """Registers a new interactive session. Call once, right after
    persona_selector has run (or with equivalent data), before the first
    step_debate_turn() call. Overwrites any existing session with the same id."""
    _sessions[session_id] = {
        "persona_id": persona_id,
        "essay_text": essay_text,
        "summary": summary,
        "prior_weaknesses": prior_weaknesses or [],
        "language": language or detect_language(essay_text),
        "turns": [],
    }


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
