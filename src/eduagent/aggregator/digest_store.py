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
