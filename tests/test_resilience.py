"""Unit tests for PHASE 4 resilience: retry-then-degrade behavior across
llm.py and every node/aggregator step that calls it. All external calls are
mocked -- these must run fast and offline, unlike the real outage they
simulate.
"""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

import pytest
from google.genai import errors as genai_errors

from eduagent.llm import LLMGenerationError, generate_json, generate_text


def _server_error(code: int = 503) -> genai_errors.ServerError:
    return genai_errors.ServerError(code, {"error": {"message": "unavailable"}})


def test_generate_json_retries_then_succeeds():
    good_response = MagicMock(text='{"ok": true}')
    with patch("eduagent.llm._client") as mock_client:
        mock_client.return_value.models.generate_content.side_effect = [
            _server_error(),
            _server_error(),
            good_response,
        ]
        result = generate_json(model="m", system_instruction="s", prompt="p", response_schema={})
    assert result == {"ok": True}
    assert mock_client.return_value.models.generate_content.call_count == 3


def test_generate_json_raises_llm_generation_error_after_exhausting_retries():
    with patch("eduagent.llm._client") as mock_client:
        mock_client.return_value.models.generate_content.side_effect = _server_error()
        with pytest.raises(LLMGenerationError):
            generate_json(model="m", system_instruction="s", prompt="p", response_schema={})
    assert mock_client.return_value.models.generate_content.call_count == 3


def test_generate_text_degrades_to_llm_generation_error():
    with patch("eduagent.llm._client") as mock_client:
        mock_client.return_value.models.generate_content.side_effect = _server_error()
        with pytest.raises(LLMGenerationError):
            generate_text(model="m", system_instruction="s", prompt="p")


def test_summarizer_degrades_to_empty_summary_on_llm_outage():
    from eduagent.nodes.summarizer import summarizer

    ctx = MagicMock()
    ctx.state = {"sanitized_text": "a real essay with actual content"}

    with patch("eduagent.nodes.summarizer.generate_json", side_effect=LLMGenerationError("down")):
        result = asyncio.run(summarizer(ctx))

    assert result == {"main_claim": "", "claims": [], "evidence": [], "fallacies_draft": []}
    assert ctx.state["summary_degraded"] is True


def test_scorer_degrades_and_flags_instead_of_faking_a_score():
    from eduagent.nodes.scorer import cognitive_scorer

    ctx = MagicMock()
    ctx.state = {"sanitized_text": "a real essay", "summary": {}, "debate_turns": []}

    with patch("eduagent.nodes.scorer.generate_json", side_effect=LLMGenerationError("down")):
        result = asyncio.run(cognitive_scorer(ctx))

    assert all(v == 0 for v in result.values())
    assert ctx.state["scores_degraded"] is True


def test_scorer_stores_student_feedback_on_success():
    from eduagent.nodes.scorer import cognitive_scorer

    ctx = MagicMock()
    ctx.state = {"sanitized_text": "a real essay", "summary": {}, "debate_turns": [], "language": "en"}

    fake_result = {
        "scores": {"logical_coherence": 5, "evidence_quality": 5, "counterargument_handling": 5, "scope_awareness": 5},
        "rationale": {k: "" for k in ("logical_coherence", "evidence_quality", "counterargument_handling", "scope_awareness")},
        "student_feedback": "Nice use of evidence! Next time, address the counterargument directly.",
    }
    with patch("eduagent.nodes.scorer.generate_json", return_value=fake_result):
        asyncio.run(cognitive_scorer(ctx))

    assert ctx.state["student_feedback"] == "Nice use of evidence! Next time, address the counterargument directly."
    assert ctx.state["scores_degraded"] is False


def test_debate_loop_falls_back_to_persona_question_on_llm_outage():
    from eduagent.nodes.debate import debate_loop

    ctx = MagicMock()
    ctx.state = {"persona": "skeptic", "sanitized_text": "essay", "summary": {}, "student_responses": [], "prior_weakness_taxonomy": []}

    with patch("eduagent.nodes.debate.generate_text", side_effect=LLMGenerationError("down")):
        result = asyncio.run(debate_loop(ctx))

    assert len(result["debate_turns"]) == 1
    assert "evidence" in result["debate_turns"][0]["question"].lower()  # the skeptic fallback question


