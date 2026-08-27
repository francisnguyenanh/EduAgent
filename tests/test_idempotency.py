"""Tier-A coverage (Audit Wave 24): the Pub/Sub duplicate-delivery guard.

Why this file exists: Pub/Sub is at-least-once, so `claim_event()`'s
AlreadyExists branch is not an edge case -- it is a branch production WILL
take, every time a subscriber restarts mid-ack or a delivery is retried. It
had 57% coverage and no test at all, which meant the one mechanism standing
between a redelivered message and a second (LLM-costed) teacher digest plus a
second Gmail draft was unverified.

No SDK mocking beyond a fake collection/document: the logic under test is
"which branch does an AlreadyExists take", not "does firestore work".
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from google.api_core import exceptions as gcp_exceptions

from eduagent.aggregator import idempotency


def _fake_client(*, create_raises=None, exists=True):
    doc = MagicMock()
    if create_raises is not None:
        doc.create.side_effect = create_raises
    snapshot = MagicMock()
    snapshot.exists = exists
    doc.get.return_value = snapshot
    client = MagicMock()
    client.collection.return_value.document.return_value = doc
    return client, doc


def test_first_delivery_wins_the_claim():
    client, doc = _fake_client()
    with patch.object(idempotency, "_client", return_value=client):
        assert idempotency.claim_event("evt-1") is True
    # The claim is a create(), not a set() -- set() would overwrite an existing
    # claim and let BOTH deliveries think they won.
    doc.create.assert_called_once()
    assert "claimed_at" in doc.create.call_args[0][0]


def test_duplicate_delivery_loses_the_claim_and_does_not_raise():
    """The branch production actually takes on redelivery. If AlreadyExists
    escaped instead of returning False, the subscriber would 500 and Pub/Sub
    would redeliver again -- an infinite redelivery loop on a message that was
    already processed correctly."""
    client, _ = _fake_client(create_raises=gcp_exceptions.AlreadyExists("evt-1"))
    with patch.object(idempotency, "_client", return_value=client):
        assert idempotency.claim_event("evt-1") is False


def test_a_transient_firestore_error_is_not_mistaken_for_a_duplicate():
    """ServiceUnavailable must NOT be swallowed as 'already claimed' -- that
    would silently drop a real, unprocessed essay event. It is retried by
    with_gcp_retry and then propagates."""
    client, _ = _fake_client(create_raises=gcp_exceptions.ServiceUnavailable("firestore down"))
    with patch.object(idempotency, "_client", return_value=client), patch("time.sleep", return_value=None):
        with pytest.raises(gcp_exceptions.ServiceUnavailable):
            idempotency.claim_event("evt-1")


def test_permission_denied_is_not_retried_and_not_swallowed():
    """A 403 fails identically on retry; retrying just delays the real failure."""
    client, doc = _fake_client(create_raises=gcp_exceptions.PermissionDenied("no access"))
    with patch.object(idempotency, "_client", return_value=client):
        with pytest.raises(gcp_exceptions.PermissionDenied):
            idempotency.claim_event("evt-1")
    assert doc.create.call_count == 1


def test_is_event_processed_reports_document_existence():
    client, _ = _fake_client(exists=True)
    with patch.object(idempotency, "_client", return_value=client):
        assert idempotency.is_event_processed("evt-1") is True

    client, _ = _fake_client(exists=False)
    with patch.object(idempotency, "_client", return_value=client):
        assert idempotency.is_event_processed("evt-2") is False
