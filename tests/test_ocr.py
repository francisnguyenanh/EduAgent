"""Unit tests for PHASE 6 multimodal ingestion: intake.py's image/text
routing detection (deterministic, zero LLM) and the OCR node's degrade path.
Mocks generate_json_from_image so this suite runs fast and offline -- the
real Vertex AI Vision behavior (verbatim transcription, low-confidence
flagging on a blurry image, anti-hallucination) was verified manually against
live Gemini during development; see ADR-007/ADR-008 in README.md for that evidence.
"""

from __future__ import annotations

import asyncio
from dataclasses import replace
from unittest.mock import MagicMock, patch

from eduagent.config import GEMINI
from eduagent.llm import LLMGenerationError
from eduagent.nodes.intake import _extract_essay_input, intake
from eduagent.nodes.ocr import multimodal_ocr


class _FakePart:
    def __init__(self, text=None, inline_data=None):
        self.text = text
        self.inline_data = inline_data


class _FakeInlineData:
    def __init__(self, data, mime_type):
        self.data = data
        self.mime_type = mime_type


class _FakeContent:
    def __init__(self, parts):
        self.parts = parts


def test_extract_essay_input_plain_string_is_text_only():
    text, image_bytes, mime = _extract_essay_input("Homework helps students.")
    assert text == "Homework helps students."
    assert image_bytes is None
    assert mime is None


def test_extract_essay_input_content_with_only_text_part():
    content = _FakeContent([_FakePart(text="Homework helps students.")])
    text, image_bytes, mime = _extract_essay_input(content)
    assert text == "Homework helps students."
    assert image_bytes is None


def test_extract_essay_input_content_with_image_part():
    content = _FakeContent([_FakePart(inline_data=_FakeInlineData(data=b"fake-bytes", mime_type="image/png"))])
    text, image_bytes, mime = _extract_essay_input(content)
    assert text == ""
    assert image_bytes == b"fake-bytes"
    assert mime == "image/png"


def test_intake_routes_to_text_for_plain_essay():
    ctx = MagicMock()
    ctx.state = {}
    asyncio.run(intake(ctx, "Homework helps students."))
    assert ctx.route == "text"
    assert ctx.state["raw_input"] == "Homework helps students."
    assert "ocr_image_bytes" not in ctx.state


def test_intake_routes_to_image_when_image_part_present():
    ctx = MagicMock()
    ctx.state = {}
    content = _FakeContent([_FakePart(inline_data=_FakeInlineData(data=b"fake-bytes", mime_type="image/jpeg"))])
    asyncio.run(intake(ctx, content))
    assert ctx.route == "image"
    assert ctx.state["ocr_image_bytes"] == b"fake-bytes"
    assert ctx.state["ocr_image_mime_type"] == "image/jpeg"


def test_multimodal_ocr_populates_raw_input_on_success():
    ctx = MagicMock()
    ctx.state = {"ocr_image_bytes": b"fake-bytes", "ocr_image_mime_type": "image/png", "essay_id": "e1"}

    # ADR-028: pass 1 is Gemini (JSON), pass 2 is Gemma (plain text). Both
    # must be patched -- before this was updated, only generate_json_from_image
    # was, so the Gemma call went out to the real network inside a unit test
    # and the test passed via the fallback path rather than the path it names.
    fake_result = {"transcribed_text": "Homework helps students.", "confidence": "high", "uncertain_segments": []}
    with (
        patch("eduagent.nodes.ocr.generate_json_from_image", return_value=fake_result),
        patch("eduagent.nodes.ocr.generate_text_from_image", return_value="Homework helps students.") as gemma,
    ):
        result = asyncio.run(multimodal_ocr(ctx))

    assert result["transcribed_text"] == "Homework helps students."
    assert ctx.state["raw_input"] == "Homework helps students."
    assert ctx.state["ocr_confidence"] == "high"
    assert ctx.state["ocr_degraded"] is False
    # The cross-check really ran on the other model family, and said so.
    assert gemma.call_count == 1
    assert result["cross_check_model"] == GEMINI.gemma_model
    assert ctx.state["ocr_cross_check_model"] == GEMINI.gemma_model


def test_multimodal_ocr_downgrades_confidence_when_repeated_calls_disagree():
    ctx = MagicMock()
    ctx.state = {"ocr_image_bytes": b"fake-bytes", "ocr_image_mime_type": "image/png", "essay_id": "e1"}

    # Simulates the real failure mode found during development: a badly
    # degraded image where the model confidently transcribes two DIFFERENT,
    # unrelated sentences across repeated calls -- self-reported "high"
    # confidence on both should not be trusted.
    first = {"transcribed_text": "Homework helps students focus.", "confidence": "high", "uncertain_segments": []}
    with (
        patch("eduagent.nodes.ocr.generate_json_from_image", return_value=first),
        patch("eduagent.nodes.ocr.generate_text_from_image", return_value="The weather today is sunny and warm."),
    ):
        result = asyncio.run(multimodal_ocr(ctx))

    assert result["confidence"] == "low"
    # ADR-028: and the disagreement was surfaced by the OTHER model family --
    # this is the case a same-model second pass is blind to.
    assert result["cross_check_model"] == GEMINI.gemma_model
    assert ctx.state["ocr_confidence"] == "low"
    assert any("inconsistent" in seg for seg in ctx.state["ocr_uncertain_segments"])


