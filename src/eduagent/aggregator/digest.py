"""Teacher Digest Synthesizer -- agent node (heavy Gemini model).

PROJECT_WIKI.md 8.3: this node ONLY turns already-computed ranking data into
natural-language prose for a teacher. It never re-ranks, never re-weighs --
the ranked list and common fallacies it receives are the ground truth; the
LLM's job is exposition, not decision-making. If the digest text and the
ranking data ever disagree, the ranking data is right.
"""

from __future__ import annotations

import logging

from eduagent.config import GEMINI
from eduagent.llm import LLMGenerationError, generate_json

_logger = logging.getLogger(__name__)

_SYSTEM_INSTRUCTION = (
    "You are writing a short digest for a teacher who has very little time. "
    "You are given a PRE-COMPUTED priority ranking and a list of common class-wide "
    "fallacies -- do not re-rank or second-guess the numbers, just explain what they "
    "mean in plain language and suggest one concrete action. Be concise and specific; "
    "name actual students and actual fallacies, not generic advice."
)

_SCHEMA = {
    "type": "object",
    "properties": {
        "headline": {"type": "string", "description": "One sentence summarizing today's class digest."},
        "priority_students": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "student_id": {"type": "string"},
                    "why": {"type": "string", "description": "1-2 sentence plain-language reason, from the given data only."},
                },
                "required": ["student_id", "why"],
            },
        },
        "class_wide_pattern": {
            "type": "string",
            "description": "1-2 sentences on the most common shared fallacy, or empty string if none.",
        },
        "mini_lesson_suggestion": {
            "type": "string",
            "description": "One concrete ~15-minute mini-lesson idea addressing the class-wide pattern, or empty string if none.",
        },
    },
    "required": ["headline", "priority_students", "class_wide_pattern", "mini_lesson_suggestion"],
}


def build_digest_prompt(*, ranked_students: list[dict], common_fallacies: list[str], top_n: int) -> str:
    top = ranked_students[:top_n]
    lines = [f"Top {len(top)} students by Intervention Priority Index (already computed, do not re-rank):"]
    for r in top:
        lines.append(f"- {r['student_id']} ({r['name']}): priority={r['priority']}, reason={r['reason']}")
    lines.append(f"\nClass-wide common fallacies (shared by 2+ students): {common_fallacies or 'none detected'}")
    return "\n".join(lines)


def _fallback_digest(*, ranked_students: list[dict], common_fallacies: list[str], top_n: int) -> dict:
    """Built directly from the ranking data, no LLM -- used when Gemini is
    down. Plain but still actionable: a teacher can read this and know
    exactly who to check on, even without the narrative prose."""
    top = ranked_students[:top_n]
    return {
        "headline": f"[Digest narrative unavailable -- Gemini degraded] {len(top)} student(s) flagged for review.",
        "priority_students": [
            {"student_id": r["student_id"], "why": f"priority={r['priority']}, reason={r['reason']}"} for r in top
        ],
        "class_wide_pattern": f"Common fallacies: {', '.join(common_fallacies)}" if common_fallacies else "",
        "mini_lesson_suggestion": "",
    }


async def synthesize_digest(*, ranked_students: list[dict], common_fallacies: list[str], top_n: int = 5) -> dict:
    if not ranked_students:
        return {
            "headline": "No new essays to report today.",
            "priority_students": [],
            "class_wide_pattern": "",
            "mini_lesson_suggestion": "",
        }

    prompt = build_digest_prompt(ranked_students=ranked_students, common_fallacies=common_fallacies, top_n=top_n)
    try:
        return generate_json(
            model=GEMINI.heavy_model,
            system_instruction=_SYSTEM_INSTRUCTION,
            prompt=prompt,
            response_schema=_SCHEMA,
        )
    except LLMGenerationError:
        # The ranking itself (the ground truth) already exists and cost no
        # LLM call -- degrade to a plain rendering of it rather than losing
        # the digest (and the teacher's visibility into who needs help)
        # entirely just because the narrative-writing step is down.
        _logger.error("Digest synthesis degraded to fallback rendering (Gemini unavailable)")
        return _fallback_digest(ranked_students=ranked_students, common_fallacies=common_fallacies, top_n=top_n)
