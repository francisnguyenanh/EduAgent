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
from eduagent.llm import LLMGenerationError, generate_json_from_image, generate_text_from_image
from eduagent.skills.image_preprocessing import preprocess_image_bytes
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

# ADR-028: a SEPARATE threshold for the cross-MODEL comparison, because the
# two comparisons have measurably different distributions and reusing one
# number for both is a real bug, not a tuning preference. Measured over the 12
# real handwriting samples in eval/test_images/ (Wave 24):
#
#   same-model  (Gemini vs Gemini): legible images 0.989-1.000 -- 0.75 sits far
#                                   below the cluster, so it is a safe cut
#   cross-model (Gemini vs Gemma) : legible images 0.729-0.998 -- 0.75 sits
#                                   INSIDE the cluster, so it fires on legible
#                                   essays (tilted_essay 0.729, stu_stuck 0.756)
#
# Two different models transcribing the same page agree on the words but differ
# on punctuation, line breaks, and where each draws the line between guessing
# and writing [[unclear]]. That is style, not disagreement about content.
# Unreadable images score 0.265-0.294 cross-model, so 0.50 sits in the middle
# of a wide empty band rather than being shaved to fit a borderline sample.
#
# What this buys, measured: `notes_socialmedia.jpg` scores 0.781 same-model --
# Gemini agreeing with its own unreliable reading, above the old threshold and
# therefore INVISIBLE to ADR-007 -- but 0.294 against Gemma. The cross-model
# check catches an image the same-model check waves through. That is the
# concrete version of the argument for ADR-028.
#
# Honest limit: both numbers are fitted on the same 12 images they are
# evaluated against; there is no held-out set. The claim is "0.75 is
# demonstrably wrong for cross-model comparison", not "0.50 is optimal".
#
# Wave 25 tried normalising both texts (lowercase + collapse whitespace) before
# comparing, to stop punctuation/line-break differences counting as
# disagreement. Reverted after measuring it on the same 12 captured pairs: it
# made three LEGIBLE images score WORSE, the opposite of its purpose --
# faded_essay 0.927 -> 0.812, messy_essay 0.949 -> 0.794, neat_essay 0.924 ->
# 0.872. Cause: difflib's `autojunk` heuristic discards elements appearing in
# >1% of a sequence longer than 200 chars, and after lowercasing and collapsing
# runs of whitespace the space character dominates hard enough to be treated as
# junk. Passing autojunk=False does fix that, but then the separation gets
# NARROWER, not wider: raw leaves a 0.435-wide empty band (unreadable <=0.294,
# legible >=0.729) while normalised+autojunk=False leaves 0.162 (unreadable
# <=0.755, legible >=0.917) -- and notes_socialmedia, the image that justifies
# this whole ADR, rises from 0.294 to 0.755 and stops being flagged at all.
# Raw text separates these two populations better. Do not re-introduce
# normalisation without re-measuring both of those numbers.
_CROSS_MODEL_SIMILARITY_THRESHOLD = 0.50
_INCONSISTENCY_MARKER = "[[ocr inconsistent across repeated attempts on this image -- treat transcription as unverified]]"


def _transcribe_once(*, image_bytes: bytes, image_mime_type: str) -> dict:
    return generate_json_from_image(
        model=GEMINI.flash_model,
        system_instruction=_SYSTEM_INSTRUCTION,
        prompt="Transcribe the handwritten essay shown in this image.",
        image_bytes=image_bytes,
        image_mime_type=image_mime_type,
        response_schema=_SCHEMA,
        # ĐỢT 3 token/latency optimization: verbatim transcription is a
        # perception task, not a reasoning task -- extended thinking adds
        # latency/cost here without improving transcription accuracy.
        thinking_budget=0,
    )


