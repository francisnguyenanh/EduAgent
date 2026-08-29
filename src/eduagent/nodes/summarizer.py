"""Summarizer -- LLM-backed function node (Gemini Flash). Compresses the essay into a
structured claim/evidence/fallacy map that downstream nodes consume.

Kept to ONE narrow job (design principle #1: single-prompt
chatbots fail when asked to hold persona + history + scoring + formatting at
once). This node never argues with the student and never scores -- it only
extracts structure.
"""

from __future__ import annotations

from google.adk.agents.context import Context

import logging

from eduagent.config import GEMINI
from eduagent.llm import LLMGenerationError, generate_json
from eduagent.tracing import traced_node

_logger = logging.getLogger(__name__)

_SYSTEM_INSTRUCTION = (
    "You are an essay structure extractor for a critical-thinking coaching tool. "
    "You do not evaluate whether the student is right or wrong, and you do not "
    "write any part of the essay for them. You only extract what is already there. "
    "`main_claim`, `claims`, and `evidence` may be written in the essay's own "
    "language. `fallacies_draft` must be standard rhetoric/reasoning weakness categories."
)

_SCHEMA = {
    "type": "object",
    "properties": {
        "main_claim": {"type": "string", "description": "The student's central argument, in one sentence."},
        "claims": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Supporting claims the student makes, one per item.",
        },
        "evidence": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Concrete evidence/examples/sources the student cites, if any.",
        },
        "fallacies_draft": {
            "type": "array",
            "items": {"type": "string"},
            "description": (
                "Identify 1-3 specific reasoning weaknesses or gaps in the argument, classified among: "
                "- 'unsourced claim' or 'lacks empirical evidence' (missing data/sources), "
                "- 'one-sided argument' or 'lacks counterargument' (ignores opposing viewpoints), "
                "- 'unexamined assumption' or 'flawed logical deduction' (inconsistent logic or non sequitur), "
                "- 'hasty generalization' or 'overextended scope' (claims are overly broad or absolute)."
            ),
        },
    },
    "required": ["main_claim", "claims", "evidence", "fallacies_draft"],
}



_EMPTY_SUMMARY = {"main_claim": "", "claims": [], "evidence": [], "fallacies_draft": []}


def summarize_essay(essay_text: str, *, essay_id: str | None = None, student_id: str | None = None) -> tuple[dict, bool]:
    """Pure(ish) core of the node below, factored out so callers outside the
    ADK graph, such as the interactive REST API -- can run the EXACT same
    production summarization logic instead of a second, divergent
    implementation. Returns (summary, degraded)."""
    if not essay_text.strip():
        return dict(_EMPTY_SUMMARY), False

    try:
        summary = generate_json(
            model=GEMINI.flash_model,
            system_instruction=_SYSTEM_INSTRUCTION,
            prompt=f"Extract structure from this student essay:\n\n<student_essay>\n{essay_text}\n</student_essay>",
            response_schema=_SCHEMA,
            # Token/latency optimization: structure extraction is a
            # lookup/extraction task, not one that benefits from extended
            # reasoning -- Scorer/Teacher Digest Synthesizer keep the model
            # default since they actually need deeper reasoning.
            thinking_budget=0,
        )
        return summary, False
    except LLMGenerationError:
        # Gemini is down/degraded: don't crash the whole essay. Continue
        # with an empty-but-valid summary so persona selection and the
        # debate loop still run (on a plain "why do you believe that?"
        # basis) -- flagged so the teacher digest / audit trail can tell
        # this essay got a lower-fidelity pass, not that the student
        # actually wrote nothing.
        _logger.error(
            "Summarizer degraded to empty summary",
            extra={"essay_id": essay_id, "student_id": student_id},
        )
        return dict(_EMPTY_SUMMARY), True


@traced_node("summarizer")
async def summarizer(ctx: Context) -> dict:
    essay_text = ctx.state.get("sanitized_text", "")
    ctx.state["stage"] = "summarizer"

    summary, degraded = summarize_essay(essay_text, essay_id=ctx.state.get("essay_id"), student_id=ctx.state.get("student_id"))

    ctx.state["summary_degraded"] = degraded
    ctx.state["summary"] = summary
    return summary
