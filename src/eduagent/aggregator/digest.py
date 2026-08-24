"""Teacher Digest Synthesizer -- agent node (heavy Gemini model).

PROJECT_WIKI.md 8.3: this node ONLY turns already-computed ranking data into
natural-language prose for a teacher. It never re-ranks, never re-weighs --
the ranked list and common fallacies it receives are the ground truth; the
LLM's job is exposition, not decision-making. If the digest text and the
ranking data ever disagree, the ranking data is right.
"""

from __future__ import annotations

from eduagent.config import GEMINI
from eduagent.llm import generate_json

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


async def synthesize_digest(*, ranked_students: list[dict], common_fallacies: list[str], top_n: int = 5) -> dict:
    if not ranked_students:
        return {
            "headline": "No new essays to report today.",
            "priority_students": [],
            "class_wide_pattern": "",
            "mini_lesson_suggestion": "",
        }

    prompt = build_digest_prompt(ranked_students=ranked_students, common_fallacies=common_fallacies, top_n=top_n)
    return generate_json(
        model=GEMINI.heavy_model,
        system_instruction=_SYSTEM_INSTRUCTION,
        prompt=prompt,
        response_schema=_SCHEMA,
    )
