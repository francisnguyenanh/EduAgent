"""Unit tests for the Cloud Run push-subscriber HTTP entrypoint
(server.py). Mocks process_event() -- these must not touch real
Firestore/Pub/Sub/Gmail/Sheets, same discipline as test_class_aggregator.py.
"""

from __future__ import annotations

import base64
import dataclasses
import json
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from eduagent.config import PUBSUB
from eduagent.server import app

client = TestClient(app)


def _push_envelope(event: dict) -> dict:
    data = base64.b64encode(json.dumps(event).encode("utf-8")).decode("ascii")
    return {"message": {"data": data, "messageId": "m1"}, "subscription": "projects/p/subscriptions/s"}


def test_health_check_returns_ok_without_touching_gcp():
    response = client.get("/health-check")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def _bypass_push_auth():
    """ADR-014: POST / now verifies a real Pub/Sub OIDC token
    (google_id_token.verify_oauth2_token against Google's live public keys)
    before ever looking at the envelope. Tests exercising envelope/
    process_event behavior bypass that check the same way they already mock
    process_event() itself -- test_pubsub_push_auth.py below tests the
    verification logic in isolation instead."""
    return patch("eduagent.server._verify_pubsub_push_auth", return_value=None)


def test_pubsub_push_calls_process_event_and_returns_its_result():
    event = {"event_id": "e1", "student_id": "s1", "class_id": "c1", "essay_id": "e1"}
    fake_result = {"status": "processed", "event_id": "e1"}

    with _bypass_push_auth(), patch(
        "eduagent.server.process_event", new_callable=AsyncMock, return_value=fake_result
    ) as mock_process:
        response = client.post("/", json=_push_envelope(event))

    assert response.status_code == 200
    assert response.json() == fake_result
    mock_process.assert_awaited_once_with(event)


def test_pubsub_push_returns_500_when_process_event_raises_so_pubsub_retries():
    event = {"event_id": "e2", "student_id": "s1", "class_id": "c1", "essay_id": "e1"}

    with _bypass_push_auth(), patch(
        "eduagent.server.process_event", new_callable=AsyncMock, side_effect=RuntimeError("boom")
    ):
        response = client.post("/", json=_push_envelope(event))

    assert response.status_code == 500


def test_pubsub_push_drops_malformed_envelope_with_200_instead_of_retry_loop():
    with _bypass_push_auth(), patch("eduagent.server.process_event", new_callable=AsyncMock) as mock_process:
        response = client.post("/", json={"not_a_message": True})

    assert response.status_code == 200
    mock_process.assert_not_awaited()


def test_pubsub_push_drops_undecodable_payload_with_200():
    with _bypass_push_auth(), patch("eduagent.server.process_event", new_callable=AsyncMock) as mock_process:
        response = client.post("/", json={"message": {"data": "not-valid-base64-json!!"}})

    assert response.status_code == 200
    mock_process.assert_not_awaited()


def test_pubsub_push_rejects_missing_authorization_header_without_calling_process_event():
    """Blocker fix: with the service deployed --allow-unauthenticated,
    this is the only thing standing between the public internet and a
    Vertex-AI-costed process_event() call."""
    event = {"event_id": "e3", "student_id": "s1", "class_id": "c1", "essay_id": "e1"}

    with patch("eduagent.server.process_event", new_callable=AsyncMock) as mock_process:
        response = client.post("/", json=_push_envelope(event))

    assert response.status_code == 401
    mock_process.assert_not_awaited()


def test_pubsub_push_rejects_malformed_authorization_header():
    event = {"event_id": "e4", "student_id": "s1", "class_id": "c1", "essay_id": "e1"}

    with patch("eduagent.server.process_event", new_callable=AsyncMock) as mock_process:
        response = client.post(
            "/", json=_push_envelope(event), headers={"Authorization": "not-a-bearer-token"}
        )

    assert response.status_code == 401
    mock_process.assert_not_awaited()


def test_pubsub_push_rejects_invalid_oidc_token():
    """A syntactically-present but cryptographically invalid/expired token
    must be rejected -- verify_oauth2_token() is the real Google library
    call, not a mock, so this exercises the actual signature check path."""
    event = {"event_id": "e5", "student_id": "s1", "class_id": "c1", "essay_id": "e1"}

    with patch("eduagent.server.process_event", new_callable=AsyncMock) as mock_process:
        response = client.post(
            "/", json=_push_envelope(event), headers={"Authorization": "Bearer not-a-real-jwt"}
        )

    assert response.status_code == 401
    mock_process.assert_not_awaited()


def test_pubsub_push_rejects_valid_token_from_wrong_service_account():
    """Even a cryptographically valid Google-signed token must be rejected
    if PUBSUB_PUSH_SERVICE_ACCOUNT is configured and the token was issued to
    a different identity -- pins caller identity the same way ADR-013 pins
    class_id for teacher/student API tokens."""
    event = {"event_id": "e6", "student_id": "s1", "class_id": "c1", "essay_id": "e1"}
    fake_claims = {"email": "someone-else@attacker-project.iam.gserviceaccount.com"}
    pinned_pubsub = dataclasses.replace(
        PUBSUB, push_service_account="eduagent-pubsub-invoker@project.iam.gserviceaccount.com"
    )

    with patch("eduagent.server.PUBSUB", pinned_pubsub), patch(
        "eduagent.server.google_id_token.verify_oauth2_token", return_value=fake_claims
    ), patch("eduagent.server.process_event", new_callable=AsyncMock) as mock_process:
        response = client.post(
            "/", json=_push_envelope(event), headers={"Authorization": "Bearer looks-valid"}
        )

    assert response.status_code == 401
    mock_process.assert_not_awaited()


def test_pubsub_push_accepts_valid_token_matching_expected_service_account():
    event = {"event_id": "e7", "student_id": "s1", "class_id": "c1", "essay_id": "e1"}
    fake_result = {"status": "processed", "event_id": "e7"}
    fake_claims = {"email": "eduagent-pubsub-invoker@project.iam.gserviceaccount.com"}
    pinned_pubsub = dataclasses.replace(
        PUBSUB, push_service_account="eduagent-pubsub-invoker@project.iam.gserviceaccount.com"
    )

    with patch("eduagent.server.PUBSUB", pinned_pubsub), patch(
        "eduagent.server.google_id_token.verify_oauth2_token", return_value=fake_claims
    ), patch("eduagent.server.process_event", new_callable=AsyncMock, return_value=fake_result) as mock_process:
        response = client.post(
            "/", json=_push_envelope(event), headers={"Authorization": "Bearer looks-valid"}
        )

    assert response.status_code == 200
    mock_process.assert_awaited_once_with(event)
