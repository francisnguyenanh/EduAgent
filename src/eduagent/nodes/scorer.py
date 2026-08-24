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
from eduagent.tracing import traced_node

_logger = logging.getLogger(__name__)

_SYSTEM_INSTRUCTION = (
    "You are a rubric-based essay grader. Score strictly on the 4 axes given. "
    "Each axis is 0-10. Use the debate transcript as evidence of whether the "
    "student could actually defend their reasoning, not just write it well."
)

_AXES = ("logical_coherence", "evidence_quality", "counterargument_handling", "scope_awareness")

# `scores` stays a flat {axis: int} dict -- that's the contract every other
# module relies on (memory/student_profile._avg, the Firestore schema,
# tests/test_student_profile_memory.py). `rationale` is a parallel, separate
# object so adding it can't silently break anything reading `scores` alone.
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
    },
    "required": ["scores", "rationale"],
}

_ZERO_SCORES = {axis: 0 for axis in _AXES}
_EMPTY_RATIONALE = {axis: "" for axis in _AXES}


@traced_node("cognitive_scorer")
async def cognitive_scorer(ctx: Context) -> dict:
    ctx.state["stage"] = "cognitive_scorer"

    essay_text = ctx.state.get("sanitized_text", "")
    summary = ctx.state.get("summary", {})
    debate_turns = ctx.state.get("debate_turns", [])

    scores_degraded = False
    if not essay_text.strip():
        scores, rationale = dict(_ZERO_SCORES), dict(_EMPTY_RATIONALE)
    else:
        prompt = (
            f"Essay:\n{essay_text}\n\n"
            f"Extracted structure: {summary}\n\n"
            f"Debate transcript (persona questions + student replies, if any): {debate_turns}"
        )
        try:
            result = generate_json(
                model=GEMINI.flash_model,
                system_instruction=_SYSTEM_INSTRUCTION,
                prompt=prompt,
                response_schema=_SCHEMA,
            )
            scores, rationale = result["scores"], result["rationale"]
        except LLMGenerationError:
            # Critical distinction: a 0 score here would corrupt score_trend
            # and unfairly flag the student as declining because of an infra
            # outage, not their work. mutator.py checks scores_degraded and
            # routes this essay to pending_essays instead of student_profiles
            # -- no fabricated score ever reaches the permanent record.
            _logger.error(
                "Scorer degraded -- routing to pending_essays, not writing a fake score",
                extra={"essay_id": ctx.state.get("essay_id"), "student_id": ctx.state.get("student_id")},
            )
            scores, rationale = dict(_ZERO_SCORES), dict(_EMPTY_RATIONALE)
            scores_degraded = True

    ctx.state["scores"] = scores
    ctx.state["score_rationale"] = rationale
    ctx.state["scores_degraded"] = scores_degraded
    return scores