def test_multimodal_ocr_degrades_to_empty_text_on_llm_outage():
    ctx = MagicMock()
    ctx.state = {"ocr_image_bytes": b"fake-bytes", "ocr_image_mime_type": "image/png", "essay_id": "e1"}

    with patch("eduagent.nodes.ocr.generate_json_from_image", side_effect=LLMGenerationError("down")):
        result = asyncio.run(multimodal_ocr(ctx))

    assert result["transcribed_text"] == ""
    assert ctx.state["ocr_degraded"] is True
    assert ctx.state["raw_input"] == ""


def test_multimodal_ocr_handles_missing_image_bytes_without_crashing():
    ctx = MagicMock()
    ctx.state = {"essay_id": "e1"}  # routing edge case: no image bytes in state

    result = asyncio.run(multimodal_ocr(ctx))

    assert result["transcribed_text"] == ""
    assert ctx.state["ocr_degraded"] is True


# --- ADR-028: Gemma as the cross-check's second opinion --------------------
#
# The property under test is NOT "Gemma is called". It is: the cross-check
# keeps working when Gemma does not. Gemma 4 is Model-as-a-Service on shared
# capacity -- 4 of 10 raw calls returned 429 during Wave 24 integration
# testing -- so the fallback is the normal path often enough that it has to be
# the tested one.


def test_gemma_outage_falls_back_to_same_model_second_pass_and_says_so():
    """A Gemma 429/error must NOT block the student's submission (ADR-008
    degrade-don't-fail), and the result must record that the second opinion
    came from Gemini, not Gemma -- otherwise 'integrated with Gemma' would be
    unfalsifiable."""
    ctx = MagicMock()
    ctx.state = {"ocr_image_bytes": b"fake-bytes", "ocr_image_mime_type": "image/png", "essay_id": "e1"}

    gemini_result = {"transcribed_text": "Homework helps students.", "confidence": "high", "uncertain_segments": []}
    with (
        patch("eduagent.nodes.ocr.generate_json_from_image", return_value=gemini_result) as gemini,
        patch("eduagent.nodes.ocr.generate_text_from_image", side_effect=LLMGenerationError("429 queue full")),
    ):
        result = asyncio.run(multimodal_ocr(ctx))

    assert result["transcribed_text"] == "Homework helps students."
    assert ctx.state["ocr_degraded"] is False
    assert result["cross_check_model"] == "gemini-fallback"
    # Fell back to a real second Gemini pass -- the cross-check still happened,
    # it just lost the cross-MODEL property. Two calls, not one.
    assert gemini.call_count == 2


def test_gemma_returning_empty_text_falls_back_instead_of_forcing_low_confidence():
    """An empty second opinion scores ~0 similarity against any real
    transcription, which would force a spurious 'low' -- a quality regression
    disguised as a safety downgrade. It must fall back instead."""
    ctx = MagicMock()
    ctx.state = {"ocr_image_bytes": b"fake-bytes", "ocr_image_mime_type": "image/png", "essay_id": "e1"}

    gemini_result = {"transcribed_text": "Homework helps students.", "confidence": "high", "uncertain_segments": []}
    with (
        patch("eduagent.nodes.ocr.generate_json_from_image", return_value=gemini_result),
        patch("eduagent.nodes.ocr.generate_text_from_image", return_value="   "),
    ):
        result = asyncio.run(multimodal_ocr(ctx))

    assert result["confidence"] == "high"
    assert result["cross_check_model"] == "gemini-fallback"


def test_cross_check_toggle_off_never_calls_gemma():
    """EDUAGENT_OCR_CROSS_CHECK_GEMMA=false is the documented rollback lever
    for ADR-028's abort conditions. It has to actually stop the call, not just
    relabel the result."""
    ctx = MagicMock()
    ctx.state = {"ocr_image_bytes": b"fake-bytes", "ocr_image_mime_type": "image/png", "essay_id": "e1"}

    gemini_result = {"transcribed_text": "Homework helps students.", "confidence": "high", "uncertain_segments": []}
    with (
        patch("eduagent.nodes.ocr.GEMINI", replace(GEMINI, ocr_cross_check_with_gemma=False)),
        patch("eduagent.nodes.ocr.generate_json_from_image", return_value=gemini_result) as gemini,
        patch("eduagent.nodes.ocr.generate_text_from_image") as gemma,
    ):
        result = asyncio.run(multimodal_ocr(ctx))

    gemma.assert_not_called()
    assert gemini.call_count == 2
    assert result["cross_check_model"] == "gemini-fallback"


