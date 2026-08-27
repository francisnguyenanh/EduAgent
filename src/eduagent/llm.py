"""Thin, shared wrapper around google-genai (Vertex AI backend).

Kept deliberately small: every agent node calls generate_json() with its own
prompt + schema. No shared conversation state between nodes here -- that
lives in Context.state, not in this client. This is what keeps the
Summarizer, Persona Selector, Debate Loop, and Cognitive Scorer as
independently testable calls rather than one giant multi-turn chat (the
single-prompt-chatbot failure mode from PROJECT_WIKI.md 9.1 principle #1).
"""

from __future__ import annotations

import functools
import json
import logging
import re
from typing import Any

from google import genai
from google.genai import errors as genai_errors
from tenacity import retry, retry_if_exception, retry_if_exception_type, stop_after_attempt, wait_exponential

from eduagent.config import GEMINI

_logger = logging.getLogger(__name__)

# PHASE 4: retry only what's actually transient. ServerError (5xx) and a
# malformed-JSON response are both worth retrying (the latter is often a
# one-off generation glitch despite response_schema); ClientError (4xx --
# e.g. a genuinely invalid request) is NOT retried because it will fail
# identically every time and just burns the retry budget.
_RETRYABLE_EXCEPTIONS = (genai_errors.ServerError, json.JSONDecodeError, TimeoutError, ConnectionError)

_llm_retry = retry(
    retry=retry_if_exception_type(_RETRYABLE_EXCEPTIONS),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    reraise=True,
)


class LLMGenerationError(RuntimeError):
    """Raised after all retries are exhausted. Callers (nodes) decide how to
    degrade gracefully -- this module never silently returns fake data."""


@functools.lru_cache(maxsize=1)
def _client() -> genai.Client:
    import os

    if GEMINI.use_vertexai:
        os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "True")
        os.environ.setdefault("GOOGLE_CLOUD_LOCATION", GEMINI.vertex_location)
    return genai.Client()


@functools.lru_cache(maxsize=1)
def _gemma_client() -> genai.Client:
    """ADR-028: a SECOND client, pinned to `global`, used only for Gemma.

    Deliberately not the shared `_client()` above: `GEMINI.vertex_location` is
    env-overridable, and Gemma 4 MaaS is served exclusively from the `global`
    endpoint (a regional endpoint answers 400 FAILED_PRECONDITION). Inheriting
    that env var would mean a deploy-time `GOOGLE_CLOUD_LOCATION=us-central1`
    silently disables the cross-model check while everything still looks fine.
    """
    return genai.Client(vertexai=True, location=GEMINI.gemma_location)


def _is_maas_queue_full(exc: BaseException) -> bool:
    """`429 RESOURCE_EXHAUSTED -- "The request queue is full."`"""
    return isinstance(exc, genai_errors.ClientError) and getattr(exc, "code", None) == 429


# ADR-028: 429 is retryable HERE and nowhere else in this module, and the
# distinction is the whole point. The module-wide policy above deliberately
# does NOT retry ClientError (4xx) because a 4xx against Gemini means a
# genuinely malformed request that will fail identically every time. A MaaS
# queue-full is the opposite failure: the identical request succeeds seconds
# later. Measured during Wave 24 integration testing -- 4 of 10 raw Gemma
# calls returned 429, yet with this retry every one of 6 test images
# transcribed successfully. Shared capacity is the cost of MaaS; treating its
# backpressure as a permanent error would make the model unusable.
_maas_retry = retry(
    retry=retry_if_exception_type(_RETRYABLE_EXCEPTIONS) | retry_if_exception(_is_maas_queue_full),
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    reraise=True,
)


_MARKDOWN_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def _strip_markdown_fence(text: str) -> str:
    """Defensive: response_mime_type='application/json' should return bare
    JSON, but strip a ```json ... ``` fence if the model wraps it anyway."""
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = _MARKDOWN_FENCE.sub("", stripped).strip()
    return stripped


def _config_with_thinking_budget(config: dict[str, Any], thinking_budget: int | None) -> dict[str, Any]:
    """ĐỢT 3 token-optimization: a fast structural-extraction call (OCR
    transcription, Summarizer's claim/evidence extraction) doesn't need the
    model's extended reasoning mode -- only nodes that pass an explicit
    `thinking_budget` (0 = off) get it added; every other caller (Scorer,
    Teacher Digest Synthesizer) is unaffected and keeps the model default."""
    if thinking_budget is None:
        return config
    return {**config, "thinking_config": {"thinking_budget": thinking_budget}}


@_llm_retry
def _generate_json_once(
    *, model: str, system_instruction: str, prompt: str, response_schema: dict[str, Any], thinking_budget: int | None = None
) -> dict[str, Any]:
    response = _client().models.generate_content(
        model=model,
        contents=prompt,
        config=_config_with_thinking_budget(
            {
                "system_instruction": system_instruction,
                "response_mime_type": "application/json",
                "response_schema": response_schema,
                "http_options": {"timeout": 30_000},
            },
            thinking_budget,
        ),
    )
    return json.loads(_strip_markdown_fence(response.text))


