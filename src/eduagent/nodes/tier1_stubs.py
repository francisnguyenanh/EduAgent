"""Phase 0 stub nodes for the Tier 1 per-student pipeline.

Each function is a placeholder FunctionNode body: it only threads state through
so the graph shape can be verified end-to-end. Real logic lands in Phase 1
(intake/sanitizer/summarizer/validator) and Phase 2 (memory-informed persona
selector). Every stub deliberately raises no LLM calls — deterministic-first
even at skeleton stage.
"""

from __future__ import annotations

from google.adk.agents.context import Context


async def intake(ctx: Context, node_input: str) -> dict:
    """Stub: accept raw essay text, stamp pipeline start."""
    ctx.state["raw_input"] = node_input
    ctx.state["stage"] = "intake"
    return {"essay_text": node_input}


async def sanitizer(ctx: Context) -> dict:
    """Stub: pass-through. Phase 1 adds prompt-injection stripping here."""
    essay_text = ctx.state.get("raw_input", "")
    ctx.state["stage"] = "sanitizer"
    ctx.state["sanitized_text"] = essay_text
    return {"sanitized_text": essay_text}


async def summarizer(ctx: Context) -> dict:
    """Stub: no LLM call yet — Phase 1 wires in Gemini Flash here."""
    ctx.state["stage"] = "summarizer"
    summary = {"claims": [], "evidence": [], "fallacies_draft": []}
    ctx.state["summary"] = summary
    return summary


async def persona_selector(ctx: Context) -> dict:
    """Stub: fixed persona. Phase 2 reads Firestore memory before choosing."""
    ctx.state["stage"] = "persona_selector"
    persona = "skeptic"
    ctx.state["persona"] = persona
    return {"persona": persona}


async def debate_loop(ctx: Context) -> dict:
    """Stub: single mock turn. Phase 1 adds 3-turn escalation + anchoring."""
    ctx.state["stage"] = "debate_loop"
    turns = [{"turn": 1, "persona": ctx.state.get("persona"), "question": "(stub) why do you believe that?"}]
    ctx.state["debate_turns"] = turns
    return {"debate_turns": turns}


async def challenge_validator(ctx: Context) -> dict:
    """Stub: always passes. Phase 1 adds real answer-leak / length regex checks.

    Must stay a pure function node — zero LLM calls — even after Phase 1.
    """
    ctx.state["stage"] = "challenge_validator"
    result = {"passed": True, "violations": []}
    ctx.state["validation_result"] = result
    return result


async def cognitive_scorer(ctx: Context) -> dict:
    """Stub: zeroed rubric. Phase 1 adds real 4-axis scoring."""
    ctx.state["stage"] = "cognitive_scorer"
    scores = {
        "logical_coherence": 0,
        "evidence_quality": 0,
        "counterargument_handling": 0,
        "scope_awareness": 0,
    }
    ctx.state["scores"] = scores
    return scores


async def profile_mutator(ctx: Context) -> dict:
    """Stub: no Firestore write yet. Phase 1/2 mutate student_profiles here."""
    ctx.state["stage"] = "profile_mutator"
    ctx.state["profile_mutated"] = False
    return {
        "essay_text": ctx.state.get("sanitized_text"),
        "summary": ctx.state.get("summary"),
        "persona": ctx.state.get("persona"),
        "debate_turns": ctx.state.get("debate_turns"),
        "validation_result": ctx.state.get("validation_result"),
        "scores": ctx.state.get("scores"),
        "stage": ctx.state.get("stage"),
    }
