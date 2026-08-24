"""Tier 1 — Per-Student Adaptive Socratic Pipeline (ADK2 Graph Workflow).

Phase 0: wires stub FunctionNodes into a linear, deterministic-edge graph so
the shape can be verified end-to-end before any real agent/LLM logic exists.
Escalation/branching (Debate <-> Validator retry loop) is added in Phase 1;
this file intentionally stays linear until then.
"""

from __future__ import annotations

from google.adk.workflow import START, FunctionNode, Workflow

from eduagent.nodes.tier1_stubs import (
    challenge_validator,
    cognitive_scorer,
    debate_loop,
    intake,
    persona_selector,
    profile_mutator,
    sanitizer,
    summarizer,
)

_intake_node = FunctionNode(func=intake, name="intake")
_sanitizer_node = FunctionNode(func=sanitizer, name="sanitizer")
_summarizer_node = FunctionNode(func=summarizer, name="summarizer")
_persona_node = FunctionNode(func=persona_selector, name="persona_selector")
_debate_node = FunctionNode(func=debate_loop, name="debate_loop")
_validator_node = FunctionNode(func=challenge_validator, name="challenge_validator")
_scorer_node = FunctionNode(func=cognitive_scorer, name="cognitive_scorer")
_mutator_node = FunctionNode(func=profile_mutator, name="profile_mutator")


def build_tier1_workflow() -> Workflow:
    """Builds the Tier 1 graph. Called fresh per run to avoid shared state."""
    return Workflow(
        name="tier1_per_student_pipeline",
        description=(
            "Per-student Socratic debate pipeline: intake -> sanitize -> "
            "summarize -> select persona -> debate/validate -> score -> mutate profile."
        ),
        edges=[
            (START, _intake_node),
            (_intake_node, _sanitizer_node),
            (_sanitizer_node, _summarizer_node),
            (_summarizer_node, _persona_node),
            (_persona_node, _debate_node),
            (_debate_node, _validator_node),
            (_validator_node, _scorer_node),
            (_scorer_node, _mutator_node),
        ],
    )
