"""Intake + Sanitizer -- pure function nodes, zero LLM calls.

Deterministic-first (PROJECT_WIKI.md 7.5.3 / 9.2 principle #3): stripping
injection attempts is a pattern-matching problem, not a reasoning problem, so
it stays a regex function node rather than an "ask the LLM to ignore bad
instructions" prompt (which is not reliable).
"""

from __future__ import annotations

import re
import uuid

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


@traced_node("intake")
async def intake(ctx: Context, node_input: str) -> dict:
    """Accepts raw essay text, stamps pipeline start. No mutation here --
    the raw input is preserved for the audit trail even after sanitizing.

    essay_id is minted here (not later in mutator) so it stays stable across
    the whole run -- if a node downstream retries, it doesn't mint a second
    id for what is logically the same essay attempt.
    """
    ctx.state["raw_input"] = node_input
    ctx.state["stage"] = "intake"
    ctx.state.setdefault("essay_id", str(uuid.uuid4()))
    return {"essay_text": node_input}


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
        # Audit signal only -- Phase 3/7 wires this into system_audit_logs.
        ctx.state.setdefault("audit_events", []).append(
            {"stage": "sanitizer", "event": "injection_attempt_stripped", "patterns": matches}
        )

    return {"sanitized_text": cleaned, "injection_flags": matches}
