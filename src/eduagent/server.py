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

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse

from eduagent.aggregator.class_aggregator import process_event
from eduagent.aggregator.digest_store import list_recent_digests
from eduagent.api import (
    DebateSessionComplete,
    DebateStartFromImageRequest,
    DebateStartRequest,
    DebateTurnRequest,
    UnknownSessionError,
    start_debate,
    start_debate_from_image,
    submit_debate_turn,
)
from eduagent.demo_page import DEMO_PAGE_HTML
from eduagent.logging_config import configure_json_logging
from eduagent.memory.firestore_memory import list_students_by_class

configure_json_logging()
_logger = logging.getLogger(__name__)

app = FastAPI(title="eduagent-class-aggregator")


@app.get("/", response_class=HTMLResponse)
@app.get("/demo", response_class=HTMLResponse)
async def demo_page() -> HTMLResponse:
    """ĐỢT 3 #2: a human (or a judge) opening the live Cloud Run URL in a
    browser previously got nothing but the Pub/Sub push endpoint's own
    handler (POST-only, so GET / fell through to FastAPI's default 404).
    This is a GET route -- it does not collide with the POST / push
    endpoint below, which Pub/Sub still calls exactly as before."""
    return HTMLResponse(DEMO_PAGE_HTML)


@app.post("/api/debate/start")
async def api_debate_start(payload: DebateStartRequest) -> dict:
    try:
        return start_debate(payload)
    except Exception:
        _logger.exception("start_debate failed")
        raise HTTPException(status_code=502, detail="Failed to start debate session -- check server logs.")


@app.post("/api/debate/start-with-image")
async def api_debate_start_with_image(payload: DebateStartFromImageRequest) -> dict:
    try:
        return start_debate_from_image(payload)
    except Exception:
        _logger.exception("start_debate_from_image failed")
        raise HTTPException(status_code=502, detail="Failed to start debate session from image -- check server logs.")


@app.post("/api/debate/turn")
async def api_debate_turn(payload: DebateTurnRequest) -> dict:
    try:
        return submit_debate_turn(payload)
    except UnknownSessionError:
        raise HTTPException(status_code=404, detail=f"Unknown session_id: {payload.session_id!r}")
    except DebateSessionComplete as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/api/classes/{class_id}/analytics")
async def api_class_analytics(class_id: str, limit: int = 10) -> dict:
    try:
        digests = list_recent_digests(class_id=class_id, limit=limit)
    except Exception:
        _logger.exception("list_recent_digests failed for class_id=%s", class_id)
        raise HTTPException(status_code=503, detail="Firestore unavailable -- try again shortly.")
    return {"class_id": class_id, "digests": digests}


@app.get("/api/classes/{class_id}/students")
async def api_class_students(class_id: str, limit: int = 50) -> dict:
    """ĐỢT 3: class roster ordered by most-recently-active student, backed
    by the composite index in firestore.indexes.json -- see
    memory/firestore_memory.py::list_students_by_class."""
    try:
        students = list_students_by_class(class_id, limit=limit)
    except Exception:
        _logger.exception("list_students_by_class failed for class_id=%s", class_id)
        raise HTTPException(status_code=503, detail="Firestore unavailable -- try again shortly.")
    return {"class_id": class_id, "students": students}


@app.get("/health-check")
async def health_check() -> dict:
    """Cloud Run / uptime-check target -- deliberately does NOT touch
    Firestore/Pub/Sub/Vertex AI, so a transient GCP hiccup elsewhere doesn't
    make Cloud Run think this revision itself is unhealthy and restart it.

    NOT named '/healthz': real deploy testing found that exact path is
    intercepted by Cloud Run's underlying Knative/Istio infrastructure
    before requests ever reach this container or even the IAM auth check --
    every other path (including '/healthz/' with a trailing slash) proxies
    through correctly, only the literal '/healthz' does not.
    """
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
