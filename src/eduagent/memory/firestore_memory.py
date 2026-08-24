"""Firestore-backed long-term memory for student profiles.

This is the ADK "Memory" side (cross-session, PROJECT_WIKI.md 7.5.6), as
opposed to Context.state which only lives for the duration of one pipeline
run. Read-modify-write is done via a Firestore transaction so two essays
graded for the same student around the same time can't clobber each other's
history (a real failure mode once Tier 2 runs concurrently in Phase 3).
"""

from __future__ import annotations

import functools

from google.cloud import firestore

from eduagent.config import FIRESTORE
from eduagent.memory.student_profile import empty_profile, merge_essay_into_profile
from eduagent.resilience import with_gcp_retry


@functools.lru_cache(maxsize=1)
def _client() -> firestore.Client:
    return firestore.Client()


@with_gcp_retry
def get_profile(student_id: str) -> dict | None:
    doc = _client().collection(FIRESTORE.student_profiles_collection).document(student_id).get()
    return doc.to_dict() if doc.exists else None


@with_gcp_retry
def list_students_by_class(class_id: str, *, limit: int = 50) -> list[dict]:
    """ĐỢT 3 storage/retrieval optimization: a class roster view (Teacher Web
    UI) ordered by most-recently-active student, instead of loading every
    profile unordered (what class_aggregator.load_class_profiles does for
    full-class ranking -- a different, batch use case). Needs the composite
    index declared in firestore.indexes.json (class_id ASC, flags.last_updated
    DESC) -- without it Firestore rejects this exact filter+order_by combo
    at query time rather than silently full-scanning."""
    docs = (
        _client()
        .collection(FIRESTORE.student_profiles_collection)
        .where(filter=firestore.FieldFilter("class_id", "==", class_id))
        .order_by("flags.last_updated", direction=firestore.Query.DESCENDING)
        .limit(limit)
        .stream()
    )
    return [{"student_id": doc.id, **doc.to_dict()} for doc in docs]


@with_gcp_retry
def apply_essay_result(
    student_id: str,
    *,
    name: str,
    class_id: str,
    essay_id: str,
    timestamp: str,
    persona_used: str,
    scores: dict,
    weakness_detected: list[str],
    student_feedback: str = "",
) -> dict:
    """Transactional read-modify-write. Returns the profile AFTER merging."""
    doc_ref = _client().collection(FIRESTORE.student_profiles_collection).document(student_id)

    @firestore.transactional
    def _txn(transaction: firestore.Transaction) -> dict:
        snapshot = doc_ref.get(transaction=transaction)
        current = snapshot.to_dict() if snapshot.exists else empty_profile(name=name, class_id=class_id)
        updated = merge_essay_into_profile(
            current,
            essay_id=essay_id,
            timestamp=timestamp,
            persona_used=persona_used,
            scores=scores,
            weakness_detected=weakness_detected,
            student_feedback=student_feedback,
        )
        transaction.set(doc_ref, updated)
        return updated

    return _txn(_client().transaction())
