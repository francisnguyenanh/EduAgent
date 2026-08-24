"""Pub/Sub publisher for the essay.evaluated event -- the Tier 1 -> Tier 2
handoff. Kept as a thin wrapper: publishing failure must never lose the
essay result that's already safely committed to Firestore (mutator.py calls
this AFTER the Firestore write, and treats a publish failure as non-fatal --
see PHASE 4 for the retry/backoff hardening around this).
"""

from __future__ import annotations

import functools
import json

from google.cloud import pubsub_v1

from eduagent.config import PUBSUB


@functools.lru_cache(maxsize=1)
def _publisher() -> pubsub_v1.PublisherClient:
    return pubsub_v1.PublisherClient()


def _topic_path() -> str:
    return _publisher().topic_path(PUBSUB.project_id, PUBSUB.essay_evaluated_topic)


def publish_essay_evaluated(*, event_id: str, student_id: str, class_id: str, essay_id: str) -> str:
    """Publishes the event and returns the Pub/Sub message_id.

    `event_id` is OUR idempotency key (distinct from Pub/Sub's own message_id)
    -- the Class Aggregator subscriber dedupes on this, not on message_id,
    because message_id is only unique per-topic, not meaningful for "have I
    already processed this essay" business logic.
    """
    payload = {
        "event_id": event_id,
        "student_id": student_id,
        "class_id": class_id,
        "essay_id": essay_id,
    }
    future = _publisher().publish(_topic_path(), json.dumps(payload).encode("utf-8"))
    return future.result(timeout=30)
