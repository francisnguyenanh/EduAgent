"""Multimodal OCR -- agent node (Gemini Vision). PHASE 6: ingests messy,
unstructured input (a photo of a handwritten essay) instead of clean text
only -- directly answers the track's "did the team ingest unusual, messy,
or highly complex unstructured data streams?" judging question.

Runs ONLY on the 'image' route emitted by intake.py (see graph/tier1_pipeline.py
routing map) -- a text-only essay never touches this node or costs a Vision
call. Output feeds into ctx.state["raw_input"], the exact same field
sanitizer.py already reads regardless of whether the essay arrived as typed
text or a photo -- everything downstream of sanitizer is unaware OCR ever
happened (except the audit trail via ocr_confidence/ocr_uncertain_segments).

Deliberately transcribes VERBATIM, including the student's own spelling and
grammar mistakes -- correcting them here would rob the Summarizer/Debate Loop
of the actual raw material the rest of the pipeline is built to probe.
"""

from __future__ import annotations

import difflib
import logging

from google.adk.agents.context import Context

from eduagent.config import GEMINI
from eduagent.llm import LLMGenerationError, generate_json_from_image
from eduagent.tracing import traced_node

_logger = logging.getLogger(__name__)

_SYSTEM_INSTRUCTION = (
    "You are transcribing a photo of a handwritten student essay for a "
    "critical-thinking coaching tool. Transcribe the text EXACTLY as written, "
    "including the student's own spelling mistakes, grammar errors, and "
    "crossed-out words (skip crossed-out words entirely, as the student "
    "clearly meant to remove them) -- do NOT correct or improve the writing; "
    "the rest of the pipeline depends on seeing the student's actual raw "
    "work, not a cleaned-up version.\n\n"
    "CRITICAL ANTI-HALLUCINATION RULE: you must transcribe ONLY characters "
    "you can actually resolve on the page. If the image is too blurry, dark, "
    "low-resolution, or the handwriting too illegible for you to read most of "
    "a word/line with real confidence, you must NOT invent plausible-sounding "
    "replacement text (e.g. do not fall back on a generic sentence about an "
    "unrelated topic just because it 'sounds like' typical essay writing). "
    "Instead: write '[[unclear]]' for that word or line in `transcribed_text`, "
    "add the surrounding phrase to `uncertain_segments` verbatim, and set "
    "`confidence` to 'low' for the whole response if this happens for more "
    "than a couple of isolated words, or 'medium' if it's just one or two. "
    "Only use 'high' confidence when you can read essentially the entire "
    "image clearly. When in doubt between guessing and marking unclear, "
    "always mark unclear -- a wrong guess is worse than an honest gap."
)

_SCHEMA = {
    "type": "object",
    "properties": {
        "transcribed_text": {"type": "string", "description": "Verbatim transcription, '[[unclear]]' marking any illegible spans."},
        "confidence": {
            "type": "string",
            "enum": ["high", "medium", "low"],
            "description": "Overall confidence the transcription reflects what's actually on the page.",
        },
        "uncertain_segments": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Phrases from transcribed_text containing a '[[unclear]]' marker, for audit/teacher review.",
        },
    },
    "required": ["transcribed_text", "confidence", "uncertain_segments"],
}

_DEGRADED_CONFIDENCE = "unavailable"

# Real finding during PHASE 6 development: on a genuinely too-degraded image,
# Gemini Vision sometimes self-reports confidence="high" while actually
# hallucinating a plausible-sounding but entirely UNRELATED sentence, despite
# an explicit anti-hallucination instruction in the prompt above (confirmed:
# 2 of 4 manual trials against the same heavily-blurred sample produced
# fabricated, unrelated content at self-reported "high" confidence). A single
# call's self-reported confidence is not reliable enough alone -- see
# _cross_check_consistency() below for the backstop.
_CONSISTENCY_SIMILARITY_THRESHOLD = 0.75
_INCONSISTENCY_MARKER = "[[ocr inconsistent across repeated attempts on this image -- treat transcription as unverified]]"


def _transcribe_once(*, image_bytes: bytes, image_mime_type: str) -> dict:
    return generate_json_from_image(
        model=GEMINI.flash_model,
        system_instruction=_SYSTEM_INSTRUCTION,
        prompt="Transcribe the handwritten essay shown in this image.",
        image_bytes=image_bytes,
        image_mime_type=image_mime_type,
        response_schema=_SCHEMA,
    )


def _cross_check_consistency(first: dict, second: dict) -> dict:
    """Deterministic backstop on top of the model's own self-reported
    confidence: transcribe the SAME image twice and compare. The decision
    logic itself is a plain text-similarity comparison, not another LLM
    judgment -- if two independent Vision calls on the identical image
    produce substantially different text, the image is not reliably
    readable, regardless of what either call claimed about its own
    confidence. Returns `first`'s result, confidence force-downgraded to
    'low' (never upgraded) when the two disagree."""
    similarity = difflib.SequenceMatcher(None, first["transcribed_text"], second["transcribed_text"]).ratio()
    if similarity >= _CONSISTENCY_SIMILARITY_THRESHOLD:
        return first

    return {
        "transcribed_text": first["transcribed_text"],
        "confidence": "low",
        "uncertain_segments": list(first["uncertain_segments"]) + [_INCONSISTENCY_MARKER],
    }


@traced_node("multimodal_ocr")
async def multimodal_ocr(ctx: Context) -> dict:
    ctx.state["stage"] = "multimodal_ocr"

    image_bytes = ctx.state.get("ocr_image_bytes")
    image_mime_type = ctx.state.get("ocr_image_mime_type") or "image/jpeg"

    if not image_bytes:
        # Routing only sends here when intake.py actually found an image
        # part, but never trust that invariant blindly -- degrade to an
        # empty transcription rather than crashing the whole essay run.
        _logger.error("multimodal_ocr node reached with no image bytes in state", extra={"essay_id": ctx.state.get("essay_id")})
        ctx.state["raw_input"] = ""
        ctx.state["ocr_confidence"] = _DEGRADED_CONFIDENCE
        ctx.state["ocr_uncertain_segments"] = []
        ctx.state["ocr_degraded"] = True
        return {"transcribed_text": "", "confidence": _DEGRADED_CONFIDENCE, "uncertain_segments": []}

    try:
        first = _transcribe_once(image_bytes=image_bytes, image_mime_type=image_mime_type)
        second = _transcribe_once(image_bytes=image_bytes, image_mime_type=image_mime_type)
        result = _cross_check_consistency(first, second)
        transcribed_text = result["transcribed_text"]
        confidence = result["confidence"]
        uncertain_segments = result["uncertain_segments"]
        ocr_degraded = False
    except LLMGenerationError:
        # Same discipline as scorer.py/summarizer.py: never fabricate content
        # on outage. An empty essay flows into sanitizer/summarizer exactly
        # like a blank text submission would -- no fake transcription ever
        # reaches the student's permanent record.
        _logger.error(
            "Multimodal OCR degraded -- Gemini Vision unavailable",
            extra={"essay_id": ctx.state.get("essay_id"), "student_id": ctx.state.get("student_id")},
        )
        transcribed_text, confidence, uncertain_segments = "", _DEGRADED_CONFIDENCE, []
        ocr_degraded = True

    ctx.state["raw_input"] = transcribed_text
    ctx.state["ocr_confidence"] = confidence
    ctx.state["ocr_uncertain_segments"] = uncertain_segments
    ctx.state["ocr_degraded"] = ocr_degraded
    return {"transcribed_text": transcribed_text, "confidence": confidence, "uncertain_segments": uncertain_segments}
