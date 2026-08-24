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
from typing import Any

from google import genai

from eduagent.config import GEMINI


@functools.lru_cache(maxsize=1)
def _client() -> genai.Client:
    import os

    if GEMINI.use_vertexai:
        os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "True")
        os.environ.setdefault("GOOGLE_CLOUD_LOCATION", GEMINI.vertex_location)
    return genai.Client()


def generate_json(
    *,
    model: str,
    system_instruction: str,
    prompt: str,
    response_schema: dict[str, Any],
) -> dict[str, Any]:
    """Calls Gemini with a forced JSON schema, returns the parsed dict.

    Raising on malformed output is intentional -- callers (nodes) decide how
    to degrade (Phase 4 adds retry/fallback), this function does not silently
    swallow errors.
    """
    response = _client().models.generate_content(
        model=model,
        contents=prompt,
        config={
            "system_instruction": system_instruction,
            "response_mime_type": "application/json",
            "response_schema": response_schema,
        },
    )
    return json.loads(response.text)


def generate_text(*, model: str, system_instruction: str, prompt: str) -> str:
    response = _client().models.generate_content(
        model=model,
        contents=prompt,
        config={"system_instruction": system_instruction},
    )
    return response.text.strip()
