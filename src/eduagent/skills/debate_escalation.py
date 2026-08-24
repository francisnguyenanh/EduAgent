"""Escalation logic for the 3-turn Debate Loop, kept in its own module
(PROJECT_WIKI.md 8.1: "escalation logic to be in a separate skill file").

Turn 1 opens with a targeted question. Turn 2 pushes on the weakest point of
whatever the student answered in turn 1. Turn 3 forces a final defense or
concession, then the loop ends -- there is no turn 4. This keeps the Debate
Agent's job deterministic in SHAPE (always exactly 3 turns, always escalating)
even though the content of each turn is LLM-generated.
"""

from __future__ import annotations

from eduagent.config import VALIDATOR

ESCALATION_INSTRUCTIONS: dict[int, str] = {
    1: (
        "This is turn 1 of 3. Ask ONE opening Socratic question that targets the "
        "single weakest point in the student's essay, from your persona's point of "
        "view. Do not lecture. Do not summarize the essay back to them. End with a "
        "question mark."
    ),
    2: (
        "This is turn 2 of 3. The student just responded to your opening question. "
        "Push harder on the weakest part of THEIR RESPONSE (not the original essay) "
        "-- if they gave an example, ask if it generalizes; if they cited a source, "
        "ask about its reliability; if they conceded a point, ask what that means for "
        "their overall conclusion. Stay in character. End with a question mark."
    ),
    3: (
        "This is turn 3 of 3, the final turn. Ask one question that forces the "
        "student to either defend their original claim with everything they've "
        "argued so far, or explicitly state what they would now revise. This is the "
        "last exchange -- do not open a new line of attack you won't follow up on."
    ),
}


def get_escalation_instruction(turn: int) -> str:
    if turn not in ESCALATION_INSTRUCTIONS:
        raise ValueError(f"turn must be 1..{VALIDATOR.max_debate_turns}, got {turn}")
    return ESCALATION_INSTRUCTIONS[turn]
