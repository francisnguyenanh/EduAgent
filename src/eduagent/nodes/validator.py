"""Challenge Validator -- pure function node, ZERO LLM calls.

PROJECT_WIKI.md 9.1 principle #2: the Validator must be independent in logic
path from the Debate Agent it checks -- if the same LLM call that generates a
question also judges the question, the risk you're checking for IS the risk.
This module never imports eduagent.llm.

Checks:
  - answer-leak: the agent's question must not contain the answer/solution.
  - single-question rule: exactly one Socratic question, not several.
  - length guardrail: not a wall of text, not a one-word non-answer.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from eduagent.config import VALIDATOR

# Phrases that indicate the "question" has slipped into giving an answer
# instead of asking one. Deliberately narrow -- false negatives here are
# safer than blocking legitimate Socratic prompts that happen to explain a
# concept the student already raised. Bilingual (EN + VI) since essays and
# debate turns may be in either language.
_ANSWER_LEAK_PATTERNS = [
    re.compile(r"\bthe (correct|right) answer is\b", re.IGNORECASE),
    re.compile(r"\byou should (write|say|conclude|argue) that\b", re.IGNORECASE),
    re.compile(r"\bhere('s| is) (a|the) (better|corrected|revised) (version|argument|sentence)\b", re.IGNORECASE),
    re.compile(r"\blet me (fix|rewrite|correct) (that|this|it) for you\b", re.IGNORECASE),
    re.compile(r"\binstead,? (write|say):", re.IGNORECASE),
    re.compile(r"câu trả lời đúng là", re.IGNORECASE),
    re.compile(r"bạn nên (viết|nói|kết luận) là", re.IGNORECASE),
    re.compile(r"đây là (câu|đoạn|bài) (viết lại|sửa lại|đúng)", re.IGNORECASE),
    re.compile(r"thay vì vậy,? hãy viết:?", re.IGNORECASE),
]

_QUESTION_MARK = re.compile(r"\?")
_QUOTED_SPAN = re.compile(r'"[^"]*"|\'[^\']*\'')


def _count_questions_outside_quotes(text: str) -> int:
    """Counts '?' but ignores any that fall inside a quoted span, so an agent
    quoting the student's own question back (e.g. 'You said "why does it
    matter?" -- but what about...') isn't flagged as asking two questions."""
    without_quotes = _QUOTED_SPAN.sub("", text)
    return len(_QUESTION_MARK.findall(without_quotes))


@dataclass
class ValidationResult:
    passed: bool
    violations: list[str] = field(default_factory=list)


def validate_debate_turn(text: str) -> ValidationResult:
    violations: list[str] = []

    for pattern in _ANSWER_LEAK_PATTERNS:
        if pattern.search(text):
            violations.append(f"answer_leak:{pattern.pattern}")

    question_count = _count_questions_outside_quotes(text)
    if question_count == 0:
        violations.append("single_question_rule:no_question_found")
    elif question_count > 1:
        violations.append("single_question_rule:multiple_questions_found")

    if len(text) < VALIDATOR.min_response_chars:
        violations.append(f"length:too_short:{len(text)}<{VALIDATOR.min_response_chars}")
    if len(text) > VALIDATOR.max_response_chars:
        violations.append(f"length:too_long:{len(text)}>{VALIDATOR.max_response_chars}")

    return ValidationResult(passed=not violations, violations=violations)


# --- Graph node wrapper -----------------------------------------------------

from google.adk.agents.context import Context  # noqa: E402

from eduagent.tracing import traced_node  # noqa: E402


@traced_node("challenge_validator")
async def challenge_validator(ctx: Context) -> dict:
    """Validates the full debate transcript produced by debate_loop.

    Per-turn validation already happens inside debate_loop's regenerate loop;
    this node is the final independent check before scoring, so a bug in the
    inline check can't silently let a bad transcript through.
    """
    ctx.state["stage"] = "challenge_validator"
    turns = ctx.state.get("debate_turns", [])

    all_violations: list[str] = []
    for turn in turns:
        result = validate_debate_turn(turn.get("question", ""))
        if not result.passed:
            all_violations.extend(f"turn_{turn.get('turn')}:{v}" for v in result.violations)

    validation_result = {"passed": not all_violations, "violations": all_violations}
    ctx.state["validation_result"] = validation_result
    return validation_result
