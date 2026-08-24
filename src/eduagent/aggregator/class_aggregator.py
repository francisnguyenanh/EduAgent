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

from opentelemetry import trace

from eduagent.aggregator.digest import synthesize_digest
from eduagent.aggregator.digest_store import persist_digest
from eduagent.aggregator.idempotency import claim_event
from eduagent.aggregator.priority_engine import cluster_fallacies, common_fallacies, rank_students
from eduagent.config import FIRESTORE, SHEETS, TEACHER
from eduagent.logging_config import configure_json_logging
from eduagent.tracing import configure_tracing

_logger = logging.getLogger(__name__)
_tracer = trace.get_tracer("eduagent")


def load_class_profiles(class_id: str) -> dict[str, dict]:
    from google.cloud import firestore

    db = firestore.Client()
    query = db.collection(FIRESTORE.student_profiles_collection).where(
        filter=firestore.FieldFilter("class_id", "==", class_id)
    )
    return {doc.id: doc.to_dict() for doc in query.stream()}


def _display_name(student_id: str, name_by_id: dict[str, str]) -> str:
    """'Binh (stu_stuck)' when a real name is known, else just the raw id --
    the LLM digest only ever sees/echoes student_id (build_digest_prompt in
    digest.py), so the human-friendly name is resolved here deterministically
    from the ranking data instead of trusting the LLM to spell it right."""
    name = name_by_id.get(student_id)
    return f"{name} ({student_id})" if name else student_id


def format_digest_email(digest: dict, name_by_id: dict[str, str] | None = None) -> str:
    name_by_id = name_by_id or {}
    lines = [digest["headline"], ""]
    if digest["priority_students"]:
        lines.append("Students to check on first:")
        for p in digest["priority_students"]:
            lines.append(f"  - {_display_name(p['student_id'], name_by_id)}: {p['why']}")
        lines.append("")
    if digest["class_wide_pattern"]:
        lines.append(f"Class-wide pattern: {digest['class_wide_pattern']}")
    if digest["mini_lesson_suggestion"]:
        lines.append(f"Suggested mini-lesson: {digest['mini_lesson_suggestion']}")
    return "\n".join(lines)


def _priority_badges(reason: dict) -> str:
    badges = []
    if reason.get("stuck_streak_count", 0) >= 3:
        badges.append('<span style="background:#fde2e1;color:#9b1c1c;padding:2px 8px;border-radius:10px;font-size:12px;">stuck streak</span>')
    if reason.get("score_trend") == "declining":
        badges.append('<span style="background:#fef3c7;color:#92400e;padding:2px 8px;border-radius:10px;font-size:12px;">declining</span>')
    if reason.get("inactivity_days", 0) >= 14:
        badges.append('<span style="background:#e5e7eb;color:#374151;padding:2px 8px;border-radius:10px;font-size:12px;">inactive</span>')
    if reason.get("shared_fallacies"):
        badges.append('<span style="background:#dbeafe;color:#1e3a8a;padding:2px 8px;border-radius:10px;font-size:12px;">shared fallacy</span>')
    return " ".join(badges)


def format_digest_email_html(digest: dict, ranked_students: list[dict], name_by_id: dict[str, str] | None = None) -> str:
    """Same content as format_digest_email(), rendered as an HTML table with
    priority index + status badges and a boxed mini-lesson suggestion --
    intended to read as a professional teacher-facing report inside Gmail
    rather than a plain-text dump. The plain-text version stays the source
    of truth for content; this only changes presentation."""
    name_by_id = name_by_id or {}
    breakdown_by_id = {r["student_id"]: r for r in ranked_students}

    rows = []
    for p in digest["priority_students"]:
        r = breakdown_by_id.get(p["student_id"], {})
        rows.append(
            "<tr>"
            f"<td style=\"padding:6px 10px;border-bottom:1px solid #e5e7eb;\">{_display_name(p['student_id'], name_by_id)}</td>"
            f"<td style=\"padding:6px 10px;border-bottom:1px solid #e5e7eb;text-align:right;\">{r.get('priority', '')}</td>"
            f"<td style=\"padding:6px 10px;border-bottom:1px solid #e5e7eb;\">{_priority_badges(r.get('reason', {}))}</td>"
            f"<td style=\"padding:6px 10px;border-bottom:1px solid #e5e7eb;\">{p['why']}</td>"
            "</tr>"
        )

    table = ""
    if rows:
        table = (
            '<table style="border-collapse:collapse;width:100%;font-family:Arial,sans-serif;font-size:13px;">'
            "<tr>"
            '<th style="text-align:left;padding:6px 10px;border-bottom:2px solid #111827;">Student</th>'
            '<th style="text-align:right;padding:6px 10px;border-bottom:2px solid #111827;">Priority</th>'
            '<th style="text-align:left;padding:6px 10px;border-bottom:2px solid #111827;">Status</th>'
            '<th style="text-align:left;padding:6px 10px;border-bottom:2px solid #111827;">Why</th>'
            "</tr>" + "".join(rows) + "</table>"
        )

    mini_lesson = ""
    if digest["mini_lesson_suggestion"]:
        mini_lesson = (
            '<div style="margin-top:16px;padding:12px 16px;background:#f0fdf4;border-left:4px solid #16a34a;'
            'font-family:Arial,sans-serif;font-size:13px;">'
            f"<strong>Suggested mini-lesson:</strong> {digest['mini_lesson_suggestion']}</div>"
        )

    class_pattern = (
        f'<p style="font-family:Arial,sans-serif;font-size:13px;">Class-wide pattern: {digest["class_wide_pattern"]}</p>'
        if digest["class_wide_pattern"]
        else ""
    )

    return (
        f'<div style="font-family:Arial,sans-serif;">'
        f'<h2 style="font-size:16px;">{digest["headline"]}</h2>'
        f"{table}{class_pattern}{mini_lesson}"
        "</div>"
    )


