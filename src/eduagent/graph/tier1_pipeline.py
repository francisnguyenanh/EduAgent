"""Tier 1 — Per-Student Adaptive Socratic Pipeline (ADK2 Graph Workflow).

Phase 1: real node logic (LLM calls via Vertex AI + deterministic function
nodes) replaces the Phase 0 stubs. Graph shape stays linear -- branching for
Debate<->Validator retry happens INSIDE debate_loop (see nodes/debate.py),
not as separate graph edges, so the overall pipeline shape stays simple and
auditable.
"""

from __future__ import annotations

from google.adk.workflow import START, FunctionNode, Workflow

from eduagent.nodes.debate import debate_loop
from eduagent.nodes.intake import intake, sanitizer
from eduagent.nodes.mutator import profile_mutator
from eduagent.nodes.persona_selector import persona_selector
from eduagent.nodes.scorer import cognitive_scorer
from eduagent.nodes.summarizer import summarizer
from eduagent.nodes.validator import challenge_validator
from eduagent.logging_config import configure_json_logging
from eduagent.tracing import configure_tracing

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
    configure_tracing()
    configure_json_logging()
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