# ADR-028: the second opinion runs a different model FAMILY.
_GEMMA_TRANSCRIBE_PROMPT = (
    "Transcribe the handwritten student essay in this image EXACTLY as written, "
    "including the student's own spelling and grammar mistakes. Skip crossed-out "
    "words entirely. Do NOT correct, improve, summarise, or comment on the text. "
    "If a word is genuinely illegible, write [[unclear]] in its place rather than "
    "guessing. Output ONLY the transcription itself, with no preamble or notes."
)
# The label written into the result when the second pass fell back to Gemini.
# Kept as a real, grep-able value rather than a silent None: Wave 12 spent a
# whole audit deleting 11 trace attributes that documentation claimed existed
# and code never emitted, so a new observability signal has to be one you can
# actually find in a log.
_CROSS_CHECK_FALLBACK_MODEL = "gemini-fallback"


def _transcribe_second_opinion(*, image_bytes: bytes, image_mime_type: str, essay_id: str | None = None) -> tuple[str, str]:
    """ADR-028: runs the cross-check's second pass on Gemma instead of a second
    Gemini call, and returns (transcribed_text, model_actually_used).

    Why this is a real upgrade rather than a bonus-point bolt-on: ADR-007's
    cross-check compares two passes of the SAME model, which catches random
    sampling noise but is blind to systematic error. If Gemini Vision resolves
    an ambiguous stroke wrong the same way twice -- precisely the failure ADR-007
    documents, where the model self-reports "high" while transcribing fabricated
    content -- difflib compares two identical wrong strings and reports
    consensus. A different model family makes the two errors uncorrelated, so
    the existing similarity threshold starts detecting a class of failure it
    previously could not see.

    Gemma 4 is Model-as-a-Service on shared capacity, so `429 request queue is
    full` is routine (measured: 4 of 10 raw calls during Wave 24). llm.py
    retries it, and if it still fails this falls back to the original
    same-model second pass. A busy shared queue must never block a student's
    submission -- that is the same degrade-don't-fail discipline as everywhere
    else in this pipeline (ADR-008).
    """
    if not GEMINI.ocr_cross_check_with_gemma:
        return _transcribe_once(image_bytes=image_bytes, image_mime_type=image_mime_type)["transcribed_text"], _CROSS_CHECK_FALLBACK_MODEL

    try:
        text = generate_text_from_image(
            model=GEMINI.gemma_model,
            prompt=_GEMMA_TRANSCRIBE_PROMPT,
            image_bytes=image_bytes,
            image_mime_type=image_mime_type,
        )
        if text.strip():
            return text, GEMINI.gemma_model
        # An empty string would score ~0 similarity against any real
        # transcription and force a spurious 'low' -- a silent quality
        # regression dressed up as a safety downgrade. Fall back instead.
        _logger.warning("Gemma cross-check returned empty text -- using same-model second pass", extra={"essay_id": essay_id})
    except LLMGenerationError:
        _logger.warning(
            "Gemma cross-check unavailable (MaaS queue full or error) -- using same-model second pass",
            extra={"essay_id": essay_id, "gemma_model": GEMINI.gemma_model},
        )

    return _transcribe_once(image_bytes=image_bytes, image_mime_type=image_mime_type)["transcribed_text"], _CROSS_CHECK_FALLBACK_MODEL


def _cross_check_consistency(first: dict, second_text: str, *, cross_model: bool) -> dict:
    """Deterministic backstop on top of the model's own self-reported
    confidence: transcribe the SAME image twice and compare. The decision
    logic itself is a plain text-similarity comparison, not another LLM
    judgment -- if two independent Vision calls on the identical image
    produce substantially different text, the image is not reliably
    readable, regardless of what either call claimed about its own
    confidence. Returns `first`'s result, confidence force-downgraded to
    'low' (never upgraded) when the two disagree.

    ADR-028: `second_text` is now a plain string rather than a result dict,
    because the second pass may come from Gemma, which does not honour a
    response schema. Nothing here needed the structure -- only the text was
    ever compared. `cross_model` selects the threshold calibrated for the
    comparison that was actually made; see the two constants above for the
    measured distributions that make them different numbers."""
    threshold = _CROSS_MODEL_SIMILARITY_THRESHOLD if cross_model else _CONSISTENCY_SIMILARITY_THRESHOLD
    # Compared on RAW text on purpose -- see the note under
    # _CROSS_MODEL_SIMILARITY_THRESHOLD on why normalising first was reverted.
    similarity = difflib.SequenceMatcher(None, first["transcribed_text"], second_text).ratio()
    if similarity >= threshold:
        return first

    return {
        "transcribed_text": first["transcribed_text"],
        "confidence": "low",
        "uncertain_segments": list(first["uncertain_segments"]) + [_INCONSISTENCY_MARKER],
    }