async def process_event(event: dict) -> dict:
    """event: {event_id, student_id, class_id, essay_id} from essay.evaluated.

    Returns a result dict describing what happened -- always, even on the
    idempotency-skip path -- so callers/logs can tell a duplicate delivery
    from a real processing failure.
    """
    configure_tracing()
    configure_json_logging()
    event_id = event["event_id"]
    class_id = event["class_id"]

    with _tracer.start_as_current_span("eduagent.node.class_aggregator") as span:
        span.set_attribute("eduagent.event_id", event_id)
        span.set_attribute("eduagent.class_id", class_id)
        result = await _process_event_traced(event_id, class_id)
        span.set_attribute("eduagent.status", result["status"])
        return result


async def _process_event_traced(event_id: str, class_id: str) -> dict:
    if not claim_event(event_id):
        _logger.info("Skipping duplicate delivery", extra={"event_id": event_id, "class_id": class_id})
        return {"status": "skipped_duplicate", "event_id": event_id}

    profiles = load_class_profiles(class_id)
    if not profiles:
        return {"status": "no_profiles", "event_id": event_id, "class_id": class_id}

    now = datetime.now(timezone.utc)
    ranked = rank_students(profiles, now=now)
    fallacies = common_fallacies(cluster_fallacies(profiles))

    digest = await synthesize_digest(ranked_students=ranked, common_fallacies=fallacies)
    name_by_id = {r["student_id"]: r["name"] for r in ranked}

    # Gmail and Sheets are independent side effects -- one failing must not
    # prevent the other (PHASE 4: "Gmail MCP loi -> digest van duoc luu
    # Firestore + hien tren Web UI, khong mat du lieu"). The digest itself
    # (the actual analysis) already exists in `digest` regardless of what
    # happens below; only the delivery channels can fail here.
    draft_id = None
    if TEACHER.email:
        try:
            from eduagent.integrations.gmail_mcp import create_digest_draft

            draft_id = create_digest_draft(
                to_address=TEACHER.email,
                subject=f"[eduagent] Class digest for {class_id}: {digest['headline'][:60]}",
                body_text=format_digest_email(digest, name_by_id),
                body_html=format_digest_email_html(digest, ranked, name_by_id),
            )
        except Exception:
            _logger.exception("Failed to create Gmail draft -- digest still returned/logged", extra={"class_id": class_id, "event_id": event_id})

    if SHEETS.audit_spreadsheet_id:
        try:
            from eduagent.integrations.sheets_mcp import append_audit_row

            append_audit_row(
                spreadsheet_id=SHEETS.audit_spreadsheet_id,
                row=[
                    now.isoformat(),
                    class_id,
                    "digest_created",
                    digest["headline"],
                    ", ".join(_display_name(p["student_id"], name_by_id) for p in digest["priority_students"]),
                    draft_id or "",
                ],
            )
        except Exception:
            _logger.exception(
                "Failed to append Sheets audit row -- draft_id not lost, just not logged",
                extra={"class_id": class_id, "event_id": event_id, "draft_id": draft_id},
            )

    try:
        persist_digest(
            class_id=class_id,
            digest_id=event_id,
            digest=digest,
            ranked_students=ranked,
            common_fallacies=fallacies,
            gmail_draft_id=draft_id,
            now=now,
        )
    except Exception:
        # History/Web-UI visibility, not the digest itself -- Gmail draft and
        # Sheets row (the teacher-facing outputs) already succeeded/failed
        # independently above, so a Firestore write failure here must not
        # turn an otherwise-successful digest into a reported failure.
        _logger.exception("Failed to persist digest to class_analytics -- Gmail/Sheets outputs unaffected", extra={"class_id": class_id, "event_id": event_id})

    return {
        "status": "processed",
        "event_id": event_id,
        "class_id": class_id,
        "ranked_students": ranked,
        "common_fallacies": fallacies,
        "digest": digest,
        "gmail_draft_id": draft_id,
    }
