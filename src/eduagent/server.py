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

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from google.auth.transport import requests as google_auth_requests
from google.oauth2 import id_token as google_id_token

from eduagent.aggregator.class_aggregator import process_event
from eduagent.aggregator.digest_store import list_recent_digests
from eduagent.api import (
    ClassSettingsRequest,
    TestSheetsRequest,
    DebateSessionComplete,
    DebateStartFromGDocRequest,
    DebateStartFromImageRequest,
    DebateStartRequest,
    DebateTurnRequest,
    DebateReflectionRequest,
    LoginError,
    LoginRequest,
    ParentNoteRequest,
    UnknownSessionError,
    class_priority,
    get_settings,
    login,
    parent_note,
    start_debate,
    start_debate_from_gdoc,
    start_debate_from_image,
    submit_debate_turn,
    submit_reflection,
    update_settings,
    test_sheets_connection,
)

from eduagent.auth import verify_access_token
from eduagent.config import PUBSUB
from eduagent.demo_page import DEMO_PAGE_HTML
from eduagent.logging_config import configure_json_logging
from eduagent.memory.firestore_memory import list_students_by_class

configure_json_logging()
_logger = logging.getLogger(__name__)

app = FastAPI(title="eduagent-class-aggregator")

_google_auth_request = google_auth_requests.Request()


def _verify_pubsub_push_auth(authorization: str | None) -> None:
    """ĐỢT 8 / ADR-014: this service is deployed --allow-unauthenticated so
    judges can open the Web UI without a GCP identity, which means Cloud Run
    IAM no longer protects `POST /` -- this endpoint must authenticate the
    Pub/Sub push subscription's own OIDC token itself, at the application
    layer, or it becomes a public trigger for LLM-costed digest generation.

    Real Pub/Sub push subscriptions always attach `Authorization: Bearer
    <OIDC token>` signed by the subscription's configured service account
    (see https://cloud.google.com/pubsub/docs/authenticate-push-subscriptions).
    google.oauth2.id_token.verify_oauth2_token() cryptographically verifies
    the token against Google's public keys -- a request without a valid,
    unexpired, Google-signed token is rejected regardless of configuration.
    If PUBSUB_PUSH_AUDIENCE / PUBSUB_PUSH_SERVICE_ACCOUNT are also set (as
    they are at real deploy time), the token's audience and calling service
    account identity are pinned too, closing the same class of "any valid
    Google token from anyone" gap that ADR-013 closed for teacher/student API
    tokens.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Pub/Sub push OIDC token.")
    token = authorization.split(" ", 1)[1].strip()
    try:
        claims = google_id_token.verify_oauth2_token(
            token, _google_auth_request, audience=PUBSUB.push_audience or None
        )
    except Exception as exc:
        _logger.warning("Rejected POST / push request with invalid OIDC token: %s", exc)
        raise HTTPException(status_code=401, detail="Invalid Pub/Sub push OIDC token.")

    if PUBSUB.push_service_account and claims.get("email") != PUBSUB.push_service_account:
        _logger.warning(
            "Rejected POST / push request from unexpected service account: %s", claims.get("email")
        )
        raise HTTPException(status_code=401, detail="OIDC token not issued to the expected push service account.")


def _verify_class_auth(class_id: str, authorization: str | None) -> dict:
    """ĐỢT 6 P0 IDOR prevention: verifies the request carries a valid Bearer token
    for the exact class_id in the URL path."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication required: missing or invalid Bearer token.")
    token = authorization.split(" ", 1)[1].strip()
    try:
        claims = verify_access_token(token)
    except LoginError as exc:
        raise HTTPException(status_code=401, detail=f"Invalid authentication token: {exc}")
    except Exception:
        raise HTTPException(status_code=401, detail="Failed to verify authentication token.")

    if claims.get("class_id") != class_id:
        raise HTTPException(
            status_code=403,
            detail=f"Forbidden: token for class {claims.get('class_id')!r} cannot access class {class_id!r}.",
        )
    return claims


@app.get("/", response_class=HTMLResponse)
@app.get("/demo", response_class=HTMLResponse)
async def demo_page() -> HTMLResponse:
    """ĐỢT 3 #2: a human (or a judge) opening the live Cloud Run URL in a
    browser previously got nothing but the Pub/Sub push endpoint's own
    handler (POST-only, so GET / fell through to FastAPI's default 404).
    This is a GET route -- it does not collide with the POST / push
    endpoint below, which Pub/Sub still calls exactly as before."""
    return HTMLResponse(DEMO_PAGE_HTML)


@app.post("/api/auth/login")
async def api_login(payload: LoginRequest) -> dict:
    try:
        return login(payload)
    except LoginError as exc:
        raise HTTPException(status_code=401, detail=str(exc))


