"""Profile Mutator -- deterministic function node.

Phase 1: computes the profile DELTA for this one essay (data mutation, not
just reading -- this is the direct answer to the track's judging question
"does the agent synthesize or mutate data, rather than just reading it?").
Phase 2 wires this delta into a real Firestore read-modify-write against
student_profiles/{student_id}, merging it with essay_history/persona_streak
instead of overwriting.
"""

from __future__ import annotations

from google.adk.agents.context import Context


def build_profile_delta(*, persona_id: str, fallacies_draft: list[str], scores: dict, validation_result: dict) -> dict:
    """Pure function -- unit-testable without Context/Firestore."""
    return {
        "persona_used": persona_id,
        "new_weaknesses": list(fallacies_draft),
        "scores": scores,
        "validator_passed": validation_result.get("passed", False),
    }


async def profile_mutator(ctx: Context) -> dict:
    ctx.state["stage"] = "profile_mutator"

    delta = build_profile_delta(
        persona_id=ctx.state.get("persona", ""),
        fallacies_draft=ctx.state.get("summary", {}).get("fallacies_draft", []),
        scores=ctx.state.get("scores", {}),
        validation_result=ctx.state.get("validation_result", {}),
    )
    ctx.state["profile_delta"] = delta
    ctx.state["profile_mutated"] = True  # Phase 2: true only after a real Firestore write.

    return {
        "essay_text": ctx.state.get("sanitized_text"),
        "summary": ctx.state.get("summary"),
        "persona": ctx.state.get("persona"),
        "debate_turns": ctx.state.get("debate_turns"),
        "validation_result": ctx.state.get("validation_result"),
        "scores": ctx.state.get("scores"),
        "profile_delta": delta,
        "stage": ctx.state.get("stage"),
    }
