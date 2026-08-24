"""Unit tests for PHASE 6 multimodal ingestion: intake.py's image/text
routing detection (deterministic, zero LLM) and the OCR node's degrade path.
Mocks generate_json_from_image so this suite runs fast and offline -- the
real Vertex AI Vision behavior (verbatim transcription, low-confidence
flagging on a blurry image, anti-hallucination) was verified manually against
live Gemini during development; see TODO.md PHASE 6 for that evidence.
"""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

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

    # Both repeated calls agree -- the self-consistency cross-check should
    # not downgrade confidence.
    fake_result = {"transcribed_text": "Homework helps students.", "confidence": "high", "uncertain_segments": []}
    with patch("eduagent.nodes.ocr.generate_json_from_image", return_value=fake_result):
        result = asyncio.run(multimodal_ocr(ctx))

    assert result["transcribed_text"] == "Homework helps students."
    assert ctx.state["raw_input"] == "Homework helps students."
    assert ctx.state["ocr_confidence"] == "high"
    assert ctx.state["ocr_degraded"] is False


def test_multimodal_ocr_downgrades_confidence_when_repeated_calls_disagree():
    ctx = MagicMock()
    ctx.state = {"ocr_image_bytes": b"fake-bytes", "ocr_image_mime_type": "image/png", "essay_id": "e1"}

    # Simulates the real failure mode found during development: a badly
    # degraded image where the model confidently transcribes two DIFFERENT,
    # unrelated sentences across repeated calls -- self-reported "high"
    # confidence on both should not be trusted.
    first = {"transcribed_text": "Homework helps students focus.", "confidence": "high", "uncertain_segments": []}
    second = {"transcribed_text": "The weather today is sunny and warm.", "confidence": "high", "uncertain_segments": []}
    with patch("eduagent.nodes.ocr.generate_json_from_image", side_effect=[first, second]):
        result = asyncio.run(multimodal_ocr(ctx))

    assert result["confidence"] == "low"
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