@app.get("/api/classes/{class_id}/priority")
async def api_class_priority(class_id: str, authorization: str | None = Header(None)) -> dict:
    _verify_class_auth(class_id, authorization)
    try:
        return class_priority(class_id)
    except Exception:
        _logger.exception("class_priority failed for class_id=%s", class_id)
        raise HTTPException(status_code=503, detail="Firestore unavailable -- try again shortly.")


@app.get("/api/classes/{class_id}/settings")
async def api_get_settings(class_id: str, authorization: str | None = Header(None)) -> dict:
    _verify_class_auth(class_id, authorization)
    try:
        return get_settings(class_id)
    except Exception:
        _logger.exception("get_settings failed for class_id=%s", class_id)
        raise HTTPException(status_code=503, detail="Firestore unavailable -- try again shortly.")


@app.put("/api/classes/{class_id}/settings")
async def api_update_settings(class_id: str, payload: ClassSettingsRequest, authorization: str | None = Header(None)) -> dict:
    _verify_class_auth(class_id, authorization)
    try:
        return update_settings(class_id, payload)
    except Exception:
        _logger.exception("update_settings failed for class_id=%s", class_id)
        raise HTTPException(status_code=503, detail="Firestore unavailable -- try again shortly.")


@app.post("/api/classes/{class_id}/test-sheets")
async def api_test_sheets(class_id: str, payload: TestSheetsRequest | None = None, authorization: str | None = Header(None)) -> dict:
    _verify_class_auth(class_id, authorization)
    try:
        return test_sheets_connection(class_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        _logger.exception("test_sheets_connection failed for class_id=%s", class_id)
        raise HTTPException(status_code=502, detail=f"Google Sheets test failed: {exc}")



@app.post("/api/parent-note")
async def api_parent_note(payload: ParentNoteRequest, authorization: str | None = Header(None)) -> dict:
    _verify_class_auth(payload.class_id, authorization)
    try:
        return parent_note(payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception:
        _logger.exception("parent_note failed for student_id=%s", payload.student_id)
        raise HTTPException(status_code=502, detail="Failed to draft parent note -- check server logs.")


@app.post("/api/debate/start")
async def api_debate_start(payload: DebateStartRequest) -> dict:
    try:
        return start_debate(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception:
        _logger.exception("start_debate failed")
        raise HTTPException(status_code=502, detail="Failed to start debate session -- check server logs.")


@app.post("/api/debate/start-with-image")
async def api_debate_start_with_image(payload: DebateStartFromImageRequest) -> dict:
    try:
        return start_debate_from_image(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception:
        _logger.exception("start_debate_from_image failed")
        raise HTTPException(status_code=502, detail="Failed to start debate session from image -- check server logs.")


@app.post("/api/debate/start-with-gdoc")
async def api_debate_start_with_gdoc(payload: DebateStartFromGDocRequest) -> dict:
    try:
        return start_debate_from_gdoc(payload)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception:
        _logger.exception("start_debate_from_gdoc failed")
        raise HTTPException(status_code=502, detail="Failed to fetch Google Doc or start debate -- check server logs.")


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


@app.post("/api/debate/reflect")
async def api_debate_reflect(payload: DebateReflectionRequest) -> dict:
    """ĐỢT 7: Metacognitive self-correction loop -- evaluates the student's
    post-debate revised claim and updates their profile with growth bonus."""
    try:
        return submit_reflection(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception:
        _logger.exception("submit_reflection failed for student_id=%s", payload.student_id)
        raise HTTPException(status_code=502, detail="Failed to evaluate reflection -- check server logs.")



@app.get("/api/classes/{class_id}/analytics")
async def api_class_analytics(class_id: str, limit: int = 10, authorization: str | None = Header(None)) -> dict:
    _verify_class_auth(class_id, authorization)
    try:
        digests = list_recent_digests(class_id=class_id, limit=limit)
    except Exception:
        _logger.exception("list_recent_digests failed for class_id=%s", class_id)
        raise HTTPException(status_code=503, detail="Firestore unavailable -- try again shortly.")
    return {"class_id": class_id, "digests": digests}


@app.get("/api/classes/{class_id}/students")
async def api_class_students(class_id: str, limit: int = 50, authorization: str | None = Header(None)) -> dict:
    """ĐỢT 3: class roster ordered by most-recently-active student, backed
    by the composite index in firestore.indexes.json -- see
    memory/firestore_memory.py::list_students_by_class."""
    _verify_class_auth(class_id, authorization)
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
async def pubsub_push(request: Request, authorization: str | None = Header(None)) -> JSONResponse:
    _verify_pubsub_push_auth(authorization)

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
