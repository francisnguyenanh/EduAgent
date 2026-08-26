"""ĐỢT 3 #2 -- Interactive REST API for the Cloud Run service.

`server.py`'s original surface was a Pub/Sub push-only endpoint: a human (or
a judge) opening the deployed URL in a browser got a bare 404/JSON. This
module adds the student-facing debate flow (reusing `interactive.py`'s
session helper -- itself a thin wrapper around the exact production
summarizer/persona_selector/debate functions, not a second implementation)
and a read-only teacher analytics endpoint over the digests PHASE 3/ĐỢT 2
already persist to Firestore.

ĐỢT 5: once the 3rd turn completes, this module also scores the debate (via
`interactive.complete_debate_session()`, itself a thin wrapper around
`nodes/scorer.py`'s `score_essay()` -- the exact same prompt/schema PHASE 1's
batch `cognitive_scorer` node uses, not a second divergent copy) and returns
it gated behind the class's `show_score_radar_to_students` setting. This is
read-only, for the student-facing "how did I do" summary -- it deliberately
does NOT persist to Firestore or mutate the student's profile. That
write-back (`profile_mutator`, weakness_taxonomy merge, Pub/Sub publish) only
ever happens through the ADK2 graph; duplicating it here would create a
second, divergent path into `student_profiles`.
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
    DebateNotComplete,
    DebateSessionComplete,
    ReflectionAlreadySubmitted,
    UnknownSessionError,
    claim_reflection,
    complete_debate_session,
    end_debate_session,
    get_debate_session,
    record_student_reply,
    start_debate_session,
    step_debate_turn,
)

from eduagent.memory.firestore_memory import get_profile
from eduagent.memory.student_profile import persona_history_from_profile, weakness_taxonomy_from_profile
from eduagent.nodes.intake import strip_injection_attempts
from eduagent.nodes.ocr import transcribe_essay_image
from eduagent.nodes.persona_selector import choose_persona
from eduagent.nodes.summarizer import summarize_essay
from eduagent.skills.language import detect_language
from eduagent.skills.parent_note import draft_parent_note
from eduagent.skills.personas import get_persona

_logger = logging.getLogger(__name__)

# ĐỢT 6: Input caps & boundaries to prevent cost-DoS, prompt-injection, and 504 timeouts
MAX_ESSAY_CHARS = 20_000
MAX_IMAGE_B64_CHARS = 14_000_000  # ~10MB binary equivalent
MAX_STUDENT_REPLY_CHARS = 4_000


class DebateStartRequest(BaseModel):
    essay_text: str
    student_id: str
    name: str = ""
    class_id: str = ""
    persona_id: str | None = None


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
    persona_id: str | None = None


class DebateStartFromGDocRequest(BaseModel):
    """Debate start using a publicly shared Google Doc link (viewable by anyone with link)."""

    gdoc_url: str
    student_id: str
    name: str = ""
    class_id: str = ""
    persona_id: str | None = None



class DebateTurnRequest(BaseModel):
    session_id: str
    student_reply: str


class ClassSettingsRequest(BaseModel):
    show_score_radar_to_students: bool | None = None
    stuck_streak_threshold: int | None = None
    digest_notify_email: str | None = None
    audit_spreadsheet_id: str | None = None
    socratic_persona: str | None = None


class TestSheetsRequest(BaseModel):
    spreadsheet_id: str | None = None


class ParentNoteRequest(BaseModel):
    class_id: str
    student_id: str



def _start_debate_from_essay_text(
    essay_text: str,
    *,
    student_id: str,
    name: str = "",
    class_id: str = "",
    ocr_meta: dict | None = None,
    persona_id: str | None = None,
) -> dict:
    """Shared core of start_debate()/start_debate_from_image(): runs the
    exact production summarizer -> memory-informed persona selection ->
    first debate turn, same as the batch graph's intake->...->debate_loop
    prefix, then keeps the session open for step_debate_turn() calls -- see
    interactive.py's module docstring for why this bridge exists instead of
    true ADK interrupt/resume. `ocr_meta`, when the essay came from a photo,
    is passed through unchanged into the response for the caller to display
    (confidence/uncertain_segments) -- it never affects persona/debate logic."""
    if len(essay_text) > MAX_ESSAY_CHARS:
        raise ValueError(f"Essay too long: {len(essay_text)} characters (maximum allowed is {MAX_ESSAY_CHARS}).")

    # ĐỢT 6 P0 fix: ensure live API inputs pass through deterministic prompt-injection stripping
    clean_essay_text, injection_matches = strip_injection_attempts(essay_text)
    if injection_matches:
        _logger.warning("Sanitized prompt injection attempt from live essay input", extra={"matches": injection_matches, "student_id": student_id})

    language = detect_language(clean_essay_text)
    summary, summary_degraded = summarize_essay(clean_essay_text, student_id=student_id)

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

    # Look up teacher settings for persona enforcement (Student cannot pick, teacher enforces it)
    enforced_persona = "auto"
    inferred_class_id = class_id
    if not inferred_class_id and student_id and "_" in student_id:
        inferred_class_id = student_id.split("_")[0]
    
    if inferred_class_id:
        try:
            settings = get_class_settings(class_id=inferred_class_id)
            enforced_persona = settings.get("socratic_persona", "auto")
        except Exception:
            _logger.exception("Failed to load class settings for debate start -- defaulting to auto persona")

    selected_persona_id = enforced_persona if enforced_persona in ("skeptic", "devils_advocate", "nitpicker", "expander") else None
    if not selected_persona_id:
        selected_persona_id = choose_persona(summary.get("fallacies_draft", []), persona_history, essay_seed=clean_essay_text)
    persona = get_persona(selected_persona_id)

    session_id = str(uuid.uuid4())
    start_debate_session(
        session_id,
        persona_id=selected_persona_id,
        essay_text=clean_essay_text,
        summary=summary,
        prior_weaknesses=prior_weaknesses,
        language=language,
        student_id=student_id,
        name=name,
        class_id=class_id,
    )
    first_turn = step_debate_turn(session_id)

    result = {
        "session_id": session_id,
        "persona_id": selected_persona_id,
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
    return _start_debate_from_essay_text(
        payload.essay_text,
        student_id=payload.student_id,
        name=payload.name,
        class_id=payload.class_id,
        persona_id=payload.persona_id,
    )


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
    if len(payload.image_base64) > MAX_IMAGE_B64_CHARS:
        raise ValueError(f"Image payload too large ({len(payload.image_base64)} chars, max {MAX_IMAGE_B64_CHARS}).")

    image_bytes = base64.b64decode(payload.image_base64)
    ocr_result = transcribe_essay_image(image_bytes, payload.image_mime_type, student_id=payload.student_id)

    result = _start_debate_from_essay_text(
        ocr_result["transcribed_text"],
        student_id=payload.student_id,
        name=payload.name,
        class_id=payload.class_id,
        ocr_meta={
            "confidence": ocr_result["confidence"],
            "uncertain_segments": ocr_result["uncertain_segments"],
            "degraded": ocr_result["degraded"],
        },
        persona_id=payload.persona_id,
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
        name=payload.name,
        class_id=payload.class_id,
        ocr_meta=None,
        persona_id=payload.persona_id,
    )

    result["gdoc"] = {
        "doc_id": doc_id,
        "char_count": len(essay_text),
    }
    return result



def submit_debate_turn(payload: DebateTurnRequest) -> dict:
    if len(payload.student_reply) > MAX_STUDENT_REPLY_CHARS:
        raise ValueError(f"Student reply too long: {len(payload.student_reply)} characters (maximum allowed is {MAX_STUDENT_REPLY_CHARS}).")

    clean_reply, matches = strip_injection_attempts(payload.student_reply)
    if matches:
        _logger.warning("Sanitized prompt injection attempt from student reply", extra={"matches": matches, "session_id": payload.session_id})

    session = get_debate_session(payload.session_id)
    turns = session["turns"]

    # If all max questions (e.g. 3) were already asked, this reply is the answer to Turn 3.
    if len(turns) >= _max_turns():
        record_student_reply(payload.session_id, clean_reply)
        result = _score_and_close_session(payload.session_id)
        return {"turn": None, "turn_number": len(turns), "completed": True, "result": result}


    turn = step_debate_turn(payload.session_id, clean_reply)
    turns_so_far = len(get_debate_session(payload.session_id)["turns"])
    return {"turn": turn, "turn_number": turns_so_far, "completed": False}



def _score_and_close_session(session_id: str) -> dict:
    """ĐỢT 5 -- runs once Turn 3 (VALIDATOR.max_debate_turns) finishes:
    scores the debate via the exact cognitive_scorer prompt (interactive.py's
    complete_debate_session(), which itself ends the session -- no separate
    end_debate_session() call needed here) and gates the numeric radar behind
    the class's own show_score_radar_to_students setting (ĐỢT 4 #2), same
    respected-by-default=True fallback get_settings() already uses elsewhere,
    so a Firestore hiccup degrades to "show the radar" rather than silently
    hiding it from every student in the class."""
    scored = complete_debate_session(session_id)
    show_radar = True
    class_id = scored.get("class_id", "")
    if class_id:
        try:
            show_radar = bool(get_class_settings(class_id=class_id).get("show_score_radar_to_students", True))
        except Exception:
            _logger.exception("get_class_settings failed while gating score radar for class_id=%s -- defaulting to shown", class_id)

    result = {"student_feedback": scored["student_feedback"], "show_score_radar": show_radar, "degraded": scored["degraded"]}
    if show_radar:
        result["scores"] = scored["scores"]
        result["rationale"] = scored["rationale"]
    return result


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
        "token": result.token,
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


def test_sheets_connection(class_id: str, payload: TestSheetsRequest | None = None) -> dict:
    from eduagent.config import SHEETS
    from eduagent.integrations.sheets_mcp import append_audit_row, extract_spreadsheet_id

    settings = get_class_settings(class_id=class_id)
    target = (payload and payload.spreadsheet_id) or settings.get("audit_spreadsheet_id") or SHEETS.audit_spreadsheet_id
    sheet_id = extract_spreadsheet_id(target)
    if not sheet_id:
        raise ValueError("No Google Spreadsheet ID or URL provided or configured.")

    now_str = datetime.now(timezone.utc).isoformat()
    append_audit_row(
        spreadsheet_id=sheet_id,
        row=[
            now_str,
            class_id,
            "test_connection",
            "Manual connection test from Teacher Settings Web UI",
            "N/A",
            "manual-test",
        ],
    )
    return {"status": "ok", "spreadsheet_id": sheet_id, "timestamp": now_str}



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


class DebateReflectionRequest(BaseModel):
    """ĐỢT 15 #2/#4: carries only the session_id and the new claim.

    It used to also accept `student_id`, `class_id`, `original_fallacy`,
    `original_claim` and `language` straight from the client, with no link to
    any debate. Two separate holes came out of that single design mistake:

      1. Score farming -- `POST /api/debate/reflect` with a made-up claim
         credited `growth_bonus` and `breakthrough_count` to a profile without
         any essay or debate ever having happened. The endpoint was
         authenticated (ADR-018), so a student could not farm *someone else's*
         profile, but nothing stopped them farming their own in a loop, which
         is worse for the product: the metacognitive metric the teacher reads
         stopped meaning "this student revised their thinking".
      2. Prompt injection -- `original_claim` and `original_fallacy` went into
         the Gemini prompt unsanitized while only `revised_claim` was cleaned,
         violating ADR-012's layered-sanitization rule at the one endpoint
         nobody re-checked after ADR-012 was written.

    Both close with the same change, which is why they are one fix: every field
    the prompt and the profile write need now comes from the server's own
    session record (`interactive.claim_reflection()`), so there is nothing left
    for a caller to forge and nothing new to sanitize -- the essay was already
    sanitized at intake, before it was ever stored.
    """

    session_id: str
    revised_claim: str


_REFLECTION_SCHEMA = {
    "type": "object",
    "properties": {
        "resolved": {
            "type": "boolean",
            "description": "True if the student's revised claim successfully addresses or removes the original logical fallacy/reasoning weakness.",
        },
        "feedback": {
            "type": "string",
            "description": "1-2 sentences of encouraging, specific feedback on how their revised claim improved their reasoning.",
        },
        "growth_bonus": {
            "type": "number",
            "description": "Growth bonus between 0.0 and 1.0 (e.g. 0.5 for a clear, improved claim).",
        },
    },
    "required": ["resolved", "feedback", "growth_bonus"],
}


def submit_reflection(payload: DebateReflectionRequest) -> dict:
    """DOT 7: Metacognitive Self-Correction Loop. Evaluates the student's
    post-debate revised claim, rewards cognitive growth into their Firestore
    profile, and returns encouraging constructive feedback.

    ĐỢT 15 #2/#4: everything except the revised claim itself is read off the
    server's session record -- see DebateReflectionRequest for the two holes
    that closes. The reflection is claimed (and the session marked spent) BEFORE
    the LLM call, so a slow Gemini response cannot be double-submitted into two
    growth bonuses; the session is torn down after the profile write, which is
    the real end of the debate flow.
    """
    if len(payload.revised_claim) > MAX_STUDENT_REPLY_CHARS:
        raise ValueError(f"Revised claim too long (max {MAX_STUDENT_REPLY_CHARS} chars)")

    session = claim_reflection(payload.session_id)

    student_id = session.get("student_id", "")
    class_id = session.get("class_id") or "c1"
    original_claim = session.get("essay_text", "")
    fallacies = (session.get("summary") or {}).get("fallacies_draft") or []
    original_fallacy = fallacies[0] if fallacies else "Unspecified reasoning gap"

    sanitized_revised, matches = strip_injection_attempts(payload.revised_claim)
    if matches:
        _logger.warning(
            "Sanitized prompt injection attempt from revised claim",
            extra={"matches": matches, "session_id": payload.session_id},
        )
    from eduagent.config import GEMINI
    from eduagent.llm import LLMGenerationError, generate_json
    from eduagent.skills.language import language_instruction

    # The session already recorded the language detected from the essay at start
    # time -- re-detecting it from the revision would let one short reply flip
    # the language of feedback mid-flow.
    lang = session.get("language") or detect_language(sanitized_revised)

    system_instruction = (
        "You are an expert Socratic reasoning coach evaluating a student's post-debate self-correction. "
        "The student was challenged on a logical fallacy/weakness during debate and has submitted a revised claim. "
        "Determine if the revised claim makes a meaningful effort to fix the fallacy or qualify their thesis. "
        "Be encouraging yet intellectually honest.\n\n"
        f"{language_instruction(lang)}"
    )
    prompt = (
        f"Original Weakness/Fallacy Identified: {original_fallacy}\n"
        f"Original Context/Claim: <student_essay>{original_claim}</student_essay>\n"
        f"Student's Revised Claim: <student_reply>{sanitized_revised}</student_reply>"
    )

    try:
        result = generate_json(
            model=GEMINI.flash_model,
            system_instruction=system_instruction,
            prompt=prompt,
            response_schema=_REFLECTION_SCHEMA,
        )
        resolved = bool(result.get("resolved", True))
        growth_bonus = float(result.get("growth_bonus", 0.5)) if resolved else 0.0
        fallback_msg = "Luận điểm chỉnh sửa thể hiện sự tiến bộ tư duy." if lang == "vi" else "Good effort in revising your claim."
        feedback = str(result.get("feedback", fallback_msg))
    except LLMGenerationError:
        _logger.warning("LLM evaluation of reflection failed, degrading gracefully")
        resolved = True
        growth_bonus = 0.5
        feedback = (
            "Câu luận điểm chỉnh sửa của em đã được ghi nhận và thể hiện sự tiến bộ tư duy rõ rệt."
            if lang == "vi"
            else "Your revised claim has been recorded and reflects thoughtful growth."
        )

    # Record into student profile transactional memory
    try:
        from eduagent.memory.firestore_memory import apply_reflection_result

        apply_reflection_result(
            student_id=student_id,
            reflection_text=sanitized_revised,
            original_fallacy=original_fallacy,
            resolved=resolved,
            growth_bonus=growth_bonus,
            timestamp=datetime.now(timezone.utc).isoformat(),
            class_id=class_id,
        )
    except Exception:
        _logger.exception("Failed to persist student reflection for student_id=%s", student_id)

    end_debate_session(payload.session_id)

    return {
        "student_id": student_id,
        "resolved": resolved,
        "growth_bonus": growth_bonus,
        "feedback": feedback,
    }


__all__ = [
    "DebateStartRequest",
    "DebateStartFromImageRequest",
    "DebateStartFromGDocRequest",
    "DebateTurnRequest",
    "DebateReflectionRequest",
    "ClassSettingsRequest",
    "TestSheetsRequest",
    "ParentNoteRequest",
    "get_debate_session",
    "start_debate",
    "start_debate_from_image",
    "start_debate_from_gdoc",
    "submit_debate_turn",
    "submit_reflection",
    "login",
    "class_priority",
    "get_settings",
    "update_settings",
    "test_sheets_connection",
    "parent_note",

    "UnknownSessionError",
    "DebateNotComplete",
    "ReflectionAlreadySubmitted",
    "DebateSessionComplete",
    "LoginError",
]

