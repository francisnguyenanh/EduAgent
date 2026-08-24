"""Debate Loop -- agent node, 3-turn escalation with persona anchoring.

Persona anchoring fix (PROJECT_WIKI.md 9.3): the persona.anchor text is
re-injected into EVERY turn's prompt, not just a system prompt set once at
the start -- this is the concrete fix for the old project's "persona drift
into an agreeable assistant" failure mode.

Each generated question is checked against the independent Validator
(nodes/validator.py) before being accepted; on failure it regenerates up to
VALIDATOR.max_regeneration_retries times, then falls back to a safe canned
question rather than ever emitting a validated-bad turn.

Phase 1 note: this pipeline runs as a single batch call per essay (no live
back-and-forth UI yet), so turns 2 and 3 use `ctx.state["student_responses"]`
if a caller supplied them (e.g. a test, or later the Web UI); otherwise the
loop only produces turn 1 -- there is nothing to escalate against yet.
"""

from __future__ import annotations

from google.adk.agents.context import Context

from eduagent.config import GEMINI, VALIDATOR
from eduagent.llm import LLMGenerationError, generate_text
from eduagent.nodes.validator import validate_debate_turn
from eduagent.skills.debate_escalation import get_escalation_instruction
from eduagent.skills.personas import get_persona
from eduagent.tracing import traced_node

# One canned fallback per persona -- used only when the LLM fails to produce
# a validator-passing question after all retries. A single generic fallback
# would break persona anchoring right at the moment it matters most (the
# regenerate loop already failed once).
_PERSONA_FALLBACK_QUESTIONS: dict[str, str] = {
    "skeptic": "What evidence led you to that conclusion, and where does it come from?",
    "devils_advocate": "What would someone who disagrees with you say, and how would you respond?",
    "nitpicker": "Walk me through the reasoning step by step -- where exactly does one point lead to the next?",
    "expander": "Does this still hold true in a different context, or only in the specific case you described?",
}
_DEFAULT_FALLBACK_QUESTION = "That's an interesting point -- what evidence led you to that conclusion?"


def _build_prompt(
    *,
    essay_text: str,
    summary: dict,
    turn: int,
    prior_turns: list[dict],
    student_response: str | None,
    prior_weaknesses: list[str],
) -> str:
    parts = [f"Original essay:\n{essay_text}", f"Extracted summary: {summary}"]
    if turn == 1 and prior_weaknesses:
        # Memory injection (Phase 2 -> Phase 3 follow-up): only surfaced on
        # the opening turn, where "have you improved on this before" is a
        # meaningful question to ask -- repeating it every turn would just be
        # noise once the live back-and-forth is underway.
        parts.append(
            "This student has previously struggled with: "
            + ", ".join(prior_weaknesses)
            + ". If this essay repeats one of these patterns, consider probing it directly; "
            "if it's actually improved, you may acknowledge that briefly before pushing further."
        )
    for t in prior_turns:
        parts.append(f"Turn {t['turn']} question: {t['question']}")
        if t.get("student_response"):
            parts.append(f"Student's reply: {t['student_response']}")
    if student_response:
        parts.append(f"Student's latest reply (respond to THIS): {student_response}")
    return "\n\n".join(parts)


@traced_node("debate_loop")
async def debate_loop(ctx: Context) -> dict:
    ctx.state["stage"] = "debate_loop"

    persona_id = ctx.state.get("persona", "skeptic")
    persona = get_persona(persona_id)
    essay_text = ctx.state.get("sanitized_text", "")
    summary = ctx.state.get("summary", {})
    student_responses: list[str] = ctx.state.get("student_responses", [])
    prior_weaknesses: list[str] = ctx.state.get("prior_weakness_taxonomy", [])

    turns: list[dict] = []
    max_turns = min(VALIDATOR.max_debate_turns, 1 + len(student_responses))

    for turn_number in range(1, max_turns + 1):
        student_response = student_responses[turn_number - 2] if turn_number > 1 else None
        escalation = get_escalation_instruction(turn_number)
        system_instruction = f"{persona.anchor}\n\n{escalation}"
        prompt = _build_prompt(
            essay_text=essay_text,
            summary=summary,
            turn=turn_number,
            prior_turns=turns,
            student_response=student_response,
            prior_weaknesses=prior_weaknesses,
        )

        question = None
        for _attempt in range(VALIDATOR.max_regeneration_retries + 1):
            try:
                candidate = generate_text(model=GEMINI.flash_model, system_instruction=system_instruction, prompt=prompt)
            except LLMGenerationError:
                # Gemini itself is down (not just a bad-content regenerate) --
                # no point burning remaining attempts on the same outage;
                # go straight to the persona fallback for this turn.
                break
            if validate_debate_turn(candidate).passed:
                question = candidate
                break
        if question is None:
            question = _PERSONA_FALLBACK_QUESTIONS.get(persona_id, _DEFAULT_FALLBACK_QUESTION)

        turns.append(
            {
                "turn": turn_number,
                "persona": persona_id,
                "question": question,
                "student_response": student_response,
            }
        )

    ctx.state["debate_turns"] = turns
    return {"debate_turns": turns}
