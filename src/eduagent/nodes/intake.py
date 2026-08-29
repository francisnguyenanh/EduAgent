"""Intake + Sanitizer -- pure function nodes, zero LLM calls.

Deterministic-first (design principle #3, docs/eligibility_statement.md): stripping
injection attempts is a pattern-matching problem, not a reasoning problem, so
it stays a regex function node rather than an "ask the LLM to ignore bad
instructions" prompt (which is not reliable).
"""

from __future__ import annotations

import re
import uuid
from typing import Any

from google.adk.agents.context import Context

from eduagent.skills.language import detect_language
from eduagent.tracing import traced_node

# Patterns aimed at overriding the system/agent instructions, not the essay's
# actual content. Deliberately conservative -- false positives here just mean
# a phrase gets redacted, not that the whole essay is rejected.
_INJECTION_PATTERNS = [
    re.compile(r"ignore (all |any |previous |prior |above ){1,3}instructions?", re.IGNORECASE),
    re.compile(r"disregard (all |any |previous |prior |above ){1,3}(instructions?|prompts?)", re.IGNORECASE),
    re.compile(r"you are now\b", re.IGNORECASE),
    re.compile(r"new (system )?instructions?:", re.IGNORECASE),
    re.compile(r"act as (if you (are|were)|an?)\b.{0,40}(instead|now)", re.IGNORECASE),
    re.compile(r"</?system>", re.IGNORECASE),
    re.compile(r"</?(instructions?|prompt)>", re.IGNORECASE),
    re.compile(r"</?user>", re.IGNORECASE),
    re.compile(r"</?assistant>", re.IGNORECASE),
    re.compile(r"reveal (your|the) (system )?prompt", re.IGNORECASE),
    re.compile(r"what (is|was) your (original |system ){0,2}(prompt|instructions?)\b", re.IGNORECASE),
    re.compile(r"print (your|the) (system )?prompt", re.IGNORECASE),
]

_REDACTION_MARKER = "[redacted: possible instruction-override attempt]"


def strip_injection_attempts(text: str) -> tuple[str, list[str]]:
    """Returns (cleaned_text, list of matched pattern strings) for audit logging."""
    matches: list[str] = []
    cleaned = text
    for pattern in _INJECTION_PATTERNS:
        found = pattern.findall(cleaned)
        if found:
            matches.append(pattern.pattern)
        cleaned = pattern.sub(_REDACTION_MARKER, cleaned)
    return cleaned, matches


def _extract_essay_input(node_input: Any) -> tuple[str, bytes | None, str | None]:
    """Returns (text, image_bytes, image_mime_type).

    Multimodal ingestion: node_input is annotated as ``Any``, not
    ``str`` -- FunctionNode only auto-coerces types.Content -> str when the
    annotation expects str (see google.adk.workflow.FunctionNode docstring),
    which would silently DROP an image part before intake ever saw it. A
    plain string caller (existing tests, run_debug()) still works unchanged;
    a types.Content with an inline image Part is detected here instead.
    """
    if isinstance(node_input, str):
        return node_input, None, None

    parts = getattr(node_input, "parts", None) or []
    text_parts: list[str] = []
    image_bytes: bytes | None = None
    image_mime_type: str | None = None
    for part in parts:
        text = getattr(part, "text", None)
        if text:
            text_parts.append(text)
        inline_data = getattr(part, "inline_data", None)
        mime_type = getattr(inline_data, "mime_type", None) if inline_data else None
        if image_bytes is None and mime_type and mime_type.startswith("image/"):
            image_bytes = inline_data.data
            image_mime_type = mime_type
    return "\n".join(text_parts), image_bytes, image_mime_type


@traced_node("intake")
async def intake(ctx: Context, node_input: Any) -> dict:
    """Accepts raw essay text OR a photo of a handwritten essay, stamps
    pipeline start, and routes to the Multimodal OCR node when an
    image is present -- a text-only essay never touches OCR or costs a
    Vision call. No mutation of the text itself here -- it's preserved for
    the audit trail even after sanitizing.

    essay_id is minted here (not later in mutator) so it stays stable across
    the whole run -- if a node downstream retries, it doesn't mint a second
    id for what is logically the same essay attempt.
    """
    text, image_bytes, image_mime_type = _extract_essay_input(node_input)
    if text and ("docs.google.com/document" in text or "drive.google.com" in text):
        from eduagent.integrations.gdocs import extract_gdoc_id, fetch_gdoc_text

        doc_id = extract_gdoc_id(text)
        if doc_id:
            try:
                gdoc_text = fetch_gdoc_text(text)
                ctx.state["gdoc_url"] = text
                ctx.state["gdoc_id"] = doc_id
                text = gdoc_text
            except Exception as exc:
                ctx.state.setdefault("audit_events", []).append(
                    {"stage": "intake", "event": "gdoc_fetch_failed", "error": str(exc)}
                )

    ctx.state["stage"] = "intake"
    ctx.state.setdefault("essay_id", str(uuid.uuid4()))
    ctx.state["raw_input"] = text

    if image_bytes:
        ctx.state["ocr_image_bytes"] = image_bytes
        ctx.state["ocr_image_mime_type"] = image_mime_type
        ctx.route = "image"
        return {"essay_text": text, "has_image": True}

    ctx.route = "text"
    return {"essay_text": text, "has_image": False}


@traced_node("sanitizer")
async def sanitizer(ctx: Context) -> dict:
    raw = ctx.state.get("raw_input", "")
    cleaned, matches = strip_injection_attempts(raw)

    ctx.state["stage"] = "sanitizer"
    ctx.state["sanitized_text"] = cleaned
    ctx.state["injection_flags"] = matches
    # Detected once here (not per-node) so every downstream LLM node answers
    # in the SAME language for one essay, rather than each node guessing
    # independently and possibly disagreeing with each other.
    ctx.state["language"] = detect_language(cleaned)

    if matches:
        # Audit signal only -- surfaced into system_audit_logs downstream.
        ctx.state.setdefault("audit_events", []).append(
            {"stage": "sanitizer", "event": "injection_attempt_stripped", "patterns": matches}
        )

    return {"sanitized_text": cleaned, "injection_flags": matches}
