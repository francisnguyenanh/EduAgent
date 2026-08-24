"""Class Aggregator -- Tier 2 orchestration triggered by essay.evaluated.

Wires together (in order): idempotency claim -> load class profiles from
Firestore -> deterministic ranking (priority_engine, zero LLM) -> Teacher
Digest synthesis (one LLM call, digest.py) -> Gmail draft (compose-only,
never send) -> Sheets audit log (append-only).

This module contains the ORCHESTRATION only -- every step it calls is
independently testable (idempotency.py, priority_engine.py, digest.py,
integrations/*). process_event() itself is exercised with fakes/mocks in
tests/test_class_aggregator.py rather than hitting real Firestore/Gmail/
Sheets on every test run.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from eduagent.aggregator.digest import synthesize_digest
from eduagent.aggregator.idempotency import claim_event
from eduagent.aggregator.priority_engine import cluster_fallacies, common_fallacies, rank_students
from eduagent.config import FIRESTORE, SHEETS, TEACHER

_logger = logging.getLogger(__name__)


def load_class_profiles(class_id: str) -> dict[str, dict]:
    from google.cloud import firestore

    db = firestore.Client()
    query = db.collection(FIRESTORE.student_profiles_collection).where(
        filter=firestore.FieldFilter("class_id", "==", class_id)
    )
    return {doc.id: doc.to_dict() for doc in query.stream()}


def format_digest_email(digest: dict) -> str:
    lines = [digest["headline"], ""]
    if digest["priority_students"]:
        lines.append("Students to check on first:")
        for p in digest["priority_students"]:
            lines.append(f"  - {p['student_id']}: {p['why']}")
        lines.append("")
    if digest["class_wide_pattern"]:
        lines.append(f"Class-wide pattern: {digest['class_wide_pattern']}")
    if digest["mini_lesson_suggestion"]:
        lines.append(f"Suggested mini-lesson: {digest['mini_lesson_suggestion']}")
    return "\n".join(lines)


async def process_event(event: dict) -> dict:
    """event: {event_id, student_id, class_id, essay_id} from essay.evaluated.

    Returns a result dict describing what happened -- always, even on the
    idempotency-skip path -- so callers/logs can tell a duplicate delivery
    from a real processing failure.
    """
    event_id = event["event_id"]
    class_id = event["class_id"]

    if not claim_event(event_id):
        _logger.info("Skipping duplicate delivery of event_id=%s", event_id)
        return {"status": "skipped_duplicate", "event_id": event_id}

    profiles = load_class_profiles(class_id)
    if not profiles:
        return {"status": "no_profiles", "event_id": event_id, "class_id": class_id}

    now = datetime.now(timezone.utc)
    ranked = rank_students(profiles, now=now)
    fallacies = common_fallacies(cluster_fallacies(profiles))

    digest = await synthesize_digest(ranked_students=ranked, common_fallacies=fallacies)

    draft_id = None
    if TEACHER.email:
        from eduagent.integrations.gmail_mcp import create_digest_draft

        draft_id = create_digest_draft(
            to_address=TEACHER.email,
            subject=f"[eduagent] Class digest for {class_id}: {digest['headline'][:60]}",
            body_text=format_digest_email(digest),
        )

    if SHEETS.audit_spreadsheet_id:
        from eduagent.integrations.sheets_mcp import append_audit_row

        append_audit_row(
            spreadsheet_id=SHEETS.audit_spreadsheet_id,
            row=[
                now.isoformat(),
                class_id,
                "digest_created",
                digest["headline"],
                ", ".join(p["student_id"] for p in digest["priority_students"]),
                draft_id or "",
            ],
        )

    return {
        "status": "processed",
        "event_id": event_id,
        "class_id": class_id,
        "ranked_students": ranked,
        "common_fallacies": fallacies,
        "digest": digest,
        "gmail_draft_id": draft_id,
    }