def test_gemma_location_is_pinned_global_not_inherited_from_env():
    """Gemma 4 MaaS is served only from the `global` endpoint; a regional one
    answers 400 FAILED_PRECONDITION. If this ever tracked
    GOOGLE_CLOUD_LOCATION, a regional deploy would silently disable the
    cross-MODEL check while every test and dashboard still looked green."""
    assert GEMINI.gemma_location == "global"


def test_cross_model_and_same_model_use_different_thresholds():
    """The two comparisons have measurably different distributions (Wave 24,
    12 real samples): legible images score 0.989-1.000 same-model but only
    0.729-0.998 cross-model. One shared threshold is therefore wrong for one
    of them -- 0.75 sits inside the cross-model legible cluster and fires on
    readable essays."""
    from eduagent.nodes.ocr import _CONSISTENCY_SIMILARITY_THRESHOLD, _CROSS_MODEL_SIMILARITY_THRESHOLD

    assert _CROSS_MODEL_SIMILARITY_THRESHOLD < _CONSISTENCY_SIMILARITY_THRESHOLD


def test_cross_model_genuine_disagreement_still_downgrades():
    """The recalibration must not blunt the check itself: when the two models
    read genuinely different content (measured 0.265-0.294 on the two
    unreadable samples), confidence must still drop to low."""
    ctx = MagicMock()
    ctx.state = {"ocr_image_bytes": b"fake-bytes", "ocr_image_mime_type": "image/png", "essay_id": "e1"}

    with (
        patch("eduagent.nodes.ocr.generate_json_from_image", return_value={"transcribed_text": "Homework helps students focus in class every day.", "confidence": "high", "uncertain_segments": []}),
        patch("eduagent.nodes.ocr.generate_text_from_image", return_value="Doomscrolling constantly never a break affecting sleep yes"),
    ):
        result = asyncio.run(multimodal_ocr(ctx))

    assert result["confidence"] == "low"
    assert any("inconsistent" in seg for seg in ctx.state["ocr_uncertain_segments"])


# Real transcription pair captured from `eval/test_images/tilted_essay_grading.jpg`
# during the Wave 24 ADR-028 measurement run. Similarity 0.709 -- squarely in
# the band between the cross-model threshold (0.50) and the same-model one
# (0.75), which is exactly where the false positives lived. Kept verbatim
# rather than hand-written: an earlier version of this test used invented
# strings that scored 0.921 and therefore stayed green under the very sabotage
# it was written to catch.
_REAL_GEMINI_PASS = "The Case Against Traditional Letter Grades\n\nThe traditional letter grading system (A-F) used in schools is outdated and fails to accurately reflect student learning. While intended to provide a metric for academic achievement, this rigid structure prioritizes compliance over true understanding and places excessive pressure on students, leading to anxiety rather than growth.\n\nFirstly, letter grades focus primarily on the final result, not the learning process. A single test or assignment often decide for an entire unit, ignoring the grade for an conceptual master, ignoring the effort, improvement, and conceptual mastery a student might achieve over time. This encourages students to 'grade grub' and cram for fostead thinking, fostering memorization instead of critical A student might fail an initial test but eventually master the material; however, their final grade does not reflect reflec"

_REAL_GEMMA_PASS = "The Case Against Traditional Letter Grades\nThe traditional letter grading system (A-F) used in schools is outdated and fails to accurately reflect student learning while intended to provide a metric for academic achievement, this rigid structure prioritizes compliance over true understanding and places excessive pressure on students, leading to anxiety rather than growth.\nFirstly, letter grades focus primarily on the final result, not the learning process. A single test or assignment often decide for an entire unit, ignoring the grade for an conceptual master, ignoring the effort, improvement, over time. conceptual mastery encourages students to student might 'grab' but nevertheless master this encourages students to 'memorization' instead of critical foster thinking. A student might fail an initial test but eventually master the material; however, their final grade does not reflect\nSeco"


def test_real_captured_pair_is_not_parked_by_the_cross_model_check():
    """The regression this recalibration exists to prevent, using measured
    text rather than a plausible-looking substitute. Both passes read the same
    essay; they differ in line breaks, punctuation and [[unclear]] policy."""
    ctx = MagicMock()
    ctx.state = {"ocr_image_bytes": b"fake-bytes", "ocr_image_mime_type": "image/jpeg", "essay_id": "e1"}

    with (
        patch("eduagent.nodes.ocr.generate_json_from_image", return_value={"transcribed_text": _REAL_GEMINI_PASS, "confidence": "high", "uncertain_segments": []}),
        patch("eduagent.nodes.ocr.generate_text_from_image", return_value=_REAL_GEMMA_PASS),
    ):
        result = asyncio.run(multimodal_ocr(ctx))

    assert result["confidence"] == "high"
    assert result["cross_check_model"] == GEMINI.gemma_model