def test_digest_falls_back_to_plain_rendering_on_llm_outage():
    from eduagent.aggregator.digest import synthesize_digest

    ranked = [{"student_id": "stu_1", "name": "A", "priority": 5.0, "breakdown": {}, "reason": {"stuck_streak_count": 3}}]

    with patch("eduagent.aggregator.digest.generate_json", side_effect=LLMGenerationError("down")):
        digest = asyncio.run(synthesize_digest(ranked_students=ranked, common_fallacies=["hasty generalization"]))

    assert "stu_1" in digest["priority_students"][0]["student_id"]
    assert "hasty generalization" in digest["class_wide_pattern"]
    assert "unavailable" in digest["headline"].lower()


def test_mutator_parks_pending_essay_instead_of_writing_fake_score():
    from eduagent.nodes.mutator import profile_mutator

    ctx = MagicMock()
    ctx.state = {
        "student_id": "stu_1",
        "class_id": "c1",
        "persona": "skeptic",
        "summary": {"fallacies_draft": []},
        "scores": {"logical_coherence": 0, "evidence_quality": 0, "counterargument_handling": 0, "scope_awareness": 0},
        "scores_degraded": True,
        "validation_result": {"passed": True},
        "essay_id": "e1",
        "raw_input": "raw",
        "sanitized_text": "clean",
    }

    with (
        patch("eduagent.nodes.mutator._park_pending_essay") as mock_park,
        patch("eduagent.nodes.mutator.apply_essay_result") as mock_apply,
    ):
        result = asyncio.run(profile_mutator(ctx))

    mock_park.assert_called_once()
    mock_apply.assert_not_called()
    assert result["pending_retry"] is True
    assert result["profile_after_mutation"] is None


def test_mutator_parks_pending_essay_when_ocr_confidence_is_low():
    from eduagent.nodes.mutator import profile_mutator

    ctx = MagicMock()
    ctx.state = {
        "student_id": "stu_1",
        "class_id": "c1",
        "persona": "skeptic",
        "summary": {"fallacies_draft": []},
        # Scores exist (scorer ran fine on whatever text OCR handed it) but
        # nodes/ocr.py's self-consistency check flagged the SOURCE TEXT
        # itself as unreliable -- scores computed on possibly-fabricated
        # text must not reach the permanent profile either.
        "scores": {"logical_coherence": 3, "evidence_quality": 2, "counterargument_handling": 1, "scope_awareness": 2},
        "scores_degraded": False,
        "ocr_confidence": "low",
        "ocr_uncertain_segments": ["[[ocr inconsistent across repeated attempts on this image -- treat transcription as unverified]]"],
        "validation_result": {"passed": True},
        "essay_id": "e1",
        "raw_input": "some hallucinated ocr text",
        "sanitized_text": "some hallucinated ocr text",
    }

    with (
        patch("eduagent.nodes.mutator._park_pending_essay") as mock_park,
        patch("eduagent.nodes.mutator.apply_essay_result") as mock_apply,
    ):
        result = asyncio.run(profile_mutator(ctx))

    mock_park.assert_called_once()
    assert mock_park.call_args.kwargs["reason"] == "ocr_confidence_low"
    mock_apply.assert_not_called()
    assert result["pending_retry"] is True
    assert result["profile_after_mutation"] is None


def test_mutator_forwards_student_feedback_to_apply_essay_result():
    from eduagent.nodes.mutator import profile_mutator

    ctx = MagicMock()
    ctx.state = {
        "student_id": "stu_1",
        "class_id": "c1",
        "persona": "skeptic",
        "summary": {"fallacies_draft": []},
        "scores": {"logical_coherence": 5, "evidence_quality": 5, "counterargument_handling": 5, "scope_awareness": 5},
        "student_feedback": "Great job citing your source!",
        "scores_degraded": False,
        "validation_result": {"passed": True},
        "essay_id": "e1",
        "raw_input": "raw",
        "sanitized_text": "clean",
    }

    with (
        patch("eduagent.nodes.mutator.apply_essay_result") as mock_apply,
        patch("eduagent.nodes.mutator.publish_essay_evaluated"),
    ):
        result = asyncio.run(profile_mutator(ctx))

    assert mock_apply.call_args.kwargs["student_feedback"] == "Great job citing your source!"
    assert result["student_feedback"] == "Great job citing your source!"
