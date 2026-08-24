"""Idempotency guard for the Class Aggregator subscriber.

Pub/Sub is at-least-once delivery -- the same essay.evaluated message WILL
arrive more than once eventually (redelivery on a slow ack, a subscriber
restart mid-processing, etc). Without this, a duplicate delivery would
re-run the (LLM-costed) digest synthesis and could produce a second Gmail
draft for the same event.

Uses Firestore's `create()` (fails if the document already exists) as an
atomic claim -- two concurrent deliveries of the same event_id can't both
"win"; exactly one succeeds, the other gets AlreadyExists and skips.
"""

from __future__ import annotations

import functools
from datetime import datetime, timezone

from google.api_core import exceptions as gcp_exceptions
from google.cloud import firestore

from eduagent.config import FIRESTORE
from eduagent.resilience import with_gcp_retry


@functools.lru_cache(maxsize=1)
def _client() -> firestore.Client:
    return firestore.Client()


@with_gcp_retry
def claim_event(event_id: str) -> bool:
    """Returns True if this call is the first to claim event_id (proceed),
    False if it was already claimed (skip -- this is a duplicate delivery)."""
    doc_ref = _client().collection(FIRESTORE.processed_events_collection).document(event_id)
    try:
        doc_ref.create({"claimed_at": datetime.now(timezone.utc).isoformat()})
        return True
    except gcp_exceptions.AlreadyExists:
        return False


def is_event_processed(event_id: str) -> bool:
    doc = _client().collection(FIRESTORE.processed_events_collection).document(event_id).get()
    return doc.exists
