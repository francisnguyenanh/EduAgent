"""Summarizer -- agent node (Gemini Flash). Compresses the essay into a
structured claim/evidence/fallacy map that downstream nodes consume.

Kept to ONE narrow job (PROJECT_WIKI.md 9.1 principle #1: single-prompt
chatbots fail when asked to hold persona + history + scoring + formatting at
once). This node never argues with the student and never scores -- it only
extracts structure.
"""

from __future__ import annotations

from google.adk.agents.context import Context

from eduagent.config import GEMINI
from eduagent.llm import generate_json

_SYSTEM_INSTRUCTION = (
    "You are an essay structure extractor for a critical-thinking coaching tool. "
    "You do not evaluate whether the student is right or wrong, and you do not "
    "write any part of the essay for them. You only extract what is already there."
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
                "Draft list of possible reasoning gaps or fallacies observed "
                "(e.g. 'hasty generalization', 'unsourced claim', 'ad hominem'). "
                "This is a draft for the Debate Loop to probe, not a final verdict."
            ),
        },
    },
    "required": ["main_claim", "claims", "evidence", "fallacies_draft"],
}


async def summarizer(ctx: Context) -> dict:
    essay_text = ctx.state.get("sanitized_text", "")
    ctx.state["stage"] = "summarizer"

    if not essay_text.strip():
        summary = {"main_claim": "", "claims": [], "evidence": [], "fallacies_draft": []}
    else:
        summary = generate_json(
            model=GEMINI.flash_model,
            system_instruction=_SYSTEM_INSTRUCTION,
            prompt=f"Extract structure from this student essay:\n\n{essay_text}",
            response_schema=_SCHEMA,
        )

    ctx.state["summary"] = summary
    return summary
