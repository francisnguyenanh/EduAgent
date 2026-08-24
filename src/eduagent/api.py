"""ĐỢT 3 #2 -- Interactive REST API for the Cloud Run service.

`server.py`'s original surface was a Pub/Sub push-only endpoint: a human (or
a judge) opening the deployed URL in a browser got a bare 404/JSON. This
module adds the student-facing debate flow (reusing `interactive.py`'s
session helper -- itself a thin wrapper around the exact production
summarizer/persona_selector/debate functions, not a second implementation)
and a read-only teacher analytics endpoint over the digests PHASE 3/ĐỢT 2
already persist to Firestore.

Deliberately NOT wired here: turning a finished 3-turn debate into a score +
profile mutation. That path (`cognitive_scorer` + `profile_mutator`) runs
inside the ADK2 graph against `Context`, and duplicating it as hand-rolled
plumbing here would create a second, divergent copy of PHASE 1's scoring
logic -- exactly the risk `interactive.py`'s own docstring already flags for
debate turns. This surface closes the "human can actually reach the
service" gap; full write-back stays the graph's job.
"""

from __future__ import annotations

import base64
import logging
import uuid
from datetime import datetime, timezone

from pydantic import BaseModel

from eduagent.aggregator.digest_store import get_class_settings, set_class_settings
from eduagent.aggregator.priority_engine import compute_priority, rank_students
from eduagent.auth import LoginError, LoginRequest, login as auth_login
from eduagent.interactive import (
    DebateSessionComplete,
    UnknownSessionError,
    end_debate_session,
    get_debate_session,
    start_debate_session,
    step_debate_turn,
)
from eduagent.memory.firestore_memory import get_profile
from eduagent.memory.student_profile import persona_history_from_profile, weakness_taxonomy_from_profile
from eduagent.nodes.ocr import transcribe_essay_image
from eduagent.nodes.persona_selector import choose_persona
from eduagent.nodes.summarizer import summarize_essay
from eduagent.skills.language import detect_language
from eduagent.skills.parent_note import draft_parent_note
from eduagent.skills.personas import get_persona

_logger = logging.getLogger(__name__)


class DebateStartRequest(BaseModel):
    essay_text: str
    student_id: str
    name: str = ""
    class_id: str = ""


class DebateStartFromImageRequest(BaseModel):
    """ĐỢT 3 #7: same as DebateStartRequest but the essay arrives as a photo
    of handwriting instead of typed text -- image_base64 is the raw image
    bytes, base64-encoded (as a browser's FileReader.readAsDataURL would
    produce, stripped of the `data:image/...;base64,` prefix)."""

    image_base64: str
    image_mime_type: str = "image/jpeg"
    student_id: str
    name: str = ""
    class_id: str = ""


class DebateStartFromGDocRequest(BaseModel):
    """Debate start using a publicly shared Google Doc link (viewable by anyone with link)."""

    gdoc_url: str
    student_id: str
    name: str = ""
    class_id: str = ""


class DebateTurnRequest(BaseModel):
    session_id: str
    student_reply: str


class ClassSettingsRequest(BaseModel):
    show_score_radar_to_students: bool | None = None
    stuck_streak_threshold: int | None = None
    digest_notify_email: str | None = None


class ParentNoteRequest(BaseModel):
    class_id: str
    student_id: str


def _start_debate_from_essay_text(essay_text: str, *, student_id: str, ocr_meta: dict | None = None) -> dict:
    """Shared core of start_debate()/start_debate_from_image(): runs the
    exact production summarizer -> memory-informed persona selection ->
    first debate turn, same as the batch graph's intake->...->debate_loop
    prefix, then keeps the session open for step_debate_turn() calls -- see
    interactive.py's module docstring for why this bridge exists instead of
    true ADK interrupt/resume. `ocr_meta`, when the essay came from a photo,
    is passed through unchanged into the response for the caller to display
    (confidence/uncertain_segments) -- it never affects persona/debate logic."""
    language = detect_language(essay_text)
    summary, summary_degraded = summarize_essay(essay_text, student_id=student_id)

    try:
        profile = get_profile(student_id) if student_id else None
    except Exception:
        # Same discipline as persona_selector.py's own ctx.state read: a
        # Firestore hiccup degrades to "no memory this run", not a 500 that
        # blocks the student from starting at all.
        _logger.exception("get_profile failed for interactive debate start -- continuing without memory")
        profile = None

    persona_history = persona_history_from_profile(profile) if profile else []
    prior_weaknesses = weakness_taxonomy_from_profile(profile) if profile else []

    persona_id = choose_persona(summary.get("fallacies_draft", []), persona_history)
    persona = get_persona(persona_id)

    session_id = str(uuid.uuid4())
    start_debate_session(
        session_id,
        persona_id=persona_id,
        essay_text=essay_text,
        summary=summary,
        prior_weaknesses=prior_weaknesses,
        language=language,
    )
    first_turn = step_debate_turn(session_id)

    result = {
        "session_id": session_id,
        "persona_id": persona_id,
        "persona_name": persona.display_name,
        "language": language,
        "summary": summary,
        "summary_degraded": summary_degraded,
        "turn": first_turn,
        "turn_number": 1,
    }
    if ocr_meta is not None:
        result["ocr"] = ocr_meta
    return result


def start_debate(payload: DebateStartRequest) -> dict:
    return _start_debate_from_essay_text(payload.essay_text, student_id=payload.student_id)


