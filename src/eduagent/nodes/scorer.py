"""Cognitive Scorer -- agent node (Gemini Flash). Scores the ORIGINAL essay
against 4 rubric axes, informed by how the student handled the debate.

Kept separate from the Debate Agent (own LLM call) so that grading pressure
never leaks into how challenging the debate questions are, and vice versa.
"""

from __future__ import annotations

from google.adk.agents.context import Context

import logging

from eduagent.config import GEMINI
from eduagent.llm import LLMGenerationError, generate_json
from eduagent.skills.language import language_instruction
from eduagent.tracing import traced_node

_logger = logging.getLogger(__name__)

_SYSTEM_INSTRUCTION = (
    "You are a rubric-based essay grader. Score strictly on the 4 axes given. "
    "Each axis is 0-10. Use the debate transcript as evidence of whether the "
    "student could actually defend their reasoning, not just write it well. "
    "Besides the per-axis rationale, also write `student_feedback`: 2-4 "
    "encouraging, constructive sentences addressed directly to the student -- "
    "name one genuine strength and one concrete way to improve next time. "
    "This is the only part of your output the student actually reads, so keep "
    "it kind and specific, never just a restatement of the numeric scores."
)

_AXES = ("logical_coherence", "evidence_quality", "counterargument_handling", "scope_awareness")

# `scores` stays a flat {axis: int} dict -- that's the contract every other
# module relies on (memory/student_profile._avg, the Firestore schema,
# tests/test_student_profile_memory.py). `rationale` and `student_feedback`
# are parallel, separate fields so adding them can't silently break anything
# reading `scores` alone.
_SCHEMA = {
    "type": "object",
    "properties": {
        "scores": {
            "type": "object",
            "properties": {axis: {"type": "integer", "minimum": 0, "maximum": 10} for axis in _AXES},
            "required": list(_AXES),
        },
        "rationale": {
            "type": "object",
            "properties": {axis: {"type": "string", "description": "1-2 sentence justification for this axis's score."} for axis in _AXES},
            "required": list(_AXES),
        },
        "student_feedback": {
            "type": "string",
            "description": "2-4 sentences of encouraging, constructive feedback addressed directly to the student.",
        },
    },
    "required": ["scores", "rationale", "student_feedback"],
}

_ZERO_SCORES = {axis: 0 for axis in _AXES}
_EMPTY_RATIONALE = {axis: "" for axis in _AXES}
_DEGRADED_STUDENT_FEEDBACK = ""


def score_essay(
    *,
    essay_text: str,
    summary: dict,
    debate_turns: list[dict],
    language: str = "en",
    log_context: dict | None = None,
) -> tuple[dict, dict, str, bool]:
    """Scores one essay against the 4 rubric axes. Pulled out of
    cognitive_scorer() so the SAME logic backs both the batch graph node
    (against `Context`) and the interactive debate API (ĐỢT 5 -- scoring a
    session right after its 3rd turn completes, without duplicating this
    prompt/schema/degradation logic a second time) -- same pattern as
    debate.py's generate_debate_turn().

    Returns (scores, rationale, student_feedback, degraded).
    """
    if not essay_text.strip():
        return dict(_ZERO_SCORES), dict(_EMPTY_RATIONALE), _DEGRADED_STUDENT_FEEDBACK, False

    prompt = (
        f"Essay:\n{essay_text}\n\n"
        f"Extracted structure: {summary}\n\n"
        f"Debate transcript (persona questions + student replies, if any): {debate_turns}"
    )
    try:
        result = generate_json(
            model=GEMINI.flash_model,
            system_instruction=f"{_SYSTEM_INSTRUCTION}\n\n{language_instruction(language)}",
            prompt=prompt,
            response_schema=_SCHEMA,
        )
        return result["scores"], result["rationale"], result["student_feedback"], False
    except LLMGenerationError:
        # Critical distinction: a 0 score here would corrupt score_trend
        # and unfairly flag the student as declining because of an infra
        # outage, not their work. Callers check the `degraded` flag and
        # route around persisting a fabricated score (mutator.py ->
        # pending_essays; the interactive API -> hides the radar and
        # returns only a generic feedback message).
        _logger.error("Scorer degraded -- not returning a fake score", extra=log_context or {})
        return dict(_ZERO_SCORES), dict(_EMPTY_RATIONALE), _DEGRADED_STUDENT_FEEDBACK, True


@traced_node("cognitive_scorer")
async def cognitive_scorer(ctx: Context) -> dict:
    ctx.state["stage"] = "cognitive_scorer"

    essay_text = ctx.state.get("sanitized_text", "")
    summary = ctx.state.get("summary", {})
    debate_turns = ctx.state.get("debate_turns", [])
    language = ctx.state.get("language", "en")

    scores, rationale, student_feedback, scores_degraded = score_essay(
        essay_text=essay_text,
        summary=summary,
        debate_turns=debate_turns,
        language=language,
        log_context={"essay_id": ctx.state.get("essay_id"), "student_id": ctx.state.get("student_id")},
    )

    ctx.state["scores"] = scores
    ctx.state["score_rationale"] = rationale
    ctx.state["student_feedback"] = student_feedback
    ctx.state["scores_degraded"] = scores_degraded
    return scores
