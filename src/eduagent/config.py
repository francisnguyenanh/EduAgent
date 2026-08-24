"""Central configuration: env vars and audit-able constants.

Deterministic constants (e.g. Intervention Priority Index weights) live here,
in code, so they can be inspected/audited — never inferred by an LLM.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class GeminiConfig:
    """Vertex AI-backed Gemini config (uses the eduagent-sa ADC, not a raw API key).

    ADR-002: `gemini-3.5-pro` does not exist as a publisher model in this
    project/region (verified via client.models.list() during Phase 1 setup —
    only the Flash lineage — 3.5/3.6/3.7 — and image variants are available).
    `heavy_model` substitutes a newer Flash release for tasks that need
    deeper reasoning (e.g. Teacher Digest Synthesizer); it still satisfies the
    hackathon's "Gemini 3.5 or newer" requirement since 3.7 > 3.5.
    """

    flash_model: str = os.getenv("EDUAGENT_FLASH_MODEL", "gemini-3.5-flash")
    heavy_model: str = os.getenv("EDUAGENT_HEAVY_MODEL", "gemini-3.7-flash")
    use_vertexai: bool = os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "True").lower() != "false"
    vertex_location: str = os.getenv("GOOGLE_CLOUD_LOCATION", "global")


@dataclass(frozen=True)
class FirestoreConfig:
    project_id: str = os.getenv("GCP_PROJECT_ID", "")
    student_profiles_collection: str = "student_profiles"
    class_analytics_collection: str = "class_analytics"
    audit_log_collection: str = "system_audit_logs"
    processed_events_collection: str = "processed_events"


@dataclass(frozen=True)
class PubSubConfig:
    project_id: str = os.getenv("GCP_PROJECT_ID", "")
    essay_evaluated_topic: str = "essay-evaluated"
    class_aggregator_subscription: str = "class-aggregator-sub"
    dead_letter_topic: str = "essay-evaluated-dlq"
    # ADR-003: Google Pub/Sub enforces a platform minimum of 5 for
    # max-delivery-attempts (a subscription create with 3 was rejected) --
    # the TODO.md plan's "fail 3 times -> DLQ" is implemented as 5, the
    # platform floor, not a design choice.
    max_delivery_attempts: int = 5


@dataclass(frozen=True)
class SheetsConfig:
    audit_spreadsheet_id: str = os.getenv("EDUAGENT_AUDIT_SPREADSHEET_ID", "")


@dataclass(frozen=True)
class TeacherConfig:
    email: str = os.getenv("EDUAGENT_TEACHER_EMAIL", "")


@dataclass(frozen=True)
class PriorityWeights:
    """Weights for the Intervention Priority Index (Phase 3, deterministic).

    Priority = w1*stuck_streak + w2*score_decline + w3*inactivity_days + w4*shared_fallacy_weight

    Chosen so that a student stuck on the same persona for 3+ essays without
    improvement (w1) outweighs a single missed submission (w3) — persistent
    non-progress is a stronger signal than a one-off gap. Values are placeholders
    to be tuned against seed data in Phase 2/3; keep them here, not in a prompt,
    so the ranking stays explainable to teachers.
    """

    stuck_streak: float = 3.0
    score_decline: float = 2.5
    inactivity_days: float = 1.0
    shared_fallacy_weight: float = 1.5


@dataclass(frozen=True)
class ValidatorConfig:
    """Deterministic guardrails for the Challenge Validator function node."""

    max_response_chars: int = 600
    min_response_chars: int = 20
    max_debate_turns: int = 3
    max_regeneration_retries: int = 2


GEMINI = GeminiConfig()
FIRESTORE = FirestoreConfig()
PUBSUB = PubSubConfig()
SHEETS = SheetsConfig()
TEACHER = TeacherConfig()
PRIORITY_WEIGHTS = PriorityWeights()
VALIDATOR = ValidatorConfig()