def generate_json(
    *,
    model: str,
    system_instruction: str,
    prompt: str,
    response_schema: dict[str, Any],
    thinking_budget: int | None = None,
) -> dict[str, Any]:
    """Calls Gemini with a forced JSON schema, returns the parsed dict.

    Retries transient failures (5xx, malformed JSON, timeout) up to 3 times
    with exponential backoff; after that, raises LLMGenerationError so the
    caller can degrade explicitly instead of silently returning fake data.

    `thinking_budget`: pass 0 to disable extended reasoning for a fast
    structural-extraction call; omit (None) to keep the model's default for
    calls that actually benefit from deeper reasoning (e.g. cognitive_scorer).
    """
    try:
        return _generate_json_once(
            model=model, system_instruction=system_instruction, prompt=prompt, response_schema=response_schema, thinking_budget=thinking_budget
        )
    except _RETRYABLE_EXCEPTIONS as exc:
        _logger.error("generate_json exhausted retries for model=%s: %s", model, exc)
        raise LLMGenerationError(f"generate_json failed after retries: {exc}") from exc


@_llm_retry
def _generate_json_from_image_once(
    *,
    model: str,
    system_instruction: str,
    prompt: str,
    image_bytes: bytes,
    image_mime_type: str,
    response_schema: dict[str, Any],
    thinking_budget: int | None = None,
) -> dict[str, Any]:
    from google.genai import types

    response = _client().models.generate_content(
        model=model,
        contents=[types.Part.from_bytes(data=image_bytes, mime_type=image_mime_type), types.Part.from_text(text=prompt)],
        config=_config_with_thinking_budget(
            {
                "system_instruction": system_instruction,
                "response_mime_type": "application/json",
                "response_schema": response_schema,
                # PHASE 6 real finding: a real phone-camera photo (multi-MB JPEG/PNG)
                # takes noticeably longer for Vertex AI to process than a text-only
                # prompt -- a real ~2.6MB test photo hit a 504 DEADLINE_EXCEEDED at
                # the same 30s budget generate_json() uses, even though the image
                # was perfectly legible. Multimodal calls get a longer budget.
                "http_options": {"timeout": 60_000},
            },
            thinking_budget,
        ),
    )
    return json.loads(_strip_markdown_fence(response.text))


def generate_json_from_image(
    *,
    model: str,
    system_instruction: str,
    prompt: str,
    image_bytes: bytes,
    image_mime_type: str,
    response_schema: dict[str, Any],
    thinking_budget: int | None = None,
) -> dict[str, Any]:
    """Multimodal variant of generate_json() -- PHASE 6 (Multimodal OCR): sends
    an image alongside the text prompt. Same retry/degrade contract: raises
    LLMGenerationError after exhausting retries rather than ever returning
    fabricated transcription."""
    try:
        return _generate_json_from_image_once(
            model=model,
            system_instruction=system_instruction,
            prompt=prompt,
            image_bytes=image_bytes,
            image_mime_type=image_mime_type,
            response_schema=response_schema,
            thinking_budget=thinking_budget,
        )
    except _RETRYABLE_EXCEPTIONS as exc:
        _logger.error("generate_json_from_image exhausted retries for model=%s: %s", model, exc)
        raise LLMGenerationError(f"generate_json_from_image failed after retries: {exc}") from exc


@_maas_retry
def _generate_text_from_image_once(*, model: str, prompt: str, image_bytes: bytes, image_mime_type: str) -> str:
    from google.genai import types

    response = _gemma_client().models.generate_content(
        model=model,
        contents=[types.Part.from_bytes(data=image_bytes, mime_type=image_mime_type), types.Part.from_text(text=prompt)],
        # Same 60s multimodal budget as generate_json_from_image (ADR-009).
        # No system_instruction and no response_schema on purpose -- see the
        # docstring below.
        config={"http_options": {"timeout": 60_000}},
    )
    return (response.text or "").strip()


def generate_text_from_image(*, model: str, prompt: str, image_bytes: bytes, image_mime_type: str) -> str:
    """ADR-028: multimodal call that returns PLAIN TEXT, used for the OCR
    cross-check's second opinion on a non-Gemini model.

    Why not reuse generate_json_from_image(): Wave 22 measured that Gemma
    ignores `response_schema` -- asked for `{resolved, reason}` it returned
    `{"answer": ...}`. Building on that would mean defensive parsing of a
    structure the model never promised. This function sidesteps the problem
    instead of patching it: the cross-check compares two transcriptions with
    `difflib` on raw strings, so no structure is needed at all. The instruction
    goes in the prompt rather than `system_instruction` for the same reason --
    fewer assumptions about what this model family honours.

    Raises LLMGenerationError after retries, exactly like its siblings, so the
    caller can fall back rather than fail the student's submission.
    """
    try:
        return _generate_text_from_image_once(model=model, prompt=prompt, image_bytes=image_bytes, image_mime_type=image_mime_type)
    except (*_RETRYABLE_EXCEPTIONS, genai_errors.APIError) as exc:
        _logger.error("generate_text_from_image exhausted retries for model=%s: %s", model, exc)
        raise LLMGenerationError(f"generate_text_from_image failed after retries: {exc}") from exc


@_llm_retry
def _generate_text_once(*, model: str, system_instruction: str, prompt: str) -> str:
    response = _client().models.generate_content(
        model=model,
        contents=prompt,
        config={"system_instruction": system_instruction, "http_options": {"timeout": 30_000}},
    )
    return response.text.strip()


def generate_text(*, model: str, system_instruction: str, prompt: str) -> str:
    """Same retry/degrade contract as generate_json -- raises LLMGenerationError
    after retries are exhausted rather than propagating the raw transient error."""
    try:
        return _generate_text_once(model=model, system_instruction=system_instruction, prompt=prompt)
    except _RETRYABLE_EXCEPTIONS as exc:
        _logger.error("generate_text exhausted retries for model=%s: %s", model, exc)
        raise LLMGenerationError(f"generate_text failed after retries: {exc}") from exc
