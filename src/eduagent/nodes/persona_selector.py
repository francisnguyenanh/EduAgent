"""Persona Selector -- deterministic FUNCTION NODE, not an agent node.

PROJECT_WIKI.md 7.5.3: prefer function/deterministic logic wherever LLM
reasoning isn't required. Matching a weakness keyword to a persona focus is a
lookup problem, not a reasoning problem -- so it stays rule-based and
auditable ("why was Skeptic chosen for this student?" has a real answer).

Phase 1: works off the current essay's fallacies_draft only. Phase 2 adds
`ctx.state["persona_history"]` (populated from Firestore student_profile) so
this function avoids repeating a persona the student hasn't improved against.
"""

from __future__ import annotations

from google.adk.agents.context import Context

from eduagent.memory.firestore_memory import get_profile
from eduagent.memory.student_profile import persona_history_from_profile, weakness_taxonomy_from_profile
from eduagent.skills.personas import PERSONA_IDS, get_persona
from eduagent.tracing import traced_node

_FALLACY_KEYWORDS: dict[str, str] = {
    "skeptic": "evidence|source|unsourced|citation|proof|statistic|data",
    "devils_advocate": "counterargument|one-sided|rebuttal|opposing|bias",
    "nitpicker": "logic|assumption|non sequitur|inconsistent|fallacy|contradiction",
    "expander": "generaliz|scope|edge case|context|exception|always|never",
}


def _score_persona(persona_id: str, fallacies_draft: list[str]) -> int:
    import re

    pattern = re.compile(_FALLACY_KEYWORDS[persona_id], re.IGNORECASE)
    return sum(1 for f in fallacies_draft if pattern.search(f))


def choose_persona(
    fallacies_draft: list[str],
    persona_history: list[str] | None = None,
) -> str:
    """Pure function (unit-testable without Context/Firestore)."""
    persona_history = persona_history or []
    last_used = persona_history[-1] if persona_history else None

    scores = {pid: _score_persona(pid, fallacies_draft) for pid in PERSONA_IDS}

    # Avoid immediate repetition unless every other persona scores strictly lower.
    candidates = [pid for pid in PERSONA_IDS if pid != last_used] or list(PERSONA_IDS)
    best = max(candidates, key=lambda pid: scores[pid])

    if scores[best] == 0:
        # No keyword signal at all -- rotate deterministically instead of
        # defaulting to the same persona every time.
        start = (PERSONA_IDS.index(last_used) + 1) % len(PERSONA_IDS) if last_used in PERSONA_IDS else 0
        best = PERSONA_IDS[start]

    return best


@traced_node("persona_selector")
async def persona_selector(ctx: Context) -> dict:
    summary = ctx.state.get("summary", {})
    fallacies_draft = summary.get("fallacies_draft", [])

    student_id = ctx.state.get("student_id")
    profile = get_profile(student_id) if student_id else None
    persona_history = persona_history_from_profile(profile) if profile else []
    prior_weaknesses = weakness_taxonomy_from_profile(profile) if profile else []
    ctx.state["persona_history"] = persona_history  # audit trail for this run
    ctx.state["prior_weakness_taxonomy"] = prior_weaknesses  # consumed by debate_loop for memory injection

    persona_id = choose_persona(fallacies_draft, persona_history)
    persona = get_persona(persona_id)

    ctx.state["stage"] = "persona_selector"
    ctx.state["persona"] = persona_id
    ctx.state["persona_anchor"] = persona.anchor
    return {"persona": persona_id}
