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

    # ADR-028: a DIFFERENT model family for the OCR cross-check's second pass.
    # ADR-007 runs the same model twice, which catches random noise but not a
    # systematic misread -- if Gemini Vision resolves a stroke wrong the same
    # way on both passes, difflib sees two identical strings and reports
    # consensus on a wrong transcription. Gemma is a separate family, so the
    # two errors are uncorrelated.
    gemma_model: str = os.getenv("EDUAGENT_GEMMA_MODEL", "gemma-4-26b-a4b-it-maas")
    # PINNED, not env-derived: Gemma 4 MaaS is served ONLY from the `global`
    # endpoint (us-central1 returns 400 FAILED_PRECONDITION "is only available
    # via global endpoint"; the bare `gemma3`/`gemma4` ids are Model Garden
    # entries needing a self-deployed GPU endpoint and return 404). Inheriting
    # `vertex_location` would silently break the cross-check the moment anyone
    # sets GOOGLE_CLOUD_LOCATION to a region.
    gemma_location: str = "global"
    # The revert switch. Set EDUAGENT_OCR_CROSS_CHECK_GEMMA=false to put the
    # second pass back on Gemini with no code change -- the rollback path for
    # ADR-028's abort conditions (quality regression, latency blowout, or a
    # Gemma 429 rate high enough that "integrated with Gemma" stops being true).
    ocr_cross_check_with_gemma: bool = os.getenv("EDUAGENT_OCR_CROSS_CHECK_GEMMA", "true").lower() != "false"


@dataclass(frozen=True)
class FirestoreConfig:
    project_id: str = os.getenv("GCP_PROJECT_ID", "")
    student_profiles_collection: str = "student_profiles"
    class_analytics_collection: str = "class_analytics"
    audit_log_collection: str = "system_audit_logs"
    processed_events_collection: str = "processed_events"
    pending_essays_collection: str = "pending_essays"


@dataclass(frozen=True)
class PubSubConfig:
    project_id: str = os.getenv("GCP_PROJECT_ID", "")
    essay_evaluated_topic: str = "essay-evaluated"
    class_aggregator_subscription: str = "class-aggregator-sub"
    dead_letter_topic: str = "essay-evaluated-dlq"
    # ADR-003: Google Pub/Sub enforces a platform minimum of 5 for
    # max-delivery-attempts (a subscription create with 3 was rejected) --
    # the original plan's "fail 3 times -> DLQ" is implemented as 5, the
    # platform floor, not a design choice.
    max_delivery_attempts: int = 5
    # Wave 8: the Cloud Run service is deployed --allow-unauthenticated (so
    # judges can open the Web UI without a GCP identity), which means the
    # `POST /` Pub/Sub push endpoint itself is no longer protected by Cloud
    # Run IAM -- it must verify the push subscription's own OIDC token at
    # the application layer instead (see ADR-014). Both are set at deploy
    # time; if either is left unset in production, verify_oauth2_token()
    # still runs (mandatory Google-signed-token check), it just cannot also
    # pin the expected caller identity/audience.
    push_audience: str = os.getenv("PUBSUB_PUSH_AUDIENCE", "")
    push_service_account: str = os.getenv("PUBSUB_PUSH_SERVICE_ACCOUNT", "")


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
              + w5*score_volatility

    Chosen so that a student stuck on the same persona for 3+ essays without
    improvement (w1) outweighs a single missed submission (w3) — persistent
    non-progress is a stronger signal than a one-off gap. Values were tuned
    and frozen against 5-student seed data in Phase 2/3 and verified in Phase 4;
    kept here in deterministic code, not in an LLM prompt, so the ranking
    stays 100% explainable to teachers.
    """

    stuck_streak: float = 3.0
    score_decline: float = 2.5
    inactivity_days: float = 1.0
    shared_fallacy_weight: float = 1.5
    # Wave 15 #3: a score that collapsed and recovered inside the trend window
    # (score_trend == "volatile"). Weighted BELOW score_decline on purpose: an
    # unstable student needs a look, but a student on a sustained downward slope
    # needs it more, and the two are mutually exclusive by construction (a
    # volatile verdict is only reachable when the slope is inside the flat band).
    score_volatility: float = 1.5


@dataclass(frozen=True)
class DigestDebounceConfig:
    """Wave 3 high-load resiliency: if a whole class submits within a short
    window of each other, one digest per essay would spam the teacher's
    inbox. `window_seconds` bounds how often a NEW digest is generated per
    class_id -- a coalesced event still has its underlying student_profile
    write (Tier 1, already durable) untouched; it just skips Tier 2's
    digest/Gmail/Sheets step, which the NEXT event for that class_id (from
    any student) will naturally cover since ranking re-reads every profile
    fresh each time."""

    window_seconds: int = int(os.getenv("EDUAGENT_DIGEST_DEBOUNCE_SECONDS", "120"))




@dataclass(frozen=True)
class CloudRunConfig:
    """PHASE 7 deployed service, referenced only by scripts/doctor.py's remote
    health check (Wave 3 #5) -- never by application code, so a missing/stale
    URL degrades that one check to WARN, not a pipeline failure."""

    service_url: str = os.getenv("EDUAGENT_CLOUD_RUN_URL", "https://eduagent-class-aggregator-636767063018.asia-southeast1.run.app")


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
CLOUD_RUN = CloudRunConfig()
DIGEST_DEBOUNCE = DigestDebounceConfig()
