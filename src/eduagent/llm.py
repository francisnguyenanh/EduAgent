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
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

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
