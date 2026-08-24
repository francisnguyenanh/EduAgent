"""Cloud Run entrypoint -- Class Aggregator as a Pub/Sub PUSH subscriber.

PHASE 7: replaces scripts/run_class_aggregator_subscriber.py's pull loop
(Phase 3 dev-mode) with the transport Cloud Run actually needs: an HTTPS
endpoint that Pub/Sub calls directly. `process_event()` itself (the actual
business logic -- idempotency, ranking, digest, Gmail/Sheets) is UNCHANGED
from Phase 3, exactly as planned back then ("same process_event() call,
different transport"). This module is transport plumbing only.

Pub/Sub push message contract: https://cloud.google.com/pubsub/docs/push
  POST / with body {"message": {"data": "<base64 essay.evaluated JSON>", ...}}
  - 2xx response -> Pub/Sub acks (success)
  - non-2xx response -> Pub/Sub retries per the subscription's retry policy,
    eventually dead-lettering after PUBSUB.max_delivery_attempts (Phase 3/4)
"""

from __future__ import annotations

import base64
import json
import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from eduagent.aggregator.class_aggregator import process_event
from eduagent.logging_config import configure_json_logging

configure_json_logging()
_logger = logging.getLogger(__name__)

app = FastAPI(title="eduagent-class-aggregator")


@app.get("/healthz")
async def healthz() -> dict:
    """Cloud Run / uptime-check target -- deliberately does NOT touch
    Firestore/Pub/Sub/Vertex AI, so a transient GCP hiccup elsewhere doesn't
    make Cloud Run think this revision itself is unhealthy and restart it."""
    return {"status": "ok"}


@app.post("/")
async def pubsub_push(request: Request) -> JSONResponse:
    envelope = await request.json()
    message = envelope.get("message")
    if not message or "data" not in message:
        # Malformed push request (not a valid Pub/Sub envelope) -- this is a
        # client/config error, not a transient failure. Per PHASE 4's chaos-
        # test finding, retrying a message that will fail identically every
        # time just burns delivery attempts; ack it (200) so Pub/Sub doesn't
        # loop on something that can never succeed, but log loudly so a
        # misconfigured push subscription is visible in Cloud Logging.
        _logger.error("Received push request with no Pub/Sub message.data -- acking and dropping", extra={"envelope": envelope})
        return JSONResponse({"status": "dropped_malformed_envelope"}, status_code=200)

    try:
        event = json.loads(base64.b64decode(message["data"]).decode("utf-8"))
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
        _logger.exception("Failed to decode Pub/Sub push message data -- acking and dropping", extra={"message_id": message.get("messageId")})
        return JSONResponse({"status": "dropped_undecodable_payload"}, status_code=200)

    try:
        result = await process_event(event)
    except Exception:
        # Same discipline as the Phase 3/4 pull subscriber: an exception here
        # means retry (return non-2xx) so Pub/Sub redelivers -- eventually
        # dead-lettering per PUBSUB.max_delivery_attempts -- rather than
        # silently swallowing a real processing failure.
        _logger.exception("process_event() raised -- returning 500 so Pub/Sub retries", extra={"event": event})
        return JSONResponse({"status": "error"}, status_code=500)

    return JSONResponse(result, status_code=200)
