"""Persist Teacher Digests to Firestore -- the historical record a teacher
(or a future Web UI) can browse across days, not just the one-shot Gmail
draft / Sheets row that already exist per PHASE 3.

Schema: class_analytics/{class_id}/digests/{digest_id}, digest_id == the
Pub/Sub event_id that triggered it (one digest per essay.evaluated event,
naturally idempotent under redelivery -- a retried write just overwrites
the same document with the same content).
"""

from __future__ import annotations

import functools
from datetime import datetime

from google.cloud import firestore

from eduagent.config import FIRESTORE
from eduagent.resilience import with_gcp_retry


@functools.lru_cache(maxsize=1)
def _client() -> firestore.Client:
    return firestore.Client()


@with_gcp_retry
def persist_digest(
    *,
    class_id: str,
    digest_id: str,
    digest: dict,
    ranked_students: list[dict],
    common_fallacies: list[str],
    gmail_draft_id: str | None,
    now: datetime,
) -> None:
    doc_ref = (
        _client()
        .collection(FIRESTORE.class_analytics_collection)
        .document(class_id)
        .collection("digests")
        .document(digest_id)
    )
    doc_ref.set(
        {
            "digest_text": digest,
            "ranked_students": ranked_students,
            "common_fallacies": common_fallacies,
            "gmail_draft_id": gmail_draft_id,
            "timestamp": now.isoformat(),
        }
    )


@with_gcp_retry
def get_last_digest_timestamp(*, class_id: str) -> datetime | None:
    """ĐỢT 3 high-load debounce: the single most recent digest's timestamp
    for this class, or None if it has never had one. Backs
    class_aggregator.py's coalescing check -- kept as its own tiny query
    (limit=1) rather than reusing list_recent_digests(limit=1) so the
    debounce hot path doesn't pull ranked_students/digest_text it doesn't need."""
    docs = list(
        _client()
        .collection(FIRESTORE.class_analytics_collection)
        .document(class_id)
        .collection("digests")
        .order_by("timestamp", direction=firestore.Query.DESCENDING)
        .limit(1)
        .stream()
    )
    if not docs:
        return None
    raw = docs[0].to_dict().get("timestamp")
    return datetime.fromisoformat(raw) if raw else None


DEFAULT_CLASS_SETTINGS = {
    "show_score_radar_to_students": True,
    "stuck_streak_threshold": 3,
    "digest_notify_email": "",
}


@with_gcp_retry
def get_class_settings(*, class_id: str) -> dict:
    """ĐỢT 4 #2 Settings Tab -- pedagogical toggles a teacher can adjust per
    class, stored on the parent `class_analytics/{class_id}` doc (a sibling
    of the `digests` subcollection above, not a new collection) so a class
    with no settings saved yet still resolves cleanly to the defaults."""
    doc = _client().collection(FIRESTORE.class_analytics_collection).document(class_id).get()
    stored = (doc.to_dict() or {}).get("settings", {}) if doc.exists else {}
    return {**DEFAULT_CLASS_SETTINGS, **stored}


@with_gcp_retry
def set_class_settings(*, class_id: str, settings: dict) -> dict:
    """Merges `settings` onto the existing (or default) settings for this
    class and persists it -- a partial update (e.g. only `stuck_streak_threshold`)
    never wipes out other previously-saved toggles."""
    merged = {**get_class_settings(class_id=class_id), **settings}
    _client().collection(FIRESTORE.class_analytics_collection).document(class_id).set(
        {"settings": merged}, merge=True
    )
    return merged


@with_gcp_retry
def list_recent_digests(*, class_id: str, limit: int = 10) -> list[dict]:
    """ĐỢT 3 #2: read path for the Cloud Run analytics endpoint / Web demo --
    newest-first, so a teacher/judge opening the page sees the latest
    Priority Index ranking without having to wait for a fresh essay."""
    docs = (
        _client()
        .collection(FIRESTORE.class_analytics_collection)
        .document(class_id)
        .collection("digests")
        .order_by("timestamp", direction=firestore.Query.DESCENDING)
        .limit(limit)
        .stream()
    )
    return [{"digest_id": doc.id, **doc.to_dict()} for doc in docs]
