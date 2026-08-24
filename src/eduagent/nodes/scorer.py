"""Cognitive Scorer -- agent node (Gemini Flash). Scores the ORIGINAL essay
against 4 rubric axes, informed by how the student handled the debate.

Kept separate from the Debate Agent (own LLM call) so that grading pressure
never leaks into how challenging the debate questions are, and vice versa.
"""

from __future__ import annotations

from google.adk.agents.context import Context

from eduagent.config import GEMINI
from eduagent.llm import generate_json

_SYSTEM_INSTRUCTION = (
    "You are a rubric-based essay grader. Score strictly on the 4 axes given. "
    "Each axis is 0-10. Use the debate transcript as evidence of whether the "
    "student could actually defend their reasoning, not just write it well."
)

_SCHEMA = {
    "type": "object",
    "properties": {
        "logical_coherence": {"type": "integer", "minimum": 0, "maximum": 10},
        "evidence_quality": {"type": "integer", "minimum": 0, "maximum": 10},
        "counterargument_handling": {"type": "integer", "minimum": 0, "maximum": 10},
        "scope_awareness": {"type": "integer", "minimum": 0, "maximum": 10},
    },
    "required": ["logical_coherence", "evidence_quality", "counterargument_handling", "scope_awareness"],
}


async def cognitive_scorer(ctx: Context) -> dict:
    ctx.state["stage"] = "cognitive_scorer"

    essay_text = ctx.state.get("sanitized_text", "")
    summary = ctx.state.get("summary", {})
    debate_turns = ctx.state.get("debate_turns", [])

    if not essay_text.strip():
        scores = {"logical_coherence": 0, "evidence_quality": 0, "counterargument_handling": 0, "scope_awareness": 0}
    else:
        prompt = (
            f"Essay:\n{essay_text}\n\n"
            f"Extracted structure: {summary}\n\n"
            f"Debate transcript (persona questions + student replies, if any): {debate_turns}"
        )
        scores = generate_json(
            model=GEMINI.flash_model,
            system_instruction=_SYSTEM_INSTRUCTION,
            prompt=prompt,
            response_schema=_SCHEMA,
        )

    ctx.state["scores"] = scores
    return scores
