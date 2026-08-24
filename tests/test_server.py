"""Unit tests for the PHASE 7 Cloud Run push-subscriber HTTP entrypoint
(server.py). Mocks process_event() -- these must not touch real
Firestore/Pub/Sub/Gmail/Sheets, same discipline as test_class_aggregator.py.
"""

from __future__ import annotations

import base64
import json
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from eduagent.server import app

client = TestClient(app)


def _push_envelope(event: dict) -> dict:
    data = base64.b64encode(json.dumps(event).encode("utf-8")).decode("ascii")
    return {"message": {"data": data, "messageId": "m1"}, "subscription": "projects/p/subscriptions/s"}


def test_health_check_returns_ok_without_touching_gcp():
    response = client.get("/health-check")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_pubsub_push_calls_process_event_and_returns_its_result():
    event = {"event_id": "e1", "student_id": "s1", "class_id": "c1", "essay_id": "e1"}
    fake_result = {"status": "processed", "event_id": "e1"}

    with patch("eduagent.server.process_event", new_callable=AsyncMock, return_value=fake_result) as mock_process:
        response = client.post("/", json=_push_envelope(event))

    assert response.status_code == 200
    assert response.json() == fake_result
    mock_process.assert_awaited_once_with(event)


def test_pubsub_push_returns_500_when_process_event_raises_so_pubsub_retries():
    event = {"event_id": "e2", "student_id": "s1", "class_id": "c1", "essay_id": "e1"}

    with patch("eduagent.server.process_event", new_callable=AsyncMock, side_effect=RuntimeError("boom")):
        response = client.post("/", json=_push_envelope(event))

    assert response.status_code == 500


def test_pubsub_push_drops_malformed_envelope_with_200_instead_of_retry_loop():
    with patch("eduagent.server.process_event", new_callable=AsyncMock) as mock_process:
        response = client.post("/", json={"not_a_message": True})

    assert response.status_code == 200
    mock_process.assert_not_awaited()


def test_pubsub_push_drops_undecodable_payload_with_200():
    with patch("eduagent.server.process_event", new_callable=AsyncMock) as mock_process:
        response = client.post("/", json={"message": {"data": "not-valid-base64-json!!"}})

    assert response.status_code == 200
    mock_process.assert_not_awaited()