def start_debate_from_image(payload: DebateStartFromImageRequest) -> dict:
    """ĐỢT 3 #7: image-upload variant -- transcribes via the exact
    production OCR path (transcribe_essay_image(), same EXIF/downscale
    preprocessing + self-consistency cross-check as the batch graph's
    multimodal_ocr node) before handing off to the shared debate-start core.
    A low/unavailable-confidence transcription still starts a debate (the
    student should see SOMETHING) but the caller can surface a warning from
    the returned `ocr` block -- unlike the batch pipeline, there is no
    pending_essays parking here since no score/profile mutation happens on
    this path at all (see module docstring)."""
    image_bytes = base64.b64decode(payload.image_base64)
    ocr_result = transcribe_essay_image(image_bytes, payload.image_mime_type, student_id=payload.student_id)

    result = _start_debate_from_essay_text(
        ocr_result["transcribed_text"],
        student_id=payload.student_id,
        ocr_meta={
            "confidence": ocr_result["confidence"],
            "uncertain_segments": ocr_result["uncertain_segments"],
            "degraded": ocr_result["degraded"],
        },
    )
    return result


def start_debate_from_gdoc(payload: DebateStartFromGDocRequest) -> dict:
    """Starts a debate session by fetching essay text from a publicly shared Google Doc."""
    from eduagent.integrations.gdocs import extract_gdoc_id, fetch_gdoc_text

    doc_id = extract_gdoc_id(payload.gdoc_url)
    essay_text = fetch_gdoc_text(payload.gdoc_url)

    result = _start_debate_from_essay_text(
        essay_text,
        student_id=payload.student_id,
        ocr_meta=None,
    )
    result["gdoc"] = {
        "doc_id": doc_id,
        "char_count": len(essay_text),
    }
    return result


def submit_debate_turn(payload: DebateTurnRequest) -> dict:
    turn = step_debate_turn(payload.session_id, payload.student_reply)
    turns_so_far = len(get_debate_session(payload.session_id)["turns"])
    completed = turns_so_far >= _max_turns()
    if completed:
        end_debate_session(payload.session_id)
    return {"turn": turn, "turn_number": turns_so_far, "completed": completed}


def _max_turns() -> int:
    from eduagent.config import VALIDATOR

    return VALIDATOR.max_debate_turns


def login(payload: LoginRequest) -> dict:
    """ĐỢT 4 #1 -- see auth.py's module docstring for why this is a mock,
    stateless login rather than real Firebase Auth/OAuth. Raises LoginError
    (mapped to HTTP 401 in server.py) for a bad password or malformed ID."""
    result = auth_login(payload)
    return {
        "role": result.role,
        "class_id": result.class_id,
        "user_id": result.user_id,
        "display_name": result.display_name,
    }


def class_priority(class_id: str) -> dict:
    """ĐỢT 4 #2 Teacher Executive Dashboard -- the deterministic Intervention
    Priority Index (priority_engine.rank_students, PHASE 3) as a live
    read, independent of whatever the last persisted digest happened to
    rank at send-time. Zero LLM calls."""
    from eduagent.aggregator.class_aggregator import load_class_profiles

    profiles = load_class_profiles(class_id)
    ranked = rank_students(profiles, now=datetime.now(timezone.utc))
    return {"class_id": class_id, "ranking": ranked}


def get_settings(class_id: str) -> dict:
    return {"class_id": class_id, "settings": get_class_settings(class_id=class_id)}


def update_settings(class_id: str, payload: ClassSettingsRequest) -> dict:
    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    return {"class_id": class_id, "settings": set_class_settings(class_id=class_id, settings=updates)}


def parent_note(payload: ParentNoteRequest) -> dict:
    """ĐỢT 4 #3 -- "Copy Parent Update Note" button's backend: re-derives
    this one student's priority `reason` (same pure function the ranking
    table already used) and hands it to the LLM only to phrase, never to
    decide, per parent_note.py's module docstring."""
    profile = get_profile(payload.student_id)
    if profile is None:
        raise ValueError(f"No profile found for student_id={payload.student_id!r}")

    common_fallacy_set = set()
    from eduagent.aggregator.class_aggregator import load_class_profiles
    from eduagent.aggregator.priority_engine import cluster_fallacies, common_fallacies

    profiles = load_class_profiles(payload.class_id)
    common_fallacy_set = set(common_fallacies(cluster_fallacies(profiles)))

    priority = compute_priority(profile, now=datetime.now(timezone.utc), common_fallacy_set=common_fallacy_set)
    student_name = profile.get("name", payload.student_id)
    essay_history = profile.get("essay_history", [])
    language = "en"
    if essay_history:
        language = essay_history[-1].get("language", "en")

    note, degraded = draft_parent_note(student_name=student_name, reason=priority["reason"], language=language)
    return {"student_id": payload.student_id, "note": note, "degraded": degraded, "priority": priority}


__all__ = [
    "DebateStartRequest",
    "DebateStartFromImageRequest",
    "DebateStartFromGDocRequest",
    "DebateTurnRequest",
    "ClassSettingsRequest",
    "ParentNoteRequest",
    "start_debate",
    "start_debate_from_image",
    "start_debate_from_gdoc",
    "submit_debate_turn",
    "login",
    "class_priority",
    "get_settings",
    "update_settings",
    "parent_note",
    "UnknownSessionError",
    "DebateSessionComplete",
    "LoginError",
]