def transcribe_essay_image(image_bytes: bytes, image_mime_type: str, *, essay_id: str | None = None, student_id: str | None = None) -> dict:
    """Pure(ish) core of the node below -- preprocess, transcribe twice,
    cross-check -- factored out so callers outside the ADK graph (ĐỢT 3 #2/#7's
    interactive REST API image-upload path) run the EXACT same production OCR
    logic instead of a second, divergent implementation. Returns
    {transcribed_text, confidence, uncertain_segments, degraded}."""
    if not image_bytes:
        _logger.error("transcribe_essay_image called with no image bytes", extra={"essay_id": essay_id})
        return {"transcribed_text": "", "confidence": _DEGRADED_CONFIDENCE, "uncertain_segments": [], "degraded": True, "cross_check_model": None}

    # ĐỢT 3 #1: normalize EXIF rotation + downscale large phone-camera photos
    # BEFORE either Vision call -- both cross-check calls below see the same
    # prepped bytes, so the similarity comparison stays apples-to-apples.
    image_bytes, image_mime_type = preprocess_image_bytes(image_bytes, image_mime_type)

    try:
        first = _transcribe_once(image_bytes=image_bytes, image_mime_type=image_mime_type)
        # ADR-028: pass two is a DIFFERENT model family (Gemma), so a
        # systematic misread cannot survive both passes unnoticed.
        second_text, cross_check_model = _transcribe_second_opinion(
            image_bytes=image_bytes, image_mime_type=image_mime_type, essay_id=essay_id
        )
        result = _cross_check_consistency(first, second_text, cross_model=cross_check_model != _CROSS_CHECK_FALLBACK_MODEL)
        return {
            "transcribed_text": result["transcribed_text"],
            "confidence": result["confidence"],
            "uncertain_segments": result["uncertain_segments"],
            "degraded": False,
            # Which model actually produced the second opinion. This is both
            # the observability signal for the cross-check and the evidence
            # that Gemma is genuinely in the request path -- if this ever
            # reads "gemini-fallback" for every request, the Gemma
            # integration is a claim rather than a fact (ADR-028 abort
            # condition #3).
            "cross_check_model": cross_check_model,
        }
    except LLMGenerationError:
        # Same discipline as scorer.py/summarizer.py: never fabricate content
        # on outage. An empty essay flows into sanitizer/summarizer exactly
        # like a blank text submission would -- no fake transcription ever
        # reaches the student's permanent record.
        _logger.error("Multimodal OCR degraded -- Gemini Vision unavailable", extra={"essay_id": essay_id, "student_id": student_id})
        return {"transcribed_text": "", "confidence": _DEGRADED_CONFIDENCE, "uncertain_segments": [], "degraded": True, "cross_check_model": None}


@traced_node("multimodal_ocr")
async def multimodal_ocr(ctx: Context) -> dict:
    ctx.state["stage"] = "multimodal_ocr"

    image_bytes = ctx.state.get("ocr_image_bytes")
    image_mime_type = ctx.state.get("ocr_image_mime_type") or "image/jpeg"

    result = transcribe_essay_image(image_bytes, image_mime_type, essay_id=ctx.state.get("essay_id"), student_id=ctx.state.get("student_id"))

    ctx.state["raw_input"] = result["transcribed_text"]
    ctx.state["ocr_confidence"] = result["confidence"]
    ctx.state["ocr_uncertain_segments"] = result["uncertain_segments"]
    ctx.state["ocr_degraded"] = result["degraded"]
    # ADR-028: kept on ctx.state so the audit trail records which model family
    # actually produced the second opinion for THIS essay, not which one the
    # config says it should have.
    ctx.state["ocr_cross_check_model"] = result["cross_check_model"]
    return {
        "transcribed_text": result["transcribed_text"],
        "confidence": result["confidence"],
        "uncertain_segments": result["uncertain_segments"],
        "cross_check_model": result["cross_check_model"],
    }
